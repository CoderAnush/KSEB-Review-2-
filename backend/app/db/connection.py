"""SQLAlchemy engine for the Postgres CSV store.

Reads DATABASE_URL from the environment - no working default is baked in
here on purpose, so no credential (even a trivial local-dev one) ever lives
in committed source. Copy .env.example to .env (same values docker-compose.yml
reads) and either `python-dotenv`-load it or export it in your shell before
running any app.db.* script.

Requires the [db] extra: pip install -e ".[db]"
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine


def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env (repo root), "
            "export its values, then retry. See docker-compose.yml for the "
            "matching Postgres service."
        )
    return create_engine(url, future=True)
