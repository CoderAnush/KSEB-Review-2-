from __future__ import annotations

import math
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SeriesCatalog, TsObservation
from app.domain import timeblocks as tb
from app.domain.entities import SeriesPoint
from app.domain.enums import QualityFlag


class TimeseriesRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_series(self, series_id: str, unit: str, description: str = "") -> None:
        stmt = (
            pg_insert(SeriesCatalog)
            .values(series_id=series_id, unit=unit, description=description)
            .on_conflict_do_nothing(index_elements=["series_id"])
        )
        await self.session.execute(stmt)

    async def upsert_points(self, points: list[SeriesPoint]) -> int:
        if not points:
            return 0
        rows = [
            {
                "series_id": p.series_id,
                "ts": p.ts,
                "value": p.value,
                "quality_flag": p.quality.value,
                "source": p.source,
            }
            for p in points
        ]
        stmt = pg_insert(TsObservation).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["series_id", "ts"],
            set_={
                "value": stmt.excluded.value,
                "quality_flag": stmt.excluded.quality_flag,
                "source": stmt.excluded.source,
            },
        )
        await self.session.execute(stmt)
        return len(rows)

    async def read_range(self, series_id: str, start: datetime, end: datetime) -> list[SeriesPoint]:
        stmt = (
            select(TsObservation)
            .where(
                TsObservation.series_id == series_id,
                TsObservation.ts >= start,
                TsObservation.ts < end,
            )
            .order_by(TsObservation.ts)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            SeriesPoint(
                series_id=r.series_id,
                ts=r.ts,
                value=r.value,
                quality=QualityFlag(r.quality_flag),
                source=r.source,
            )
            for r in rows
        ]

    async def read_day_blocks(self, series_id: str, day: date) -> list[float]:
        """Exactly 96 values for `day` (block order), NaN where missing."""
        start = tb.block_start(day, 1)
        end = tb.block_end(day, tb.BLOCKS_PER_DAY)
        points = await self.read_range(series_id, start, end)
        out = [math.nan] * tb.BLOCKS_PER_DAY
        for p in points:
            d, idx = tb.block_of(p.ts)
            if d == day:
                out[idx - 1] = p.value
        return out

    async def coverage(self, series_id: str) -> dict:
        stmt = select(
            func.min(TsObservation.ts),
            func.max(TsObservation.ts),
            func.count(),
        ).where(TsObservation.series_id == series_id)
        min_ts, max_ts, total = (await self.session.execute(stmt)).one()
        by_quality_stmt = (
            select(TsObservation.quality_flag, func.count())
            .where(TsObservation.series_id == series_id)
            .group_by(TsObservation.quality_flag)
        )
        by_quality = dict((await self.session.execute(by_quality_stmt)).all())
        by_source_stmt = (
            select(TsObservation.source, func.count())
            .where(TsObservation.series_id == series_id)
            .group_by(TsObservation.source)
        )
        by_source = dict((await self.session.execute(by_source_stmt)).all())
        return {
            "series_id": series_id,
            "min_ts": min_ts,
            "max_ts": max_ts,
            "n": total,
            "by_quality": by_quality,
            "by_source": by_source,
        }
