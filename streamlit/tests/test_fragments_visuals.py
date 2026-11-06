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
)
from quadrant.visuals import (
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
    for family in ("GLI-2012", "GLI-Global 2022", "NHANES III"):
        assert family in svg
    assert svg.count('class="marker"') == 9
    assert svg.count('class="legend-marker"') == 3


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


UNCLASSIFIED = {"pattern": None, "severity": None}


def test_pattern_label_for_an_unclassified_result():
    assert pattern_label(UNCLASSIFIED) == "Not classified (no z-score for this equation)"


def test_badge_colour_is_gray_when_not_classified():
    assert badge_colour(UNCLASSIFIED) == "gray"


def test_unclassified_results_render_and_are_skipped_in_the_summary():
    assert "Not classified" in render_pattern_badge(UNCLASSIFIED)
    assert "Not classified" in render_interpretation(UNCLASSIFIED)
    assert (
        "This equation gives no z-score, so the result is not classified."
        in render_interpretation(UNCLASSIFIED)
    )
    assert "lower limit" not in render_interpretation(UNCLASSIFIED)
    normal = {"pattern": "normal", "severity": None}
    assert classification_summary({"gli_2012": normal, "gli_2022": UNCLASSIFIED}) is None


# Equations without a z-score or without a lower limit give NaN in those
# columns. The display helpers show a hyphen, never the text "nan", and
# never the below-LLN asterisk for a missing z-score.
def _eccs_and_pereira_tables():
    from quadrant.wrappers import compute_eccs_1993, compute_pereira_2007

    return (
        compute_eccs_1993(40, 170, 1, 3.0, 4.0),
        compute_pereira_2007(40, 170, 1, 3.0, 4.0),
    )


def test_reference_table_html_shows_a_hyphen_for_missing_limits():
    from quadrant.fragments import reference_table_html

    eccs, pereira = _eccs_and_pereira_tables()
    html = reference_table_html(eccs)
    assert "nan" not in html.lower()
    assert "<td>-</td>" in html
    html = reference_table_html(pereira)
    assert "nan" not in html.lower()
    for value in pereira["lln"]:
        assert f"<td>{value:.2f}</td>" in html


def test_interpretation_fragments_have_no_nan_text_for_either_table():
    from quadrant.interpretation import interpret_spirometry

    for table in _eccs_and_pereira_tables():
        result = interpret_spirometry(table)
        for html in (render_interpretation(result), render_pattern_badge(result)):
            assert "nan" not in html.lower()


def test_svg_has_one_marker_per_equation_and_parameter_for_six_equations():
    nan = float("nan")
    tables = {f"Eq {i}": _table([-1, -2, -3]) for i in range(5)}
    tables["Eq 5"] = _table([-1, nan, nan])
    svg = cross_family_chart_svg(tables)
    assert svg.count('class="marker"') == 5 * 3 + 1
    assert svg.count('class="legend-marker"') == 6
    assert "nan" not in svg.lower()
    for i in range(6):
        assert f"Eq {i}" in svg


def test_all_nan_equation_has_no_legend_entry_or_lane():
    nan = float("nan")
    svg = cross_family_chart_svg({"A": _table([-1, -2, -3]), "Empty": _table([nan, nan, nan])})
    assert "Empty" not in svg
    assert svg.count('class="legend-marker"') == 1


def test_eight_legend_markers_sit_on_two_rows_with_distinct_shapes():
    import re

    svg = cross_family_chart_svg({f"Eq {i}": _table([-1, -2, -3]) for i in range(8)})
    tags = re.findall(r'<(circle|rect|polygon)[^>]*class="legend-marker"', svg)
    assert len(tags) == 8
    labels = re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-weight="600">Eq \d', svg)
    assert len(labels) == 8
    assert len({y for _, y in labels}) == 2
    assert len({x for x, _ in labels}) == 4
    polygons = re.findall(r'<polygon[^>]*class="legend-marker"[^>]*>', svg)
    assert len(set(polygons)) == len(polygons) == 6


def test_the_ratio_is_labelled_fev1_fvc_in_the_notes_and_the_svg():
    notes = comparison_notes(_table([0, 0, -1.0]), _table([0, 0, -2.0]))
    assert len(notes) == 1 and notes[0].startswith("FEV1/FVC: GLI-2012 z = -1.00")
    svg = cross_family_chart_svg({"GLI-2012": _table([0, 0, -1.0])})
    assert ">FEV1/FVC</text>" in svg and ">FEV1FVC<" not in svg
