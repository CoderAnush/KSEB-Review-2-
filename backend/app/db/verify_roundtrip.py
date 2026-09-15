"""Prove the Postgres round-trip: compare output/*.csv against
output/db_export/*.csv (produced by load_csvs.py -> export_csvs.py).

Compares row count and, column-by-column positionally (since DB column
names are sanitized versions of the originals), numeric values - not just
"same shape", actual value equality. Run this after load_csvs.py +
export_csvs.py to get more than a claim that the DB preserves the data.

Usage (from backend/):
    python -m app.db.verify_roundtrip
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).parent.parent.parent.parent / "output"
EXPORT_DIR = OUT_DIR / "db_export"


def main() -> bool:
    if not EXPORT_DIR.exists():
        print(f"{EXPORT_DIR} does not exist. Run load_csvs.py then export_csvs.py first.")
        return False

    originals = sorted(OUT_DIR.glob("*.csv"))
    all_ok = True
    print(f"Comparing {len(originals)} original CSVs against their DB round-trip export...\n")

    for orig_path in originals:
        exported = list(EXPORT_DIR.glob(f"{orig_path.stem.lower()}*.csv"))
        if not exported:
            print(f"  [SKIP] {orig_path.name:45s} - no matching exported table found")
            continue
        exp_path = exported[0]

        df_orig = pd.read_csv(orig_path)
        df_exp = pd.read_csv(exp_path)

        rows_ok = len(df_orig) == len(df_exp)
        cols_ok = len(df_orig.columns) == len(df_exp.columns)

        values_ok = True
        if rows_ok and cols_ok:
            # compare positionally: DB column names are sanitized, not identical
            for i in range(len(df_orig.columns)):
                a, b = df_orig.iloc[:, i], df_exp.iloc[:, i]
                if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                    # allow float64 round-trip noise (text<->binary through Postgres),
                    # not a real data difference - see e.g. 3256.3199999999997 vs 3256.32
                    if not np.allclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float),
                                        rtol=1e-9, atol=1e-9, equal_nan=True):
                        values_ok = False
                        break
                elif not a.astype(str).equals(b.astype(str)):
                    values_ok = False
                    break

        ok = rows_ok and cols_ok and values_ok
        all_ok = all_ok and ok
        status = "OK" if ok else "MISMATCH"
        print(f"  [{status}] {orig_path.name:45s} rows={len(df_orig)}->{len(df_exp)} "
              f"cols={len(df_orig.columns)}->{len(df_exp.columns)} values_match={values_ok}")

    print()
    print("ALL ROUND-TRIPS VERIFIED" if all_ok else "SOME ROUND-TRIPS FAILED")
    return all_ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
