#!/usr/bin/env python3
"""Master script to regenerate ALL 10 output charts from source data.

Charts 1-7: KSEB 8-day field-data reconciliation charts
Charts 8-10: Forecasting model validation charts

Usage:
    python -m scripts.generate_all_charts

This script regenerates all committed PNG charts from their source data
(CSVs, JSONs, raw KSEB 8-day data). It ensures full reproducibility
and can be re-run after any config or data change to verify outputs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).parent.parent.parent / "output"


def main():
    print("=" * 80)
    print("REGENERATING ALL 10 CHARTS FROM SOURCE DATA")
    print("=" * 80)

    # Charts 8-10: Forecasting model validation (from plot_real_model_outputs.py)
    print("\n[Charts 8-10] Forecasting model validation charts...")
    try:
        from backend.plot_real_model_outputs import main as plot_main
        plot_main()
        print("✅ Charts 8-10 regenerated successfully")
    except Exception as e:
        print(f"❌ Charts 8-10 FAILED: {e}")
        return False

    # Chart: Calibration comparison (from generate_demand_calibration_chart.py)
    print("\n[Chart demand_profile_after] Calibration comparison chart...")
    try:
        from backend.generate_demand_calibration_chart import main as gen_main
        gen_main()
        print("✅ Chart demand_profile_after regenerated successfully")
    except Exception as e:
        print(f"❌ Chart demand_profile_after FAILED: {e}")
        return False

    # Charts 1-7: KSEB 8-day reconciliation charts (from kseb_8day_*.csv sources)
    print("\n[Charts 1-7] KSEB 8-day reconciliation charts...")
    try:
        from backend.plot_kseb_reconciliation_charts import main as recon_main
        recon_main()
        print("✅ Charts 1-7 regenerated successfully")
    except Exception as e:
        print(f"❌ Charts 1-7 FAILED: {e}")
        return False

    print("\n" + "=" * 80)
    print("✅ ALL 10 CHARTS REGENERATED SUCCESSFULLY")
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
    ]
    for i, chart in enumerate(charts, 1):
        path = OUT_DIR / chart
        status = "✅ exists" if path.exists() else "❌ MISSING"
        print(f"  {i:2d}. {chart:40s} {status}")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
