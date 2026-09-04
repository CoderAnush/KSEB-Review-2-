"""Rolling-origin backtesting: MAPE / MAE / pinball per fold (Gate 3 evidence)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.domain import timeblocks as tb
from app.domain.entities import ForecastMetrics
from app.domain.enums import ForecastTarget
from app.forecasting.features import build_feature_frame
from app.forecasting.models import make_model, quantile_label
from app.logging_setup import get_logger

log = get_logger(__name__)


def pinball_loss(actual: np.ndarray, pred: np.ndarray, q: float) -> float:
    diff = actual - pred
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


def rolling_origin_backtest(
    history: pd.DataFrame,
    weather: pd.DataFrame | None,
    target: ForecastTarget,
    cfg: dict[str, Any],
) -> ForecastMetrics:
    bt = cfg.get("backtest", {})
    folds = int(bt.get("folds", 4))
    fold_days = int(bt.get("fold_days", 14))
    min_train_days = int(bt.get("min_train_days", 180))
    target_cfg = cfg.get("targets", {}).get(target.value, {})
    quantiles = sorted(float(q) for q in cfg.get("quantiles", [0.1, 0.5, 0.9]))
    q_lo, q_mid, q_hi = quantiles[0], quantiles[len(quantiles) // 2], quantiles[-1]

    frame = build_feature_frame(history, weather, target_cfg)
    if frame.empty:
        raise ValueError(f"no usable history for target {target.value}")

    days = pd.DatetimeIndex(frame.index.normalize().unique()).sort_values()
    need = min_train_days + folds * fold_days
    if len(days) < need:
        # shrink folds rather than fail: statistical power degrades gracefully (A12)
        folds = max(1, (len(days) - min_train_days) // fold_days)
        if folds < 1:
            raise ValueError(
                f"history too short for backtest: {len(days)} days < {min_train_days + fold_days}"
            )
        log.warning("backtest_shrunk", target=target.value, folds=folds)

    fold_details: list[dict[str, float]] = []
    mapes, maes, pin_lo, pin_hi = [], [], [], []
    for i in range(folds):
        test_end = days[len(days) - (folds - 1 - i) * fold_days - 1]
        test_start = test_end - pd.Timedelta(days=fold_days - 1)
        train = frame[frame.index < test_start]
        # half-open [test_start, test_end + 1 day): `<=` here pulled in the midnight
        # block of the day AFTER test_end, double-counting it with the next fold's
        # first block (audit fix — one-block metric double-count, not leakage)
        test = frame[(frame.index >= test_start) & (frame.index < test_end + pd.Timedelta(days=1))]
        if train.empty or test.empty:
            continue

        model = make_model(target, cfg)
        model.fit(train)
        preds = model.predict_day(test)

        actual = test["value"].to_numpy(dtype=float)
        p50 = np.asarray(preds[quantile_label(q_mid)], dtype=float)
        mae = float(np.mean(np.abs(actual - p50)))
        nz = np.abs(actual) > 1e-6
        mape = float(np.mean(np.abs((actual[nz] - p50[nz]) / actual[nz])) * 100) if nz.any() else np.nan
        lo = pinball_loss(actual, np.asarray(preds[quantile_label(q_lo)], dtype=float), q_lo)
        hi = pinball_loss(actual, np.asarray(preds[quantile_label(q_hi)], dtype=float), q_hi)

        mapes.append(mape)
        maes.append(mae)
        pin_lo.append(lo)
        pin_hi.append(hi)
        fold_details.append(
            {
                "fold": i + 1,
                "test_start": str(test_start.date()),
                "mape_pct": round(mape, 3),
                "mae": round(mae, 3),
            }
        )

    model_name = make_model(target, cfg).name
    return ForecastMetrics(
        target=target,
        model_name=model_name,
        mape_pct=float(np.nanmean(mapes)) if mapes else None,
        mae=float(np.mean(maes)) if maes else None,
        pinball_p10=float(np.mean(pin_lo)) if pin_lo else None,
        pinball_p90=float(np.mean(pin_hi)) if pin_hi else None,
        n_folds=len(fold_details),
        detail={"folds": fold_details, "blocks_per_day": tb.BLOCKS_PER_DAY},
    )
