#!/usr/bin/env python3
"""Regenerate the 400-day raw demand/price/inflow/combined CSVs.

The scripts that originally produced these files (Sep 4) are gone from the repo
and the inflow file was found stale vs the corrected ADR-14 config
(inflow_daily_mean_mwh: 9000 -> 19000). This regenerates all 4 from the current
SyntheticAdapter + configs/adapters.yaml so they match today's real config.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from app.adapters.synthetic import make_synthetic_adapter
from app.forecasting.features import points_to_frame
from datetime import date, timedelta

OUT_DIR = Path(__file__).parent.parent / "output"

SERIES = {
    "demand": ("demand", "demand_mw", 42, "raw_demand"),
    "price": ("price", "price_dam_inr_mwh", 43, "raw_price"),
    "inflow": ("inflow", "inflow_mwh", 44, "raw_inflow"),
}


def generate(name: str, series_id: str, seed: int, days: int, end: date) -> pd.DataFrame:
    adapter = make_synthetic_adapter(name, series_id, seed)
    points = []
    d = end - timedelta(days=days)
    while d < end:
        points.extend(adapter.generate_day(d))
        d += timedelta(days=1)
    frame = points_to_frame(points)
    if frame.index.name == "ts":
        frame.index = frame.index.tz_localize(None)
    return frame


def main() -> None:
    END_DATE = date(2026, 7, 1)
    DAYS = 400

    frames = {}
    for key, (name, series_id, seed, col_prefix) in SERIES.items():
        print(f"[*] Generating {name} ({DAYS} days, seed={seed})...")
        frame = generate(name, series_id, seed, DAYS, END_DATE)
        frames[key] = frame

        out = pd.DataFrame({"ts": frame.index, col_prefix: frame["value"].values})
        path = OUT_DIR / f"{col_prefix}_400days.csv"
        out.to_csv(path, index=False)
        print(f"    saved {path.name}: {len(out)} rows, "
              f"range [{out[col_prefix].min():.2f}, {out[col_prefix].max():.2f}]")

    print("\n[*] Building combined CSV...")
    combined = pd.DataFrame({
        "ts": frames["demand"].index,
        "demand_mw": frames["demand"]["value"].values,
        "price_inr_mwh": frames["price"]["value"].values,
        "inflow_mwh": frames["inflow"]["value"].values,
    })
    combined_path = OUT_DIR / "raw_combined_400days.csv"
    combined.to_csv(combined_path, index=False)
    print(f"    saved {combined_path.name}: {len(combined)} rows x {combined.shape[1]} columns")

    daily_inflow = frames["inflow"]["value"].mean() * 96
    print(f"\n[CHECK] Mean per-block inflow x 96 blocks/day = {daily_inflow:.1f} MWh/day "
          f"(configs/adapters.yaml target: 19,000 MWh/day)")

    print("\n[DONE] All 4 raw CSVs regenerated from the current config.")


if __name__ == "__main__":
    main()
