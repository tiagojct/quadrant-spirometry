"""Tests for the equation registry."""

import pandas as pd
import pytest

from quadrant.registry import DEFAULT_KEYS, EQUATIONS, Subject, compute_equation
from quadrant.wrappers import (
    compute_eccs_1993,
    compute_gli_2012,
    compute_kubota_2014,
    compute_pereira_2007,
)


def test_default_keys_are_the_three_current_equations():
    assert DEFAULT_KEYS == ("gli_2012", "gli_2022", "nhanes3")
    assert tuple(EQUATIONS)[:3] == DEFAULT_KEYS


def test_every_spec_has_population_citation_and_group():
    for key, spec in EQUATIONS.items():
        assert spec.key == key
        assert spec.name and spec.citation and spec.population
        assert spec.group in {"recommended", "historical", "regional"}


def test_regional_and_historical_sets_are_not_default():
    for key in DEFAULT_KEYS:
        assert EQUATIONS[key].group != "regional"
    assert EQUATIONS["nhanes3"].group == "historical"
    assert EQUATIONS["nhanes3"].caveat
    for key, spec in EQUATIONS.items():
        if spec.group == "regional":
            assert key not in DEFAULT_KEYS


def test_compute_equation_matches_the_direct_wrapper():
    subject = Subject(40, 170, 1, 3.0, 4.0)
    got = compute_equation("gli_2012", subject, 1)
    expected = compute_gli_2012(40, 170, 1, 1, 3.0, 4.0)
    pd.testing.assert_frame_equal(got, expected)


def test_compute_equation_rejects_an_unknown_key():
    with pytest.raises(ValueError, match="No equation is registered under that key."):
        compute_equation("nope", Subject(40, 170, 1, 3.0, 4.0))


def test_kubota_2014_is_registered_as_a_regional_set():
    spec = EQUATIONS["kubota_2014"]
    assert spec.group == "regional"
    assert spec.ethnicities is None
    assert spec.has_lower_limit is True
    assert spec.age_range == (17, 95)
    assert "women below 94 years" in spec.population
    assert spec.caveat
    assert "kubota_2014" not in DEFAULT_KEYS


def test_compute_equation_kubota_matches_the_direct_wrapper():
    subject = Subject(40, 170, 2, 2.5, 3.2)
    got = compute_equation("kubota_2014", subject)
    pd.testing.assert_frame_equal(got, compute_kubota_2014(40, 170, 2, 2.5, 3.2))


def test_pereira_2007_is_registered_as_a_regional_set():
    spec = EQUATIONS["pereira_2007"]
    assert spec.name == "Pereira 2007 (Brazil)"
    assert spec.citation == "Pereira et al., J Bras Pneumol 2007"
    assert spec.group == "regional"
    assert spec.ethnicities is None
    assert spec.has_lower_limit is True
    assert spec.age_range == (20, 86)
    assert spec.population.startswith("White Brazilian adults, 20 to 86 years")
    assert "152 to 192 cm" in spec.population
    assert "137 to 182 cm" in spec.population
    assert "White Brazilian adults" in spec.caveat
    assert "z-score" in spec.caveat
    assert "not classified" not in spec.caveat
    assert "severity is not graded" in spec.caveat
    assert "pereira_2007" not in DEFAULT_KEYS


def test_compute_equation_pereira_matches_the_direct_wrapper():
    subject = Subject(40, 165, 2, 2.5, 3.2)
    got = compute_equation("pereira_2007", subject)
    pd.testing.assert_frame_equal(got, compute_pereira_2007(40, 165, 2, 2.5, 3.2))


def test_eccs_1993_is_registered_as_a_historical_set():
    spec = EQUATIONS["eccs_1993"]
    assert spec.name == "ECCS/Quanjer 1993"
    assert spec.citation == "Quanjer et al., Eur Respir J 1993"
    assert spec.group == "historical"
    assert spec.ethnicities is None
    assert spec.has_lower_limit is False
    assert spec.age_range == (18, 70)
    assert spec.population.startswith("Adults of European descent, 18 to 70 years")
    assert "155 to 195 cm" in spec.population
    assert "145 to 180 cm" in spec.population
    assert spec.caveat == (
        "Predicted values and percent of predicted only. No lower limit or "
        "z-score, so the result is not classified. Historical set, kept for "
        "comparison. For men the source gives the ratio as FEV1/VC; it is "
        "shown here as FEV1/FVC."
    )
    assert "eccs_1993" not in DEFAULT_KEYS


def test_compute_equation_eccs_matches_the_direct_wrapper():
    subject = Subject(40, 165, 2, 2.5, 3.2)
    got = compute_equation("eccs_1993", subject)
    pd.testing.assert_frame_equal(got, compute_eccs_1993(40, 165, 2, 2.5, 3.2))
