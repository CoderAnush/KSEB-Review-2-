#!/usr/bin/env python3
"""Show the feature engineering process step-by-step."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
import math
from app.config import load_config
from app.forecasting.features import points_to_frame, kerala_holidays
from app.adapters.synthetic import make_synthetic_adapter
from app.domain import timeblocks as tb
from datetime import date, timedelta

def main():
    print("\n" + "="*80)
    print("FEATURE ENGINEERING PROCESS - STEP BY STEP")
    print("="*80)

    # Step 1: Generate raw synthetic demand
    print("\n[STEP 1] Generate RAW Synthetic Demand Data")
    print("-" * 80)

    adapter = make_synthetic_adapter("demand", "demand_mw", seed=42)
    points = []

    END_DATE = date(2026, 7, 1)
    # Need MORE than max(lags_days) history or every row's oldest lag is NaN and
    # dropna() below removes the whole frame. Use 21 days so lag_7d has 14 days
    # of surviving rows after the drop (bug found 2026-09-06: 7-day window
    # produced a 0-row CSV because lag_7d needs a full 7 days of prior history).
    START_DATE = END_DATE - timedelta(days=21)

    d = START_DATE
    while d < END_DATE:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)

    history = points_to_frame(points)

    # Remove timezone
    if history.index.name == 'ts':
        history.index = history.index.tz_localize(None)

    print(f"\nRaw Data Shape: {history.shape[0]} rows × {history.shape[1]} columns")
    print(f"Date Range: {history.index.min()} to {history.index.max()}")
    print(f"\nFirst 10 raw demand values (MW):")
    print(history.head(10).to_string())

    # Step 2: Add Lag Features - real lags_days from configs/forecasting.yaml, not hardcoded
    cfg = load_config("forecasting")
    lags_days = cfg["targets"]["demand"]["lags_days"]
    print(f"\n\n[STEP 2] Add LAG FEATURES (Autoregressive) - lags_days={lags_days}")
    print("-" * 80)

    frame = history.copy()

    lag_cols = []
    for d_lag in lags_days:
        col = f"lag_{d_lag}d"
        frame[col] = frame["value"].shift(tb.BLOCKS_PER_DAY * d_lag)
        lag_cols.append(col)
        print(f"{col}: Shift by {tb.BLOCKS_PER_DAY * d_lag} blocks ({d_lag} day(s))")

    print(f"\nAfter adding lags (first 10 rows):")
    print(frame[["value"] + lag_cols].head(10).to_string())

    # Step 3: Add Temporal Features
    print("\n\n[STEP 3] Add TEMPORAL FEATURES (Time-of-Day)")
    print("-" * 80)

    idx = frame.index

    # block_sin and block_cos: circular encoding of time within 24-hour cycle
    block = (idx.hour * 60 + idx.minute) // tb.BLOCK_MINUTES + 1  # 1-96
    frame["block_sin"] = np.sin(2 * math.pi * block / tb.BLOCKS_PER_DAY)
    frame["block_cos"] = np.cos(2 * math.pi * block / tb.BLOCKS_PER_DAY)

    print(f"block_sin/cos: Circular encoding of 96 blocks per day")
    print(f"  Block 1 (00:00): sin={frame['block_sin'].iloc[0]:.4f}, cos={frame['block_cos'].iloc[0]:.4f}")
    print(f"  Block 48 (12:00): sin={frame['block_sin'].iloc[96*2+48]:.4f}, cos={frame['block_cos'].iloc[96*2+48]:.4f}")
    print(f"  Block 96 (23:45): sin={frame['block_sin'].iloc[96*4+95]:.4f}, cos={frame['block_cos'].iloc[96*4+95]:.4f}")

    # Step 4: Add Calendar Features
    print("\n\n[STEP 4] Add CALENDAR FEATURES (Day/Week/Holiday)")
    print("-" * 80)

    frame["dow"] = idx.dayofweek  # 0=Monday, 6=Sunday
    frame["is_weekend"] = (idx.dayofweek >= 5).astype(int)

    print(f"dow (day-of-week): 0=Monday, 1=Tuesday, ..., 6=Sunday")
    print(f"is_weekend: 0=Weekday, 1=Saturday/Sunday")

    # Holiday flag
    years = range(idx.year.min(), idx.year.max() + 1)
    holidays = set()
    for y in years:
        holidays |= kerala_holidays(y)
    frame["is_holiday"] = pd.Series(idx.date, index=idx).isin(holidays).astype(int).to_numpy()

    print(f"is_holiday: Onam, Vishu, Independence Day, etc.")

    print(f"\nAfter adding calendar (sample rows):")
    print(frame[["value", "dow", "is_weekend", "is_holiday"]].iloc[0:5].to_string())

    # Step 5: Add Seasonal Features
    print("\n\n[STEP 5] Add SEASONAL FEATURES (Month/Year)")
    print("-" * 80)

    frame["month_sin"] = np.sin(2 * math.pi * idx.month / 12)
    frame["month_cos"] = np.cos(2 * math.pi * idx.month / 12)

    print(f"month_sin/cos: Circular encoding of 12 months")
    print(f"  Jan: sin={frame['month_sin'].iloc[0]:.4f}, cos={frame['month_cos'].iloc[0]:.4f}")
    print(f"  Jul: sin={frame['month_sin'].iloc[96*4]:.4f}, cos={frame['month_cos'].iloc[96*4]:.4f}")

    # Step 6: Add Weather Features
    print("\n\n[STEP 6] Add WEATHER FEATURES")
    print("-" * 80)

    frame["temperature_2m"] = 0.0  # No weather in synthetic (would come from API)
    frame["precipitation"] = 0.0
    frame["cloud_cover"] = 0.0

    print(f"temperature_2m: Temperature in °C")
    print(f"precipitation: Rain in mm")
    print(f"cloud_cover: Cloud coverage %")
    print(f"\nNote: Synthetic data uses weather=0. Real data would fetch from OpenMeteo API.")

    # Step 7: Drop NaN rows
    print("\n\n[STEP 7] Drop rows with NaN lags")
    print("-" * 80)

    before_drop = len(frame)
    lag_cols = [c for c in frame.columns if c.startswith("lag_")]
    frame = frame.dropna(subset=lag_cols)
    after_drop = len(frame)
    dropped = before_drop - after_drop

    print(f"Before drop: {before_drop} rows")
    print(f"After drop: {after_drop} rows")
    print(f"Dropped: {dropped} rows (first 7 days, where lag_7d is NaN)")

    # Final summary
    print("\n\n" + "="*80)
    print("FINAL ENGINEERED FEATURES")
    print("="*80)

    print(f"\nShape: {frame.shape[0]} rows × {frame.shape[1]} columns")
    print(f"\nColumns:")
    for i, col in enumerate(frame.columns, 1):
        print(f"  {i:2d}. {col}")

    print(f"\nSample data (first 5 rows after engineering):")
    print(frame.head().to_string())

    # Export to CSV
    output_file = Path(__file__).parent.parent / "output" / "feature_engineering_process_sample.csv"
    frame.to_csv(output_file)
    print(f"\n✅ Saved sample to: {output_file.name}")

    # Create detailed breakdown file
    print("\n\n" + "="*80)
    print("FEATURE CATEGORIES SUMMARY")
    print("="*80)

    breakdown = """
FEATURE ENGINEERING BREAKDOWN
==============================

1. AUTOREGRESSIVE (Lag) FEATURES - 3 features
   |- lag_1d: Demand from 24 hours ago (1 day = 96 blocks)
   |- lag_2d: Demand from 48 hours ago (2 days = 192 blocks)
   |- lag_7d: Demand from 7 days ago (7 days = 672 blocks)
   +- Why: Captures daily and weekly patterns

2. TEMPORAL (Intra-day) FEATURES - 2 features
   |- block_sin: Circular encoding of time-of-day (0-1 wave)
   |- block_cos: Circular encoding of time-of-day (0-1 wave)
   +- Why: 00:00 = (sin~0, cos~1), 06:00 = (sin~1, cos~0), etc.

3. CALENDAR (Structural) FEATURES - 3 features
   |- dow: Day of week (0=Mon, 1=Tue, ..., 6=Sun)
   |- is_weekend: Binary flag (0=weekday, 1=Sat/Sun)
   |- is_holiday: Binary flag (0=normal, 1=Onam/Vishu/etc)
   +- Why: Different demand patterns on holidays/weekends

4. SEASONAL (Annual) FEATURES - 2 features
   |- month_sin: Circular encoding of month (1-12)
   |- month_cos: Circular encoding of month (1-12)
   +- Why: Summer vs. monsoon vs. winter demand differences

5. WEATHER FEATURES - 3 features
   |- temperature_2m: Temperature in C
   |- precipitation: Rain in mm
   |- cloud_cover: Cloud coverage %
   +- Why: Temperature affects AC load, rain affects solar (generated
      as 0 in synthetic data; see note on real importance below)

TOTAL: 13 features + 1 target (value) = 14 columns
(Per configs/forecasting.yaml targets.demand: lags_days=[1,2,7],
weather_features=[temperature_2m, cloud_cover, precipitation])

RAW DATA STATISTICS (400-day synthetic dataset, 37,728 rows after lag drop,
from output/engineered_features_demand_400days.csv):
|- Value (demand): mean=2,993.9 MW, std=547.5 MW, range=[2,167-5,207]
|- lag_1d correlation with value: 0.9721
|- lag_2d correlation with value: 0.9437
|- lag_7d correlation with value: 0.9683
|- Block_sin/cos: mean~0, std~0.71 (circular uniform distribution)
|- dow: mean=2.99, std=2.00 (uniform 0-6)
|- month_sin/cos: mean~0 (circular uniform)
+- Weather: all zeros in synthetic data (real deployment would fetch live)

REAL FEATURE IMPORTANCE (from an actually-trained LightGBM model,
output/real_feature_importance.json - NOT estimated, pulled directly from
the model's .feature_importances_):
1. lag_7d       19.9%  <- most important
2. lag_1d       18.3%
3. lag_2d       16.6%
4. dow          13.3%  (surprisingly strong)
5. month_sin    10.0%
6. month_cos     7.8%
7. block_sin     7.2%
8. block_cos     5.7%
9. is_holiday    1.2%
10. is_weekend, temperature_2m, cloud_cover, precipitation: 0% each
    (the trained model never split on these 4 features at all)
    """

    print(breakdown)

    # Save breakdown to file
    breakdown_file = Path(__file__).parent.parent / "output" / "FEATURE_ENGINEERING_BREAKDOWN.txt"
    breakdown_file.write_text(breakdown, encoding='utf-8')
    print(f"✅ Saved breakdown to: {breakdown_file.name}")

if __name__ == "__main__":
    main()
