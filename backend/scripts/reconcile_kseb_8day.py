"""Regenerate output/kseb_filedrop.csv + reconciliation_stats.json from data/Data_final.xlsx.

Reproducibility backfill for the KSEB 8-day field data (ADR-14). The original ad-hoc
reconciliation script was never committed; this reconstructs the two machine-consumed artifacts
from the raw workbook so the real-data chain is reproducible end to end.

Consumed artifacts this reproduces:
  * kseb_filedrop.csv          demand_mw (col Z "Total Demand with Actual Drawn") +
                               price_dam_inr_mwh (col I "PX RATE/UNIT" x 1000). The file_drop
                               ingest input. Target: byte-identical to the committed CSV.
  * reconciliation_stats.json  cost.total_8day_inr = sum of per-block "Total Cost" (col AD).
                               Read by `eval_savings --realized-stats` for the MILP-vs-KSEB-actual row.

ponytail: descriptive-only fields in the committed stats — market/deviation histograms,
per-station hydro (needs the Hydro_final sheet), and synthetic_vs_actual (depends on the
PRE-ADR-14 synthetic generator and no longer reproduces) — are NOT recomputed here; they live in
output/FINDINGS_KSEB_8DAY.md. Recompute them only if a future FINDINGS regen needs them machine-made.

Usage (from backend/, needs the [ingest] extra for openpyxl):
  python -m scripts.reconcile_kseb_8day --xlsx ../data/Data_final.xlsx --out-dir ../output

Verify: the regenerated kseb_filedrop.csv should diff-clean against the committed one, and
cost.total_8day_inr should equal 2068610789.09 (+/- 0.01).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from app.domain import timeblocks as tb

N_DAYS = 8
BLOCKS = 96
N = N_DAYS * BLOCKS  # 768
START = date(2025, 5, 5)

SHEET = "Shedule break rate"  # workbook name has a TRAILING SPACE; matched via .strip()
HEADER_ROW = 2  # 0-indexed -> Excel row 3 is the real header (rows 1-2 are group labels)

DEMAND_COL = "Total Demand with Actual Drawn"
PX_RATE_COL = "PX RATE/UNIT"  # INR/kWh; x1000 -> INR/MWh
COST_COL = "Total Cost"
HYDRO_COL = "Hydel total"
RATE_COLS = {
    "ISGS": "ISGS Average RATE/UNIT", "LTA": "LTA RATE/UNIT", "MTOA": "MTOA RATE/UNIT",
    "PX": "PX RATE/UNIT", "RTM": "RTM RATE/UNIT", "OTS": "OTS RATE/UNIT", "REN": "REN RATE/UNIT",
    "Internal": "Internal RATE/UNIT",
}
MW_COLS = {
    "ISGS": "SYSTEM.KL_ISGS.ADD.MW", "LTA": "SYSTEM.KER_LTA_NET.MES1.MW",
    "MTOA": "SYSTEM.KER_MTOA_NET.MES1.MW", "PX": "SYSTEM.KER_PX_NET.MES1.MW",
    "RTM": "SYSTEM.KER_RTM.MES1.MW", "OTS": "SYSTEM.KL_OTS.ADD.MW", "REN": "SYSTEM.KL_REN.ADD.MW",
}


def _ts_index() -> list[str]:
    """Canonical 15-min IST index rebuilt from row order (the workbook Time serial is unreliable)."""
    out: list[str] = []
    for i in range(N):
        day = START + timedelta(days=i // BLOCKS)
        block = i % BLOCKS + 1
        out.append(tb.block_start(day, block).isoformat())
    return out


def load_schedule(xlsx: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(xlsx)
    name = next(s for s in xls.sheet_names if s.strip() == SHEET)
    df = pd.read_excel(xls, sheet_name=name, header=HEADER_ROW, nrows=N)
    if len(df) != N:
        raise ValueError(f"expected {N} data rows in {name!r}, got {len(df)}")
    return df


def _summ(s: pd.Series) -> dict[str, float]:
    return {
        "min": round(float(s.min()), 4), "p50": round(float(s.median()), 4),
        "mean": round(float(s.mean()), 4), "max": round(float(s.max()), 4),
    }


def reconcile(xlsx: Path, out_dir: Path) -> dict:
    df = load_schedule(xlsx)
    ts = _ts_index()

    # --- kseb_filedrop.csv (byte-repro target): demand block then price block ---
    demand = [round(float(v), 2) for v in df[DEMAND_COL]]
    price = [round(float(v) * 1000.0, 2) for v in df[PX_RATE_COL]]
    long = pd.concat(
        [
            pd.DataFrame({"ts": ts, "series_id": "demand_mw", "value": demand}),
            pd.DataFrame({"ts": ts, "series_id": "price_dam_inr_mwh", "value": price}),
        ],
        ignore_index=True,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    long.to_csv(out_dir / "kseb_filedrop.csv", index=False, lineterminator="\n")

    # --- reconciliation_stats.json (cost.total_8day_inr is the consumed field) ---
    total_cost = float(df[COST_COL].sum())
    hydro_mwh = df[HYDRO_COL].to_numpy().reshape(N_DAYS, BLOCKS).sum(axis=1) * 0.25  # MWh/day
    stats = {
        "rates": {k: _summ(df[c]) for k, c in RATE_COLS.items()},
        "mw": {k: _summ(df[c]) for k, c in MW_COLS.items()},
        "demand": {
            "min": round(float(df[DEMAND_COL].min()), 2),
            "mean": round(float(df[DEMAND_COL].mean()), 2),
            "max": round(float(df[DEMAND_COL].max()), 2),
        },
        "hydro_total": _summ(df[HYDRO_COL]),
        "hydro_daily_energy_mwh": {
            "min": round(float(hydro_mwh.min()), 1),
            "mean": round(float(hydro_mwh.mean()), 1),
            "max": round(float(hydro_mwh.max()), 1),
        },
        "cost": {
            "total_8day_inr": round(total_cost, 2),
            "mean_block_inr": round(float(df[COST_COL].mean()), 1),
        },
    }
    (out_dir / "reconciliation_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", default="../data/Data_final.xlsx")
    parser.add_argument("--out-dir", default="../output")
    args = parser.parse_args()
    stats = reconcile(Path(args.xlsx), Path(args.out_dir))
    tot = stats["cost"]["total_8day_inr"]
    print(f"reconciled -> {args.out_dir}/kseb_filedrop.csv + reconciliation_stats.json")
    print(f"cost.total_8day_inr = {tot:,.2f}  (expected 2,068,610,789.09)")


if __name__ == "__main__":
    main()
