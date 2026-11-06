"""Wrapper tests: contract, rspiro fixtures and validation."""

import math

import pandas as pd
import pytest

from quadrant.constants import SPIROMETRY_PARAMS
from quadrant.wrappers import (
    TABLE_COLUMNS,
    compute_eccs_1993,
    compute_gli_2012,
    compute_gli_global_2022,
    compute_kubota_2014,
    compute_nhanes3,
    compute_pereira_2007,
    validate_subject_inputs,
)
from tests.conftest import read_fixture
from tests.independent import eccs_1993 as eccs_source
from tests.independent import pereira_2007 as pereira_paper

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


# Pereira 2007: wrapper against the independent module written from
# Tables 3 and 4 of the paper. The sampled ranges differ by sex: men 26 to
# 86 years and 152 to 192 cm, women 20 to 85 years and 137 to 182 cm.
PEREIRA_TOLERANCE = 0.005
PEREIRA_SEX = {1: "male", 2: "female"}
PEREIRA_CASES = [
    # (sex_code, age_years, height_cm, fev1, fvc)
    (1, 26, 185, 4.5, 5.6),
    (1, 40, 170, 3.0, 4.0),
    (1, 50, 175, 2.5, 3.6),
    (1, 60, 165, 3.2, 4.2),
    (1, 70, 180, 2.0, 4.0),
    (1, 86, 155, 1.4, 2.0),
    (1, 45, 152, 2.9, 3.6),
    (1, 55, 192, 4.0, 5.2),
    (2, 20, 165, 3.5, 4.1),
    (2, 30, 150, 2.0, 2.4),
    (2, 40, 160, 2.6, 3.3),
    (2, 60, 170, 1.8, 3.0),
    (2, 75, 180, 2.4, 2.9),
    (2, 85, 155, 1.5, 2.2),
    (2, 50, 137, 1.8, 2.2),
    (2, 35, 182, 3.2, 4.0),
]


def _pereira_expected(sex_code, age, height, parameter):
    sex = PEREIRA_SEX[sex_code]
    scale = 100.0 if parameter == "FEV1FVC" else 1.0
    return (
        pereira_paper.predicted(sex, age, height, parameter) / scale,
        pereira_paper.lower_limit(sex, age, height, parameter) / scale,
    )


@pytest.mark.parametrize("case", PEREIRA_CASES)
def test_pereira_matches_the_published_equations(case):
    sex_code, age, height, fev1, fvc = case
    table = compute_pereira_2007(age, height, sex_code, fev1, fvc)
    assert list(table.columns) == list(TABLE_COLUMNS)
    assert tuple(table["parameter"]) == SPIROMETRY_PARAMS
    observed = {"FEV1": fev1, "FVC": fvc, "FEV1FVC": fev1 / fvc}
    for _, row in table.iterrows():
        parameter = row["parameter"]
        want_pred, want_lln = _pereira_expected(sex_code, age, height, parameter)
        assert row["observed"] == pytest.approx(observed[parameter])
        assert row["predicted"] == pytest.approx(want_pred, abs=PEREIRA_TOLERANCE)
        assert row["lln"] == pytest.approx(want_lln, abs=PEREIRA_TOLERANCE)
        assert row["percent_predicted"] == pytest.approx(
            observed[parameter] / want_pred * 100, abs=TOLERANCE_PERCENT
        )
        # The paper publishes no residual standard deviation, so no z-score.
        assert pd.isna(row["z_score"])


def test_pereira_cases_fall_on_both_sides_of_the_lower_limit():
    for parameter, index in (("FEV1", 3), ("FVC", 4)):
        below = [
            case[index]
            < _pereira_expected(case[0], case[1], case[2], parameter)[1]
            for case in PEREIRA_CASES
        ]
        assert any(below) and not all(below), parameter


PEREIRA_MALE_AGE_MESSAGE = "for men the Pereira 2007 equations cover 26 to 86 years"
PEREIRA_FEMALE_AGE_MESSAGE = "for women the Pereira 2007 equations cover 20 to 85 years"
PEREIRA_MALE_HEIGHT_MESSAGE = "for men the Pereira 2007 equations cover 152 to 192 cm"
PEREIRA_FEMALE_HEIGHT_MESSAGE = "for women the Pereira 2007 equations cover 137 to 182 cm"


def test_pereira_age_range():
    for age in (19, 25.9, 87):
        with pytest.raises(ValueError, match=PEREIRA_MALE_AGE_MESSAGE):
            compute_pereira_2007(age, 170, 1, 3.0, 4.0)
    for age in (19, 85.5, 87):
        with pytest.raises(ValueError, match=PEREIRA_FEMALE_AGE_MESSAGE):
            compute_pereira_2007(age, 160, 2, 2.0, 3.0)
    assert len(compute_pereira_2007(20, 160, 2, 2.8, 3.4)) == 3
    assert len(compute_pereira_2007(86, 170, 1, 2.0, 3.0)) == 3
    assert len(compute_pereira_2007(26, 170, 1, 3.5, 4.5)) == 3
    assert len(compute_pereira_2007(85, 160, 2, 1.5, 2.0)) == 3


def test_pereira_height_range():
    for height in (151.9, 192.1):
        with pytest.raises(ValueError, match=PEREIRA_MALE_HEIGHT_MESSAGE):
            compute_pereira_2007(40, height, 1, 3.0, 4.0)
    for height in (136.9, 182.1):
        with pytest.raises(ValueError, match=PEREIRA_FEMALE_HEIGHT_MESSAGE):
            compute_pereira_2007(40, height, 2, 2.5, 3.0)
    assert len(compute_pereira_2007(40, 152, 1, 3.0, 4.0)) == 3
    assert len(compute_pereira_2007(40, 192, 1, 3.0, 4.0)) == 3
    assert len(compute_pereira_2007(40, 137, 2, 2.0, 2.5)) == 3
    assert len(compute_pereira_2007(40, 182, 2, 3.0, 4.0)) == 3


def test_pereira_ratio_is_a_fraction():
    table = compute_pereira_2007(40, 170, 1, 3.0, 4.0)
    ratio = table[table["parameter"] == "FEV1FVC"].iloc[0]
    assert ratio["observed"] == pytest.approx(0.75)
    assert 0.7 < ratio["predicted"] < 0.9
    assert ratio["lln"] < ratio["predicted"]


def test_pereira_sex_mapping():
    male = compute_pereira_2007(40, 170, 1, 3.0, 4.0)
    female = compute_pereira_2007(40, 170, 2, 3.0, 4.0)
    assert male["predicted"].iloc[0] > female["predicted"].iloc[0]


def test_pereira_does_not_use_weight():
    import inspect

    from pyspiro import PEREIRA_2007

    assert "weight" not in inspect.signature(compute_pereira_2007).parameters
    reference = PEREIRA_2007()
    for code in (1, 3, 7):  # FVC, FEV1, FEV1FVC: the height and age models
        without = reference.lln(1, 40, 170, parameter=code)
        for weight in (50, 70, 120):
            assert reference.lln(1, 40, 170, parameter=code, weight=weight) == without
    table = compute_pereira_2007(40, 170, 1, 3.0, 4.0)
    for _, row in table.iterrows():
        want_pred, want_lln = _pereira_expected(1, 40, 170, row["parameter"])
        assert row["predicted"] == pytest.approx(want_pred, abs=PEREIRA_TOLERANCE)
        assert row["lln"] == pytest.approx(want_lln, abs=PEREIRA_TOLERANCE)


# ECCS/ERS 1993 (Quanjer): wrapper against the independent module written
# from Table 6 of the source. Predicted value and percent of predicted only.
# Heights stay inside the source range: men 155 to 195 cm, women 145 to
# 180 cm.
ECCS_TOLERANCE = 0.005
ECCS_SEX = {1: "male", 2: "female"}
ECCS_HEIGHTS = {1: (155, 170, 190, 195), 2: (145, 150, 165, 180)}
ECCS_CASES = [
    (sex_code, age, height)
    for sex_code in (1, 2)
    for age in (18, 25, 40, 70)
    for height in ECCS_HEIGHTS[sex_code]
]


def _eccs_expected(sex_code, age, height, parameter):
    scale = 100.0 if parameter == "FEV1FVC" else 1.0
    return eccs_source.predicted(ECCS_SEX[sex_code], age, height, parameter) / scale


@pytest.mark.parametrize("case", ECCS_CASES)
def test_eccs_matches_the_published_table(case):
    sex_code, age, height = case
    fev1, fvc = 3.0, 4.0
    table = compute_eccs_1993(age, height, sex_code, fev1, fvc)
    assert list(table.columns) == list(TABLE_COLUMNS)
    assert tuple(table["parameter"]) == SPIROMETRY_PARAMS
    observed = {"FEV1": fev1, "FVC": fvc, "FEV1FVC": fev1 / fvc}
    for _, row in table.iterrows():
        parameter = row["parameter"]
        want = _eccs_expected(sex_code, age, height, parameter)
        assert row["observed"] == pytest.approx(observed[parameter])
        assert row["predicted"] == pytest.approx(want, abs=ECCS_TOLERANCE)
        assert row["percent_predicted"] == pytest.approx(
            observed[parameter] / want * 100, abs=TOLERANCE_PERCENT
        )


def test_eccs_has_no_lower_limit():
    table = compute_eccs_1993(40, 170, 1, 3.0, 4.0)
    assert table["lln"].isna().all()
    assert table["z_score"].isna().all()
    assert table["predicted"].map(math.isfinite).all()
    assert table["percent_predicted"].map(math.isfinite).all()


def test_eccs_age_floor_below_25():
    # Table 6 footnote and section 5.1: between 18 and 25 years an age of
    # 25 years is entered into the equations. The source makes no exception
    # by sex or parameter, so the floor holds for all three parameters and
    # both sexes. Above 25 the age term applies.
    for sex_code, height in ((1, 175), (2, 165)):
        at_25 = compute_eccs_1993(25, height, sex_code, 3.0, 4.0)
        for age in (18, 21.5, 24.9):
            below = compute_eccs_1993(age, height, sex_code, 3.0, 4.0)
            pd.testing.assert_series_equal(below["predicted"], at_25["predicted"])
        at_26 = compute_eccs_1993(26, height, sex_code, 3.0, 4.0)
        assert (at_26["predicted"] < at_25["predicted"]).all()


ECCS_AGE_MESSAGE = "the ECCS 1993 equations cover 18 to 70 years"
ECCS_MALE_HEIGHT_MESSAGE = "for men the ECCS 1993 equations cover 155 to 195 cm"
ECCS_FEMALE_HEIGHT_MESSAGE = "for women the ECCS 1993 equations cover 145 to 180 cm"


def test_eccs_age_range():
    for sex_code, height in ((1, 175), (2, 165)):
        for age in (17, 17.9, 70.1, 71):
            with pytest.raises(ValueError, match=ECCS_AGE_MESSAGE):
                compute_eccs_1993(age, height, sex_code, 3.0, 4.0)
        for age in (18, 70):
            assert len(compute_eccs_1993(age, height, sex_code, 3.0, 4.0)) == 3


def test_eccs_height_range():
    for height in (154.9, 195.1):
        with pytest.raises(ValueError, match=ECCS_MALE_HEIGHT_MESSAGE):
            compute_eccs_1993(40, height, 1, 3.0, 4.0)
    for height in (144.9, 180.1):
        with pytest.raises(ValueError, match=ECCS_FEMALE_HEIGHT_MESSAGE):
            compute_eccs_1993(40, height, 2, 2.5, 3.0)
    for height in (155, 195):
        assert len(compute_eccs_1993(40, height, 1, 3.0, 4.0)) == 3
    for height in (145, 180):
        assert len(compute_eccs_1993(40, height, 2, 2.5, 3.0)) == 3


def test_eccs_ratio_is_a_fraction():
    table = compute_eccs_1993(40, 170, 1, 3.0, 4.0)
    ratio = table[table["parameter"] == "FEV1FVC"].iloc[0]
    assert ratio["observed"] == pytest.approx(0.75)
    assert 0.7 < ratio["predicted"] < 0.9
    assert ratio["percent_predicted"] == pytest.approx(
        0.75 / ratio["predicted"] * 100, abs=TOLERANCE_PERCENT
    )


def test_eccs_sex_mapping():
    male = compute_eccs_1993(40, 170, 1, 3.0, 4.0)
    female = compute_eccs_1993(40, 170, 2, 3.0, 4.0)
    assert male["predicted"].iloc[0] > female["predicted"].iloc[0]
    assert female["predicted"].iloc[0] == pytest.approx(
        _eccs_expected(2, 40, 170, "FEV1"), abs=ECCS_TOLERANCE
    )


def test_eccs_result_is_not_classified():
    from quadrant.fragments import NOT_CLASSIFIED_LABEL, pattern_label
    from quadrant.interpretation import interpret_spirometry

    result = interpret_spirometry(compute_eccs_1993(40, 170, 1, 3.0, 4.0))
    assert result["pattern"] is None
    assert result["severity"] is None
    assert pattern_label(result) == NOT_CLASSIFIED_LABEL
    assert NOT_CLASSIFIED_LABEL == "Not classified (no z-score for this equation)"


def test_nan_z_scores_never_render_as_nan_text():
    from quadrant.fragments import render_interpretation, render_pattern_badge
    from quadrant.interpretation import interpret_spirometry

    result = interpret_spirometry(compute_eccs_1993(40, 170, 2, 2.5, 3.2))
    for html in (render_interpretation(result), render_pattern_badge(result)):
        assert "nan" not in html.lower()


def test_regression_table_allows_a_missing_lln_only_when_not_required():
    from quadrant.wrappers import _ECCS_1993, _ECCS_PARAM_CODES, _regression_table

    args = (
        _ECCS_1993,
        (1, 40, 170),
        _ECCS_PARAM_CODES,
        {"FEV1": 3.0, "FVC": 4.0, "FEV1FVC": 0.75},
        "ECCS 1993",
    )
    with pytest.raises(ValueError, match="ECCS 1993 has no reference value"):
        _regression_table(*args, ratio_scale=100.0)
    table = _regression_table(*args, ratio_scale=100.0, limits_required=False)
    assert table["lln"].isna().all()
    with pytest.raises(ValueError, match="ECCS 1993 has no reference value"):
        _regression_table(
            _ECCS_1993, (1, 40, 150), *args[2:], ratio_scale=100.0,
            limits_required=False,
        )
