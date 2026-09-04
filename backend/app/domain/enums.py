"""Shared enums. String-valued so they serialize cleanly to JSON and Postgres."""

from __future__ import annotations

from enum import Enum


class Market(str, Enum):
    DAM = "dam"
    RTM = "rtm"


class PSPMode(str, Enum):
    GEN = "gen"
    PUMP = "pump"
    IDLE = "idle"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    DEGRADED = "degraded"  # completed, but with visible losses (failed adapters, dropped targets)
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStage(str, Enum):
    INGEST = "ingest"
    FORECAST = "forecast"
    OPTIMIZE = "optimize"
    VALIDATE = "validate"
    NARRATE = "narrate"


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class QualityFlag(str, Enum):
    OK = "ok"
    INTERPOLATED = "interpolated"  # A3: hourly->15-min points are flagged, never silent
    SUSPECT = "suspect"
    MISSING = "missing"


class ForecastTarget(str, Enum):
    DEMAND = "demand"
    PRICE = "price"
    INFLOW = "inflow"


class ScheduleSource(str, Enum):
    MILP = "milp"
    RL_ADJUSTED = "rl_adjusted"
    BASELINE = "baseline"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
