"""Load every CSV in output/ into Postgres - the DB becomes the source of
truth for this data going forward; output/*.csv stays as the portable,
git-committed export that charts and docs read from.

Table and column names are sanitized (lowercased, non-alphanumeric runs
collapsed to a single underscore) because several KSEB field-data CSVs have
raw column names like 'SYSTEM.ID_GEN_MW.MEAS.MW (Idukki)' or
'PX RATE/UNIT' that Postgres would otherwise require quoting for on every
query. Sanitization is deterministic, so re-running this script always
produces the same schema, and the original -> sanitized mapping is printed
during load for anyone writing SQL against the result.

Requires a running Postgres (see docker-compose.yml at the repo root:
`docker compose up -d`) and the [db] extra: pip install -e ".[db]"

Usage (from backend/):
    python -m app.db.load_csvs
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.connection import get_engine  # noqa: E402

OUT_DIR = Path(__file__).parent.parent.parent.parent / "output"


def sanitize(name: str) -> str:
    """Postgres-safe identifier: lowercase, non-alnum runs collapsed to '_'."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()
    return s or "col"


def dedupe(names: list[str]) -> list[str]:
    """Disambiguate sanitized names that collided (e.g. two columns -> same slug)."""
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def main() -> None:
    engine = get_engine()
    csvs = sorted(OUT_DIR.glob("*.csv"))
    if not csvs:
        print(f"No CSVs found in {OUT_DIR}")
        return

    print(f"Loading {len(csvs)} CSV files from {OUT_DIR} into Postgres...\n")
    for csv_path in csvs:
        table = sanitize(csv_path.stem)
        df = pd.read_csv(csv_path)
        original_cols = list(df.columns)
        df.columns = dedupe([sanitize(c) for c in df.columns])
        renamed = sum(1 for o, n in zip(original_cols, df.columns) if str(o).strip().lower() != n)

        df.to_sql(table, engine, if_exists="replace", index=False)
        print(f"  [OK] {csv_path.name:45s} -> table '{table}'  "
              f"({len(df)} rows, {len(df.columns)} cols, {renamed} renamed)")

    print(f"\nDone. {len(csvs)} tables loaded.")
    print("Verify with: docker compose exec postgres psql -U kseb -d kseb -c '\\dt'")
    print("Round-trip check: python -m app.db.export_csvs")


if __name__ == "__main__":
    main()
