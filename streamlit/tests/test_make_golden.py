"""Tests for tools/make_golden.py.

The generator writes the golden fixture for the JavaScript app: cases from
the Python oracle (quadrant.registry.compute_equation) that the JavaScript
engine must reproduce. These tests check the file, not the equations.
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path

import pytest

from quadrant import wrappers
from quadrant.registry import EQUATIONS, Subject, compute_equation
from tools import make_golden

WRAPPERS_PATH = Path(wrappers.__file__)
ROW_FIELDS = ["parameter", "observed", "predicted", "lln", "zScore", "percentPredicted"]
PARAMETERS = ["FEV1", "FVC", "FEV1FVC"]
FIXED_DATE = "2026-01-01"
MAX_BYTES = 5_000_000


def _strict_loads(text: str):
    def refuse(token):
        raise ValueError(f"non-JSON constant {token}")

    return json.loads(text, parse_constant=refuse)


@pytest.fixture(scope="module")
def golden_path(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("golden") / "golden.json"
    assert make_golden.main(["--out", str(path), "--date", FIXED_DATE]) == 0
    return path


@pytest.fixture(scope="module")
def golden(golden_path) -> dict:
    return _strict_loads(golden_path.read_text(encoding="utf-8"))


def _subject(case: dict) -> Subject:
    def number(value):
        return math.nan if value is None else value

    s = case["subject"]
    return Subject(
        number(s["ageYears"]),
        number(s["heightCm"]),
        s["sexCode"],
        number(s["fev1"]),
        number(s["fvc"]),
    )


def _oracle(case: dict):
    """Expected value of a case, from a direct call of the oracle."""
    try:
        table = compute_equation(case["equation"], _subject(case), case["ethnicityCode"])
    except ValueError as error:
        return {"error": str(error)}
    rows = []
    for record in table.to_dict("records"):
        row = {
            "parameter": record["parameter"],
            "observed": record["observed"],
            "predicted": record["predicted"],
            "lln": record["lln"],
            "zScore": record["z_score"],
            "percentPredicted": record["percent_predicted"],
        }
        rows.append(
            {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
        )
    return rows


# --- shape -----------------------------------------------------------------


def test_golden_has_cases_for_all_six_equations(golden):
    assert set(golden) == {"meta", "cases"}
    counts = {key: 0 for key in EQUATIONS}
    for case in golden["cases"]:
        counts[case["equation"]] += 1
    assert set(counts) == {
        "gli_2012",
        "gli_2022",
        "nhanes3",
        "kubota_2014",
        "pereira_2007",
        "eccs_1993",
    }
    for key, count in counts.items():
        assert count >= 100, key
    # Both outcomes appear for every equation.
    for key in EQUATIONS:
        mine = [c for c in golden["cases"] if c["equation"] == key]
        assert any(isinstance(c["expected"], list) for c in mine), key
        assert any(isinstance(c["expected"], dict) for c in mine), key


def test_meta_and_case_shape(golden):
    meta = golden["meta"]
    for field in ("generator", "pyspiroVersion", "appCommit", "date"):
        assert isinstance(meta[field], str) and meta[field], field
    assert meta["date"] == FIXED_DATE
    assert meta["generator"] == "streamlit/tools/make_golden.py"
    for case in golden["cases"]:
        assert list(case) == ["equation", "subject", "ethnicityCode", "expected"]
        assert list(case["subject"]) == ["ageYears", "heightCm", "sexCode", "fev1", "fvc"]
        assert case["ethnicityCode"] is None or isinstance(case["ethnicityCode"], (int, float))
        expected = case["expected"]
        if isinstance(expected, dict):
            assert list(expected) == ["error"]
            assert isinstance(expected["error"], str) and expected["error"]
        else:
            assert [row["parameter"] for row in expected] == PARAMETERS
            for row in expected:
                assert list(row) == ROW_FIELDS


def test_ethnicities_cover_every_code_of_the_equation(golden):
    wanted = {
        "gli_2012": {1, 2, 3, 4, 5},
        "nhanes3": {1, 2, 3},
    }
    for key, codes in wanted.items():
        seen = {
            c["ethnicityCode"]
            for c in golden["cases"]
            if c["equation"] == key and isinstance(c["expected"], list)
        }
        assert codes <= seen, key


def test_both_sexes_and_fractional_ages_appear(golden):
    for key in EQUATIONS:
        mine = [c for c in golden["cases"] if c["equation"] == key]
        valid = [c for c in mine if isinstance(c["expected"], list)]
        assert {c["subject"]["sexCode"] for c in valid} == {1, 2}, key
        ages = {c["subject"]["ageYears"] for c in valid}
        assert 40.5 in ages and 33.33 in ages, key


def test_nhanes3_change_point_ages_are_present(golden):
    for sex in (1, 2):
        ages = {
            c["subject"]["ageYears"]
            for c in golden["cases"]
            if c["equation"] == "nhanes3" and c["subject"]["sexCode"] == sex
        }
        assert {8, 17, 17.5, 18, 19, 19.5, 20} <= ages


def test_pereira_paper_limit_case_is_present(golden):
    hits = [
        c
        for c in golden["cases"]
        if c["equation"] == "pereira_2007"
        and c["subject"]
        == {"ageYears": 27, "heightCm": 163, "sexCode": 1, "fev1": 3.28, "fvc": 4.0}
    ]
    assert len(hits) == 1 and isinstance(hits[0]["expected"], list)


def test_edge_inputs_are_present(golden):
    for key in EQUATIONS:
        mine = [c for c in golden["cases"] if c["equation"] == key]
        subjects = [c["subject"] for c in mine]
        assert any(
            s["fev1"] is not None and s["fvc"] is not None and s["fev1"] > s["fvc"]
            for s in subjects
        ), key
        assert any(
            s["fev1"] is not None and s["fvc"] is not None and s["fev1"] == s["fvc"] > 0
            for s in subjects
        ), key
        assert any(s["fev1"] is not None and s["fev1"] <= 0 for s in subjects), key
        assert any(
            s["fev1"] is not None and 0 < s["fev1"] <= 1e-9 for s in subjects
        ), key
        assert any(s["fvc"] is not None and s["fvc"] >= 1e6 for s in subjects), key
        assert any(s["sexCode"] not in (1, 2) for s in subjects), key
        assert any(s["heightCm"] in (49, 251) for s in subjects), key
        assert any(s["ageYears"] is not None and s["ageYears"] < 0 for s in subjects), key
        assert any(s["ageYears"] is not None and s["ageYears"] > 120 for s in subjects), key
    for key in ("gli_2012", "nhanes3"):
        codes = {
            c["ethnicityCode"]
            for c in golden["cases"]
            if c["equation"] == key and isinstance(c["expected"], dict)
        }
        assert codes - {1, 2, 3, 4, 5} or None in codes, key


# --- error messages --------------------------------------------------------


def _raise_templates() -> list[re.Pattern]:
    """One regular expression for each ValueError raised in wrappers.py.

    Read from the source: a constant part is escaped, a formatted part
    (an f-string field) becomes a wildcard.
    """
    tree = ast.parse(WRAPPERS_PATH.read_text(encoding="utf-8"))
    patterns = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Raise)
            and isinstance(node.exc, ast.Call)
            and getattr(node.exc.func, "id", None) == "ValueError"
        ):
            continue
        argument = node.exc.args[0]
        if isinstance(argument, ast.Constant):
            text = re.escape(argument.value)
        elif isinstance(argument, ast.JoinedStr):
            text = "".join(
                re.escape(part.value) if isinstance(part, ast.Constant) else ".+?"
                for part in argument.values
            )
        else:
            raise AssertionError(f"unexpected raise at line {node.lineno}")
        patterns.append(re.compile(f"^{text}$", re.DOTALL))
    return patterns


# The step 3 message ("has no reference value") is reachable only for
# NHANES III. For the other five equations no input that passes the checks
# of steps 1 and 2 gives NaN (checked on a grid of ages 0 to 100 and heights
# 49 to 251 in both sexes). Their patterns need no case.
STEP3_ONLY_NHANES = "NHANES III has no reference value for these inputs"


def test_wrappers_source_has_the_expected_raises():
    # If a wrapper gains or loses a ValueError, update the catalogue below.
    assert len(_raise_templates()) == 14


def test_every_wrapper_error_message_appears_at_least_once(golden):
    messages = {
        c["expected"]["error"]
        for c in golden["cases"]
        if isinstance(c["expected"], dict)
    }
    missing = []
    for template in _raise_templates():
        if template.pattern.startswith("^.+?\\ has\\ no\\ reference\\ value"):
            continue  # checked by name below
        if not any(template.match(m) for m in messages):
            missing.append(template.pattern)
    assert not missing, missing
    assert any(m.startswith(STEP3_ONLY_NHANES) for m in messages)


def test_every_variant_of_a_parameterised_message_appears(golden):
    messages = {
        c["expected"]["error"]
        for c in golden["cases"]
        if isinstance(c["expected"], dict)
    }
    required = [
        "Age must be a single number.",
        "Height must be a single number.",
        "FEV1 must be a single number.",
        "FVC must be a single number.",
        "Age must be between 3 and 95 years for this equation.",
        "Age must be between 8 and 80 years for this equation.",
        "Age must be between 17 and 95 years for this equation.",
        "Age must be between 0 and 120 years for this equation.",
        "Height must be between 50 and 250 cm.",
        "FEV1 and FVC must be greater than zero.",
        "FEV1 cannot be larger than FVC. Check the values.",
        "Sex must be one of the codes 1 (male), 2 (female).",
        "Ethnicity must be one of the codes of this equation: "
        "1 (Caucasian), 2 (African-American), 3 (NE Asian), 4 (SE Asian), "
        "5 (Other/mixed).",
        "Ethnicity must be one of the codes of this equation: "
        "1 (Caucasian), 2 (African-American), 3 (Mexican-American).",
        "For women, Kubota 2014 (JRS) covers ages below 94 years.",
        "For men, Pereira 2007 covers ages 26 to 86 years.",
        "For women, Pereira 2007 covers ages 20 to 85 years.",
        "For men, Pereira 2007 covers heights 152 to 192 cm.",
        "For women, Pereira 2007 covers heights 137 to 182 cm.",
        "ECCS 1993 covers ages 18 to 70 years.",
        "For men, ECCS 1993 covers heights 155 to 195 cm.",
        "For women, ECCS 1993 covers heights 145 to 180 cm.",
        "NHANES III has no reference value for these inputs. The equation "
        "covers a limited range of age and height.",
    ]
    missing = [text for text in required if text not in messages]
    assert not missing, missing


# --- determinism, oracle, floor, JSON --------------------------------------


def test_the_file_is_deterministic(golden_path, tmp_path):
    second = tmp_path / "again" / "golden.json"
    assert make_golden.main(["--out", str(second), "--date", FIXED_DATE]) == 0
    assert golden_path.read_bytes() == second.read_bytes()


def test_a_sample_of_20_cases_equals_a_direct_oracle_call(golden):
    cases = golden["cases"]
    step = len(cases) // 20
    sample = cases[::step][:20]
    assert len(sample) == 20
    for case in sample:
        assert _oracle(case) == case["expected"], case
    # Plus one valid and one error case from every equation.
    for key in EQUATIONS:
        mine = [c for c in cases if c["equation"] == key]
        for wanted in (list, dict):
            case = next(c for c in mine if isinstance(c["expected"], wanted))
            assert _oracle(case) == case["expected"], case


def test_eccs_cases_between_18_and_25_show_the_floor(golden):
    young = [
        c
        for c in golden["cases"]
        if c["equation"] == "eccs_1993"
        and isinstance(c["expected"], list)
        and 18 <= c["subject"]["ageYears"] < 25
    ]
    assert any(c["subject"]["ageYears"] == 18 for c in young)
    assert any(c["subject"]["ageYears"] == 24.99 for c in young)
    assert {c["subject"]["sexCode"] for c in young} == {1, 2}
    for case in young:
        s = dict(case["subject"])
        s["ageYears"] = 25
        floored = compute_equation(
            "eccs_1993",
            Subject(s["ageYears"], s["heightCm"], s["sexCode"], s["fev1"], s["fvc"]),
        )
        for row, record in zip(case["expected"], floored.to_dict("records")):
            assert row["predicted"] == record["predicted"]
            assert row["percentPredicted"] == record["percent_predicted"]


def test_the_file_has_no_nan_or_infinity_literal(golden_path):
    text = golden_path.read_text(encoding="utf-8")
    assert not re.search(r"\bNaN\b|-?\bInfinity\b", text)
    _strict_loads(text)  # a strict parser refuses NaN and Infinity
    data = json.loads(text)
    nulls = 0
    for case in data["cases"]:
        if isinstance(case["expected"], list):
            for row in case["expected"]:
                for field in ROW_FIELDS[1:]:
                    value = row[field]
                    assert value is None or math.isfinite(value)
                    nulls += value is None
    assert nulls > 0  # Pereira and ECCS have no z-score


def test_regression_equations_without_z_score_give_null(golden):
    for key, columns in (
        ("pereira_2007", {"zScore"}),
        ("eccs_1993", {"zScore", "lln"}),
    ):
        rows = [
            row
            for c in golden["cases"]
            if c["equation"] == key and isinstance(c["expected"], list)
            for row in c["expected"]
        ]
        assert rows
        for row in rows:
            for column in columns:
                assert row[column] is None
        for column in set(ROW_FIELDS[1:]) - columns:
            assert all(row[column] is not None for row in rows), (key, column)


def test_the_file_fits_the_cap_and_meta_states_the_thinning(golden_path, golden):
    assert golden_path.stat().st_size <= MAX_BYTES
    thinning = golden["meta"]["thinning"]
    assert {"ageStepYears", "heightStepCm", "thinned"} <= set(thinning)
    assert golden["meta"]["caseCount"] == len(golden["cases"])


def test_the_pereira_limit_cells_are_covered(golden):
    # Cells where the computed limit differs from the paper limit in the last
    # bit: observed values equal to the limit rounded to two decimals.
    hits = 0
    for c in golden["cases"]:
        if c["equation"] != "pereira_2007" or not isinstance(c["expected"], list):
            continue
        row = c["expected"][0]
        if row["lln"] != row["observed"] and abs(row["lln"] - row["observed"]) < 1e-9:
            hits += 1
    assert hits >= 5
