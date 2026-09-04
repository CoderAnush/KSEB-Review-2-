"""Typed views over configs/*.yaml. Pure parsing — no file I/O here.

Load the raw dict with app.config.load_config(name) and parse with .model_validate
or the from_config helpers below. Shared by optimization and twin so the MILP and
the simulator can never disagree about plant physics or tariffs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PSPSpec(BaseModel):
    # forbid unknown keys: a YAML key that reaches here without a field is a dead
    # key (parsed-but-ignored) — the exact failure class that hid storage_hours
    # and mode_switch_blocks for months. Fail loudly instead.
    model_config = ConfigDict(extra="forbid")

    name: str = "synthetic-psp-1"
    units: int = 2
    unit_mw: float = 60.0
    head_m: float = 660.0  # A2 provenance only (Idukki-seeded); energy-domain model reads no head
    eta_pump: float = 0.88
    eta_gen: float = 0.875
    usable_storage_mwh: float = 720.0
    storage_hours: float | None = None  # if set, must equal usable_storage_mwh / max_mw
    inflow_share: float = 0.03  # share of state inflow reaching the PSP pond (rest → hydro fleet)
    soc_init_frac: float = 0.5
    soc_min_frac: float = 0.05
    soc_max_frac: float = 1.0
    terminal_band_frac: tuple[float, float] = (0.45, 0.55)
    min_gen_mw: float = 10.0
    min_pump_mw: float = 40.0
    ramp_mw_per_block: float = 120.0

    @property
    def max_mw(self) -> float:
        return self.units * self.unit_mw

    @property
    def eta_rt(self) -> float:
        return self.eta_pump * self.eta_gen

    @property
    def soc_init_mwh(self) -> float:
        return self.soc_init_frac * self.usable_storage_mwh

    @property
    def soc_min_mwh(self) -> float:
        return self.soc_min_frac * self.usable_storage_mwh

    @property
    def soc_max_mwh(self) -> float:
        return self.soc_max_frac * self.usable_storage_mwh

    @property
    def terminal_band_mwh(self) -> tuple[float, float]:
        lo, hi = self.terminal_band_frac
        return lo * self.usable_storage_mwh, hi * self.usable_storage_mwh

    def pond_inflow_mwh(self, total_inflow_mwh: float) -> float:
        """The slice of a block's state inflow that lands in the PSP upper pond."""
        return self.inflow_share * total_inflow_mwh

    @model_validator(mode="after")
    def _storage_hours_consistent(self) -> PSPSpec:
        # storage_hours is documentation unless it disagrees with the authoritative
        # usable_storage_mwh — then the config is self-contradictory and must not load
        if self.storage_hours is not None and self.max_mw > 0:
            implied = self.storage_hours * self.max_mw
            if abs(implied - self.usable_storage_mwh) > 1e-6 * max(self.usable_storage_mwh, 1.0):
                raise ValueError(
                    f"storage_hours ({self.storage_hours} h x {self.max_mw} MW = {implied} MWh) "
                    f"contradicts usable_storage_mwh ({self.usable_storage_mwh} MWh)"
                )
        return self

    @classmethod
    def from_config(cls, cfg: dict) -> PSPSpec:
        plant = dict(cfg.get("plant", {}))
        ops = dict(cfg.get("operations", {}))
        band = ops.pop("terminal_band_frac", [0.45, 0.55])
        return cls(**plant, **ops, terminal_band_frac=(band[0], band[1]))


class HydroStation(BaseModel):
    name: str
    max_mw: float
    min_mw: float = 0.0


class HydroFleet(BaseModel):
    stations: list[HydroStation] = Field(default_factory=list)
    daily_energy_budget_mwh: float = 0.0
    cost_inr_per_kwh: float = 0.0  # KSEB booked internal-generation rate (ADR-14)

    @property
    def max_mw(self) -> float:
        return sum(s.max_mw for s in self.stations)

    @property
    def rate_inr_per_mwh(self) -> float:
        return self.cost_inr_per_kwh * 1000.0

    @classmethod
    def from_config(cls, cfg: dict) -> HydroFleet:
        return cls.model_validate(cfg.get("hydro", {}))


class PPATranche(BaseModel):
    name: str
    rate_inr_per_kwh: float
    max_mw: float
    must_run_mw: float = 0.0

    @property
    def rate_inr_per_mwh(self) -> float:
        return self.rate_inr_per_kwh * 1000.0


class MarketLimits(BaseModel):
    price_cap_inr_per_kwh: float = 10.0
    price_floor_inr_per_kwh: float = 0.0
    max_buy_mw: float = 1500.0
    max_sell_mw: float = 800.0


class PPAStack(BaseModel):
    tranches: list[PPATranche]
    market: MarketLimits = Field(default_factory=MarketLimits)

    @model_validator(mode="after")
    def _sorted_merit(self) -> PPAStack:
        self.tranches.sort(key=lambda t: t.rate_inr_per_kwh)
        return self

    @classmethod
    def from_config(cls, cfg: dict) -> PPAStack:
        return cls.model_validate(cfg)


class FrequencyBand(BaseModel):
    freq_below: float
    over_drawal_mult: float
    under_drawal_mult: float


class DSMConfig(BaseModel):
    normal_rate_source: str = "daily_wap_acp"
    fallback_rate_inr_per_kwh: float = 4.0
    free_band_frac: float = 0.01
    max_deviation_frac: float = 0.10
    frequency_multipliers: list[FrequencyBand] = Field(default_factory=list)
    expected_frequency_band: int = 3  # 1-indexed into frequency_multipliers
    # default matches configs/dsm.yaml — a code path that forgets from_config()
    # must not silently run a tighter (or looser) penalty gate than the shipped config
    daily_penalty_cap_inr: float = 6_000_000.0
    intra_state_enabled: bool = False
    intra_state_multiplier: float = 1.0

    @property
    def expected_band(self) -> FrequencyBand:
        if not self.frequency_multipliers:
            return FrequencyBand(freq_below=99.0, over_drawal_mult=1.0, under_drawal_mult=1.0)
        idx = min(max(self.expected_frequency_band - 1, 0), len(self.frequency_multipliers) - 1)
        return self.frequency_multipliers[idx]

    @classmethod
    def from_config(cls, cfg: dict) -> DSMConfig:
        nr = cfg.get("normal_rate", {})
        dev = cfg.get("deviation", {})
        intra = cfg.get("intra_state", {})
        return cls(
            normal_rate_source=nr.get("source", "daily_wap_acp"),
            fallback_rate_inr_per_kwh=nr.get("fallback_inr_per_kwh", 4.0),
            free_band_frac=dev.get("free_band_frac", 0.01),
            max_deviation_frac=dev.get("max_frac", 0.10),
            frequency_multipliers=[
                FrequencyBand.model_validate(b) for b in cfg.get("frequency_multipliers", [])
            ],
            expected_frequency_band=cfg.get("expected_frequency_band", 3),
            daily_penalty_cap_inr=cfg.get("daily_penalty_cap_inr", 2_500_000.0),
            intra_state_enabled=intra.get("enabled", False),
            intra_state_multiplier=intra.get("multiplier", 1.0),
        )


class BlockWindow(BaseModel):
    from_block: int
    to_block: int


class BaselineRule(BaseModel):
    pump_windows: list[BlockWindow] = Field(default_factory=list)
    gen_windows: list[BlockWindow] = Field(default_factory=list)
    pump_mw: float = 120.0
    gen_mw: float = 120.0
    buy_when_short: bool = True
    sell_when_surplus: bool = False

    @classmethod
    def from_config(cls, cfg: dict) -> BaselineRule:
        psp = cfg.get("psp", {})
        market = cfg.get("market", {})
        return cls(
            pump_windows=[BlockWindow.model_validate(w) for w in psp.get("pump_windows", [])],
            gen_windows=[BlockWindow.model_validate(w) for w in psp.get("gen_windows", [])],
            pump_mw=psp.get("pump_mw", 120.0),
            gen_mw=psp.get("gen_mw", 120.0),
            buy_when_short=market.get("buy_when_short", True),
            sell_when_surplus=market.get("sell_when_surplus", False),
        )
