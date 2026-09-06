#!/usr/bin/env python3
"""Regenerate chart_demand_profile_after.png: real KSEB 8-day mean vs the
calibrated synthetic generator, using make_synthetic_adapter() so the ADR-14
calibration in configs/adapters.yaml actually applies (bug fixed 2026-09-06).

The original script that produced this chart (and chart_demand_profile.png /
chart_demand_delta.png) is not in this repo; this replaces it with one that is
live and reproducible.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from app.adapters.synthetic import make_synthetic_adapter
from datetime import date, timedelta

OUT_DIR = Path(__file__).parent.parent / "output"


def main():
    """Generate the demand profile calibration comparison chart."""
    # --- Real KSEB 8-day mean profile (96 blocks) ---
    real = pd.read_csv(OUT_DIR / "kseb_8day_schedule_tidy.csv")
    real_profile = real.groupby("block")["Total Demand with Actual Drawn"].mean().sort_index()
    assert len(real_profile) == 96, f"expected 96 blocks, got {len(real_profile)}"

    # --- Calibrated synthetic profile (May, matching the real data's month) ---
    adapter = make_synthetic_adapter("demand", "demand_mw")
    may_days = [date(2026, 5, d) for d in range(5, 13)]  # same 8 calendar days, different year
    sim_blocks = {b: [] for b in range(1, 97)}
    for d in may_days:
        for p in adapter.generate_day(d):
            block = ((p.ts.hour * 60 + p.ts.minute) // 15) + 1
            sim_blocks[block].append(p.value)
    sim_profile = pd.Series({b: np.mean(v) for b, v in sim_blocks.items()}).sort_index()

    mape = float(np.mean(np.abs((real_profile.values - sim_profile.values) / real_profile.values)) * 100)
    print(f"Calibrated synthetic vs real KSEB 8-day mean profile MAPE: {mape:.2f}%")

    hours = [(b - 1) * 0.25 for b in range(1, 97)]

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(hours, real_profile.values, label="KSEB actual (8-day mean)", color="#0074D9", linewidth=2.5)
    ax.plot(hours, sim_profile.values, label=f"Calibrated synthetic ({mape:.1f}% MAPE)",
            color="#2ECC40", linewidth=2.2, linestyle="--")
    ax.set_xlabel("Hour of day (IST)", fontsize=12)
    ax.set_ylabel("Demand (MW)", fontsize=12)
    ax.set_title("Demand Profile: KSEB Actual vs Calibrated Synthetic",
                  fontsize=13, fontweight="bold")
    ax.set_xticks(range(0, 25, 3))
    ax.legend(fontsize=11, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out_path = OUT_DIR / "chart_demand_profile_after.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[OK] saved {out_path.name}")


if __name__ == "__main__":
    main()
