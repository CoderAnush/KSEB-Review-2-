"""Extract REAL values from the trained model and backtest - zero fabrication.

Every number here comes directly from:
- app.forecasting.backtest.rolling_origin_backtest() -> ForecastMetrics.detail["folds"]
- A LightGBMQuantile model's underlying LGBMRegressor.feature_importances_
- A trained model's own predict_day() output (real P10/P50/P90 forecasts)

Run from backend/:  python extract_real_model_outputs.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from app.adapters.synthetic import make_synthetic_adapter
from app.config import load_config
from app.domain.enums import ForecastTarget
from app.forecasting.backtest import rolling_origin_backtest
from app.forecasting.features import build_feature_frame, points_to_frame
from app.forecasting.models import make_model, quantile_label

OUT_DIR = Path("../output")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def synthetic_history(target: ForecastTarget, days: int, end: date):
    name, series_id, seed = {
        ForecastTarget.DEMAND: ("demand", "demand_mw", 42),
        ForecastTarget.PRICE: ("price", "price_dam_inr_mwh", 43),
        ForecastTarget.INFLOW: ("inflow", "inflow_mwh", 44),
    }[target]
    adapter = make_synthetic_adapter(name, series_id, seed)
    points = []
    d = end - timedelta(days=days)
    while d < end:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)
    return points_to_frame(points)


def main() -> None:
    cfg = load_config("forecasting")
    end = date.fromisoformat("2026-07-01")
    days = 400
    target = ForecastTarget.DEMAND

    print("=" * 70)
    print("STEP 1: Real per-fold backtest results (rolling_origin_backtest)")
    print("=" * 70)
    history = synthetic_history(target, days, end)
    metrics = rolling_origin_backtest(history, None, target, cfg)
    fold_details = metrics.detail["folds"]
    for f in fold_details:
        print(f"  Fold {f['fold']}: test_start={f['test_start']}  MAPE={f['mape_pct']}%  MAE={f['mae']}")
    print(f"\n  Overall: model={metrics.model_name}  n_folds={metrics.n_folds}  "
          f"MAPE={metrics.mape_pct:.3f}%  MAE={metrics.mae:.3f}  "
          f"pinball_p10={metrics.pinball_p10:.3f}  pinball_p90={metrics.pinball_p90:.3f}")

    with open(OUT_DIR / "real_fold_details.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "target": target.value,
                "model": metrics.model_name,
                "n_folds": metrics.n_folds,
                "overall_mape_pct": metrics.mape_pct,
                "overall_mae": metrics.mae,
                "overall_pinball_p10": metrics.pinball_p10,
                "overall_pinball_p90": metrics.pinball_p90,
                "folds": fold_details,
            },
            fh,
            indent=2,
        )
    print(f"\n  written: {OUT_DIR / 'real_fold_details.json'}")

    print("\n" + "=" * 70)
    print("STEP 2: Real feature importances from a trained LightGBM model")
    print("=" * 70)
    target_cfg = cfg["targets"][target.value]
    frame = build_feature_frame(history, None, target_cfg)
    model = make_model(target, cfg)
    if model.name != "lightgbm":
        print(f"  WARNING: lightgbm not available, degraded to {model.name} — no feature_importances_")
        return
    model.fit(frame)

    p50_model = model._models[quantile_label(0.5)]
    feature_names = model._features
    importances = p50_model.feature_importances_.tolist()
    total = sum(importances) or 1
    ranked = sorted(zip(feature_names, importances), key=lambda t: -t[1])

    print("  (raw LightGBM 'split' importances from the p50 model, real training run)")
    for name, imp in ranked:
        pct = 100 * imp / total
        print(f"    {name:20s}  raw={imp:6d}  ({pct:5.1f}%)")

    with open(OUT_DIR / "real_feature_importance.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "target": target.value,
                "quantile": "p50",
                "importance_type": p50_model.importance_type,
                "features": [{"name": n, "raw_importance": i, "pct": 100 * i / total} for n, i in ranked],
            },
            fh,
            indent=2,
        )
    print(f"\n  written: {OUT_DIR / 'real_feature_importance.json'}")

    print("\n" + "=" * 70)
    print("STEP 3: Real actual-vs-forecast (P10/P50/P90) on a held-out test window")
    print("=" * 70)
    # Train on everything except the last 30 days; predict_day on those 30 days = real
    # out-of-sample forecast from the actual fitted model (not backtest-internal).
    cutoff = frame.index.max() - timedelta(days=30)
    train_frame = frame[frame.index < cutoff]
    test_frame = frame[frame.index >= cutoff]

    holdout_model = make_model(target, cfg)
    holdout_model.fit(train_frame)
    preds = holdout_model.predict_day(test_frame)

    actual = test_frame["value"].tolist()
    p10 = preds[quantile_label(0.1)]
    p50 = preds[quantile_label(0.5)]
    p90 = preds[quantile_label(0.9)]

    rows = [
        {"ts": str(ts), "actual": a, "p10": lo, "p50": mid, "p90": hi}
        for ts, a, lo, mid, hi in zip(test_frame.index, actual, p10, p50, p90)
    ]
    with open(OUT_DIR / "real_holdout_forecast.json", "w", encoding="utf-8") as fh:
        json.dump({"target": target.value, "cutoff": str(cutoff), "rows": rows}, fh, indent=2)
    print(f"  Held out {len(rows)} blocks from {cutoff.date()} onward")
    print(f"  written: {OUT_DIR / 'real_holdout_forecast.json'}")

    print("\nDONE. All three JSON files contain real, non-fabricated model output.")


if __name__ == "__main__":
    main()
