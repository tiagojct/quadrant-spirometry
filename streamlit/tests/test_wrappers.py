"""Wrapper tests: contract, rspiro fixtures and validation."""

import pandas as pd
import pytest

from quadrant.constants import SPIROMETRY_PARAMS
from quadrant.wrappers import (
    TABLE_COLUMNS,
    compute_gli_2012,
    compute_gli_global_2022,
    compute_kubota_2014,
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


def test_long_table_allows_nan_limits_only_when_not_required():
    import pytest as _pytest
    from quadrant.wrappers import _long_table

    class Ref:
        def __init__(self, predicted=1.0, percent=100.0):
            self.p, self.c = predicted, percent

        def lms(self, *a):
            return (0, self.p, 0, 0)

        def lln(self, *a):
            return float("nan")

        def zscore(self, *a):
            return float("nan")

        def percent(self, *a):
            return self.c

    args = ((1, 40, 170), {"FEV1": 1, "FVC": 2, "FEV1FVC": 3},
            {"FEV1": 3.0, "FVC": 4.0, "FEV1FVC": 0.75}, "Test")
    df = _long_table(Ref(), *args, limits_required=False)
    assert df["lln"].isna().all() and df["z_score"].isna().all()
    with _pytest.raises(ValueError):
        _long_table(Ref(), *args)
    with _pytest.raises(ValueError):
        _long_table(Ref(predicted=float("nan")), *args, limits_required=False)
    with _pytest.raises(ValueError):
        _long_table(Ref(percent=float("nan")), *args, limits_required=False)


@pytest.mark.parametrize("rows", _cases("jrs_reference_cases.csv"))
def test_kubota_2014_matches_rspiro(rows):
    _check_case(compute_kubota_2014(**_args(rows, False)), rows)


def test_kubota_age_range_is_17_to_95():
    with pytest.raises(ValueError, match="between 17 and 95"):
        compute_kubota_2014(16, 170, 1, 3.0, 4.0)
    with pytest.raises(ValueError, match="between 17 and 95"):
        compute_kubota_2014(96, 170, 1, 2.0, 3.0)
    assert len(compute_kubota_2014(17, 170, 1, 3.0, 4.0)) == 3
    assert len(compute_kubota_2014(95, 170, 1, 2.0, 3.0)) == 3
    assert len(compute_kubota_2014(17, 160, 2, 2.8, 3.4)) == 3


def test_kubota_women_are_accepted_below_94_years():
    # rspiro returns NA for women from 94 years. A fractional age below 94
    # still has a value (rspiro: 1.8283 L at 93.5 years, 170 cm).
    assert len(compute_kubota_2014(93, 160, 2, 1.2, 1.6)) == 3
    assert len(compute_kubota_2014(93.5, 160, 2, 1.2, 1.6)) == 3
    assert len(compute_kubota_2014(93.99, 160, 2, 1.2, 1.6)) == 3
    for age in (94.0, 94, 95):
        with pytest.raises(
            ValueError,
            match="for women the JRS 2014 equations are available below 94 years",
        ):
            compute_kubota_2014(age, 160, 2, 1.2, 1.6)


def test_kubota_age_edges_are_symmetric_for_both_sexes():
    # rspiro returns NA at 16 and 96 for both sexes and at 95.01 for men.
    for sex in (1, 2):
        for age in (16, 96):
            with pytest.raises(ValueError, match="between 17 and 95"):
                compute_kubota_2014(age, 165, sex, 1.5, 2.0)
    with pytest.raises(ValueError, match="between 17 and 95"):
        compute_kubota_2014(95.01, 170, 1, 2.0, 3.0)


def test_kubota_men_are_not_limited_below_95():
    for age in (93, 94, 95):
        assert len(compute_kubota_2014(age, 170, 1, 2.0, 3.0)) == 3


def test_kubota_non_integer_age_matches_rspiro():
    # rspiro floors the age only for the spline lookup. The LMS terms use
    # the exact age, so 30.7 years differs from 30. Values: rspiro 0.5,
    # height 1.70 m, FEV1 pred and LLN.
    male = compute_kubota_2014(30.7, 170, 1, 3.0, 4.0).iloc[0]
    assert male["predicted"] == pytest.approx(3.83508979, abs=TOLERANCE)
    assert male["lln"] == pytest.approx(3.15990941, abs=TOLERANCE)
    female = compute_kubota_2014(30.7, 170, 2, 3.0, 4.0).iloc[0]
    assert female["predicted"] == pytest.approx(3.19842422, abs=TOLERANCE)
    assert female["lln"] == pytest.approx(2.60004671, abs=TOLERANCE)
    assert male["predicted"] != pytest.approx(
        compute_kubota_2014(30, 170, 1, 3.0, 4.0).iloc[0]["predicted"], abs=1e-4
    )


def test_kubota_ratio_is_a_fraction():
    table = compute_kubota_2014(40, 170, 1, 3.0, 4.0)
    ratio = table[table["parameter"] == "FEV1FVC"].iloc[0]
    assert ratio["observed"] == pytest.approx(0.75)
    assert 0.7 < ratio["predicted"] < 0.9
    assert ratio["lln"] < ratio["predicted"]


def test_kubota_sex_mapping():
    male = compute_kubota_2014(40, 170, 1, 3.0, 4.0)
    female = compute_kubota_2014(40, 170, 2, 3.0, 4.0)
    assert male["predicted"].iloc[0] > female["predicted"].iloc[0]
