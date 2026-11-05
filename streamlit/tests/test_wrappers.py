"""Wrapper tests: contract, rspiro fixtures and validation."""

import pandas as pd
import pytest

from quadrant.constants import SPIROMETRY_PARAMS
from quadrant.wrappers import (
    TABLE_COLUMNS,
    compute_gli_2012,
    compute_gli_global_2022,
    compute_nhanes3,
    validate_subject_inputs,
)
from tests.conftest import read_fixture

# Contract from CLAUDE.md: predicted, LLN and z-score within 0.01 of the
# reference. Percent of predicted is on a 0 to 100 scale and gets 0.05.
TOLERANCE = 0.01
TOLERANCE_PERCENT = 0.05


def _cases(name):
    rows = read_fixture(name)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["case_id"], []).append(row)
    return list(grouped.values())


def _check_case(table, rows):
    assert list(table["parameter"]) == [r["parameter"] for r in rows]
    for (_, got), want in zip(table.iterrows(), rows):
        assert got["predicted"] == pytest.approx(float(want["predicted"]), abs=TOLERANCE)
        assert got["lln"] == pytest.approx(float(want["lln"]), abs=TOLERANCE)
        assert got["z_score"] == pytest.approx(float(want["z_score"]), abs=TOLERANCE)
        assert got["percent_predicted"] == pytest.approx(
            float(want["percent_predicted"]), abs=TOLERANCE_PERCENT
        )


def _args(rows, with_ethnicity):
    first = rows[0]
    args = dict(
        age_years=float(first["age_years"]),
        height_cm=float(first["height_cm"]),
        sex_code=int(first["sex_code"]),
        fev1=float(first["fev1_input"]),
        fvc=float(first["fvc_input"]),
    )
    if with_ethnicity:
        args["ethnicity_code"] = int(first["ethnicity_code"])
    return args


@pytest.mark.parametrize("rows", _cases("gli_2012_reference_cases.csv"))
def test_gli_2012_matches_rspiro(rows):
    _check_case(compute_gli_2012(**_args(rows, True)), rows)


@pytest.mark.parametrize("rows", _cases("gli_global_2022_reference_cases.csv"))
def test_gli_global_2022_matches_rspiro(rows):
    _check_case(compute_gli_global_2022(**_args(rows, False)), rows)


@pytest.mark.parametrize("rows", _cases("nhanes3_reference_cases.csv"))
def test_nhanes3_matches_rspiro(rows):
    _check_case(compute_nhanes3(**_args(rows, True)), rows)


def test_fixtures_hold_at_least_five_cases_per_family():
    for name in (
        "gli_2012_reference_cases.csv",
        "gli_global_2022_reference_cases.csv",
        "nhanes3_reference_cases.csv",
    ):
        assert len(_cases(name)) >= 5


@pytest.mark.parametrize(
    "table",
    [
        compute_gli_2012(40, 170, 1, 1, 3.0, 4.0),
        compute_gli_global_2022(40, 170, 1, 3.0, 4.0),
        compute_nhanes3(40, 170, 1, 1, 3.0, 4.0),
    ],
)
def test_wrappers_return_the_long_form_contract(table):
    assert isinstance(table, pd.DataFrame)
    assert list(table.columns) == list(TABLE_COLUMNS)
    assert list(table["parameter"]) == list(SPIROMETRY_PARAMS)
    assert table.loc[table["parameter"] == "FEV1FVC", "observed"].iloc[0] == pytest.approx(0.75)


def test_ratio_is_returned_as_a_fraction_for_every_family():
    for table in (
        compute_gli_2012(40, 170, 1, 1, 3.0, 4.0),
        compute_nhanes3(40, 170, 1, 1, 3.0, 4.0),
    ):
        ratio = table[table["parameter"] == "FEV1FVC"].iloc[0]
        assert 0.5 < ratio["predicted"] < 1.0
        assert 0.5 < ratio["lln"] < ratio["predicted"]


def test_female_codes_map_to_the_female_equations():
    male = compute_gli_global_2022(40, 170, 1, 3.0, 4.0)
    female = compute_gli_global_2022(40, 170, 2, 3.0, 4.0)
    assert female["predicted"].iloc[0] < male["predicted"].iloc[0]


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (dict(age_years=-1), "age_years"),
        (dict(height_cm=30), "height_cm"),
        (dict(sex_code=9), "sex_code"),
        (dict(ethnicity_code=99), "ethnicity_code"),
        (dict(fev1=5.0, fvc=4.0), "fev1 cannot exceed fvc"),
        (dict(fev1=0.0), "positive"),
        (dict(age_years=None), "age_years"),
        (dict(age_years=float("nan")), "age_years"),
    ],
)
def test_gli_2012_rejects_bad_inputs(kwargs, message):
    base = dict(age_years=40, height_cm=170, sex_code=1, ethnicity_code=1, fev1=3.0, fvc=4.0)
    base.update(kwargs)
    with pytest.raises(ValueError, match=message):
        compute_gli_2012(**base)


def test_gli_age_range_is_3_to_95():
    with pytest.raises(ValueError, match="between 3 and 95"):
        compute_gli_2012(2.9, 100, 1, 1, 1.2, 1.4)
    with pytest.raises(ValueError, match="between 3 and 95"):
        compute_gli_global_2022(95.1, 170, 1, 2.0, 3.0)
    assert len(compute_gli_2012(3, 100, 1, 1, 1.2, 1.4)) == 3
    assert len(compute_gli_global_2022(95, 170, 1, 2.0, 3.0)) == 3


def test_nhanes3_age_range_is_8_to_80():
    with pytest.raises(ValueError, match="between 8 and 80"):
        compute_nhanes3(7.9, 130, 1, 1, 1.8, 2.1)
    with pytest.raises(ValueError, match="between 8 and 80"):
        compute_nhanes3(80.1, 170, 1, 1, 2.0, 3.0)
    assert len(compute_nhanes3(80, 170, 1, 1, 2.0, 3.0)) == 3


def test_nhanes3_height_outside_the_sampled_range_gives_a_message():
    # pyspiro returns NA here. The wrapper must say so, not return NaN.
    with pytest.raises(ValueError, match="no reference value"):
        compute_nhanes3(40, 150, 1, 2, 3.0, 4.0)


def test_gli_global_has_no_ethnicity_argument():
    with pytest.raises(TypeError):
        compute_gli_global_2022(40, 170, 1, 3.0, 4.0, ethnicity_code=1)


def test_validate_skips_ethnicity_when_not_requested():
    validate_subject_inputs(age_years=40, height_cm=170, sex_code=1, fev1=3.0, fvc=4.0)
