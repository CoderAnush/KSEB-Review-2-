"""IST 96-block calendar — THE single time authority (assumption A13).

Conventions, fixed project-wide:
- All timestamps are IST (UTC+05:30). India has no DST; none is modelled.
- A day has 96 blocks of 15 minutes. Block 1 = 00:00-00:15, block 96 = 23:45-24:00.
- Block intervals are half-open [start, end).

Never construct block indices by hand anywhere else in the codebase.

NOTE: BLOCKS_PER_DAY and IST are architectural constants (the KSEB grid operates on a 96×15-min
block structure and IST timezone). These values are hardcoded here rather than loaded from
configs/forecasting.yaml because they are immutable project domain constraints, not configurable
parameters. See configs/forecasting.yaml:5-6 (calendar.blocks_per_day, calendar.timezone) for the
documentation of these values; they serve as a single source of truth for their semantic meaning
but are not expected to change at runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
BLOCKS_PER_DAY = 96
BLOCK_MINUTES = 15
BLOCK_HOURS = BLOCK_MINUTES / 60.0


def _check_index(index: int, blocks_per_day: int = BLOCKS_PER_DAY) -> None:
    if not 1 <= index <= blocks_per_day:
        raise ValueError(f"block index {index} outside 1..{blocks_per_day}")


def block_start(day: date, index: int) -> datetime:
    """IST-aware start of block `index` (1-based) on `day`."""
    _check_index(index)
    return datetime.combine(day, time(0, 0), tzinfo=IST) + timedelta(minutes=(index - 1) * BLOCK_MINUTES)


def block_end(day: date, index: int) -> datetime:
    return block_start(day, index) + timedelta(minutes=BLOCK_MINUTES)


def block_of(ts: datetime) -> tuple[date, int]:
    """(day, block index 1..96) containing `ts`. Naive datetimes are taken as IST."""
    ts_ist = ts.replace(tzinfo=IST) if ts.tzinfo is None else ts.astimezone(IST)
    minutes = ts_ist.hour * 60 + ts_ist.minute
    return ts_ist.date(), minutes // BLOCK_MINUTES + 1


@dataclass(frozen=True)
class Block:
    day: date
    index: int  # 1..96

    def __post_init__(self) -> None:
        _check_index(self.index)

    @property
    def start(self) -> datetime:
        return block_start(self.day, self.index)

    @property
    def end(self) -> datetime:
        return block_end(self.day, self.index)

    @property
    def label(self) -> str:
        return f"{self.start:%H:%M}-{self.end:%H:%M}"


def day_blocks(day: date) -> list[Block]:
    return [Block(day, i) for i in range(1, BLOCKS_PER_DAY + 1)]


def hour_of_block(index: int) -> int:
    """Hour 0..23 that block `index` falls in."""
    _check_index(index)
    return (index - 1) * BLOCK_MINUTES // 60


def blocks_of_hour(hour: int) -> list[int]:
    """The four block indices inside hour 0..23."""
    if not 0 <= hour <= 23:
        raise ValueError(f"hour {hour} outside 0..23")
    first = hour * 4 + 1
    return [first, first + 1, first + 2, first + 3]


def block_range(from_block: int, to_block: int) -> list[int]:
    """Inclusive block index range, validated."""
    _check_index(from_block)
    _check_index(to_block)
    if to_block < from_block:
        raise ValueError("to_block before from_block")
    return list(range(from_block, to_block + 1))


def expand_hourly_to_blocks(values: Sequence[float]) -> list[float]:
    """Shape-preserving hourly -> 15-min expansion (assumption A3).

    Linear interpolation through hour midpoints, then rescaled so the mean of the
    four blocks in each hour equals the original hourly value exactly
    (energy-preserving). Callers must flag the resulting points INTERPOLATED.
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [float(values[0])] * 4

    # positions in "hour" units: block centres at (b + 0.5)/4, hour midpoints at h + 0.5
    raw: list[float] = []
    for b in range(4 * n):
        pos = (b + 0.5) / 4.0
        h = pos - 0.5  # fractional index into hour-midpoint grid
        if h <= 0:
            v = float(values[0])
        elif h >= n - 1:
            v = float(values[-1])
        else:
            lo = int(h)
            frac = h - lo
            v = float(values[lo]) * (1 - frac) + float(values[lo + 1]) * frac
        raw.append(v)

    # per-hour rescale so block means reproduce the hourly value exactly
    out: list[float] = []
    for h in range(n):
        chunk = raw[4 * h : 4 * h + 4]
        mean = sum(chunk) / 4.0
        target = float(values[h])
        if mean == 0.0:
            out.extend([target] * 4)
        else:
            out.extend(c * target / mean for c in chunk)
    return out
