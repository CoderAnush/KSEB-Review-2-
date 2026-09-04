"""Versioned model artifacts: pickle + meta.json under configs' registry_dir."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from app.config import load_config, resolve_configs_dir
from app.domain.entities import ForecastMetrics
from app.domain.enums import ForecastTarget
from app.logging_setup import get_logger

log = get_logger(__name__)


def _registry_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config("forecasting")
    raw = Path(cfg.get("registry_dir", "artifacts/models"))
    if not raw.is_absolute():
        raw = resolve_configs_dir().parent / raw  # anchor to repo root
    return raw


def save_artifact(
    target: ForecastTarget,
    model: Any,
    metrics: ForecastMetrics | None,
    cfg: dict[str, Any] | None = None,
) -> str:
    tdir = _registry_dir(cfg) / target.value
    tdir.mkdir(parents=True, exist_ok=True)
    version = len(list(tdir.glob("v*"))) + 1
    vdir = tdir / f"v{version:04d}"
    vdir.mkdir()
    with (vdir / "model.pkl").open("wb") as fh:
        pickle.dump(model, fh)
    meta = {
        "target": target.value,
        "model_name": getattr(model, "name", type(model).__name__),
        "version": f"v{version:04d}",
        "metrics": metrics.model_dump(mode="json") if metrics else None,
    }
    (vdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("model_saved", target=target.value, version=meta["version"])
    return str(vdir)


def load_latest(
    target: ForecastTarget, cfg: dict[str, Any] | None = None
) -> tuple[Any, dict[str, Any]] | None:
    tdir = _registry_dir(cfg) / target.value
    if not tdir.exists():
        return None
    versions = sorted(tdir.glob("v*"))
    if not versions:
        return None
    vdir = versions[-1]
    try:
        with (vdir / "model.pkl").open("rb") as fh:
            model = pickle.load(fh)
        meta = json.loads((vdir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, pickle.UnpicklingError) as exc:
        log.error("model_load_failed", target=target.value, version=vdir.name, error=str(exc))
        return None
    return model, meta
