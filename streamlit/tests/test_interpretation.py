"""Pattern and severity tests, ported from the R suite."""

import pandas as pd
import pytest

from quadrant.interpretation import (
    classify_pattern,
    classify_pattern_from_limits,
    grade_severity,
    interpret_spirometry,
)
from quadrant.wrappers import compute_pereira_2007
from tests.independent import pereira_2007 as pereira_paper


def test_classify_pattern_branches():
    assert classify_pattern(0, 0, 0) == "normal"
    assert classify_pattern(-2.0, -1.0, -2.0) == "obstructive"
    assert classify_pattern(-2.0, -2.0, 0.0) == "restrictive pattern (suggestive)"
    assert classify_pattern(-3.0, -2.0, -2.0) == "mixed pattern (suggestive)"
    assert classify_pattern(-2.0, -1.0, -1.0) == "non-specific"


def test_the_lln_boundary_counts_as_normal():
    assert classify_pattern(-1.645, -1.645, -1.645) == "normal"
    assert classify_pattern(-1.646, 0, 0) == "non-specific"


@pytest.mark.parametrize("bad", [None, float("nan"), "low"])
def test_classify_pattern_rejects_bad_inputs(bad):
    with pytest.raises(ValueError, match="non-missing numeric"):
        classify_pattern(bad, 0, 0)


@pytest.mark.parametrize(
    "z, expected",
    [
        (1.5, "mild"), (0.0, "mild"), (-1.7, "mild"), (-2.0, "mild"), (-2.5, "mild"),
        (-2.51, "moderate"), (-3.0, "moderate"), (-4.0, "moderate"),
        (-4.01, "severe"), (-6.0, "severe"),
    ],
)
def test_grade_severity_three_levels(z, expected):
    assert grade_severity(z) == expected


def test_grade_severity_rejects_bad_inputs():
    with pytest.raises(ValueError):
        grade_severity(None)
    with pytest.raises(ValueError):
        grade_severity(float("nan"))


def _table(fev1_z, fvc_z, ratio_z):
    return pd.DataFrame(
        {"parameter": ["FEV1", "FVC", "FEV1FVC"], "z_score": [fev1_z, fvc_z, ratio_z]}
    )


def test_interpret_spirometry_combines_pattern_and_severity():
    normal = interpret_spirometry(_table(0, 0, 0))
    assert normal["pattern"] == "normal" and normal["severity"] is None

    obstructive = interpret_spirometry(_table(-2.7, -1.0, -3.0))
    assert (obstructive["pattern"], obstructive["severity"]) == ("obstructive", "moderate")

    mixed = interpret_spirometry(_table(-4.5, -2.0, -2.0))
    assert (mixed["pattern"], mixed["severity"]) == ("mixed pattern (suggestive)", "severe")

    restrictive = interpret_spirometry(_table(-1.0, -2.0, 0.0))
    assert (restrictive["pattern"], restrictive["severity"]) == (
        "restrictive pattern (suggestive)", "mild")

    non_specific = interpret_spirometry(_table(-2.5, -1.0, -1.0))
    assert (non_specific["pattern"], non_specific["severity"]) == ("non-specific", "mild")


def test_interpret_spirometry_returns_the_z_scores_it_used():
    result = interpret_spirometry(_table(-2.0, -3.0, -1.0))
    assert (result["fev1_z"], result["fvc_z"], result["fev1_fvc_z"]) == (-2.0, -3.0, -1.0)


def test_interpret_spirometry_fails_on_a_malformed_table():
    with pytest.raises(ValueError, match="missing required columns"):
        interpret_spirometry(pd.DataFrame({"foo": [1]}))
    with pytest.raises(ValueError, match="FEV1FVC"):
        interpret_spirometry(pd.DataFrame({"parameter": ["FEV1", "FVC"], "z_score": [-1, -1]}))


def _nan_table(z_values, lln=float("nan")):
    return pd.DataFrame(
        {
            "parameter": ["FEV1", "FVC", "FEV1FVC"],
            "observed": [3.0, 4.0, 0.75],
            "predicted": [3.5, 4.5, 0.78],
            "lln": [lln] * 3,
            "z_score": z_values,
            "percent_predicted": [86.0, 89.0, 96.0],
        }
    )


def test_a_table_with_nan_limits_is_not_classified():
    nan = float("nan")
    result = interpret_spirometry(_nan_table([nan, nan, nan]))
    assert result["pattern"] is None
    assert result["severity"] is None
    assert pd.isna(result["fev1_z"])


def test_partial_nan_z_scores_still_raise():
    with pytest.raises(ValueError, match="all present or all missing"):
        interpret_spirometry(_nan_table([-1.0, float("nan"), 0.0]))


# Equations that publish a lower limit but no z-score (Pereira 2007) are
# classified from the observed values against that lower limit. The rule
# is the same as for z-scores: only a value strictly below the limit counts.


LIMITS = {"FEV1": 3.0, "FVC": 4.0, "FEV1FVC": 0.70}


def _observed(fev1, fvc, ratio):
    return {"FEV1": fev1, "FVC": fvc, "FEV1FVC": ratio}


def test_classify_pattern_from_limits_branches():
    assert classify_pattern_from_limits(_observed(3.5, 4.5, 0.78), LIMITS) == "normal"
    assert classify_pattern_from_limits(_observed(2.5, 4.5, 0.60), LIMITS) == "obstructive"
    assert classify_pattern_from_limits(_observed(2.5, 3.5, 0.75), LIMITS) == (
        "restrictive pattern (suggestive)")
    assert classify_pattern_from_limits(_observed(2.0, 3.5, 0.60), LIMITS) == (
        "mixed pattern (suggestive)")
    assert classify_pattern_from_limits(_observed(2.9, 4.1, 0.71), LIMITS) == "non-specific"


def test_a_value_equal_to_the_lower_limit_is_not_below_it():
    assert classify_pattern_from_limits(dict(LIMITS), LIMITS) == "normal"
    assert classify_pattern_from_limits(_observed(3.0, 4.0, 0.6999), LIMITS) == "obstructive"


@pytest.mark.parametrize(
    "fev1_low, fvc_low, ratio_low",
    [(a, b, c) for a in (False, True) for b in (False, True) for c in (False, True)],
)
def test_the_two_paths_share_one_rule(fev1_low, fvc_low, ratio_low):
    z = [-2.0 if low else 0.0 for low in (fev1_low, fvc_low, ratio_low)]
    observed = {
        p: LIMITS[p] * (0.9 if low else 1.1)
        for p, low in zip(("FEV1", "FVC", "FEV1FVC"), (fev1_low, fvc_low, ratio_low))
    }
    assert classify_pattern(*z) == classify_pattern_from_limits(observed, LIMITS)


@pytest.mark.parametrize("bad", [None, float("nan"), "low", True])
def test_classify_pattern_from_limits_rejects_missing_or_bad_limits(bad):
    with pytest.raises(ValueError, match="non-missing numeric"):
        classify_pattern_from_limits(_observed(3.5, 4.5, 0.78), {**LIMITS, "FVC": bad})
    with pytest.raises(ValueError, match="non-missing numeric"):
        classify_pattern_from_limits({**_observed(3.5, 4.5, 0.78), "FEV1": bad}, LIMITS)


def test_classify_pattern_from_limits_needs_every_parameter():
    with pytest.raises(ValueError, match="FEV1FVC"):
        classify_pattern_from_limits({"FEV1": 3.5, "FVC": 4.5}, LIMITS)
    with pytest.raises(ValueError, match="FVC"):
        classify_pattern_from_limits(_observed(3.5, 4.5, 0.78), {"FEV1": 3.0, "FEV1FVC": 0.7})


def _limit_table(observed, lln):
    nan = float("nan")
    return pd.DataFrame(
        {
            "parameter": ["FEV1", "FVC", "FEV1FVC"],
            "observed": observed,
            "predicted": [3.5, 4.5, 0.78],
            "lln": lln,
            "z_score": [nan, nan, nan],
            "percent_predicted": [86.0, 89.0, 96.0],
        }
    )


def test_interpret_spirometry_uses_the_lower_limit_when_there_is_no_z_score():
    result = interpret_spirometry(_limit_table([2.5, 4.5, 0.60], [3.0, 4.0, 0.70]))
    assert result["pattern"] == "obstructive"
    assert result["severity"] is None
    assert result["basis"] == "lower limit"
    assert all(pd.isna(result[k]) for k in ("fev1_z", "fvc_z", "fev1_fvc_z"))
    normal = interpret_spirometry(_limit_table([3.5, 4.5, 0.78], [3.0, 4.0, 0.70]))
    assert (normal["pattern"], normal["severity"], normal["basis"]) == (
        "normal", None, "lower limit")


def test_interpret_spirometry_states_the_z_score_basis():
    assert interpret_spirometry(_table(0, 0, 0))["basis"] == "z-score"
    assert interpret_spirometry(_table(-3, -1, -3))["basis"] == "z-score"


def test_no_z_score_and_no_lower_limit_stays_unclassified():
    result = interpret_spirometry(_nan_table([float("nan")] * 3))
    assert result["pattern"] is None and result["basis"] is None
    # A table without the lower-limit columns is not classified either.
    result = interpret_spirometry(_table(float("nan"), float("nan"), float("nan")))
    assert result["pattern"] is None and result["basis"] is None


def test_a_partly_missing_lower_limit_raises_and_is_never_normal():
    nan = float("nan")
    with pytest.raises(ValueError, match="lower limits must be all present or all missing"):
        interpret_spirometry(_limit_table([3.5, 4.5, 0.78], [3.0, nan, 0.70]))


def test_a_missing_observed_value_with_a_lower_limit_raises():
    with pytest.raises(ValueError, match="non-missing numeric"):
        interpret_spirometry(_limit_table([3.5, float("nan"), 0.78], [3.0, 4.0, 0.70]))
    table = _limit_table([3.5, 4.5, 0.78], [3.0, 4.0, 0.70]).drop(columns="observed")
    with pytest.raises(ValueError, match="observed"):
        interpret_spirometry(table)


def test_partial_z_scores_still_raise_when_the_lower_limit_is_set():
    with pytest.raises(ValueError, match="all present or all missing"):
        interpret_spirometry(_nan_table([-1.0, float("nan"), 0.0], lln=3.0))


# Real Pereira 2007 tables against the independent module of the paper.


_PEREIRA_SEX = {1: "male", 2: "female"}
_PARAMS = ("FEV1", "FVC", "FEV1FVC")


def _paper_pattern(sex_code, age, height, fev1, fvc):
    """Pattern by hand: observed against the paper's lower limit."""
    sex = _PEREIRA_SEX[sex_code]
    observed = {"FEV1": fev1, "FVC": fvc, "FEV1FVC": fev1 / fvc * 100}
    low = {p: observed[p] < pereira_paper.lower_limit(sex, age, height, p) for p in _PARAMS}
    z = [-2.0 if low[p] else 0.0 for p in _PARAMS]
    return classify_pattern(*z)


# Values worked by hand from Tables 3 and 4 of the paper:
# man 40 years, 170 cm: lower limit FEV1 3.189 L, FVC 3.881 L, ratio 75.07 %.
# woman 50 years, 160 cm: lower limit FEV1 2.046 L, FVC 2.623 L, ratio 72.70 %.
PEREIRA_PATTERN_CASES = [
    ((1, 40, 170, 2.7, 4.0), "obstructive"),
    ((1, 40, 170, 3.5, 4.5), "normal"),
    ((2, 50, 160, 1.9, 2.4), "restrictive pattern (suggestive)"),
    ((2, 50, 160, 1.5, 2.4), "mixed pattern (suggestive)"),
    ((2, 50, 160, 2.0, 2.65), "non-specific"),
]


@pytest.mark.parametrize("case, expected", PEREIRA_PATTERN_CASES)
def test_pereira_patterns_match_the_paper_by_hand(case, expected):
    sex_code, age, height, fev1, fvc = case
    result = interpret_spirometry(compute_pereira_2007(age, height, sex_code, fev1, fvc))
    assert result["pattern"] == expected
    assert _paper_pattern(*case) == expected
    assert result["severity"] is None
    assert result["basis"] == "lower limit"


def test_pereira_ratio_lower_limit_is_a_fraction():
    table = compute_pereira_2007(40, 170, 1, 2.7, 4.0).set_index("parameter")
    want = pereira_paper.lower_limit("male", 40, 170, "FEV1FVC") / 100
    assert 0 < table.loc["FEV1FVC", "lln"] < 1
    assert table.loc["FEV1FVC", "lln"] == pytest.approx(want, abs=1e-9)
    assert table.loc["FEV1FVC", "observed"] == pytest.approx(0.675)


def test_pereira_observed_equal_to_the_lower_limit_is_not_below():
    first = compute_pereira_2007(40, 170, 1, 3.5, 4.5).set_index("parameter")
    fvc_lln = float(first.loc["FVC", "lln"])
    table = compute_pereira_2007(40, 170, 1, 3.3, fvc_lln)
    row = table.set_index("parameter").loc["FVC"]
    assert row["observed"] == row["lln"]
    assert interpret_spirometry(table)["pattern"] == "normal"


@pytest.mark.parametrize(
    "sex_code, age, height",
    [(1, 26, 170), (1, 86, 170), (2, 20, 160), (2, 85, 160),
     (1, 40, 152), (1, 40, 192), (2, 40, 137), (2, 40, 182)],
)
def test_pereira_is_classified_at_the_age_and_height_edges(sex_code, age, height):
    sex = _PEREIRA_SEX[sex_code]
    fvc = pereira_paper.predicted(sex, age, height, "FVC")
    fev1 = 0.6 * fvc
    result = interpret_spirometry(compute_pereira_2007(age, height, sex_code, fev1, fvc))
    assert result["basis"] == "lower limit"
    assert result["pattern"] == _paper_pattern(sex_code, age, height, fev1, fvc)
    assert result["pattern"] in ("obstructive", "mixed pattern (suggestive)")


def test_the_basis_follows_has_lower_limit_for_every_registered_equation():
    from quadrant.registry import EQUATIONS, Subject, compute_equation

    subject = Subject(40, 170, 1, 3.0, 4.0)
    for key, spec in EQUATIONS.items():
        code = next(iter(spec.ethnicities.values())) if spec.ethnicities else None
        table = compute_equation(key, subject, code)
        result = interpret_spirometry(table)
        if table["z_score"].notna().all():
            assert result["basis"] == "z-score", key
        elif spec.has_lower_limit:
            assert result["basis"] == "lower limit", key
            assert result["severity"] is None
        else:
            assert result["basis"] is None and result["pattern"] is None, key
    assert interpret_spirometry(compute_equation("pereira_2007", subject))["basis"] == (
        "lower limit")
    assert interpret_spirometry(compute_equation("eccs_1993", subject))["pattern"] is None
