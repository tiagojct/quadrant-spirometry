"""Tests for the HTML fragments and the SVG chart."""

import pandas as pd

from quadrant.constants import LLN_Z, SEVERITY_MILD_Z_MIN, SEVERITY_MODERATE_Z_MIN
from quadrant.fragments import (
    badge_colour,
    classification_summary,
    comparison_notes,
    input_problem,
    pattern_label,
    render_gli_comparison,
    render_interpretation,
    render_pattern_badge,
    results_for_display,
)
from quadrant.visuals import (
    FAMILY_COLOURS,
    SEVERITY_BANDS,
    Z_AXIS_MAX,
    Z_AXIS_MIN,
    cross_family_chart_svg,
    is_svg,
    z_to_x,
)


def _table(z):
    return pd.DataFrame(
        {
            "parameter": ["FEV1", "FVC", "FEV1FVC"],
            "observed": [3.0, 4.0, 0.75],
            "predicted": [3.5, 4.5, 0.8],
            "lln": [2.8, 3.6, 0.7],
            "z_score": z,
            "percent_predicted": [85.0, 90.0, 94.0],
        }
    )


def test_input_problem_is_silent_for_usable_or_missing_values():
    assert input_problem(3.0, 4.0) is None
    assert input_problem(4.0, 4.0) is None
    assert input_problem(None, 4.0) is None
    assert input_problem(3.0, float("nan")) is None


def test_input_problem_explains_unusable_values():
    assert "FEV1 is larger than FVC" in input_problem(5.0, 4.0)
    assert "greater than zero" in input_problem(0, 4.0)
    assert "greater than zero" in input_problem(3.0, -1)


def test_results_for_display_marks_values_below_the_lln():
    frame = results_for_display(_table([-2.0, 0.0, -1.645]))
    assert list(frame.columns) == ["Parameter", "Pred.", "LLN", "Z-score", "% pred"]
    assert list(frame["Z-score"]) == ["-2.00 *", "0.00", "-1.65"]
    assert list(frame["% pred"]) == ["85.0", "90.0", "94.0"]


def test_pattern_label_is_descriptive():
    assert pattern_label({"pattern": "normal", "severity": None}) == "Pattern consistent with normal"
    assert pattern_label({"pattern": "obstructive", "severity": "severe"}) == (
        "Pattern consistent with obstructive \u00b7 severe")
    assert pattern_label({"pattern": "mixed pattern (suggestive)", "severity": "moderate"}) == (
        "Consistent with mixed pattern (suggestive) \u00b7 moderate")


def test_badge_colour_follows_severity():
    colours = [badge_colour({"pattern": "x", "severity": s}) for s in (None, "mild", "moderate", "severe")]
    assert colours == ["green", "yellow", "orange", "red"]


def test_comparison_notes_cover_missing_agreeing_and_flipped_tables():
    assert comparison_notes(None, _table([0, 0, 0])) is None
    assert comparison_notes(_table([0, 0, 0]), _table([0, 0, 0])) == []
    notes = comparison_notes(_table([-1.0, 0, 0]), _table([-2.0, 0, 0]))
    assert len(notes) == 1 and notes[0].startswith("FEV1: GLI-2012 z = -1.00 (within LLN)")


def test_badge_wording_is_descriptive():
    normal = render_pattern_badge({"pattern": "normal", "severity": None})
    assert "Pattern consistent with normal" in normal
    severe = render_pattern_badge({"pattern": "obstructive", "severity": "severe"})
    assert "Pattern consistent with obstructive" in severe and "· severe" in severe
    mixed = render_pattern_badge({"pattern": "mixed pattern (suggestive)", "severity": "moderate"})
    assert "Consistent with mixed pattern (suggestive)" in mixed
    assert "Pattern consistent with mixed" not in mixed
    assert "Enter values" in render_pattern_badge(None)


def test_interpretation_block_for_normal_and_impaired():
    assert "not graded" in render_interpretation({"pattern": "normal", "severity": None})
    assert "moderate" in render_interpretation({"pattern": "obstructive", "severity": "moderate"})
    assert "Enter values" in render_interpretation(None)


def test_gli_comparison_reports_a_flip():
    agree = render_gli_comparison(_table([0, 0, 0]), _table([0, 0, 0]))
    assert "same side" in agree
    flip = render_gli_comparison(_table([-1.0, 0, 0]), _table([-2.0, 0, 0]))
    assert "Classification differs" in flip and "FEV1" in flip
    assert "Enter values" in render_gli_comparison(None, _table([0, 0, 0]))


def test_z_to_x_maps_axis_ends_and_clamps():
    assert z_to_x(Z_AXIS_MIN, 100, 800) == 100
    assert z_to_x(Z_AXIS_MAX, 100, 800) == 900
    assert z_to_x(Z_AXIS_MIN - 10, 100, 800) == 100
    assert z_to_x(Z_AXIS_MAX + 10, 100, 800) == 900


def test_severity_bands_cover_the_axis_and_match_the_cut_offs():
    los = [b["z_lo"] for b in SEVERITY_BANDS]
    his = [b["z_hi"] for b in SEVERITY_BANDS]
    assert los[0] == Z_AXIS_MIN and his[-1] == Z_AXIS_MAX
    assert los[1:] == his[:-1]
    assert {SEVERITY_MODERATE_Z_MIN, SEVERITY_MILD_Z_MIN, LLN_Z} <= set(his)
    assert [b["label"] for b in SEVERITY_BANDS] == ["severe", "moderate", "mild", "normal"]


def test_chart_draws_one_marker_per_family_and_parameter():
    svg = cross_family_chart_svg(
        {"GLI-2012": _table([-1, -2, -3]), "GLI-Global 2022": _table([-1, -2, -3]),
         "NHANES III": _table([0, 0, 0])}
    )
    assert svg.startswith("<svg") and is_svg(svg)
    for family in FAMILY_COLOURS:
        assert family in svg
    assert svg.count("<circle") == 12  # nine markers and three legend circles


def test_chart_skips_families_without_results():
    svg = cross_family_chart_svg({"GLI-2012": _table([-1, -2, -3]), "NHANES III": None})
    assert "NHANES III" not in svg and "GLI-2012" in svg


def test_chart_returns_a_prompt_without_results():
    out = cross_family_chart_svg({"GLI-2012": None, "NHANES III": None})
    assert "Enter values" in out and not is_svg(out)


def _interp(pattern, severity=None):
    return {"pattern": pattern, "severity": severity}


def test_classification_summary_agree_differ_and_missing():
    same = {"gli_2012": _interp("normal"), "gli_2022": _interp("normal"), "nhanes3": _interp("normal")}
    assert classification_summary(same) == "The equations agree on the classification."
    two = {"gli_2012": _interp("normal"), "gli_2022": _interp("normal"), "nhanes3": None}
    assert classification_summary(two) == "The equations agree on the classification."
    differ = {
        "gli_2012": _interp("obstructive", "severe"),
        "gli_2022": _interp("obstructive", "moderate"),
        "nhanes3": _interp("obstructive", "severe"),
    }
    text = classification_summary(differ)
    assert text.startswith("The equations differ in classification.")
    assert "GLI-Global 2022: obstructive \u00b7 moderate" in text
    assert classification_summary({"gli_2012": _interp("normal"), "gli_2022": None, "nhanes3": None}) is None
