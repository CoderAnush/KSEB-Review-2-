#!/usr/bin/env python3
"""Show how 4 raw columns became 13 engineered features (per configs/forecasting.yaml)."""

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
    print("\n" + "="*90)
    print("HOW 4 RAW COLUMNS BECAME 13 ENGINEERED FEATURES")
    print("="*90)

    # Step 1: Show raw data (4 columns)
    print("\n[STEP 1] START WITH 4 RAW COLUMNS")
    print("-" * 90)

    adapter_demand = make_synthetic_adapter("demand", "demand_mw", seed=42)
    adapter_price = make_synthetic_adapter("price", "price_dam_inr_mwh", seed=43)
    adapter_inflow = make_synthetic_adapter("inflow", "inflow_mwh", seed=44)

    points_demand = []
    points_price = []
    points_inflow = []

    # Use just 2 days for clear visualization
    END_DATE = date(2026, 7, 1)
    START_DATE = END_DATE - timedelta(days=2)

    d = START_DATE
    while d < END_DATE:
        points_demand.extend(adapter_demand.generate_day(d))
        points_price.extend(adapter_price.generate_day(d))
        points_inflow.extend(adapter_inflow.generate_day(d))
        d += timedelta(days=1)

    demand_df = points_to_frame(points_demand)
    price_df = points_to_frame(points_price)
    inflow_df = points_to_frame(points_inflow)

    if demand_df.index.name == 'ts':
        demand_df.index = demand_df.index.tz_localize(None)
        price_df.index = price_df.index.tz_localize(None)
        inflow_df.index = inflow_df.index.tz_localize(None)

    # Combine into raw data
    raw_data = pd.DataFrame({
        "ts": demand_df.index,
        "demand_mw": demand_df["value"].values,
        "price_inr_mwh": price_df["value"].values,
        "inflow_mwh": inflow_df["value"].values
    })
    raw_data.set_index("ts", inplace=True)

    print(f"\nRaw Data Shape: {raw_data.shape[0]} rows × {raw_data.shape[1]} columns")
    print(f"Columns: {list(raw_data.columns)}")
    print(f"\nFirst 5 rows:")
    print(raw_data.head(5).to_string())

    # Step 2: Extract demand only
    print("\n\n[STEP 2] EXTRACT DEMAND ONLY (1 column → stays as 'value')")
    print("-" * 90)

    demand_only = demand_df.copy()
    print(f"\nDemand only shape: {demand_only.shape[0]} rows × {demand_only.shape[1]} column")
    print(f"Column: {list(demand_only.columns)}")
    print(f"\nFirst 5 values:")
    print(demand_only.head(5).to_string())

    print(f"\n[NOTE] We DROP price & inflow (they're for separate models)")
    print(f"     - Price forecasting = separate model with price features")
    print(f"     - Inflow forecasting = separate model with inflow features")
    print(f"     - Demand forecasting = THIS model with demand features")

    # Step 3: Add features - using the REAL demand target config, not hardcoded
    cfg = load_config("forecasting")
    target_cfg = cfg["targets"]["demand"]
    print(f"\n\n[STEP 3] ENGINEER 13 FEATURES FROM THIS 1 COLUMN + TIMESTAMP")
    print(f"(lags_days={target_cfg['lags_days']}, weather_features={target_cfg['weather_features']})")
    print("-" * 90)

    engineered = build_feature_frame(demand_only, None, target_cfg)

    print(f"\nEngineered shape: {engineered.shape[0]} rows × {engineered.shape[1]} columns")
    print(f"\nColumns breakdown:")
    print(f"  1. value           ← ORIGINAL demand (1 column)")
    print(f"\n  AUTOREGRESSIVE (3 features - from demand history):")
    print(f"    2. lag_1d        ← Demand from 24 hours ago")
    print(f"    3. lag_2d        ← Demand from 48 hours ago")
    print(f"    4. lag_7d        ← Demand from 7 days ago")
    print(f"\n  TEMPORAL (2 features - from timestamp):")
    print(f"    5. block_sin     ← Time-of-day sine wave (00:00-23:45)")
    print(f"    6. block_cos     ← Time-of-day cosine wave (00:00-23:45)")
    print(f"\n  CALENDAR (3 features - from timestamp + holiday calendar):")
    print(f"    7. dow           ← Day of week (0=Mon, 6=Sun)")
    print(f"    8. is_weekend    ← Binary (Sat/Sun = 1)")
    print(f"    9. is_holiday    ← Binary (Onam/Vishu/fixed dates = 1)")
    print(f"\n  SEASONAL (2 features - from timestamp):")
    print(f"   10. month_sin     ← Month of year sine wave (Jan-Dec)")
    print(f"   11. month_cos     ← Month of year cosine wave (Jan-Dec)")
    print(f"\n  WEATHER (3 features - from API or synthetic):")
    print(f"   12. temperature_2m ← Temperature in °C")
    print(f"   13. precipitation  ← Rain in mm")
    print(f"   14. cloud_cover    ← Cloud coverage %")

    print(f"\n\nFinal result: 1 original + 13 engineered = 14 total columns")
    print(f"\nFirst 5 rows:")
    print(engineered.head(5).to_string())

    # Show the transformation
    print("\n\n" + "="*90)
    print("TRANSFORMATION DIAGRAM")
    print("="*90)

    diagram = """
RAW DATA (4 columns)
├─ ts               (timestamp)
├─ demand_mw        ◄─ EXTRACTED
├─ price_inr_mwh    (dropped - separate model)
└─ inflow_mwh       (dropped - separate model)
         │
         ▼
DEMAND ONLY (1 column)
└─ value = demand_mw
         │
         ├─ From DEMAND HISTORY
         │  ├─ lag_1d (yesterday at same time)
         │  ├─ lag_2d (2 days ago at same time)
         │  └─ lag_7d (last week at same time)
         │
         ├─ From TIMESTAMP
         │  ├─ block_sin/cos (time within 24h)
         │  ├─ month_sin/cos (time within year)
         │  └─ dow (day of week)
         │
         ├─ From TIMESTAMP + CALENDAR
         │  ├─ is_weekend (Sat/Sun flag)
         │  └─ is_holiday (Onam/Vishu flag)
         │
         └─ From WEATHER API (or synthetic = 0)
            ├─ temperature_2m
            ├─ precipitation
            └─ cloud_cover
                   │
                   ▼
ENGINEERED DATA (14 columns)
├─ value (original)
├─ lag_1d, lag_2d, lag_7d (autoregressive)
├─ block_sin, block_cos (temporal)
├─ dow, is_weekend (calendar)
├─ is_holiday (holidays)
├─ month_sin, month_cos (seasonal)
└─ temperature_2m, precipitation, cloud_cover (weather)
    """

    print(diagram)

    print("\n" + "="*90)
    print("KEY INSIGHT")
    print("="*90)
    print("""
We START with 1 column (demand value), then CREATE 13 new features from:
  • Historical patterns (lags: 1, 2, and 7 days back)
  • Time patterns (sin/cos encoding)
  • Calendar structure (weekends, holidays)
  • External data (weather)

This is called FEATURE ENGINEERING - turning raw data into ML-ready features!

Note: per the trained model's real feature_importances_ (see
ALL_CHARTS_AT_A_GLANCE.md), is_weekend, temperature_2m, cloud_cover and
precipitation currently contribute 0% importance - the model never splits on
them. They're still generated here for completeness but aren't pulling weight.
    """)

if __name__ == "__main__":
    main()
