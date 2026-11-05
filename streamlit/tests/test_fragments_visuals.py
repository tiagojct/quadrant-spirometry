"""Tests for the HTML fragments and the SVG chart."""

import pandas as pd

from quadrant.constants import LLN_Z, SEVERITY_MILD_Z_MIN, SEVERITY_MODERATE_Z_MIN
from quadrant.fragments import (
    input_notice,
    render_gli_comparison,
    render_interpretation,
    render_pattern_badge,
    render_reference_table,
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


def test_input_notice_is_silent_for_usable_or_missing_values():
    assert input_notice(3.0, 4.0) is None
    assert input_notice(4.0, 4.0) is None
    assert input_notice(None, 4.0) is None
    assert input_notice(3.0, float("nan")) is None


def test_input_notice_explains_unusable_values():
    assert "FEV1 is larger than FVC" in input_notice(5.0, 4.0)
    assert "greater than zero" in input_notice(0, 4.0)
    assert "greater than zero" in input_notice(3.0, -1)


def test_reference_table_shows_the_message_instead_of_a_table():
    html = render_reference_table(None, "age_years must be between 8 and 80 years.")
    assert "Not available for these inputs" in html and "<table" not in html


def test_reference_table_escapes_the_message():
    assert "<script>" not in render_reference_table(None, "<script>x</script>")


def test_reference_table_flags_values_below_lln():
    html = render_reference_table(_table([-2.0, 0.0, 0.0]))
    assert "FEV1 (below LLN)" in html and "FVC (below LLN)" not in html


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
