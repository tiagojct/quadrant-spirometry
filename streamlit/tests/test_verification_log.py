"""Tests for the verification log and the JRS reference fixture."""

import csv
from pathlib import Path

from quadrant.registry import EQUATIONS

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "docs" / "verification.md"
FIXTURE = ROOT / "tests" / "testthat" / "fixtures" / "jrs_reference_cases.csv"
ALLOWED_STATUS = {"verified", "single source", "excluded"}


def _table_rows():
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] == "key" or set(cells[0]) <= {"-", ":", " "}:
            continue
        rows.append(cells)
    return rows


def _fixture_rows():
    with FIXTURE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_registered_equation_has_a_verification_row():
    rows = _table_rows()
    keys = {row[0].strip("`") for row in rows}
    for key in EQUATIONS:
        assert key in keys, f"{key} has no row in docs/verification.md"
    for row in rows:
        assert len(row) == 6, row
        assert row[5].strip("`") in ALLOWED_STATUS, row


def test_jrs_fixture_has_fifteen_cases_with_three_rows_each():
    rows = _fixture_rows()
    case_ids = {r["case_id"] for r in rows}
    assert len(case_ids) == 15
    assert len(rows) == 45
    for cid in case_ids:
        params = sorted(r["parameter"] for r in rows if r["case_id"] == cid)
        assert params == ["FEV1", "FEV1FVC", "FVC"]


def test_jrs_fixture_covers_both_sexes_and_the_age_edges():
    rows = _fixture_rows()
    assert {int(r["sex_code"]) for r in rows} == {1, 2}
    ages = {int(float(r["age_years"])) for r in rows}
    assert {17, 18, 30, 50, 80, 95} <= ages
