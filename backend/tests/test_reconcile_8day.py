"""Check the 8-day reconciliation reproduces the consumed artifacts from the real xlsx.

Skips cleanly when openpyxl (the [ingest] extra) or the workbook is absent, so the
core-deps-only unit subset stays green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("openpyxl")

XLSX = Path(__file__).resolve().parents[2] / "data" / "Data_final.xlsx"


@pytest.mark.skipif(not XLSX.exists(), reason="KSEB Data_final.xlsx not present")
def test_reconcile_reproduces_cost_and_filedrop(tmp_path: Path) -> None:
    from scripts.reconcile_kseb_8day import reconcile

    stats = reconcile(XLSX, tmp_path)

    # the ONLY field the pipeline consumes: KSEB realized cost total
    assert abs(stats["cost"]["total_8day_inr"] - 2_068_610_789.09) < 1.0

    lines = (tmp_path / "kseb_filedrop.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "ts,series_id,value"
    assert len(lines) == 1 + 768 * 2  # header + demand block + price block

    # compare parsed fields, not raw float text (byte-identity is the manual git-diff verify step)
    d_ts, d_series, d_val = lines[1].split(",")  # first demand row
    assert (d_ts, d_series) == ("2025-05-05T00:00:00+05:30", "demand_mw")
    assert float(d_val) == 4452.59
    p_ts, p_series, p_val = lines[769].split(",")  # first price row (col I x 1000)
    assert (p_ts, p_series) == ("2025-05-05T00:00:00+05:30", "price_dam_inr_mwh")
    assert abs(float(p_val) - 4070.6) < 0.005
