#!/usr/bin/env python3
"""Export raw synthetic data (before feature engineering)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from app.adapters.synthetic import make_synthetic_adapter
from app.forecasting.features import points_to_frame
from datetime import date, timedelta

def main():
    print("\n" + "="*80)
    print("EXPORTING RAW SYNTHETIC DATA (BEFORE FEATURE ENGINEERING)")
    print("="*80)

    OUTPUT_DIR = Path(__file__).parent.parent / "output"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    END_DATE = date(2026, 7, 1)
    DAYS = 400
    START_DATE = END_DATE - timedelta(days=DAYS)

    # Export three raw data series
    targets = [
        ("demand", "demand_mw", 42),
        ("price", "price_dam_inr_mwh", 43),
        ("inflow", "inflow_mwh", 44),
    ]

    for name, series_id, seed in targets:
        print(f"\n[*] Exporting raw {name} data...")

        adapter = make_synthetic_adapter(name, series_id, seed)
        points = []

        d = START_DATE
        while d < END_DATE:
            points.extend(adapter.generate_day(d))
            d += timedelta(days=1)

        df = points_to_frame(points)
        if df.index.name == 'ts':
            df.index = df.index.tz_localize(None)

        # Rename column to be clear
        df.columns = [f"raw_{name}"]

        # Export
        output_file = OUTPUT_DIR / f"raw_{name}_{DAYS}days.csv"
        df.to_csv(output_file)

        print(f"    OK - {output_file.name}")
        print(f"    Rows: {len(df)}")
        print(f"    Date range: {df.index.min()} to {df.index.max()}")
        print(f"    Value range: {df.iloc[:, 0].min():.2f} to {df.iloc[:, 0].max():.2f}")
        print(f"    Mean: {df.iloc[:, 0].mean():.2f}")

        # Show sample
        print(f"    First 5 rows:")
        print(f"    {df.head(5).to_string()}")

    # Create combined raw dataset
    print(f"\n[*] Creating combined raw dataset...")

    combined_points = {}

    for name, series_id, seed in targets:
        adapter = make_synthetic_adapter(name, series_id, seed)
        points = []

        d = START_DATE
        while d < END_DATE:
            points.extend(adapter.generate_day(d))
            d += timedelta(days=1)

        df = points_to_frame(points)
        if df.index.name == 'ts':
            df.index = df.index.tz_localize(None)

        combined_points[name] = df.iloc[:, 0]

    combined_df = pd.DataFrame(combined_points)
    combined_df.columns = ["demand_mw", "price_inr_mwh", "inflow_mwh"]

    output_file = OUTPUT_DIR / f"raw_combined_{DAYS}days.csv"
    combined_df.to_csv(output_file)

    print(f"    OK - {output_file.name}")
    print(f"    Rows: {len(combined_df)}")
    print(f"    Columns: {list(combined_df.columns)}")

    print(f"\n    Combined statistics:")
    print(combined_df.describe().to_string())

    print(f"\n    First 10 rows:")
    print(combined_df.head(10).to_string())

    print("\n" + "="*80)
    print("RAW DATA EXPORT COMPLETE")
    print("="*80)
    print("\nFiles created:")
    print(f"  • raw_demand_{DAYS}days.csv     - Raw demand in MW")
    print(f"  • raw_price_{DAYS}days.csv       - Raw prices in Rs/MWh")
    print(f"  • raw_inflow_{DAYS}days.csv      - Raw inflow in MWh")
    print(f"  • raw_combined_{DAYS}days.csv    - All three combined")
    print("\nUse these for your PPT to show the raw input data!")

if __name__ == "__main__":
    main()
