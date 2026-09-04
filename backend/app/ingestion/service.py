from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import build_adapters
from app.config import load_config
from app.db.repositories.timeseries import TimeseriesRepo
from app.domain import timeblocks as tb
from app.domain.entities import DataQualityReport, SeriesPoint
from app.domain.enums import QualityFlag
from app.logging_setup import get_logger

log = get_logger(__name__)


def _to_ist(ts: datetime) -> datetime:
    """Coerce a naive timestamp to IST-aware (naive == IST, A13/I12). Idempotent for
    already-aware timestamps. This prevents the mixed naive/aware TypeError when a
    single batch carries both (some adapters emit aware, file-drop CSVs often naive)."""
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=tb.IST)


_UNITS = {
    "demand_mw": "MW",
    "price_dam_inr_mwh": "INR/MWh",
    "inflow_mwh": "MWh",
}


def apply_quality_rules(
    points: list[SeriesPoint], cfg: dict[str, Any], source: str = ""
) -> tuple[list[SeriesPoint], list[DataQualityReport]]:
    """Dedupe → spike flagging → bounded gap interpolation. Pure and unit-tested.

    Returns cleaned points plus one DataQualityReport per series present.
    """
    max_gap_blocks = int(cfg.get("max_gap_blocks", 8))
    spike_z = float(cfg.get("spike_zscore", 6.0))
    bounds = cfg.get("bounds", {})  # optional per-series {min, max} for out-of-range clamping

    by_series: dict[str, dict[datetime, SeriesPoint]] = {}
    for p in points:
        # Normalize tz up front (I12): naive == IST. Without this, a batch mixing
        # naive and aware timestamps raises TypeError on the sort/subtraction below.
        ts = _to_ist(p.ts)
        norm = p if ts == p.ts else p.model_copy(update={"ts": ts})
        by_series.setdefault(p.series_id, {})[ts] = norm  # dedupe: last write wins

    cleaned: list[SeriesPoint] = []
    reports: list[DataQualityReport] = []
    for series_id, by_ts in by_series.items():
        pts = [by_ts[t] for t in sorted(by_ts)]
        n_suspect = 0
        n_interpolated = sum(1 for p in pts if p.quality is QualityFlag.INTERPOLATED)

        # out-of-range clamp/winsorize (optional, config-driven). Clamps values outside
        # [min, max] to the bound and flags them SUSPECT (negative demand/inflow, price
        # above cap). No-op when the series has no configured bounds.
        srange = bounds.get(series_id)
        if srange is not None:
            lo_b = srange.get("min")
            hi_b = srange.get("max")
            for i, p in enumerate(pts):
                clamped = p.value
                if lo_b is not None and clamped < lo_b:
                    clamped = float(lo_b)
                if hi_b is not None and clamped > hi_b:
                    clamped = float(hi_b)
                if clamped != p.value and p.quality is QualityFlag.OK:
                    pts[i] = p.model_copy(update={"value": clamped, "quality": QualityFlag.SUSPECT})
                    n_suspect += 1

        # spike detection — Hampel filter (leave-one-out local median/MAD), replacing
        # global mean/stdev which had two failure modes: (a) a big spike inflates the
        # mean AND stdev of its own window and can mask itself; (b) a global threshold
        # flags legitimate daily peaks on shaped series. Each point is scored against
        # the median/MAD of its neighbours ONLY (itself excluded), so it can never
        # dilute its own statistic; 1.4826*MAD estimates sigma, so spike_z keeps its
        # "sigmas" meaning.
        values = [p.value for p in pts]
        if len(values) >= 8:
            half_w = 5  # ~75 min of neighbours each side at 15-min cadence
            for i, p in enumerate(pts):
                if p.quality is not QualityFlag.OK:
                    continue
                window = values[max(0, i - half_w) : i] + values[i + 1 : i + 1 + half_w]
                if len(window) < 4:
                    continue
                med = statistics.median(window)
                mad = statistics.median([abs(v - med) for v in window])
                scale = 1.4826 * mad
                if scale > 0:
                    is_spike = abs(values[i] - med) / scale > spike_z
                else:
                    # constant neighbourhood: any material deviation from it is a spike
                    is_spike = abs(values[i] - med) > 1e-6 * max(1.0, abs(med))
                if is_spike:
                    pts[i] = p.model_copy(update={"quality": QualityFlag.SUSPECT})
                    n_suspect += 1

        # bounded gap interpolation on the series' own cadence
        filled: list[SeriesPoint] = []
        if len(pts) >= 3:
            steps = [
                (b.ts - a.ts).total_seconds()
                for a, b in zip(pts, pts[1:])
                if (b.ts - a.ts).total_seconds() > 0
            ]
            step_s = statistics.median(steps) if steps else 900.0
            max_gap_s = max_gap_blocks * 900.0
            for a, b in zip(pts, pts[1:]):
                gap = (b.ts - a.ts).total_seconds()
                if step_s < gap <= max_gap_s:
                    n_missing_steps = round(gap / step_s) - 1
                    for k in range(1, n_missing_steps + 1):
                        frac = k / (n_missing_steps + 1)
                        filled.append(
                            SeriesPoint(
                                series_id=series_id,
                                ts=a.ts + timedelta(seconds=step_s * k),
                                value=a.value + (b.value - a.value) * frac,
                                quality=QualityFlag.INTERPOLATED,
                            )
                        )
        n_interpolated += len(filled)
        all_pts = sorted(pts + filled, key=lambda p: p.ts)
        cleaned.extend(all_pts)
        reports.append(
            DataQualityReport(
                source=source,
                series_id=series_id,
                start=all_pts[0].ts if all_pts else None,
                end=all_pts[-1].ts if all_pts else None,
                n_points=len(all_pts),
                n_interpolated=n_interpolated,
                n_suspect=n_suspect,
            )
        )
    return cleaned, reports


async def ingest_points(
    session: AsyncSession, points: list[SeriesPoint], quality_cfg: dict[str, Any], source: str = ""
) -> list[DataQualityReport]:
    """Quality-rule + upsert a batch of points (shared by flows and the seed script)."""
    cleaned, reports = apply_quality_rules(points, quality_cfg, source=source)
    # provenance: every persisted point carries its source so synthetic and real
    # data are distinguishable downstream (audit fix); adapter-set sources win
    cleaned = [p if p.source else p.model_copy(update={"source": source}) for p in cleaned]
    repo = TimeseriesRepo(session)
    for series_id in {p.series_id for p in cleaned}:
        await repo.ensure_series(series_id, _UNITS.get(series_id, ""), f"ingested via {source}")
    await repo.upsert_points(cleaned)
    return reports


async def ingest_range(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    sources: list[str] | None = None,
) -> list[DataQualityReport]:
    cfg = load_config("adapters")
    quality_cfg = cfg.get("quality", {})
    adapters = build_adapters(cfg)
    reports: list[DataQualityReport] = []
    for name, adapter in adapters.items():
        if sources is not None and name not in sources:
            continue
        try:
            points = adapter.fetch(start, end)
        except Exception as exc:
            log.error("adapter_fetch_failed", adapter=name, error=str(exc))
            # audit fix: carry the failure in the report so the flow can mark the
            # run DEGRADED instead of an indistinguishable SUCCESS
            reports.append(
                DataQualityReport(source=name, series_id=adapter.series_id, error=str(exc)[:500])
            )
            continue
        # class name in the provenance string is what separates SyntheticAdapter
        # data from real feeds sharing the same series_id
        rs = await ingest_points(session, points, quality_cfg, source=f"{type(adapter).__name__}:{name}")
        log.info("ingested", adapter=name, series=len(rs), points=sum(r.n_points for r in rs))
        reports.extend(rs)
    return reports
