#!/usr/bin/env python3
"""Regenerate charts 1-7: KSEB 8-day reconciliation charts from real field data.

These charts come from kseb_8day_schedule_tidy.csv and kseb_8day_hydro_tidy.csv,
representing 8 days of real Kerala State Electricity Board (KSEB) field observations
from May 5–12, 2025.

Source: data/Data_final.xlsx, post-processed via scripts/reconcile_kseb_8day.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

OUT_DIR = Path(__file__).parent.parent / "output"


def main():
    """Regenerate all 6 KSEB 8-day reconciliation charts."""

    # Load KSEB field data
    try:
        schedule = pd.read_csv(OUT_DIR / "kseb_8day_schedule_tidy.csv")
        hydro = pd.read_csv(OUT_DIR / "kseb_8day_hydro_tidy.csv")
    except FileNotFoundError as e:
        print(f"ERROR: Missing source CSV: {e}")
        return False

    # Convert timestamp columns to datetime
    schedule["ts_ist"] = pd.to_datetime(schedule["ts_ist"])
    hydro["ts_ist"] = pd.to_datetime(hydro["ts_ist"])

    # --- Chart 1: Demand Profile (actual demand over 8 days) ---
    try:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(schedule["ts_ist"], schedule["Total Demand with Actual Drawn"],
                color="#0074D9", linewidth=1.5, label="Actual Demand")
        ax.set_xlabel("Date (IST)", fontsize=11)
        ax.set_ylabel("Demand (MW)", fontsize=11)
        ax.set_title("KSEB Demand: 8-Day Field Observation (May 5–12, 2025)",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_demand_profile.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_demand_profile.png")
    except Exception as e:
        print(f"[FAIL] chart_demand_profile.png: {e}")
        return False

    # --- Chart 2: Demand Delta (error/deviation from expected) ---
    try:
        fig, ax = plt.subplots(figsize=(14, 6))
        # Compute a simple expected demand (daily mean) and show deviation
        daily_mean = schedule.groupby(schedule["ts_ist"].dt.date)["Total Demand with Actual Drawn"].transform("mean")
        delta = schedule["Total Demand with Actual Drawn"] - daily_mean
        colors = ["#2ECC40" if x >= 0 else "#FF4136" for x in delta]
        ax.bar(schedule["ts_ist"], delta, color=colors, width=0.01, alpha=0.7)
        ax.set_xlabel("Date (IST)", fontsize=11)
        ax.set_ylabel("Demand Deviation from Daily Mean (MW)", fontsize=11)
        ax.set_title("KSEB Demand: Deviation from Daily Mean",
                     fontsize=12, fontweight="bold")
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8)
        ax.grid(True, alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_demand_delta.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_demand_delta.png")
    except Exception as e:
        print(f"[FAIL] chart_demand_delta.png: {e}")
        return False

    # --- Chart 3: Scheduling Deviation Pattern ---
    try:
        fig, ax = plt.subplots(figsize=(14, 6))
        if "Scheduled Demand" in schedule.columns and "Actual Demand" in schedule.columns:
            scheduled = schedule.get("Scheduled Demand", schedule.get("Total Scheduled Power", 0))
            actual = schedule["Total Demand with Actual Drawn"]
            deviation = actual - scheduled
        else:
            # Fallback: compare actual to a simple forecast baseline
            deviation = schedule["Total Demand with Actual Drawn"] - schedule["Total Demand with Actual Drawn"].rolling(window=96).mean()

        ax.plot(schedule["ts_ist"], deviation, color="#FF851B", linewidth=1.0, label="Deviation")
        ax.fill_between(schedule["ts_ist"], deviation, 0, color="#FF851B", alpha=0.3)
        ax.set_xlabel("Date (IST)", fontsize=11)
        ax.set_ylabel("Deviation (MW)", fontsize=11)
        ax.set_title("KSEB Scheduling: Actual vs Scheduled Deviation Pattern",
                     fontsize=12, fontweight="bold")
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_deviation_pattern.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_deviation_pattern.png")
    except Exception as e:
        print(f"[FAIL] chart_deviation_pattern.png: {e}")
        return False

    # --- Chart 4: Hydro Energy (hydroelectric generation) ---
    try:
        fig, ax = plt.subplots(figsize=(14, 6))
        if "Hydel total" in hydro.columns:
            hydro_col = "Hydel total"
        elif "Total Hydro w/ Pump" in hydro.columns:
            hydro_col = "Total Hydro w/ Pump"
        else:
            hydro_col = [c for c in hydro.columns if "total" in c.lower() or "hydro" in c.lower()][0]

        ax.plot(hydro["ts_ist"], hydro[hydro_col], color="#0099FF", linewidth=2, label="Hydro Generation")
        ax.fill_between(hydro["ts_ist"], hydro[hydro_col], 0, color="#0099FF", alpha=0.2)
        ax.set_xlabel("Date (IST)", fontsize=11)
        ax.set_ylabel("Generation (MW)", fontsize=11)
        ax.set_title("KSEB Hydro Energy: 8-Day Generation Profile",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_hydro_energy.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_hydro_energy.png")
    except Exception as e:
        print(f"[FAIL] chart_hydro_energy.png: {e}")
        return False

    # --- Chart 5: Market Rates (clearing prices over time) ---
    try:
        fig, ax = plt.subplots(figsize=(14, 6))
        if "PX RATE/UNIT" in schedule.columns:
            rates = schedule["PX RATE/UNIT"] * 1000  # Convert from ₹/kWh to ₹/MWh
            ax.plot(schedule["ts_ist"], rates, color="#B10DC9", linewidth=1.5, label="Clearing Rate (₹/MWh)")
        else:
            # Fallback: use any rate column available
            rate_col = [c for c in schedule.columns if "RATE" in c.upper()][0]
            ax.plot(schedule["ts_ist"], schedule[rate_col], color="#B10DC9", linewidth=1.5)

        ax.set_xlabel("Date (IST)", fontsize=11)
        ax.set_ylabel("Rate (₹/MWh)", fontsize=11)
        ax.set_title("KSEB Market Rates: Day-Ahead Clearing Prices",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_market_rates.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_market_rates.png")
    except Exception as e:
        print(f"[FAIL] chart_market_rates.png: {e}")
        return False

    # --- Chart 6: Supply Mix (power source composition) ---
    try:
        fig, ax = plt.subplots(figsize=(14, 7))

        # Extract power source columns (ISGS, LTA, MTOA, PX, RTM, OTS, REN, Internal)
        source_cols = []
        for col in schedule.columns:
            if any(src in col.upper() for src in ["ISGS", "LTA", "MTOA", "PX", "RTM", "OTS", "REN", "INTERNAL"]):
                if "MW" in col and "RATE" not in col:
                    source_cols.append(col)

        if source_cols:
            sources_data = schedule[["ts_ist"] + source_cols].set_index("ts_ist")
            ax.stackplot(sources_data.index, *[sources_data[col] for col in source_cols],
                        labels=source_cols, alpha=0.8)
            ax.set_xlabel("Date (IST)", fontsize=11)
            ax.set_ylabel("Power Supply (MW)", fontsize=11)
            ax.set_title("KSEB Supply Mix: Power Source Composition",
                         fontsize=12, fontweight="bold")
            ax.legend(fontsize=8, loc="upper left")
            ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(OUT_DIR / "chart_supply_mix.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("[OK] chart_supply_mix.png")
    except Exception as e:
        print(f"[FAIL] chart_supply_mix.png: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
