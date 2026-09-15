#!/usr/bin/env python3
"""Master script to regenerate ALL 16 output charts from source data.

Charts 1-7:   KSEB 8-day field-data reconciliation charts
Charts 8-10:  Demand forecasting model validation charts
Charts 11-13: Price forecasting model validation charts
Charts 14-16: Inflow forecasting model validation charts

Usage:
    python -m scripts.generate_all_charts

This script regenerates all committed PNG charts from their source data
(CSVs, JSONs, raw KSEB 8-day data). It ensures full reproducibility
and can be re-run after any config or data change to verify outputs.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = REPO_ROOT / "output"


def main():
    print("=" * 80)
    print("REGENERATING ALL 16 CHARTS FROM SOURCE DATA (demand + price + inflow)")
    print("=" * 80)

    # Re-extract real fold/feature-importance/holdout JSON for all 3 targets
    print("\n[Extract] Real model outputs for demand, price, inflow...")
    try:
        from backend.reports.extract_real_model_outputs import main as extract_main
        extract_main()
        print("✅ Real model outputs extracted successfully")
    except Exception as e:
        print(f"❌ Extraction FAILED: {e}")
        return False

    # Charts 8-16: Forecasting model validation for all 3 targets (from plot_real_model_outputs.py)
    print("\n[Charts 8-16] Forecasting model validation charts (demand, price, inflow)...")
    try:
        from backend.reports.plot_real_model_outputs import main as plot_main
        plot_main()
        print("✅ Charts 8-16 regenerated successfully")
    except Exception as e:
        print(f"❌ Charts 8-16 FAILED: {e}")
        return False

    # Chart: Calibration comparison (from generate_demand_calibration_chart.py)
    print("\n[Chart demand_profile_after] Calibration comparison chart...")
    try:
        from backend.reports.generate_demand_calibration_chart import main as gen_main
        gen_main()
        print("✅ Chart demand_profile_after regenerated successfully")
    except Exception as e:
        print(f"❌ Chart demand_profile_after FAILED: {e}")
        return False

    # Charts 1-7: KSEB 8-day reconciliation charts (from kseb_8day_*.csv sources)
    print("\n[Charts 1-7] KSEB 8-day reconciliation charts...")
    try:
        from backend.reports.plot_kseb_reconciliation_charts import main as recon_main
        recon_main()
        print("✅ Charts 1-7 regenerated successfully")
    except Exception as e:
        print(f"❌ Charts 1-7 FAILED: {e}")
        return False

    print("\n" + "=" * 80)
    print("✅ ALL 16 CHARTS REGENERATED SUCCESSFULLY")
    print("=" * 80)
    print("\nChart status:")
    charts = [
        "chart_demand_profile.png",
        "chart_demand_delta.png",
        "chart_deviation_pattern.png",
        "chart_hydro_energy.png",
        "chart_market_rates.png",
        "chart_supply_mix.png",
        "chart_demand_profile_after.png",
        "chart_real_validation_folds.png",
        "chart_real_feature_importance.png",
        "chart_real_holdout_forecast.png",
        "chart_price_validation_folds.png",
        "chart_price_feature_importance.png",
        "chart_price_holdout_forecast.png",
        "chart_inflow_validation_folds.png",
        "chart_inflow_feature_importance.png",
        "chart_inflow_holdout_forecast.png",
    ]
    all_present = True
    for i, chart in enumerate(charts, 1):
        path = OUT_DIR / chart
        exists = path.exists()
        all_present = all_present and exists
        status = "✅ exists" if exists else "❌ MISSING"
        print(f"  {i:2d}. {chart:40s} {status}")

    return all_present


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
