from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import load_config
from app.db.repositories.runs import RunsRepo
from app.db.repositories.timeseries import TimeseriesRepo
from app.domain import timeblocks as tb
from app.domain.entities import ForecastSet
from app.domain.enums import ForecastTarget
from app.forecasting.features import build_feature_frame, points_to_frame
from app.forecasting.models import future_frame_for_day, make_model
from app.forecasting.registry import load_latest, save_artifact
from app.logging_setup import get_logger

log = get_logger(__name__)

HISTORY_DAYS = 540
NON_NEGATIVE = {ForecastTarget.DEMAND, ForecastTarget.INFLOW}


async def _weather_frame(repo: TimeseriesRepo, start: datetime, end: datetime) -> pd.DataFrame | None:
    cols = {}
    for sub in ("temperature_2m", "precipitation", "cloud_cover"):
        series_id = f"weather.{sub}"
        pts = await repo.read_range(series_id, start, end)
        if pts:
            cols[series_id] = points_to_frame(pts)["value"]
    return pd.DataFrame(cols) if cols else None


async def run_forecasts(
    session: AsyncSession,
    day: date,
    targets: list[ForecastTarget] | None = None,
    pipeline_run_id: int | None = None,
) -> dict[ForecastTarget, ForecastSet]:
    """Forecast all 96 blocks of `day` (D+1) per target; persist and return sets."""
    cfg = load_config("forecasting")
    ts_repo = TimeseriesRepo(session)
    runs_repo = RunsRepo(session)

    end = tb.block_start(day, 1)  # history strictly before the target day
    start = end - timedelta(days=HISTORY_DAYS)
    weather = await _weather_frame(ts_repo, start, tb.block_end(day, tb.BLOCKS_PER_DAY))

    out: dict[ForecastTarget, ForecastSet] = {}
    for target in targets or list(ForecastTarget):
        target_cfg = cfg["targets"][target.value]
        pts = await ts_repo.read_range(target_cfg["series_id"], start, end)
        if len(pts) < tb.BLOCKS_PER_DAY * 14:
            log.warning("insufficient_history", target=target.value, points=len(pts))
            continue
        history = points_to_frame(pts)

        loaded = load_latest(target, cfg)
        if loaded is not None:
            model, meta = loaded
            version = meta.get("version", "")
        else:
            model = make_model(target, cfg)
            frame = build_feature_frame(history, weather, target_cfg)
            model.fit(frame)
            version = save_artifact(target, model, None, cfg).rsplit("v", 1)[-1]
            version = f"v{version}"

        future = future_frame_for_day(history, weather, target_cfg, day)
        if len(future) != tb.BLOCKS_PER_DAY:
            log.error("future_frame_incomplete", target=target.value, rows=len(future))
            continue
        quantiles = model.predict_day(future)
        if target in NON_NEGATIVE:
            quantiles = {k: [max(v, 0.0) for v in vals] for k, vals in quantiles.items()}

        fs = ForecastSet(
            target=target,
            day=day,
            quantiles=quantiles,
            model_name=getattr(model, "name", type(model).__name__),
            model_version=version,
            issued_at=datetime.now(timezone.utc),
        )
        await runs_repo.save_forecast(pipeline_run_id, fs)
        out[target] = fs
        log.info("forecast_done", target=target.value, day=str(day), model=fs.model_name)
    return out
