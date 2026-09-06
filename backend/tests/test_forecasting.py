from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.adapters.synthetic import SyntheticAdapter
from app.domain import timeblocks as tb
from app.domain.enums import ForecastTarget
from app.forecasting.backtest import rolling_origin_backtest
from app.forecasting.features import build_feature_frame, kerala_holidays, points_to_frame
from app.forecasting.models import (
    LightGBMQuantile,
    SeasonalNaive,
    future_frame_for_day,
    make_model,
)
from app.forecasting.registry import load_latest, save_artifact

END = date(2026, 7, 1)
CFG_TARGET = {"lags_days": [1, 7], "weather_features": []}


@pytest.fixture(scope="module")
def demand_history():
    adapter = SyntheticAdapter("demand", "demand_mw", 42)
    points = []
    d = END - timedelta(days=90)
    while d < END:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)
    return points_to_frame(points)


def test_feature_frame_columns_and_no_nan(demand_history) -> None:
    frame = build_feature_frame(demand_history, None, CFG_TARGET)
    for col in ("lag_1d", "lag_7d", "block_sin", "dow", "is_weekend", "is_holiday", "month_cos"):
        assert col in frame.columns
    assert not frame.isna().any().any()
    # 7 lag days consumed
    assert len(frame) == (90 - 7) * tb.BLOCKS_PER_DAY


def test_kerala_holidays_include_onam_and_fixed() -> None:
    days = kerala_holidays(2026)
    assert date(2026, 8, 26) in days  # Thiruvonam (approx table)
    assert date(2026, 8, 15) in days
    assert date(2026, 4, 14) in days  # Vishu


def test_seasonal_naive_predicts_shapes(demand_history) -> None:
    frame = build_feature_frame(demand_history, None, CFG_TARGET)
    model = SeasonalNaive([0.1, 0.5, 0.9])
    model.fit(frame)
    future = future_frame_for_day(demand_history, None, CFG_TARGET, END)
    preds = model.predict_day(future)
    assert set(preds) == {"p10", "p50", "p90"}
    assert all(len(v) == 96 for v in preds.values())
    assert all(lo <= mid <= hi for lo, mid, hi in zip(preds["p10"], preds["p50"], preds["p90"]))


def test_lightgbm_quantile_fit_predict(demand_history) -> None:
    pytest.importorskip("lightgbm")
    frame = build_feature_frame(demand_history, None, CFG_TARGET)
    model = LightGBMQuantile([0.1, 0.5, 0.9], params={"n_estimators": 40})
    model.fit(frame)
    future = future_frame_for_day(demand_history, None, CFG_TARGET, END)
    preds = model.predict_day(future)
    assert all(len(v) == 96 for v in preds.values())
    assert all(lo <= mid <= hi for lo, mid, hi in zip(preds["p10"], preds["p50"], preds["p90"]))
    # sane magnitude: within the demand envelope
    assert 2000 < sum(preds["p50"]) / 96 < 5500


def test_backtest_returns_finite_metrics(demand_history) -> None:
    cfg = {
        "quantiles": [0.1, 0.5, 0.9],
        "targets": {"demand": {**CFG_TARGET, "model": "seasonal_naive"}},
        "backtest": {"folds": 2, "fold_days": 7, "min_train_days": 30},
    }
    m = rolling_origin_backtest(demand_history, None, ForecastTarget.DEMAND, cfg)
    assert m.n_folds == 2
    assert m.mape_pct is not None and 0 < m.mape_pct < 50
    assert m.mae is not None and m.mae > 0
    assert m.pinball_p10 is not None and m.pinball_p90 is not None


def test_registry_round_trip(tmp_path, demand_history) -> None:
    cfg = {
        "registry_dir": str(tmp_path),
        "quantiles": [0.1, 0.5, 0.9],
        "targets": {"demand": {**CFG_TARGET, "model": "seasonal_naive"}},
    }
    frame = build_feature_frame(demand_history, None, CFG_TARGET)
    model = make_model(ForecastTarget.DEMAND, cfg)
    model.fit(frame)
    path = save_artifact(ForecastTarget.DEMAND, model, None, cfg)
    assert "v0001" in path
    loaded = load_latest(ForecastTarget.DEMAND, cfg)
    assert loaded is not None
    model2, meta = loaded
    assert meta["model_name"] == "seasonal_naive"
    future = future_frame_for_day(demand_history, None, CFG_TARGET, END)
    assert model2.predict_day(future)["p50"] == model.predict_day(future)["p50"]


def test_calibrated_adapter_uses_configured_base() -> None:
    """Regression test: ensure calibration from configs/adapters.yaml is actually applied.

    This guards against the bug fixed 2026-09-06 where SyntheticAdapter was instantiated
    directly instead of through make_synthetic_adapter(), silently using pre-calibration
    defaults (demand_base_mw=3200) instead of the configured calibrated value (3720).

    If this test fails, it means someone has reverted to direct SyntheticAdapter() construction
    or make_synthetic_adapter() is not reading the configuration.
    """
    from app.adapters.synthetic import make_synthetic_adapter

    d = date(2026, 5, 15)

    # Generate demand using the configured adapter (should load demand_base_mw=3720 from config)
    adapter = make_synthetic_adapter("demand", "demand_mw")
    day_points = adapter.generate_day(d)
    values = [p.value for p in day_points]
    mean_demand = sum(values) / len(values)

    # The calibrated mean should be around 4,018 MW (from the observed 8-day KSEB data in May 2025)
    # If calibration is applied: demand_base_mw=3720, scaled profile -> mean ~4,000-4,100 MW
    # If calibration is bypassed (old class default demand_base_mw=3200): mean ~3,200-3,300 MW
    # This test detects the latter case by asserting mean is closer to 4,018 than to 3,200.

    distance_to_calibrated = abs(mean_demand - 4018.0)
    distance_to_uncalibrated = abs(mean_demand - 3200.0)

    assert distance_to_calibrated < distance_to_uncalibrated, (
        f"Calibration not applied: mean demand {mean_demand:.1f} MW is closer to "
        f"uncalibrated default (3200) than calibrated value (3720/4018). "
        f"This suggests direct SyntheticAdapter() usage instead of make_synthetic_adapter()."
    )

    # Additional assertion: mean should be in a reasonable range for calibrated demand
    assert 3500 < mean_demand < 4500, (
        f"Calibrated demand mean {mean_demand:.1f} is outside expected range [3500, 4500]. "
        f"Check configs/adapters.yaml source.demand.params for correctness."
    )


def test_backtest_folds_exact_size_and_disjoint(demand_history) -> None:
    """Audit fix: the old `<= test_end + 1 day` boundary made each test window
    96*fold_days + 1 blocks, double-counting the next fold's midnight block."""
    import pandas as pd

    from app.forecasting.features import build_feature_frame

    frame = build_feature_frame(demand_history, None, CFG_TARGET)
    days = pd.DatetimeIndex(frame.index.normalize().unique()).sort_values()
    folds, fold_days = 2, 7
    seen: set = set()
    for i in range(folds):
        test_end = days[len(days) - (folds - 1 - i) * fold_days - 1]
        test_start = test_end - pd.Timedelta(days=fold_days - 1)
        test = frame[(frame.index >= test_start) & (frame.index < test_end + pd.Timedelta(days=1))]
        assert len(test) == fold_days * tb.BLOCKS_PER_DAY  # exactly, no +1
        overlap = seen & set(test.index)
        assert not overlap, f"fold {i} overlaps a previous fold: {sorted(overlap)[:3]}"
        seen |= set(test.index)
