"""Tests for the example inputs and the what-if comparison."""

import pandas as pd
import pytest

from quadrant.constants import GLI_AGE_RANGE_YEARS, HEIGHT_RANGE_CM, SEX_CODES
from quadrant.interpretation import interpret_spirometry
from quadrant.presets import PRESETS, delta_frame
from quadrant.registry import Subject, compute_equation

NAN = float("nan")

# The pattern that each example must give under GLI-2012 (Caucasian).
STATED_PATTERNS = {
    "normal_adult": "normal",
    "obstructive": "obstructive",
    "restrictive": "restrictive pattern (suggestive)",
    "child": "normal",
}


def _subject(preset):
    return Subject(preset.age_years, preset.height_cm, preset.sex_code,
                   preset.fev1, preset.fvc)


def _z_table(fev1, fvc, ratio):
    return pd.DataFrame(
        {"parameter": ["FEV1", "FVC", "FEV1FVC"], "z_score": [fev1, fvc, ratio]}
    )


def test_there_are_four_examples_and_each_label_says_example():
    assert list(PRESETS) == list(STATED_PATTERNS)
    for preset in PRESETS.values():
        assert preset.label.startswith("Example: ")


@pytest.mark.parametrize("key", list(STATED_PATTERNS))
def test_each_preset_gives_its_stated_pattern_under_gli_2012(key):
    table = compute_equation("gli_2012", _subject(PRESETS[key]), 1)
    assert interpret_spirometry(table)["pattern"] == STATED_PATTERNS[key]


def test_the_child_example_is_10_years_old():
    assert PRESETS["child"].age_years == 10


@pytest.mark.parametrize("key", list(STATED_PATTERNS))
def test_preset_values_are_inside_the_gli_ranges(key):
    preset = PRESETS[key]
    assert GLI_AGE_RANGE_YEARS[0] <= preset.age_years <= GLI_AGE_RANGE_YEARS[1]
    assert HEIGHT_RANGE_CM[0] <= preset.height_cm <= HEIGHT_RANGE_CM[1]
    assert preset.sex_code in SEX_CODES.values()
    # The app accepts FEV1 up to 8 L and FVC up to 10 L.
    assert 0 < preset.fev1 <= preset.fvc
    assert preset.fev1 <= 8 and preset.fvc <= 10
    for key_ in ("gli_2012", "gli_2022"):
        table = compute_equation(key_, _subject(preset), 1)
        assert not table["z_score"].isna().any()


def test_delta_frame_subtracts_pinned_z_scores():
    current = {"GLI-2012": _z_table(-1.20, 0.30, -2.00)}
    pinned = {"GLI-2012": _z_table(-1.62, 1.40, -2.00)}
    frames = delta_frame(current, pinned)
    assert list(frames) == ["FEV1", "FVC", "FEV1/FVC"]
    for frame in frames.values():
        assert frame.index.name == "Equation"
        assert list(frame.columns) == ["Change in z"]
    assert frames["FEV1"].loc["GLI-2012", "Change in z"] == "+0.42"
    assert frames["FVC"].loc["GLI-2012", "Change in z"] == "-1.10"
    assert frames["FEV1/FVC"].loc["GLI-2012", "Change in z"] == "0.00"


def test_delta_frame_compares_only_the_equations_in_both():
    current = {
        "GLI-2012": _z_table(-1.0, 0.0, 0.0),
        "NHANES III": _z_table(-2.0, 0.0, 0.0),
        "Kubota 2014 (JRS)": None,
    }
    pinned = {"GLI-2012": _z_table(-1.5, 0.0, 0.0), "GLI-Global 2022": _z_table(0, 0, 0)}
    frames = delta_frame(current, pinned)
    assert list(frames["FEV1"].index) == ["GLI-2012"]
    assert frames["FEV1"].loc["GLI-2012", "Change in z"] == "+0.50"


def test_a_pinned_nan_gives_a_hyphen():
    current = {"ECCS/Quanjer 1993": _z_table(NAN, NAN, NAN), "GLI-2012": _z_table(-1, 0, NAN)}
    pinned = {"ECCS/Quanjer 1993": _z_table(NAN, NAN, NAN), "GLI-2012": _z_table(NAN, 0, 0)}
    frames = delta_frame(current, pinned)
    assert frames["FEV1"].loc["ECCS/Quanjer 1993", "Change in z"] == "-"
    assert frames["FEV1"].loc["GLI-2012", "Change in z"] == "-"
    assert frames["FEV1/FVC"].loc["GLI-2012", "Change in z"] == "-"


def test_a_small_negative_change_does_not_show_minus_zero():
    frames = delta_frame({"A": _z_table(0.001, 0, 0)}, {"A": _z_table(0.003, 0, 0)})
    assert frames["FEV1"].loc["A", "Change in z"] == "0.00"
