"""Core Pydantic entities shared across all modules. Zero I/O."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import (
    AlertSeverity,
    ApprovalDecision,
    ForecastTarget,
    QualityFlag,
    RecommendationStatus,
    ScheduleSource,
)

# --------------------------------------------------------------------------- time series


class SeriesPoint(BaseModel):
    series_id: str
    ts: datetime  # IST-aware (domain.timeblocks.IST)
    value: float
    quality: QualityFlag = QualityFlag.OK
    # provenance, e.g. "SyntheticAdapter:demand" — synthetic vs real must be
    # distinguishable downstream (audit fix)
    source: str = ""


class DataQualityReport(BaseModel):
    source: str
    series_id: str
    start: datetime | None = None
    end: datetime | None = None
    n_points: int = 0
    n_missing: int = 0
    n_interpolated: int = 0
    n_suspect: int = 0
    error: str = ""  # non-empty ⇒ the adapter fetch failed and this source is absent

    @property
    def ok_frac(self) -> float:
        good = self.n_points - self.n_suspect - self.n_missing
        return good / self.n_points if self.n_points else 0.0


# --------------------------------------------------------------------------- forecasting


class ForecastSet(BaseModel):
    """One target, one delivery day (D+1), all 96 blocks, quantile bands.

    `quantiles` maps labels like "p10"/"p50"/"p90" to lists of length blocks_per_day.
    """

    target: ForecastTarget
    day: date
    quantiles: dict[str, list[float]]
    model_name: str = ""
    model_version: str = ""
    issued_at: datetime | None = None

    def p50(self) -> list[float]:
        return self.quantiles["p50"]


class ForecastMetrics(BaseModel):
    target: ForecastTarget
    model_name: str
    mape_pct: float | None = None
    mae: float | None = None
    pinball_p10: float | None = None
    pinball_p90: float | None = None
    n_folds: int = 0
    detail: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- dispatch


class DispatchBlock(BaseModel):
    block: int  # 1..96
    hydro_gen_mw: float = 0.0
    psp_gen_mw: float = 0.0
    psp_pump_mw: float = 0.0
    market_buy_mw: float = 0.0
    market_sell_mw: float = 0.0
    ppa_drawal_mw: float = 0.0  # total across tranches
    soc_mwh: float = 0.0  # PSP storage at END of block
    spill_mwh: float = 0.0
    deviation_mw: float = 0.0  # signed schedule deviation (DSM-exposed)


class SolverStats(BaseModel):
    solver: str
    status: str
    objective_inr: float
    gap: float | None = None
    wall_time_s: float = 0.0
    n_binaries: int = 0


class DispatchSchedule(BaseModel):
    day: date
    source: ScheduleSource
    blocks: list[DispatchBlock]
    objective_cost_inr: float = 0.0
    solver: SolverStats | None = None

    @property
    def n_blocks(self) -> int:
        return len(self.blocks)


class EnvelopeBlock(BaseModel):
    """Per-block RL deviation bounds derived from MILP slacks/headroom (ADR-6)."""

    block: int
    psp_net_min_mw: float  # net PSP power = gen - pump
    psp_net_max_mw: float
    market_net_min_mw: float  # net market position = buy - sell
    market_net_max_mw: float
    soc_min_mwh: float
    soc_max_mwh: float


class Envelope(BaseModel):
    day: date
    blocks: list[EnvelopeBlock]


# --------------------------------------------------------------------------- twin / validation


class GateResult(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class TwinKPIs(BaseModel):
    total_cost_inr: float
    dsm_penalty_inr: float = 0.0
    energy_served_mwh: float = 0.0
    spill_mwh: float = 0.0
    terminal_soc_mwh: float = 0.0
    baseline_cost_inr: float | None = None
    savings_vs_baseline_pct: float | None = None
    regret_vs_perfect_pct: float | None = None  # vs perfect-foresight re-solve


class ScenarioResult(BaseModel):
    name: str  # e.g. "price_p90", "inflow_p10"
    feasible: bool
    cost_inr: float
    dsm_penalty_inr: float = 0.0
    notes: str = ""


class ValidationReport(BaseModel):
    day: date
    schedule_source: ScheduleSource
    gates: list[GateResult]
    kpis: TwinKPIs
    scenarios: list[ScenarioResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.gates)


# --------------------------------------------------------------------------- agent layer


class Recommendation(BaseModel):
    day: date
    rank: int
    title: str
    action_summary: str  # deterministic, template-built
    expected_cost_inr: float
    expected_savings_inr: float
    savings_vs_baseline_pct: float
    risk_score: float  # 0 (safe) .. 1 (risky)
    robustness_score: float  # 0 .. 1, scenario-stress spread
    composite_score: float
    schedule_source: ScheduleSource
    narrative: str = ""  # LLM prose — numeric-guarded, never the source of numbers
    payload: dict[str, Any] = Field(default_factory=dict)  # exactly the numbers the LLM saw
    status: RecommendationStatus = RecommendationStatus.PENDING


class RiskAlert(BaseModel):
    severity: AlertSeverity
    kind: str  # e.g. "price_spike", "low_soc", "dsm_exposure"
    message: str
    from_block: int | None = None
    to_block: int | None = None


class ThumbRule(BaseModel):
    text: str
    evidence: str = ""


class ApprovalRecord(BaseModel):
    recommendation_id: int
    decision: ApprovalDecision
    note: str  # mandatory
    username: str
    decided_at: datetime
