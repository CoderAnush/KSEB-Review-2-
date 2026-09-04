"""Idukki stage–storage curve and head-dependent energy accounting (ADR-12).

Sourced from the CWC 2019 SRS survey (configs/reservoir_idukki.yaml carries the
citations). Pure functions over a piecewise-linear elevation–capacity curve:

    level  <->  live volume        (monotone interpolation, both directions)
    head(level) = level − tailwater EL
    E_retrievable(level) = η · ρ·g · ∫ head dV / 3.6e9   [MWh]

The integral form matters: assuming the FRL head for all stored water OVER-states
energy (head falls as the reservoir draws down). `constant_head_error_pct`
quantifies exactly that bias — the audit Phase 2.5 question — and the test suite
benchmarks the integral against KSEB's 2,398 MU design-energy anchor.
"""

from __future__ import annotations

from bisect import bisect_right

from pydantic import BaseModel, Field, model_validator

RHO_G = 9810.0  # ρ·g for water, N/m³
J_PER_MWH = 3.6e9


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    """Piecewise-linear interpolation, clamped to the table's ends."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1
    frac = (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[i] + frac * (ys[i + 1] - ys[i])


class ReservoirCurve(BaseModel):
    """Dam-agnostic stage–storage curve. Required: the survey table (levels →
    cumulative live volume) plus FRL/MDDL/tailwater. Everything else — areas,
    gross capacity, historic-survey comparison, design-energy anchor — is
    optional so ANY dam dataset can load; benchmarks only run where anchors
    exist. Areas fall back to dV/dh (1 Mm² × 1 m = 1 MCM, so the units agree)."""

    name: str
    frl_m: float
    mddl_m: float
    tailwater_el_m: float
    eta_gen: float = 0.90
    installed_mw: float = 0.0
    gross_capacity_mcm: float | None = None
    live_capacity_mcm_1974: float | None = None
    design_annual_energy_gwh: float | None = None
    levels_m: list[float]
    live_mcm: list[float]
    areas_mm2: list[float] | None = None

    @model_validator(mode="after")
    def _table_sane(self) -> ReservoirCurve:
        n = len(self.levels_m)
        if len(self.live_mcm) != n:
            raise ValueError("levels/live arrays must have equal length")
        if self.areas_mm2 is not None and len(self.areas_mm2) != n:
            raise ValueError("areas array must match levels length (or be omitted)")
        if n < 3:
            raise ValueError("stage-storage table needs at least 3 points")
        for a, b in zip(self.levels_m, self.levels_m[1:]):
            if b <= a:
                raise ValueError(f"levels must be strictly increasing (got {a} -> {b})")
        for a, b in zip(self.live_mcm, self.live_mcm[1:]):
            if b <= a:
                raise ValueError(f"live capacity must be strictly increasing (got {a} -> {b})")
        if abs(self.levels_m[0] - self.mddl_m) > 0.01 or abs(self.levels_m[-1] - self.frl_m) > 0.01:
            raise ValueError("table must span exactly MDDL..FRL")
        if self.frl_m <= self.tailwater_el_m:
            raise ValueError("FRL must sit above the tailwater elevation")
        return self

    # ------------------------------------------------------------- curve lookups
    def volume_at_level(self, level_m: float) -> float:
        """Cumulative live storage (MCM) above MDDL at a water level."""
        return _interp(level_m, self.levels_m, self.live_mcm)

    def level_at_volume(self, live_mcm: float) -> float:
        """Water level (m) for a cumulative live storage (MCM) — inverse lookup."""
        return _interp(live_mcm, self.live_mcm, self.levels_m)

    def area_at_level(self, level_m: float) -> float:
        """Water-spread area (Mm²) at a level; derived as dV/dh when the dataset
        has no surveyed areas (numerically equal: 1 Mm² × 1 m = 1 MCM)."""
        if self.areas_mm2 is not None:
            return _interp(level_m, self.levels_m, self.areas_mm2)
        i = max(1, min(bisect_right(self.levels_m, level_m), len(self.levels_m) - 1))
        dv = self.live_mcm[i] - self.live_mcm[i - 1]
        dh = self.levels_m[i] - self.levels_m[i - 1]
        return dv / dh

    def gross_head_at(self, level_m: float) -> float:
        return level_m - self.tailwater_el_m

    @property
    def live_capacity_mcm(self) -> float:
        return self.live_mcm[-1]

    def fill_fraction(self, level_m: float) -> float:
        return self.volume_at_level(level_m) / self.live_capacity_mcm

    # ------------------------------------------------------- energy (integral form)
    def retrievable_energy_mwh(self, level_m: float, eta: float | None = None) -> float:
        """Electrical energy from drawing the live storage below `level_m` down to
        MDDL: η·ρ·g·∫ head dV, trapezoidal over the survey table (exact for the
        piecewise-linear curve)."""
        eta = self.eta_gen if eta is None else eta
        level_m = min(max(level_m, self.mddl_m), self.frl_m)
        v_top = self.volume_at_level(level_m)
        joules = 0.0
        prev_level, prev_v = self.levels_m[0], self.live_mcm[0]
        for lvl, v in zip(self.levels_m[1:], self.live_mcm[1:]):
            seg_top_level = min(lvl, level_m)
            seg_top_v = min(v, v_top)
            if seg_top_v <= prev_v:
                break
            mid_head = (prev_level + seg_top_level) / 2.0 - self.tailwater_el_m
            joules += RHO_G * (seg_top_v - prev_v) * 1e6 * mid_head
            prev_level, prev_v = seg_top_level, seg_top_v
        return eta * joules / J_PER_MWH

    def constant_head_error_pct(self, eta: float | None = None) -> float:
        """How much a constant-FRL-head model over-states full-pond energy vs the
        head integral (audit Phase 2.5: 'if constant, quantify the error')."""
        eta = self.eta_gen if eta is None else eta
        e_true = self.retrievable_energy_mwh(self.frl_m, eta)
        e_const = eta * RHO_G * self.live_capacity_mcm * 1e6 * self.gross_head_at(self.frl_m) / J_PER_MWH
        return (e_const - e_true) / e_true * 100.0

    # ------------------------------------------------------------------ loading
    @classmethod
    def from_config(cls, cfg: dict) -> ReservoirCurve:
        """Load any `configs/reservoir_<name>.yaml`. The operative table is
        `stage_storage` (generic); `stage_storage_2019` is accepted for the
        Idukki file's survey-year naming. Optional-anchor keys may be absent."""
        res = cfg.get("reservoir", {})
        ph = cfg.get("powerhouse", {})
        table = cfg.get("stage_storage") or cfg.get("stage_storage_2019") or {}
        areas = table.get("areas_mm2")
        tailwater = ph.get("tailwater_el_m")
        if tailwater is None and "gross_head_frl_m" in ph:
            tailwater = res["frl_m"] - ph["gross_head_frl_m"]
        return cls(
            name=res.get("name", "reservoir"),
            frl_m=res["frl_m"],
            mddl_m=res["mddl_m"],
            tailwater_el_m=tailwater,
            eta_gen=ph.get("eta_gen", 0.90),
            installed_mw=ph.get("installed_mw", 0.0),
            gross_capacity_mcm=res.get("gross_capacity_mcm"),
            live_capacity_mcm_1974=res.get("live_capacity_mcm_1974"),
            design_annual_energy_gwh=ph.get("design_annual_energy_gwh"),
            levels_m=list(table["levels_m"]),
            areas_mm2=list(areas) if areas is not None else None,
            live_mcm=list(table["live_mcm"]),
        )


class SedimentationBenchmark(BaseModel):
    """1974-vs-2019 curve drift, for research reporting (CWC Table 4/5)."""

    levels_m: list[float] = Field(default_factory=list)
    live_mcm_1974: list[float] = Field(default_factory=list)
    live_mcm_2019: list[float] = Field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: dict) -> SedimentationBenchmark:
        t74 = cfg.get("stage_storage_1974") or cfg.get("stage_storage_original") or {}
        t19 = cfg.get("stage_storage") or cfg.get("stage_storage_2019") or {}
        old, new = list(t74.get("live_mcm", [])), list(t19.get("live_mcm", []))
        if len(old) != len(new):  # comparison survey absent or incompatible — no benchmark
            old = []
        return cls(
            levels_m=list(t19.get("levels_m", [])),
            live_mcm_1974=old,
            live_mcm_2019=new,
        )

    @property
    def available(self) -> bool:
        return bool(self.live_mcm_1974)

    @property
    def capacity_loss_pct(self) -> float:
        if not self.available:
            return 0.0
        return (self.live_mcm_1974[-1] - self.live_mcm_2019[-1]) / self.live_mcm_1974[-1] * 100.0
