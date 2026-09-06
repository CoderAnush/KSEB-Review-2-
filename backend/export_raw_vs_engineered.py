#!/usr/bin/env python3
"""Export raw data alongside engineered features for comparison."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
from app.config import load_config
from app.forecasting.features import build_feature_frame, points_to_frame
from app.adapters.synthetic import make_synthetic_adapter
from datetime import date, timedelta

def main():
    print("\n[*] Generating 30-day synthetic demand data...")

    adapter = make_synthetic_adapter("demand", "demand_mw", seed=42)
    points = []

    # Use 30 days for a good visualization (2,880 blocks)
    END_DATE = date(2026, 7, 1)
    START_DATE = END_DATE - timedelta(days=30)

    d = START_DATE
    while d < END_DATE:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)

    # Step 1: Raw data
    raw_data = points_to_frame(points)
    if raw_data.index.name == 'ts':
        raw_data.index = raw_data.index.tz_localize(None)

    print(f"[OK] Generated {len(raw_data)} blocks (30 days)")

    # Step 2: Engineered features — read the REAL demand target config, not hardcoded
    cfg = load_config("forecasting")
    target_cfg = cfg["targets"]["demand"]
    print(f"[*] Engineering features (lags_days={target_cfg['lags_days']}, "
          f"weather_features={target_cfg['weather_features']})...")

    engineered = build_feature_frame(raw_data, None, target_cfg)

    print(f"[OK] Engineered {len(engineered)} rows")

    # Step 3: Create side-by-side view
    print("\n[*] Creating side-by-side comparison...")

    comparison = pd.DataFrame({
        "Timestamp": engineered.index,
        "value_raw": engineered["value"],
        "lag_1d": engineered["lag_1d"],
        "lag_2d": engineered["lag_2d"],
        "lag_7d": engineered["lag_7d"],
        "block_sin": engineered["block_sin"],
        "block_cos": engineered["block_cos"],
        "dow": engineered["dow"],
        "is_weekend": engineered["is_weekend"],
        "is_holiday": engineered["is_holiday"],
        "month_sin": engineered["month_sin"],
        "month_cos": engineered["month_cos"],
        "temperature_2m": engineered["temperature_2m"],
        "precipitation": engineered["precipitation"],
        "cloud_cover": engineered["cloud_cover"],
    })

    # Export full dataset
    output_file = Path(__file__).parent.parent / "output" / "raw_vs_engineered_30days.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_file, index=False)

    print(f"[OK] Saved to: {output_file.name}")
    print(f"    Rows: {len(comparison)}")
    print(f"    Columns: {len(comparison.columns)}")

    # Display sample
    print("\n[*] SAMPLE DATA (first 5 rows after lag drop):")
    print(comparison.head().to_string())

    print("\n[*] FEATURE STATISTICS:")
    print(comparison[["value_raw", "lag_1d", "lag_7d", "dow", "month_sin", "month_cos"]].describe().to_string())

    # Show raw value range
    print(f"\n[*] RAW DEMAND VALUE RANGE:")
    print(f"    Min: {comparison['value_raw'].min():.2f} MW")
    print(f"    Max: {comparison['value_raw'].max():.2f} MW")
    print(f"    Mean: {comparison['value_raw'].mean():.2f} MW")
    print(f"    Std: {comparison['value_raw'].std():.2f} MW")

    # Show lag correlation
    print(f"\n[*] LAG FEATURE CORRELATION with VALUE:")
    lag_corr_1d = comparison["value_raw"].corr(comparison["lag_1d"])
    lag_corr_7d = comparison["value_raw"].corr(comparison["lag_7d"])
    print(f"    lag_1d correlation: {lag_corr_1d:.4f} (strong!)")
    print(f"    lag_7d correlation: {lag_corr_7d:.4f} (strong weekly pattern)")

    # Show temporal patterns
    print(f"\n[*] TEMPORAL FEATURE PATTERNS:")
    print(f"    block_sin: mean={comparison['block_sin'].mean():.4f}, std={comparison['block_sin'].std():.4f}")
    print(f"    block_cos: mean={comparison['block_cos'].mean():.4f}, std={comparison['block_cos'].std():.4f}")
    print(f"    (These are circular encodings, so mean should be ~0)")

    print(f"\n[*] CALENDAR FEATURE PATTERNS:")
    print(f"    dow (day of week):")
    for d in range(7):
        count = (comparison['dow'] == d).sum()
        print(f"        {d} {'(Mon)' if d==0 else '(Tue)' if d==1 else '(Wed)' if d==2 else '(Thu)' if d==3 else '(Fri)' if d==4 else '(Sat)' if d==5 else '(Sun)'}: {count} blocks")

    weekday = (comparison['is_weekend'] == 0).sum()
    weekend = (comparison['is_weekend'] == 1).sum()
    print(f"    Weekdays: {weekday} blocks, Weekends: {weekend} blocks")

    print("\n[DONE] RAW vs ENGINEERED dataset ready for PPT!")

if __name__ == "__main__":
    main()
