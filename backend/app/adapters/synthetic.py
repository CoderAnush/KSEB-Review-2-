"""Seeded synthetic Kerala-shaped generators — unblocks every downstream phase offline.

Fully deterministic per (seed, timestamp): values come from sha256-hash noise, never
from global random state, so any two processes generate identical data. Demand,
price and inflow share the same intra-day/seasonal shape functions, which preserves
the structural correlations the MILP exploits (evening scarcity, solar-hour dip,
monsoon inflow) even though their noise streams differ.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta

from app.adapters.base import AdapterHealth
from app.domain import timeblocks as tb
from app.domain.entities import SeriesPoint

WEATHER_SUBSERIES = ("temperature_2m", "precipitation", "cloud_cover")


def _u(seed: int, key: str) -> float:
    """Deterministic uniform [0, 1) from (seed, key)."""
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2.0**64


def _gauss_bump(x: float, centre: float, width: float) -> float:
    return math.exp(-(((x - centre) / width) ** 2))


def demand_shape(hour: float) -> float:
    """Relative Kerala demand shape over the day (≈0.8 night .. ≈1.45 evening peak)."""
    night = 0.80
    morning = 0.18 * _gauss_bump(hour, 8.0, 2.2)
    midday = 0.10 * _gauss_bump(hour, 13.0, 3.0)
    evening = 0.62 * _gauss_bump(hour if hour > 4 else hour + 24, 20.5, 2.1)
    return night + morning + midday + evening


def demand_season(month: int) -> float:
    if month in (3, 4, 5):  # hot season
        return 1.08
    if month in (6, 7, 8, 9):  # monsoon
        return 0.96
    return 1.0


def price_shape(hour: float) -> float:
    """Relative DAM price shape: solar-hour dip, steep evening scarcity."""
    base = 0.9
    solar_dip = -0.35 * _gauss_bump(hour, 13.0, 2.6)
    morning = 0.25 * _gauss_bump(hour, 8.5, 1.8)
    evening = 1.05 * _gauss_bump(hour if hour > 4 else hour + 24, 20.0, 2.0)
    return max(base + solar_dip + morning + evening, 0.35)


def inflow_season(month: int) -> float:
    """Monsoon-dominated inflow multiplier (annual mean ≈ 1.0)."""
    table = {
        1: 0.35,
        2: 0.30,
        3: 0.30,
        4: 0.45,
        5: 0.60,
        6: 1.90,
        7: 2.30,
        8: 2.10,
        9: 1.60,
        10: 1.10,
        11: 0.70,
        12: 0.45,
    }
    return table[month]


class SyntheticAdapter:
    """`series_id` one of demand_mw | price_dam_inr_mwh | inflow_mwh | weather."""

    def __init__(
        self,
        name: str,
        series_id: str,
        seed: int = 42,
        demand_base_mw: float = 3200.0,
        demand_profile: list[float] | None = None,
        inflow_daily_mean_mwh: float = 9000.0,
    ) -> None:
        # Calibration params come from configs/adapters.yaml (ADR-11/ADR-13):
        # demand_profile is a 96-value mean-1.0 intraday shape; when absent the
        # legacy demand_shape() curve is used.
        self.name = name
        self.series_id = series_id
        self.seed = seed
        self.demand_base_mw = demand_base_mw
        self.demand_profile = demand_profile
        self.inflow_daily_mean_mwh = inflow_daily_mean_mwh

    # ------------------------------------------------------------- generators
    def _day_factor(self, day: date, spread: float) -> float:
        """Smooth day-to-day noise: average of this and previous day's draw."""
        u0 = _u(self.seed, f"day:{day.isoformat()}")
        u1 = _u(self.seed, f"day:{(day - timedelta(days=1)).isoformat()}")
        return 1.0 + spread * ((u0 + u1) - 1.0)

    def _demand(self, day: date, block: int) -> float:
        hour = (block - 1) * 0.25
        if self.demand_profile is not None:
            shape = self.demand_profile[(block - 1) % len(self.demand_profile)]
        else:
            shape = demand_shape(hour)
        v = self.demand_base_mw * shape * demand_season(day.month)
        if day.weekday() >= 5:
            v *= 0.94
        v *= self._day_factor(day, 0.06)
        v *= 1.0 + 0.03 * (_u(self.seed, f"{day}:{block}") - 0.5)
        return round(v, 2)

    def _price(self, day: date, block: int) -> float:
        hour = (block - 1) * 0.25
        base = 4200.0
        v = base * price_shape(hour)
        if day.month in (6, 7, 8, 9):  # monsoon: hydro-rich region, softer prices
            v *= 0.90
        v *= self._day_factor(day, 0.30)
        v *= 1.0 + 0.10 * (_u(self.seed, f"{day}:{block}") - 0.5)
        if _u(self.seed, f"spike:{day}:{block}") > 0.985 and 68 <= block <= 92:
            v *= 1.8  # evening scarcity spike
        return round(min(max(v, 1200.0), 10_000.0), 2)

    def _inflow(self, day: date, block: int) -> float:
        daily_mean_mwh = self.inflow_daily_mean_mwh
        season = inflow_season(day.month)
        rain_event = 1.0
        if day.month in (6, 7, 8, 9) and _u(self.seed, f"rain:{day}") > 0.75:
            rain_event = 1.6
        daily = daily_mean_mwh * season * rain_event * self._day_factor(day, 0.35)
        # mild diurnal skew (afternoon catchment response)
        hour = (block - 1) * 0.25
        diurnal = 1.0 + 0.15 * _gauss_bump(hour, 15.0, 5.0) - 0.05
        return round(daily / tb.BLOCKS_PER_DAY * diurnal, 3)

    def _weather(self, day: date, block: int) -> dict[str, float]:
        hour = (block - 1) * 0.25
        month = day.month
        t_base = {1: 26, 2: 27, 3: 29, 4: 30, 5: 29, 6: 27, 7: 26, 8: 26, 9: 27, 10: 27, 11: 26, 12: 26}[
            month
        ]
        temp = t_base + 3.5 * _gauss_bump(hour, 14.0, 4.0) - 1.5 + 1.0 * (_u(self.seed, f"t:{day}") - 0.5)
        wet = inflow_season(month) * self._day_factor(day, 0.35)
        rain_u = _u(self.seed, f"rain:{day}:{block // 8}")
        precip = max(0.0, (rain_u - 0.55) * 8.0 * wet)
        cloud = min(100.0, max(0.0, 30.0 + 55.0 * min(wet, 1.5) * rain_u))
        return {
            "temperature_2m": round(temp, 2),
            "precipitation": round(precip, 2),
            "cloud_cover": round(cloud, 1),
        }

    # ------------------------------------------------------------- contract
    def generate_day(self, day: date) -> list[SeriesPoint]:
        points: list[SeriesPoint] = []
        for block in range(1, tb.BLOCKS_PER_DAY + 1):
            ts = tb.block_start(day, block)
            if self.series_id == "weather":
                for sub, value in self._weather(day, block).items():
                    points.append(SeriesPoint(series_id=f"weather.{sub}", ts=ts, value=value))
            elif self.series_id == "demand_mw":
                points.append(SeriesPoint(series_id=self.series_id, ts=ts, value=self._demand(day, block)))
            elif self.series_id == "price_dam_inr_mwh":
                points.append(SeriesPoint(series_id=self.series_id, ts=ts, value=self._price(day, block)))
            elif self.series_id == "inflow_mwh":
                points.append(SeriesPoint(series_id=self.series_id, ts=ts, value=self._inflow(day, block)))
            else:
                raise ValueError(f"unknown synthetic series_id {self.series_id!r}")
        return points

    def fetch(self, start: datetime, end: datetime) -> list[SeriesPoint]:
        day = start.astimezone(tb.IST).date() if start.tzinfo else start.date()
        out: list[SeriesPoint] = []
        while tb.block_start(day, 1) < end:
            out.extend(p for p in self.generate_day(day) if start <= p.ts < end)
            day += timedelta(days=1)
        return out

    def health(self) -> AdapterHealth:
        return AdapterHealth(name=self.name, ok=True, detail="synthetic generator")
