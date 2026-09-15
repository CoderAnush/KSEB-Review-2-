"""Postgres persistence for output/*.csv (optional, requires the [db] extra).

connection.py   SQLAlchemy engine, reads DATABASE_URL (see docker-compose.yml
                and .env.example at the repo root).
load_csvs.py    output/*.csv -> Postgres tables (sanitized column names).
export_csvs.py  Postgres tables -> output/db_export/*.csv (round-trip proof;
                never overwrites the canonical CSVs in output/).
verify_roundtrip.py  Compares output/*.csv against output/db_export/*.csv
                     row-by-row and value-by-value.

`app/db/repositories/` is a reserved-for-future-use stub (async repository
classes for a live service layer) and is unrelated to the CSV loader above.
"""
