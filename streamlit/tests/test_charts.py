"""Tests for the interactive comparison chart."""

import pandas as pd
import pytest

from quadrant.charts import (
    BANDS,
    EDGE_MARGIN,
    Z_AXIS_MAX,
    Z_AXIS_MIN,
    band_frame,
    comparison_chart,
    points_frame,
    not_plotted_caption,
    not_plotted_names,
    style_for,
)
from quadrant.constants import LLN_Z, SEVERITY_MILD_Z_MIN, SEVERITY_MODERATE_Z_MIN


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


def test_bands_cover_the_axis_and_match_the_cut_offs():
    frame = band_frame()
    assert frame["z_lo"].iloc[0] == Z_AXIS_MIN and frame["z_hi"].iloc[-1] == Z_AXIS_MAX
    assert list(frame["z_lo"].iloc[1:]) == list(frame["z_hi"].iloc[:-1])
    assert list(frame["z_hi"].iloc[:-1]) == [SEVERITY_MODERATE_Z_MIN, SEVERITY_MILD_Z_MIN, LLN_Z]
    assert len(frame) == len(BANDS) == 4


def test_points_have_one_row_for_each_family_and_parameter():
    frame = points_frame({"GLI-2012": _table([-1, -2, -3]), "NHANES III": _table([0, 0, 0])})
    assert len(frame) == 6
    assert set(frame["family"]) == {"GLI-2012", "NHANES III"}
    assert set(frame["parameter"]) == {"FEV1", "FVC", "FEV1/FVC"}


def test_points_skip_families_without_results():
    frame = points_frame({"GLI-2012": _table([-1, -2, -3]), "NHANES III": None})
    assert set(frame["family"]) == {"GLI-2012"}


def test_off_scale_values_sit_inside_the_edge_and_keep_their_real_z():
    frame = points_frame({"GLI-2012": _table([-8.47, 0.0, 6.0])})
    low = frame[frame["parameter"] == "FEV1"].iloc[0]
    high = frame[frame["parameter"] == "FEV1/FVC"].iloc[0]
    assert low["z_plot"] == pytest.approx(Z_AXIS_MIN + EDGE_MARGIN)
    assert low["z_score"] == pytest.approx(-8.47) and low["z_text"] == "-8.47"
    assert high["z_plot"] == pytest.approx(Z_AXIS_MAX - EDGE_MARGIN)


def test_values_on_the_axis_are_not_moved():
    frame = points_frame({"GLI-2012": _table([-1.3, 0.0, 2.0])})
    assert list(frame["z_plot"]) == [-1.3, 0.0, 2.0]


def test_no_chart_without_results():
    assert comparison_chart({"GLI-2012": None, "NHANES III": None}) is None


def test_the_chart_has_bands_a_lln_line_labels_and_markers():
    chart = comparison_chart(
        {name: _table([-1, -2, -3]) for name in ("GLI-2012", "GLI-Global 2022", "NHANES III")}
    )
    spec = chart.to_dict()
    marks = [layer["mark"]["type"] for layer in spec["layer"]]
    assert marks == ["rect", "rule", "text", "point"]
    marker = spec["layer"][3]["encoding"]
    fields = {t["field"] for t in marker["tooltip"]}
    assert {"family", "parameter", "z_score", "observed", "predicted", "lln"} <= fields
    assert marker["yOffset"]["field"] == "family"
    assert marker["shape"]["field"] == "family"
    # Colour and fill keep independent scales, so the two legends do not mix.
    assert spec["resolve"]["scale"]["color"] == "independent"
    assert spec["resolve"]["scale"]["fill"] == "independent"


def test_the_marker_order_follows_the_input_order():
    chart = comparison_chart({"NHANES III": _table([0, 0, 0]), "GLI-2012": _table([0, 0, 0])})
    marker = chart.to_dict()["layer"][3]["encoding"]
    assert marker["color"]["scale"]["domain"] == ["NHANES III", "GLI-2012"]


def test_style_pairs_are_distinct_for_eight_equations():
    pairs = [style_for(i) for i in range(8)]
    assert len(set(pairs)) == 8
    assert len({colour for colour, _ in pairs}) == 8
    assert len({shape for _, shape in pairs}) == 8
    assert pairs[0] == ("#2563eb", "circle")
    assert pairs[1] == ("#9333ea", "square")
    assert pairs[2] == ("#dc2626", "diamond")
    assert style_for(8) == style_for(0)


def test_chart_skips_nan_z_scores():
    nan = float("nan")
    frame = points_frame({"A": _table([-1, nan, -3]), "B": _table([nan, nan, nan])})
    assert len(frame) == 2
    assert set(frame["family"]) == {"A"}
    assert "nan" not in " ".join(frame["z_text"])
    spec = comparison_chart({"A": _table([-1, nan, -3]), "B": _table([nan, nan, nan])}).to_dict()
    assert "nan" not in str(spec["datasets"]).lower()


def test_chart_height_grows_with_equations():
    for n in (1, 3, 6, 8):
        tables = {f"Eq {i}": _table([-1, -2, -3]) for i in range(n)}
        assert comparison_chart(tables).to_dict()["height"] == 120 + 64 * n
    spec = comparison_chart({f"Eq {i}": _table([0, 0, 0]) for i in range(8)}).to_dict()
    assert spec["layer"][3]["encoding"]["color"]["legend"]["columns"] == 4


def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def test_every_style_colour_has_contrast_on_the_backgrounds():
    for i in range(8):
        for background in ("#ffffff", "#fbf9f4", "#0d1522"):
            hi, lo = sorted((_luminance(style_for(i)[0]), _luminance(background)), reverse=True)
            assert (hi + 0.05) / (lo + 0.05) >= 3.0, (i, background)


def test_not_plotted_names_and_caption():
    nan = float("nan")
    frames = {
        "A": _table([-1, -2, -3]),
        "B": None,
        "C": _table([nan, nan, nan]),
        "D": _table([nan, -1, nan]),
    }
    assert not_plotted_names(frames) == ["B", "C"]
    assert not_plotted_caption(frames) == "Not plotted, no z-score: B, C"
    assert not_plotted_caption({"A": _table([0, 0, 0])}) == ""
