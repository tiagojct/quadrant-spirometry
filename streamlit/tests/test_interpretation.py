"""Pattern and severity tests, ported from the R suite."""

import pandas as pd
import pytest

from quadrant.interpretation import classify_pattern, grade_severity, interpret_spirometry


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
