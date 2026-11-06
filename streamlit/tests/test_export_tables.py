"""Tests for tools/export_tables.py.

The export writes the pyspiro tables of the six Quadrant equations to JSON
for the JavaScript app. These tests check four things:

1. The export is deterministic and every file has the documented header.
2. The JSON holds the same numbers as the pyspiro CSV files (read here with
   the csv module, not with pandas).
3. The shape of the tables is described in meta.shape.
4. The JSON alone is enough to reproduce the Python wrappers. The function
   _evaluate below uses only the JSON and the formulas of EXPORT_FORMAT.md.
"""

from __future__ import annotations

import csv
import importlib.metadata
import importlib.resources
import json
import math
from decimal import ROUND_HALF_UP, Decimal

import pytest
from pyspiro import (
    BOWERMAN_2022,
    ECCS_1993,
    GLI_2012,
    HANKINSON_1999,
    KUBOTA_2014,
    PEREIRA_2007,
)

from quadrant import wrappers
from quadrant.constants import SPIROMETRY_PARAMS
from tools import export_tables as ex

FILES = {
    "gli2012.json": "gli_2012",
    "gli2022.json": "gli_2022",
    "nhanes3.json": "nhanes3",
    "kubota2014.json": "kubota_2014",
    "pereira2007.json": "pereira_2007",
    "eccs1993.json": "eccs_1993",
}
MAX_TOTAL_BYTES = 2_000_000


# --- helpers -----------------------------------------------------------


def _csv_rows(name: str, delimiter: str = ";") -> list[dict]:
    path = importlib.resources.files("pyspiro.data") / name
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def _number(text: str):
    """CSV text to float; empty and NA to None (JSON null)."""
    return None if text in ("", "NA") else float(text)


def _reject_constant(name):
    raise AssertionError(f"JSON constant {name} is not allowed")


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    out = tmp_path_factory.mktemp("export")
    ex.main(["--out", str(out)])
    return out


@pytest.fixture(scope="module")
def docs(written):
    result = {}
    for name in FILES:
        text = (written / name).read_text(encoding="utf-8")
        result[name] = json.loads(text, parse_constant=_reject_constant)
    return result


# --- 1. determinism and header ----------------------------------------


def test_export_is_deterministic(written, tmp_path):
    second = tmp_path / "again"
    ex.main(["--out", str(second)])
    assert sorted(p.name for p in written.iterdir()) == sorted(FILES)
    for name in FILES:
        assert (written / name).read_bytes() == (second / name).read_bytes()


def test_keys_are_sorted_in_every_file(written):
    def check(pairs):
        keys = [k for k, _ in pairs]
        assert keys == sorted(keys)
        return dict(pairs)

    for name in FILES:
        json.loads((written / name).read_text(encoding="utf-8"), object_pairs_hook=check)


def test_meta_is_present_in_every_file(docs):
    version = importlib.metadata.version("pyspiro")
    assert version == "1.0.0"
    for name, key in FILES.items():
        doc = docs[name]
        assert set(doc) == {"meta", "tables"}
        meta = doc["meta"]
        assert meta["pyspiroVersion"] == version
        assert meta["licence"] == "MIT (pyspiro)"
        assert meta["equation"] == key
        assert "pyspiro" in meta["source"] and ".csv" in meta["source"]
        assert isinstance(meta["shape"], dict) and meta["shape"]


def test_meta_shape_describes_every_table(docs):
    for name, doc in docs.items():
        assert set(doc["meta"]["shape"]) == set(doc["tables"]), name
        assert all(isinstance(v, str) and v for v in doc["meta"]["shape"].values())


def test_total_size_stays_below_two_megabytes(written):
    total = sum(p.stat().st_size for p in written.iterdir())
    assert total < MAX_TOTAL_BYTES


# --- 2. values equal the CSV values -----------------------------------


def _lms_spline_check(doc, splines_csv, coeffs_csv):
    rows = _csv_rows(splines_csv)
    tables = doc["tables"]
    assert len(tables["ages"]) == len(rows)
    assert tables["ages"] == [float(r["age"]) for r in rows]
    columns = [c for c in rows[0] if c != "age"]
    assert sorted(tables["splines"]) == sorted(columns)
    for column in columns:
        assert len(tables["splines"][column]) == len(rows)
        assert tables["splines"][column] == [_number(r[column]) for r in rows]
    _coefficient_check(tables["coefficients"], coeffs_csv)


def _coefficient_check(coefficients, coeffs_csv):
    rows = _csv_rows(coeffs_csv)
    columns = [c for c in rows[0] if c not in ("var", "")]
    assert sorted(coefficients) == sorted(columns)
    for column in columns:
        assert len(coefficients[column]) == len(rows)
        for row in rows:
            assert coefficients[column][row["var"]] == _number(row[column])


def test_gli2012_values_equal_the_csv(docs):
    _lms_spline_check(
        docs["gli2012.json"], "gli_2012_splines.csv", "gli_2012_coefficients.csv"
    )


def test_gli2022_values_equal_the_csv(docs):
    _lms_spline_check(
        docs["gli2022.json"], "bowerman_2022_splines.csv", "bowerman_2022_coefficients.csv"
    )


def test_kubota_values_equal_the_csv(docs):
    tables = docs["kubota2014.json"]["tables"]
    rows = _csv_rows("kubota_2014_splines.csv", delimiter=",")
    assert sum(len(v["agebound"]) for v in tables["splines"].values()) == len(rows)
    sex_key = {"1": "males", "2": "females"}
    for row in rows:
        group = tables["splines"][f"{row['f']}_{sex_key[row['gender']]}"]
        index = group["agebound"].index(int(row["agebound"]))
        for name in ("Lspline", "Mspline", "Sspline"):
            assert group[name][index] == _number(row[name])
    _coefficient_check(tables["coefficients"], "kubota_2014_coefficients.csv")


def test_nhanes3_values_equal_the_csv(docs):
    tables = docs["nhanes3.json"]["tables"]
    t45 = _csv_rows("hankinson_1999_coefficients_t4_t5.csv")
    t6 = _csv_rows("hankinson_1999_coefficients_t6.csv")
    leaves = 0
    for row in t45:
        got = tables["coefficients"]["t4t5"][row["parameter"]][row["sex"]][
            row["ethnicity"]
        ][row["age_group"]]
        for name in ("a0_pred", "a1_age", "a2_age2", "a3_ht2_pred", "a3_ht2_lln"):
            assert got[name] == float(row[name])
        leaves += 1
    assert leaves == len(t45) == 60
    for row in t6:
        got = tables["coefficients"]["t6"][row["parameter"]][row["sex"]][row["ethnicity"]]
        for name in ("a0_pred", "a0_lln", "a1_age"):
            assert got[name] == float(row[name])
        assert "R2" not in got
    assert len(t6) == 12


def test_pereira_values_equal_the_csv(docs):
    coefficients = docs["pereira2007.json"]["tables"]["coefficients"]
    rows = _csv_rows("pereira_2007_coefficients.csv")
    assert sum(len(v) for v in coefficients.values()) == len(rows)
    for row in rows:
        got = coefficients[row["parameter"]][row["sex"]]
        assert got["kind"] == row["kind"]
        for name in ("a0", "a_ht", "a_age", "a_wt", "lln"):
            assert got[name] == float(row[name])


def test_eccs_values_equal_the_csv(docs):
    coefficients = docs["eccs1993.json"]["tables"]["coefficients"]
    rows = _csv_rows("eccs_1993_coefficients.csv")
    assert sum(len(v) for v in coefficients.values()) == len(rows)
    for row in rows:
        got = coefficients[row["parameter"]][row["sex"]]
        for name in ("a0", "a_ht", "a_age"):
            assert got[name] == float(row[name])


def test_spot_check_ten_cells_per_file(docs):
    """Ten fixed cells per file, as named values (guards the lookup keys)."""
    gli = docs["gli2012.json"]["tables"]
    rows = _csv_rows("gli_2012_splines.csv")
    columns = [c for c in rows[0] if c != "age"]
    for k in range(10):
        row = rows[(k * 37) % len(rows)]
        column = columns[(k * 7) % len(columns)]
        index = gli["ages"].index(float(row["age"]))
        assert gli["splines"][column][index] == _number(row[column])
    # Fixed cells of the small tables.
    assert docs["eccs1993.json"]["tables"]["coefficients"]["FEV1"]["male"]["a0"] == -2.49
    assert docs["pereira2007.json"]["tables"]["coefficients"]["FVC"]["male"]["a_ht"] == 0.0517
    nh = docs["nhanes3.json"]["tables"]["coefficients"]["t4t5"]
    assert nh["FEV1"]["male"]["caucasian"]["child"]["a0_pred"] == -0.7453


# --- NHANES III groups --------------------------------------------------


def test_nhanes3_has_child_and_adult_groups_for_both_sexes(docs):
    tables = docs["nhanes3.json"]["tables"]
    t45 = tables["coefficients"]["t4t5"]
    for parameter in ("FEV1", "FVC"):
        for sex in ("male", "female"):
            for ethnicity in ("caucasian", "african_american", "mexican_american"):
                for group in ("child", "adult"):
                    assert set(t45[parameter][sex][ethnicity][group]) == {
                        "a0_pred",
                        "a1_age",
                        "a2_age2",
                        "a3_ht2_pred",
                        "a3_ht2_lln",
                    }
                    assert group in tables["heightRangesCm"][sex][ethnicity]
    assert tables["changePointYears"] == {"female": 18, "male": 20}
    ratio = tables["coefficients"]["t6"]["FEV1FVC"]
    assert set(ratio) == {"male", "female"}


def test_nhanes3_uses_the_paper_change_point_not_the_pyspiro_one(docs):
    tables = docs["nhanes3.json"]["tables"]
    assert tables["changePointYears"]["male"] == 20
    assert tables["pyspiroChildMaxAgeYears"] == {"female": 17, "male": 19}


# --- 3. constants taken from code -------------------------------------


def test_constants_match_the_app_and_pyspiro(docs):
    p = docs["pereira2007.json"]["tables"]
    assert p["ranges"]["male"] == {"ageYears": [26, 86], "heightCm": [152.0, 192.0]}
    assert p["ranges"]["female"] == {"ageYears": [20, 85], "heightCm": [137.0, 182.0]}
    e = docs["eccs1993.json"]["tables"]
    assert e["ageRangeYears"] == [18, 70]
    assert e["heightRangesCm"] == {"female": [145.0, 180.0], "male": [155.0, 195.0]}
    assert e["app"]["ageFloorYears"] == 25
    assert e["ageFloorYears"] == 25
    assert docs["gli2012.json"]["tables"]["ageStepYears"] == 0.25
    k = docs["kubota2014.json"]["tables"]
    assert k["ageRangeYears"] == [17, 95]
    assert k["app"]["femaleMaxAgeYearsExclusive"] == 94
    for name in ("nhanes3.json", "pereira2007.json", "eccs1993.json"):
        assert docs[name]["tables"]["app"]["ratioScale"] == 100.0
    for name in ("gli2012.json", "gli2022.json", "kubota2014.json"):
        assert docs[name]["tables"]["app"]["ratioScale"] == 1.0
    for doc in docs.values():
        assert doc["tables"]["app"]["parameters"] == list(SPIROMETRY_PARAMS)
        assert doc["tables"]["app"]["sexCodes"] == {"Female": 2, "Male": 1}


# --- 4. the JSON alone reproduces the wrappers --------------------------

LLN_Z = 1.645  # the literal of pyspiro LMSReference.lln and HANKINSON_1999._result


# --- percent predicted: the rounding rule of each family -----------------
#
# The two functions below are Python mirrors of the JavaScript code in
# EXPORT_FORMAT.md. Keep them the same, line by line.
#
# LMS classes (GLI-2012, GLI-Global 2022, Kubota): the percent is a
# numpy.float64, so round(x, 2) is numpy rounding: rint(x * 100) / 100,
# half to even on the binary product.
#
#     function roundLms(x) {
#       const y = x * 100;
#       let r = Math.round(y);
#       if (r - y === 0.5 && r % 2 !== 0) r -= 1;
#       return r / 100;
#     }
#
# Regression classes (NHANES III, Pereira, ECCS): the percent is a Python
# float, so round(x, 2) is correctly rounded from the exact binary value. An
# exact tie is possible only when x is an odd multiple of 1/8. Ties go to
# the even hundredth. toFixed(2) takes ties up, so they are handled first.
#
#     function roundRegression(x) {
#       const k = x * 8;
#       if (Number.isInteger(k) && k % 2 !== 0) {
#         const lo = Math.floor(x * 100);
#         return (lo % 2 === 0 ? lo : lo + 1) / 100;
#       }
#       return Number(x.toFixed(2));
#     }


def round_lms(x):
    y = x * 100.0
    r = math.floor(y)
    if y - r >= 0.5:  # Math.round: ties go toward +infinity
        r += 1
    if r - y == 0.5 and r % 2 != 0:
        r -= 1
    return r / 100


def round_regression(x):
    k = x * 8
    if k == math.floor(k) and k % 2 != 0:
        lo = math.floor(x * 100)
        return (lo if lo % 2 == 0 else lo + 1) / 100
    # toFixed(2): exact decimal value, ties up (the ties were handled above)
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _gli_lms(tables, prefix, age, height, ethnicity, lms_kind):
    lo, hi = tables["splineAgeRangesYears"][f"{prefix}"]
    if not lo <= age <= hi:
        return None
    step = tables["ageStepYears"]
    lower = math.floor(age / step) * step
    weight = (age - lower) / step

    def at(a):
        i = round((a - tables["ages"][0]) / step)
        return [tables["splines"][f"{prefix}_{n}spline"][i] for n in "SML"]

    s_l = at(lower)
    if weight == 0:
        sp = s_l
    else:
        s_u = at(min(lower + step, hi))
        sp = [(1 - weight) * x + weight * y for x, y in zip(s_l, s_u)]
    sspline, mspline, lspline = sp
    c = tables["coefficients"][prefix]
    ln_age, ln_h = math.log(age), math.log(height)
    if lms_kind == "gli2012":
        ind = lambda code: 1.0 if ethnicity == code else 0.0  # noqa: E731
        l = c["q0"] + c["q1"] * ln_age + lspline
        m = math.exp(
            c["a0"] + c["a1"] * ln_h + c["a2"] * ln_age
            + c["a3"] * ind(2) + c["a4"] * ind(3) + c["a5"] * ind(4) + c["a6"] * ind(5)
            + mspline
        )
        s = math.exp(
            c["p0"] + c["p1"] * ln_age
            + c["p2"] * ind(2) + c["p3"] * ind(3) + c["p4"] * ind(4) + c["p5"] * ind(5)
            + sspline
        )
    else:
        param = prefix.split("_")[0]
        l = c["q0"] if param in ("FEV1", "FVC") else c["q0"] + c["q1"] * ln_age
        m = math.exp(c["a0"] + c["a1"] * ln_h + c["a2"] * ln_age + mspline)
        s = math.exp(c["p0"] + c["p1"] * ln_age + sspline)
    return l, m, s


def _lms_row(l, m, s, value):
    lln = math.exp(math.log(1 - LLN_Z * l * s) / l + math.log(m))
    z = (((value / m) ** l) - 1) / (l * s)
    return m, lln, z, round_lms(value / m * 100)


def _kubota_lms(tables, prefix, age, height):
    lo, hi = tables["ageRangeYears"]
    if not lo <= age <= hi:
        return None
    group = tables["splines"][prefix]
    if int(age) not in group["agebound"]:
        return None
    i = group["agebound"].index(int(age))
    s_, m_, l_ = group["Sspline"][i], group["Mspline"][i], group["Lspline"][i]
    if m_ is None or s_ is None:
        return None
    c = tables["coefficients"][prefix]
    l = c["q0"] + c["q1"] * math.log(age) + (0.0 if l_ is None else l_)
    m = math.exp(c["a0"] + c["a1"] * math.log(height) + c["a2"] * math.log(age) + m_)
    s = math.exp(c["p0"] + c["p1"] * math.log(age) + s_)
    return l, m, s


def _nhanes3_row(tables, param, sex_key, eth_key, age, height, value):
    lo, hi = tables["ageRangeYears"]
    if not lo <= age <= hi:
        return None
    if param == "FEV1FVC":
        r = tables["coefficients"]["t6"][param][sex_key][eth_key]
        pred = r["a0_pred"] + r["a1_age"] * age
        lln = r["a0_lln"] + r["a1_age"] * age
    else:
        group = "child" if age < tables["changePointYears"][sex_key] else "adult"
        h_lo, h_hi = tables["heightRangesCm"][sex_key][eth_key][group]
        if not h_lo <= height <= h_hi:
            return None
        r = tables["coefficients"]["t4t5"][param][sex_key][eth_key][group]
        base = r["a0_pred"] + r["a1_age"] * age + r["a2_age2"] * age**2
        pred = base + r["a3_ht2_pred"] * height**2
        lln = base + r["a3_ht2_lln"] * height**2
    see = (pred - lln) / LLN_Z
    return pred, lln, (value - pred) / see, round_regression(value / pred * 100)


def _evaluate(name, doc, subject, ethnicity):
    """Table of (predicted, lln, z, percent) in app units, from the JSON only."""
    t = doc["tables"]
    app = t["app"]
    sex_key = app["sexKeyByAppCode"][str(subject["sex"])]
    observed = {
        "FEV1": subject["fev1"],
        "FVC": subject["fvc"],
        "FEV1FVC": subject["fev1"] / subject["fvc"],
    }
    scale_all = app["ratioScale"]
    out = {}
    age, height = subject["age"], subject["height"]
    for param in app["parameters"]:
        scale = scale_all if param == "FEV1FVC" else 1.0
        value = observed[param] * scale
        if name in ("gli2012.json", "gli2022.json"):
            kind = "gli2012" if name == "gli2012.json" else "gli2022"
            lms = _gli_lms(t, f"{param}_{sex_key}", age, height, ethnicity, kind)
            row = None if lms is None else _lms_row(*lms, value)
        elif name == "kubota2014.json":
            lms = _kubota_lms(t, f"{param}_{sex_key}", age, height)
            row = None if lms is None else _lms_row(*lms, value)
        elif name == "nhanes3.json":
            eth_key = app["ethnicityKeyByCode"][str(ethnicity)]
            row = _nhanes3_row(t, param, sex_key, eth_key, age, height, value)
        elif name == "pereira2007.json":
            rng = t["ranges"][sex_key]
            if not (
                rng["ageYears"][0] <= age <= rng["ageYears"][1]
                and rng["heightCm"][0] <= height <= rng["heightCm"][1]
            ):
                row = None
            else:
                r = t["coefficients"][param][sex_key]
                if r["kind"] == "log":
                    pred = math.exp(r["a0"] + r["a_ht"] * math.log(height) + r["a_age"] * math.log(age))
                    lln = pred * r["lln"]
                else:
                    pred = r["a0"] + r["a_ht"] * height + r["a_age"] * age
                    lln = pred - r["lln"]
                row = (pred, lln, float("nan"), round_regression(value / pred * 100))
        else:  # eccs1993
            rng = t["heightRangesCm"][sex_key]
            if not (t["ageRangeYears"][0] <= age <= t["ageRangeYears"][1]
                    and rng[0] <= height <= rng[1]):
                row = None
            else:
                eq_age = max(age, app["ageFloorYears"])
                r = t["coefficients"][param][sex_key]
                pred = r["a0"] + r["a_ht"] * height + r["a_age"] * eq_age
                row = (pred, float("nan"), float("nan"), round_regression(value / pred * 100))
        if row is None:
            return None
        pred, lln, z, pct = row
        out[param] = (pred / scale, lln / scale, z, pct)
    return out


def _wrapper_call(name, s, ethnicity):
    a, h, x, f1, fv = s["age"], s["height"], s["sex"], s["fev1"], s["fvc"]
    if name == "gli2012.json":
        return wrappers.compute_gli_2012(a, h, x, ethnicity, f1, fv)
    if name == "gli2022.json":
        return wrappers.compute_gli_global_2022(a, h, x, f1, fv)
    if name == "nhanes3.json":
        return wrappers.compute_nhanes3(a, h, x, ethnicity, f1, fv)
    if name == "kubota2014.json":
        return wrappers.compute_kubota_2014(a, h, x, f1, fv)
    if name == "pereira2007.json":
        return wrappers.compute_pereira_2007(a, h, x, f1, fv)
    return wrappers.compute_eccs_1993(a, h, x, f1, fv)


def _close(a, b):
    if math.isnan(b):
        return math.isnan(a)
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


SUBJECTS = [
    {"age": 8.5, "height": 130.0, "sex": 1, "fev1": 1.9, "fvc": 2.2},
    {"age": 17.5, "height": 165.0, "sex": 2, "fev1": 3.0, "fvc": 3.6},
    {"age": 18.5, "height": 165.0, "sex": 2, "fev1": 3.1, "fvc": 3.7},
    {"age": 19.5, "height": 172.0, "sex": 1, "fev1": 4.0, "fvc": 4.9},
    {"age": 23.0, "height": 178.0, "sex": 1, "fev1": 4.4, "fvc": 5.3},
    {"age": 27.0, "height": 163.0, "sex": 1, "fev1": 3.28, "fvc": 4.1},
    {"age": 45.25, "height": 168.0, "sex": 2, "fev1": 2.5, "fvc": 3.2},
    {"age": 62.7, "height": 175.0, "sex": 1, "fev1": 2.4, "fvc": 3.9},
    {"age": 80.0, "height": 158.0, "sex": 2, "fev1": 1.3, "fvc": 2.0},
    {"age": 93.99, "height": 150.0, "sex": 2, "fev1": 0.9, "fvc": 1.4},
]


@pytest.mark.parametrize("name", list(FILES))
def test_json_alone_reproduces_the_wrapper(docs, name):
    doc = docs[name]
    ethnicities = {
        "gli2012.json": (1, 2, 3, 4, 5),
        "nhanes3.json": (1, 2, 3),
    }.get(name, (None,))
    compared = 0
    for subject in SUBJECTS:
        for ethnicity in ethnicities:
            got = _evaluate(name, doc, subject, ethnicity)
            try:
                table = _wrapper_call(name, subject, ethnicity)
            except ValueError:
                assert got is None, (name, subject, ethnicity)
                continue
            assert got is not None, (name, subject, ethnicity)
            for _, row in table.iterrows():
                pred, lln, z, pct = got[row["parameter"]]
                where = (name, subject, ethnicity, row["parameter"])
                assert _close(pred, row["predicted"]), where
                assert _close(lln, row["lln"]), where
                assert _close(z, row["z_score"]), where
                assert _close(pct, row["percent_predicted"]), where
            compared += 1
    assert compared >= 4, name


def test_a_female_change_point_of_20_is_caught(docs):
    """The woman of 18.5 years uses the adult equation (change point 18)."""
    import copy

    subject = next(s for s in SUBJECTS if s["age"] == 18.5)
    table = _wrapper_call("nhanes3.json", subject, 1)
    good = _evaluate("nhanes3.json", docs["nhanes3.json"], subject, 1)
    assert all(_close(good[r["parameter"]][0], r["predicted"]) for _, r in table.iterrows())
    wrong = copy.deepcopy(docs["nhanes3.json"])
    wrong["tables"]["changePointYears"]["female"] = 20
    bad = _evaluate("nhanes3.json", wrong, subject, 1)
    assert not _close(bad["FEV1"][0], table.iloc[0]["predicted"])


# --- percent rounding rules against real pyspiro percent() ----------------
#
# Each case is a value that puts value / predicted * 100 on or next to a
# tie at two decimals. The expected result is what pyspiro returns.

_AGE, _HEIGHT, _SEX = 40, 175, 1


def _step(value, n):
    for _ in range(abs(n)):
        value = math.nextafter(value, math.inf if n > 0 else -math.inf)
    return value


def _lms_cases():
    """(x, pyspiro percent) for GLI-2012, GLI-Global 2022 and Kubota."""
    gli, glg, jrs = GLI_2012(), BOWERMAN_2022(), KUBOTA_2014()
    setups = (
        (lambda v: gli.percent(_SEX, _AGE, _HEIGHT, 1, 1, v),
         gli.lms(_SEX, _AGE, _HEIGHT, 1, 1, 3.0)[1]),
        (lambda v: glg.percent(_SEX, _AGE, _HEIGHT, 1, v),
         glg.lms(_SEX, _AGE, _HEIGHT, 1, 3.0)[1]),
        (lambda v: jrs.percent(_SEX, _AGE, _HEIGHT, 1, v),
         jrs.lms(_SEX, _AGE, _HEIGHT, 1, 3.0)[1]),
    )
    cases = []
    for percent, m in setups:
        for i in range(28):
            tie = (5000 + 37 * i + 0.5) / 100  # a tie at two decimals, in percent
            centre = float(m) * tie / 100
            for j in range(-2, 3):
                value = _step(centre, j)
                x = float((value / m) * 100)  # same operations as LMSReference.percent
                cases.append((x, float(percent(value))))
    return cases


def _regression_cases():
    """(x, pyspiro percent) for NHANES III, Pereira and ECCS."""
    hank, per, ecc = HANKINSON_1999(), PEREIRA_2007(), ECCS_1993()
    setups = (
        (lambda v: hank.percent(_SEX, _AGE, _HEIGHT, 1, 2, v),
         hank._scalar_regression(_SEX, _AGE, _HEIGHT, 1, None, 2).pred),
        (lambda v: per.percent(_SEX, _AGE, _HEIGHT, None, 3, v),
         per._scalar_regression(_SEX, _AGE, _HEIGHT, None, None, 3).pred),
        (lambda v: ecc.percent(_SEX, _AGE, _HEIGHT, None, 2, v),
         ecc._scalar_regression(_SEX, _AGE, _HEIGHT, None, None, 2).pred),
    )
    cases, exact = [], 0
    for percent, pred in setups:
        for i in range(30):
            # decimal near-ties: not exact in binary
            decimal_tie = (5000 + 41 * i + 0.5) / 100
            # exact binary ties: an odd multiple of 1/8
            binary_tie = (400 + 2 * i + 1) / 8
            for target, search in ((decimal_tie, 2), (binary_tie, 12)):
                centre = pred * target / 100
                for j in range(-search, search + 1):
                    value = _step(centre, j)
                    x = value / pred * 100
                    if target == binary_tie and x != binary_tie:
                        continue
                    exact += target == binary_tie
                    cases.append((x, float(percent(value))))
    return cases, exact


def test_lms_family_rounds_like_numpy():
    cases = _lms_cases()
    assert len(cases) >= 400
    for x, expected in cases:
        assert round_lms(x) == expected, x
    # exact ties exist among the cases
    assert any((x * 100) % 1 == 0.5 for x, _ in cases)


def test_regression_family_rounds_like_python():
    cases, exact = _regression_cases()
    assert len(cases) >= 400
    assert exact >= 30  # exact binary ties
    for x, expected in cases:
        assert round_regression(x) == expected, x


def test_swapped_rounding_rules_fail():
    """The two rules differ on these cases, so a swap is caught."""
    lms = _lms_cases()
    reg, _ = _regression_cases()
    assert any(round_regression(x) != e for x, e in lms)
    assert any(round_lms(x) != e for x, e in reg)
    # Plain toFixed(2) (ties up) and plain Math.round are both wrong somewhere.
    assert any(float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)) != e for x, e in reg)
    assert any(math.floor(x * 100 + 0.5) / 100 != e for x, e in lms)
