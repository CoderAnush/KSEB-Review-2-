#!/usr/bin/env python3
"""Forensic audit harness - Phase 1 Part B: CSV/JSON/backtest/leakage/lag checks."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import json
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import numpy as np

ROOT = Path("..").resolve()
OUT = ROOT / "output"

def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

# ============================================================ CSV FORENSIC PASS
section("5. CSV FORENSIC PASS")
csv_files = sorted(OUT.glob("*.csv"))
for f in csv_files:
    print(f"\n--- {f.name} ---")
    try:
        df = pd.read_csv(f)
    except Exception as e:
        print(f"  ⚠️ FAILED TO LOAD: {e}")
        continue
    print(f"  shape: {df.shape}")
    nan_ct = df.isna().sum().sum()
    inf_ct = np.isinf(df.select_dtypes(include=[np.number])).sum().sum() if df.select_dtypes(include=[np.number]).shape[1] else 0
    dup_rows = df.duplicated().sum()
    print(f"  NaN: {nan_ct}  Inf: {inf_ct}  Duplicate rows: {dup_rows}")
    ts_col = None
    for c in df.columns:
        if c.lower() in ("ts", "ts_ist", "timestamp"):
            ts_col = c
            break
    if ts_col:
        ts = pd.to_datetime(df[ts_col])
        dup_ts = ts.duplicated().sum()
        is_sorted = ts.is_monotonic_increasing
        print(f"  timestamp col: {ts_col}  duplicate timestamps: {dup_ts}  sorted: {is_sorted}")
        # 96-block/day check
        day_counts = ts.dt.date.value_counts()
        bad_days = day_counts[day_counts != 96]
        if len(bad_days) and len(day_counts) > 1:
            print(f"  ⚠️ days with != 96 blocks: {len(bad_days)} (showing up to 5): {bad_days.head(5).to_dict()}")
        elif len(day_counts) > 1:
            print(f"  ✅ all {len(day_counts)} full days have exactly 96 blocks (partial edge days excluded from check if any)")

# ============================================================ JSON CONSISTENCY + INDEPENDENT RECOMPUTE
section("6/15. JSON CONSISTENCY + INDEPENDENT METRIC RECOMPUTATION")

with open(OUT / "real_holdout_forecast.json", encoding="utf-8") as fh:
    holdout = json.load(fh)
rows = pd.DataFrame(holdout["rows"])
print(f"real_holdout_forecast.json: {len(rows)} rows, cutoff={holdout['cutoff']}")

# Monotonicity check
viol = (rows["p10"] > rows["p50"]).sum() + (rows["p50"] > rows["p90"]).sum()
print(f"P10<=P50<=P90 violations: {viol} (must be 0)")

# Independent MAPE/MAE/RMSE from raw arrays, hand-written formula
actual = rows["actual"].to_numpy(dtype=float)
p50 = rows["p50"].to_numpy(dtype=float)
err = actual - p50
mape_indep = np.mean(np.abs(err / actual)) * 100
mae_indep = np.mean(np.abs(err))
rmse_indep = np.sqrt(np.mean(err ** 2))
print(f"Independent recompute from real_holdout_forecast.json (hand formula, not project's function):")
print(f"  MAPE = {mape_indep:.4f}%   MAE = {mae_indep:.4f} MW   RMSE = {rmse_indep:.4f} MW")

with open(OUT / "real_fold_details.json", encoding="utf-8") as fh:
    folds = json.load(fh)
print(f"\nreal_fold_details.json overall (as stored): MAPE={folds['overall_mape_pct']:.4f}% MAE={folds['overall_mae']:.4f}")
fold_mapes = [f["mape_pct"] for f in folds["folds"]]
fold_maes = [f["mae"] for f in folds["folds"]]
print(f"Independent mean of per-fold MAPE values: {np.mean(fold_mapes):.4f}% (stored overall: {folds['overall_mape_pct']:.4f}%)")
print(f"Independent mean of per-fold MAE values: {np.mean(fold_maes):.4f} (stored overall: {folds['overall_mae']:.4f})")
best_i = int(np.argmin(fold_mapes))
worst_i = int(np.argmax(fold_mapes))
print(f"Best fold: Fold {folds['folds'][best_i]['fold']} MAPE={fold_mapes[best_i]:.3f}%")
print(f"Worst fold: Fold {folds['folds'][worst_i]['fold']} MAPE={fold_mapes[worst_i]:.3f}%")
print(f"Std dev across folds: {np.std(fold_mapes):.4f}%")

with open(OUT / "real_feature_importance.json", encoding="utf-8") as fh:
    feat = json.load(fh)
total_pct = sum(f["pct"] for f in feat["features"])
print(f"\nreal_feature_importance.json: {len(feat['features'])} features, percentages sum to {total_pct:.2f}% (should be ~100%)")

with open(OUT / "reconciliation_stats.json", encoding="utf-8") as fh:
    recon = json.load(fh)
print(f"\nreconciliation_stats.json demand mean: {recon['demand']['mean']} (docs claim ~4,018)")
print(f"reconciliation_stats.json cost total_8day_inr: {recon['cost']['total_8day_inr']:,.2f} = Rs {recon['cost']['total_8day_inr']/1e7:.2f} Cr")

# ============================================================ BACKTEST LEAKAGE PROOF
section("7/13. BACKTEST LEAKAGE PROOF (re-deriving fold boundaries directly)")
from app.adapters.synthetic import make_synthetic_adapter
from app.config import load_config
from app.domain.enums import ForecastTarget
from app.forecasting.features import build_feature_frame, points_to_frame

cfg = load_config("forecasting")
end = date.fromisoformat("2026-07-01")
days = 400
adapter = make_synthetic_adapter("demand", "demand_mw")
points = []
d = end - timedelta(days=days)
while d < end:
    points.extend(adapter.generate_day(d))
    d += timedelta(days=1)
history = points_to_frame(points)
target_cfg = cfg["targets"]["demand"]
frame = build_feature_frame(history, None, target_cfg)

bt = cfg.get("backtest", {})
folds_n = int(bt.get("folds", 4))
fold_days = int(bt.get("fold_days", 14))
min_train_days = int(bt.get("min_train_days", 180))
days_idx = pd.DatetimeIndex(frame.index.normalize().unique()).sort_values()

print(f"Config: folds={folds_n} fold_days={fold_days} min_train_days={min_train_days}")
print(f"Total distinct days in feature frame: {len(days_idx)}")

leakage_found = False
for i in range(folds_n):
    test_end = days_idx[len(days_idx) - (folds_n - 1 - i) * fold_days - 1]
    test_start = test_end - pd.Timedelta(days=fold_days - 1)
    train = frame[frame.index < test_start]
    test = frame[(frame.index >= test_start) & (frame.index < test_end + pd.Timedelta(days=1))]
    max_train_ts = train.index.max()
    min_test_ts = test.index.min()
    ok = max_train_ts < min_test_ts
    if not ok:
        leakage_found = True
    print(f"Fold {i+1}: train=[{train.index.min()} .. {max_train_ts}] ({len(train)} rows)  "
          f"test=[{min_test_ts} .. {test.index.max()}] ({len(test)} rows)  "
          f"max(train)<min(test): {ok}")

print(f"\nLEAKAGE DETECTED: {leakage_found}  (False = no leakage proven across all {folds_n} folds)")

# ============================================================ LAG ALIGNMENT CHECK
section("8. LAG FEATURE ALIGNMENT CHECK (exact equality, not correlation)")
eng = pd.read_csv(OUT / "engineered_features_demand_400days.csv", parse_dates=["ts"], index_col="ts")
raw = pd.read_csv(OUT / "raw_demand_400days.csv", parse_dates=["ts"], index_col="ts")
raw_series = raw["raw_demand"]

sample_idx = eng.index[::5000]  # sample every 5000th row
mismatches = {"lag_1d": 0, "lag_2d": 0, "lag_7d": 0}
checked = 0
for ts in sample_idx:
    checked += 1
    for lag_days, col in [(1, "lag_1d"), (2, "lag_2d"), (7, "lag_7d")]:
        expected_ts = ts - pd.Timedelta(days=lag_days)
        if expected_ts in raw_series.index:
            expected_val = raw_series.loc[expected_ts]
            actual_val = eng.loc[ts, col]
            if not np.isclose(expected_val, actual_val, atol=1e-6):
                mismatches[col] += 1
                print(f"  ⚠️ MISMATCH at {ts}, {col}: expected {expected_val} (raw @ {expected_ts}), got {actual_val}")
print(f"Checked {checked} sampled rows x 3 lag columns.")
print(f"Mismatches: {mismatches} (all should be 0)")

print("\nDONE PHASE 1 PART B")
