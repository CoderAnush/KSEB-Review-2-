"""Tests for app.db.load_csvs' pure column/table-name sanitization logic.

No Postgres connection needed - sanitize() and dedupe() are pure string
functions. The rest of app/db/ (actually loading into Postgres) is exercised
manually via `docker compose up -d && python -m app.db.load_csvs` and
verified with `python -m app.db.verify_roundtrip`, not in this unit suite,
since CI/local runs shouldn't require a live database just to run pytest.
"""

from __future__ import annotations

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy", reason="requires the [db] extra: pip install -e '.[db]'")

from app.db.load_csvs import dedupe, sanitize  # noqa: E402


def test_sanitize_lowercases_and_collapses_special_chars():
    assert sanitize("Total Demand with Actual Drawn") == "total_demand_with_actual_drawn"
    assert sanitize("PX RATE/UNIT") == "px_rate_unit"
    assert sanitize("SYSTEM.ID_GEN_MW.MEAS.MW (Idukki)") == "system_id_gen_mw_meas_mw_idukki"


def test_sanitize_strips_leading_trailing_underscores():
    assert sanitize("  leading and trailing  ") == "leading_and_trailing"
    assert sanitize("...dots...") == "dots"


def test_sanitize_never_returns_empty_string():
    assert sanitize("") == "col"
    assert sanitize("###") == "col"


def test_dedupe_disambiguates_collisions_deterministically():
    names = ["value", "Value", "VALUE"]  # all sanitize to 'value'
    sanitized = [sanitize(n) for n in names]
    out = dedupe(sanitized)
    assert out == ["value", "value_1", "value_2"]
    assert len(set(out)) == len(out)  # no remaining collisions


def test_dedupe_is_a_noop_when_no_collisions():
    names = ["fold", "test_start", "mape_pct"]
    assert dedupe(names) == names
