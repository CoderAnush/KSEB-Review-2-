#!/usr/bin/env python3
"""Export the engineered features for demand forecasting to CSV.

Feature set is read from configs/forecasting.yaml (not hardcoded) so this always
matches what the real model actually trains on.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from app.config import load_config
from app.forecasting.features import build_feature_frame, points_to_frame
from app.adapters.synthetic import make_synthetic_adapter
from datetime import date, timedelta

def main():
    print("\n[*] Generating synthetic demand data...")

    # Generate synthetic demand
    adapter = make_synthetic_adapter("demand", "demand_mw", seed=42)
    points = []

    END_DATE = date(2026, 7, 1)
    START_DATE = END_DATE - timedelta(days=400)

    d = START_DATE
    while d < END_DATE:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)

    # Convert to DataFrame
    history = points_to_frame(points)

    # Remove timezone for CSV compatibility
    if history.index.name == 'ts':
        history.index = history.index.tz_localize(None)

    print(f"[OK] Generated {len(history)} blocks")

    # Build feature frame using the REAL demand target config (not hardcoded)
    cfg = load_config("forecasting")
    target_cfg = cfg["targets"]["demand"]
    print(f"\n[*] Engineering features (lags_days={target_cfg['lags_days']}, "
          f"weather_features={target_cfg['weather_features']})...")

    features_frame = build_feature_frame(history, None, target_cfg)

    print(f"[OK] Engineered features frame: {features_frame.shape[0]} rows × {features_frame.shape[1]} columns")
    print(f"\nFeature columns ({len(features_frame.columns)}):")
    for i, col in enumerate(features_frame.columns, 1):
        print(f"  {i:2d}. {col}")

    # Save to CSV
    output_file = Path(__file__).parent.parent / "output" / "engineered_features_demand_400days.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    features_frame.to_csv(output_file)
    print(f"\n[OK] Saved to: {output_file.name}")
    print(f"\nFirst 5 rows:")
    print(features_frame.head().to_string())
    print(f"\nLast 5 rows:")
    print(features_frame.tail().to_string())
    print(f"\nStatistics:")
    print(features_frame.describe().to_string())

if __name__ == "__main__":
    main()
