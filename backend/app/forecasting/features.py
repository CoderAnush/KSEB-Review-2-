from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from app.domain import timeblocks as tb
from app.domain.entities import SeriesPoint

# National fixed-date holidays + key Kerala observances. Onam (Thiruvonam) moves with
# the Malayalam calendar — table below is APPROXIMATE for 2024-2028 and should be
# refreshed from an official calendar before production use.
_FIXED_HOLIDAYS = [(1, 26), (5, 1), (8, 15), (10, 2), (12, 25), (4, 14)]  # incl. Vishu
_THIRUVONAM = {
    2024: date(2024, 9, 15),
    2025: date(2025, 9, 5),
    2026: date(2026, 8, 26),
    2027: date(2027, 9, 14),
    2028: date(2028, 9, 1),
}


def kerala_holidays(year: int) -> set[date]:
    days = {date(year, m, d) for m, d in _FIXED_HOLIDAYS}
    onam = _THIRUVONAM.get(year)
    if onam:
        days.update({onam, onam.replace(day=onam.day - 1)})  # First Onam + Thiruvonam
    return days


def points_to_frame(points: list[SeriesPoint]) -> pd.DataFrame:
    """SeriesPoints → DataFrame indexed by IST ts with a `value` column."""
    if not points:
        return pd.DataFrame(columns=["value"])
    frame = pd.DataFrame(
        {"value": [p.value for p in points]},
        index=pd.DatetimeIndex([p.ts for p in points], name="ts"),
    )
    return frame.sort_index()


def build_feature_frame(
    history: pd.DataFrame,
    weather: pd.DataFrame | None,
    target_cfg: dict[str, Any],
) -> pd.DataFrame:
    """History (`value` @15-min IST index) → feature frame. Rows with NaN lags dropped.

    To build features for a FUTURE day, append 96 NaN-valued rows for that day to
    `history` first; lag features only reference >=1 day back, weather is
    forward-filled (persistence), so future rows come out fully populated.
    """
    if history.empty:
        return pd.DataFrame()
    frame = history.copy()
    idx = frame.index

    for d in target_cfg.get("lags_days", [1, 7]):
        frame[f"lag_{d}d"] = frame["value"].shift(tb.BLOCKS_PER_DAY * d)

    block = (idx.hour * 60 + idx.minute) // tb.BLOCK_MINUTES + 1
    frame["block_sin"] = np.sin(2 * math.pi * block / tb.BLOCKS_PER_DAY)
    frame["block_cos"] = np.cos(2 * math.pi * block / tb.BLOCKS_PER_DAY)
    frame["dow"] = idx.dayofweek
    frame["is_weekend"] = (idx.dayofweek >= 5).astype(int)
    frame["month_sin"] = np.sin(2 * math.pi * idx.month / 12)
    frame["month_cos"] = np.cos(2 * math.pi * idx.month / 12)

    years = range(idx.year.min(), idx.year.max() + 1)
    holidays: set[date] = set()
    for y in years:
        holidays |= kerala_holidays(y)
    frame["is_holiday"] = pd.Series(idx.date, index=idx).isin(holidays).astype(int).to_numpy()

    for col in target_cfg.get("weather_features", []):
        series_id = f"weather.{col}"
        if weather is not None and series_id in weather.columns:
            joined = weather[series_id].reindex(idx, method="ffill")
            frame[col] = joined.ffill().bfill()
        else:
            frame[col] = 0.0

    lag_cols = [c for c in frame.columns if c.startswith("lag_")]
    return frame.dropna(subset=lag_cols)


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c != "value"]
