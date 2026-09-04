"""structlog JSON logging (ADR/observability). Import and call once at process start.

Named ``logging_setup`` (roadmap lists ``logging.py``) to avoid tooling confusion
with the stdlib module of the same name.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import get_settings


def configure_logging(level: str | None = None) -> None:
    lvl = getattr(logging, (level or get_settings().log_level).upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=lvl)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(lvl),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
