"""SQLAlchemy engine for the Postgres CSV store.

Reads DATABASE_URL from the environment; falls back to the docker-compose
default (see docker-compose.yml and .env.example at the repo root) so
`docker compose up -d` with no .env already works.

Requires the [db] extra: pip install -e ".[db]"
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine

DEFAULT_DATABASE_URL = "postgresql+psycopg2://kseb:kseb@localhost:5433/kseb"


def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_engine(url, future=True)
