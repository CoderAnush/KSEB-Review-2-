"""Export every Postgres table (loaded via load_csvs.py) back to CSV.

Writes to output/db_export/, NOT output/ directly - this must never
overwrite the canonical, git-committed CSVs in output/, since those keep
their exact original column names (e.g. 'Total Demand with Actual Drawn')
that downstream chart scripts and the lag-feature exact-match test depend
on, while the DB copy has sanitized column names. This script exists to
prove the Postgres round-trip preserves the data itself (row counts,
values) even though the column identifiers differ.

Requires a running Postgres with data already loaded (see load_csvs.py)
and the [db] extra: pip install -e ".[db]"

Usage (from backend/):
    python -m app.db.export_csvs
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.connection import get_engine  # noqa: E402

EXPORT_DIR = Path(__file__).parent.parent.parent.parent / "output" / "db_export"


def main() -> None:
    engine = get_engine()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    tables = inspect(engine).get_table_names()
    if not tables:
        print("No tables found. Run 'python -m app.db.load_csvs' first.")
        return

    print(f"Exporting {len(tables)} tables from Postgres to {EXPORT_DIR}...\n")
    for table in sorted(tables):
        df = pd.read_sql_table(table, engine)
        out_path = EXPORT_DIR / f"{table}.csv"
        df.to_csv(out_path, index=False)
        print(f"  [OK] {table:45s} -> {out_path.name}  ({len(df)} rows, {len(df.columns)} cols)")

    print(f"\nDone. {len(tables)} CSVs written to {EXPORT_DIR}")
    print("Row counts above should match the originals in output/ (see verify_roundtrip.py).")


if __name__ == "__main__":
    main()
