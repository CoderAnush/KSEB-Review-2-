#!/usr/bin/env python3
"""Create synthetic data CSV files."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.adapters.synthetic import make_synthetic_adapter
from app.forecasting.features import points_to_frame

OUTPUT_DIR = Path(__file__).parent.parent / "output"
END_DATE = date(2026, 7, 1)
DAYS = 400

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("\nCreating synthetic data CSV files...")
    print("Output: " + str(OUTPUT_DIR) + "\n")

    targets = [
        ("demand", "demand_mw", 42),
        ("price", "price_dam_inr_mwh", 43),
        ("inflow", "inflow_mwh", 44),
    ]

    for name, series_id, seed in targets:
        print("[*] " + name + "...")
        adapter = make_synthetic_adapter(name, series_id, seed)
        points = []

        start_date = END_DATE - timedelta(days=DAYS)
        d = start_date
        while d < END_DATE:
            points.extend(adapter.generate_day(d))
            d += timedelta(days=1)

        df = points_to_frame(points)
        if df.index.name == 'ts':
            df.index = df.index.tz_localize(None)

        output_file = OUTPUT_DIR / f"synthetic_{name}_{DAYS}days.csv"
        df.to_csv(output_file)
        print("    OK - " + output_file.name + " (" + str(len(df)) + " rows)\n")

    print("DONE!")

if __name__ == "__main__":
    main()
