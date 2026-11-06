"""Shared test helpers."""

import csv
from pathlib import Path

import pytest

# The CSV fixtures hold rspiro output and are shared with the R test suite.
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "testthat" / "fixtures"


def read_fixture(name: str) -> list[dict]:
    with open(FIXTURE_DIR / name, newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURE_DIR
