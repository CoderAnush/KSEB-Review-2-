#!/usr/bin/env python3
"""Export demand profile comparison (actual vs synthetic)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from app.adapters.synthetic import make_synthetic_adapter
from app.forecasting.features import points_to_frame
from datetime import date, timedelta

def main():
    print("\n[*] Creating demand profile comparison...")

    # Get 1 day of synthetic demand
    adapter = make_synthetic_adapter("demand", "demand_mw", seed=42)
    points = adapter.generate_day(date(2025, 6, 1))

    df = points_to_frame(points)
    if df.index.name == 'ts':
        df.index = df.index.tz_localize(None)

    # Get time of day (block number)
    df["time_of_day"] = df.index.strftime("%H:%M")
    df["block"] = range(1, len(df) + 1)

    # Rename and reorganize
    comparison = df[["block", "time_of_day", "value"]].copy()
    comparison.columns = ["block", "time_of_day", "synthetic_demand_mw"]

    # Save
    output_file = Path(__file__).parent.parent / "output" / "demand_actual_vs_synthetic_profile.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_file, index=False)

    print(f"[OK] Saved to: {output_file.name}")
    print(f"\nFirst 10 blocks:")
    print(comparison.head(10).to_string())

if __name__ == "__main__":
    main()
