"""Application settings and versioned YAML config loading.

Every research-report assumption (A1-A15) lives in ``configs/*.yaml`` (ADR-11).
This module is the only place that reads those files; callers get plain dicts
plus a short content hash so pipeline runs can record exactly which config
version produced them.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"

    db_url: str = "postgresql+asyncpg://kseb:kseb@localhost:5432/kseb_dss"
    db_url_sync: str = "postgresql+psycopg://kseb:kseb@localhost:5432/kseb_dss"

    jwt_secret: str = "dev-secret-change-me"
    jwt_expiry_minutes: int = 480

    anthropic_api_key: str = ""
    openrouter_api_key: str = ""

    configs_dir: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_configs_dir() -> Path:
    """Locate the repo-level ``configs/`` directory.

    Order: explicit setting / CONFIGS_DIR env var, then walk upwards from CWD
    (works from ``backend/``, repo root, or inside the Docker image where
    compose mounts ``/configs``).
    """
    settings = get_settings()
    if settings.configs_dir is not None:
        return Path(settings.configs_dir)
    env = os.environ.get("CONFIGS_DIR")
    if env:
        return Path(env)
    here = Path.cwd()
    for candidate in [here, *here.parents]:
        d = candidate / "configs"
        if (d / "adapters.yaml").exists():
            return d
    raise FileNotFoundError("configs/ directory not found; set CONFIGS_DIR or run from within the repository")


def load_config(name: str) -> dict[str, Any]:
    """Load ``configs/<name>.yaml`` as a dict. ``name`` is given without extension."""
    path = resolve_configs_dir() / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config {path} must be a YAML mapping")
    return data


def config_version(name: str) -> str:
    """Short content hash of a config file, recorded on every pipeline_run row."""
    path = resolve_configs_dir() / f"{name}.yaml"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def all_config_versions() -> dict[str, str]:
    return {p.stem: config_version(p.stem) for p in sorted(resolve_configs_dir().glob("*.yaml"))}


_DEFAULT_JWT_SECRET = "dev-secret-change-me"


def validate_security_settings(strict: bool | None = None) -> list[str]:
    """Refuse to run a prod-like deploy on the shipped JWT secret (audit fix).

    ``strict`` defaults to True whenever ``APP_ENV`` is not a dev/test value, so
    a production deploy that forgot to set JWT_SECRET fails at startup instead of
    signing tokens with a public secret (full auth forgery). Dev keeps working
    with a warning.
    """
    settings = get_settings()
    prod_like = settings.app_env.lower() not in ("dev", "development", "test", "local")
    if strict is None:
        strict = prod_like
    problems: list[str] = []
    if settings.jwt_secret == _DEFAULT_JWT_SECRET:
        problems.append("JWT_SECRET is the shipped default 'dev-secret-change-me' — tokens are forgeable")
    elif len(settings.jwt_secret.encode()) < 32:
        problems.append("JWT_SECRET is shorter than 32 bytes (RFC 7518 minimum for HS256)")
    if strict and problems:
        raise RuntimeError("; ".join(problems) + f" (APP_ENV={settings.app_env})")
    return problems


def validate_llm_secrets(strict: bool = False) -> list[str]:
    """Check that the active LLM provider's API key is present (fail-fast at startup).

    Returns a list of human-readable problems (empty == OK). When ``strict`` is
    True, raises ``RuntimeError`` instead — used by the API startup hook so a
    misconfigured prod deploy fails loudly rather than silently degrading every
    run to the template. Never raises for the deterministic template path: a
    missing key only disables the LLM, it never blocks the schedule.
    """
    problems: list[str] = []
    try:
        cfg = load_config("agent")
    except FileNotFoundError:
        return ["configs/agent.yaml not found"]
    settings = get_settings()
    active = str(cfg.get("provider", "anthropic"))
    key_attr = {"openrouter": "openrouter_api_key", "anthropic": "anthropic_api_key"}
    # The ACTIVE provider must have its key; failover keys are advisory.
    attr = key_attr.get(active)
    if attr and not getattr(settings, attr, ""):
        problems.append(
            f"active LLM provider '{active}' has no API key "
            f"({attr.upper()}) — narration will degrade to the deterministic template"
        )
    if strict and problems:
        raise RuntimeError("; ".join(problems))
    return problems
