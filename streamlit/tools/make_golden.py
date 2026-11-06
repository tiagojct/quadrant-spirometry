"""Write the golden fixture for the Quadrant JavaScript app.

Usage:
    uv run python tools/make_golden.py --out <path>/golden.json [--date YYYY-MM-DD]

The fixture holds cases computed by quadrant.registry.compute_equation, the
oracle. The JavaScript engine must reproduce each case: the rows within the
contract tolerances, or the error text exactly.

File shape:

    { "meta": { "generator", "pyspiroVersion", "appCommit", "appTreeDirty",
                "date", "caseCount", "caseCounts", "thinning", "notes" },
      "cases": [ { "equation": key,
                   "subject": { "ageYears", "heightCm", "sexCode", "fev1", "fvc" },
                   "ethnicityCode": number | null,
                   "expected": [ Row, Row, Row ] | { "error": text } } ] }

    Row = { "parameter", "observed", "predicted", "lln", "zScore",
            "percentPredicted" }

The rows come in the order FEV1, FVC, FEV1FVC. NaN becomes null. Floats are
written with repr(), the shortest text that reads back to the same float.
A null in a subject field stands for NaN (the wrappers reject it with
"<label> must be a single number."). The file has no NaN or Infinity
literal: the writer refuses them.

Deterministic: fixed order, no random numbers. The date is the only value
that changes between days; --date fixes it.

The grid follows tools/EXPORT_FORMAT.md and the plan (Task 5). If the full
grid is larger than MAX_BYTES, the middle ages and then the middle heights
are thinned in steps (THINNING_LEVELS). meta.thinning says which level was
used.
"""

from __future__ import annotations

import argparse
import datetime
import importlib.metadata
import json
import math
import subprocess
import sys
from pathlib import Path

# Allow "python tools/make_golden.py" from the streamlit folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quadrant import constants as C  # noqa: E402
from quadrant.registry import EQUATIONS, Subject, compute_equation  # noqa: E402

GENERATOR = "streamlit/tools/make_golden.py"
MAX_BYTES = 5_000_000
PARAMETERS = C.SPIROMETRY_PARAMS

# (age step, height step) in years and cm, from the full grid to the
# thinnest. The limits are always kept.
THINNING_LEVELS = (
    (5, 10),
    (10, 10),
    (10, 20),
    (20, 20),
    (20, 40),
    (40, 40),
)

# Ages and heights of the sub-grid that also gets the observed-value variants.
VARIANT_AGE_STEP = 40
VARIANT_HEIGHT_STEP = 80

PROBE_FEV1 = 1.0
PROBE_FVC = 2.0

# Age ranges by equation and sex code: (low, high, high_is_exclusive).
_GLI_AGES = (C.GLI_AGE_RANGE_YEARS[0], C.GLI_AGE_RANGE_YEARS[1], False)
AGE_RANGES = {
    "gli_2012": {1: _GLI_AGES, 2: _GLI_AGES},
    "gli_2022": {1: _GLI_AGES, 2: _GLI_AGES},
    "nhanes3": {
        s: (C.NHANES3_AGE_RANGE_YEARS[0], C.NHANES3_AGE_RANGE_YEARS[1], False)
        for s in (1, 2)
    },
    "kubota_2014": {
        1: (C.JRS_AGE_RANGE_YEARS[0], C.JRS_AGE_RANGE_YEARS[1], False),
        2: (C.JRS_AGE_RANGE_YEARS[0], C.JRS_FEMALE_MAX_AGE_YEARS, True),
    },
    "pereira_2007": {
        1: (*C.PEREIRA_MALE_AGE_RANGE_YEARS, False),
        2: (*C.PEREIRA_FEMALE_AGE_RANGE_YEARS, False),
    },
    "eccs_1993": {
        s: (C.ECCS_AGE_RANGE_YEARS[0], C.ECCS_AGE_RANGE_YEARS[1], False)
        for s in (1, 2)
    },
}

# Height ranges by equation and sex code. The wrapper range for the others.
_WIDE_HEIGHTS = tuple(C.HEIGHT_RANGE_CM)
HEIGHT_RANGES = {
    "gli_2012": {1: _WIDE_HEIGHTS, 2: _WIDE_HEIGHTS},
    "gli_2022": {1: _WIDE_HEIGHTS, 2: _WIDE_HEIGHTS},
    "nhanes3": {1: _WIDE_HEIGHTS, 2: _WIDE_HEIGHTS},
    "kubota_2014": {1: _WIDE_HEIGHTS, 2: _WIDE_HEIGHTS},
    "pereira_2007": {
        1: tuple(C.PEREIRA_MALE_HEIGHT_RANGE_CM),
        2: tuple(C.PEREIRA_FEMALE_HEIGHT_RANGE_CM),
    },
    "eccs_1993": {
        1: tuple(C.ECCS_MALE_HEIGHT_RANGE_CM),
        2: tuple(C.ECCS_FEMALE_HEIGHT_RANGE_CM),
    },
}

SEXES = (1, 2)

# Percent-of-predicted targets with a tie or a near tie at two decimals, to
# test the family-specific rounding of percent predicted (EXPORT_FORMAT.md).
TIE_PERCENTS = (
    40.005, 50.125, 60.375, 65.995, 70.625, 75.235, 80.125, 85.875,
    90.005, 95.375, 99.995, 100.005, 105.625, 110.125, 119.995,
)  # fmt: skip

# Special-case values.
BAD_SEX_CODES = (0, 3, -1, 1.5)
BAD_ETHNICITY_CODES = (0, 6, 7, -1, 1.5, None)
BAD_AGES = (-1, -0.01, 0, 120, 120.01, 121, 1000)
BAD_HEIGHTS = (0, -10, 49, 49.99, 250.01, 251, 300)
HUGE_VALUES = (100.0, 1e4, 1e6)
TINY_VALUE = 1e-9


class Oracle:
    """compute_equation with a memo and conversion to the fixture shape."""

    def __init__(self) -> None:
        self._memo: dict = {}

    def __call__(self, key, age, height, sex, fev1, fvc, ethnicity):
        memo_key = (key, repr(age), repr(height), repr(sex), repr(fev1), repr(fvc), repr(ethnicity))
        if memo_key not in self._memo:
            self._memo[memo_key] = self._compute(key, age, height, sex, fev1, fvc, ethnicity)
        return self._memo[memo_key]

    @staticmethod
    def _compute(key, age, height, sex, fev1, fvc, ethnicity):
        def number(value):
            return math.nan if value is None else value

        subject = Subject(number(age), number(height), sex, number(fev1), number(fvc))
        try:
            table = compute_equation(key, subject, ethnicity)
        except ValueError as error:
            return {"error": str(error)}
        rows = []
        for record in table.to_dict("records"):
            rows.append(
                {
                    "parameter": record["parameter"],
                    "observed": _clean(record["observed"]),
                    "predicted": _clean(record["predicted"]),
                    "lln": _clean(record["lln"]),
                    "zScore": _clean(record["z_score"]),
                    "percentPredicted": _clean(record["percent_predicted"]),
                }
            )
        assert [r["parameter"] for r in rows] == list(PARAMETERS)
        return rows


def _clean(value):
    """NaN to None; refuse an infinite value (JSON cannot hold it)."""
    value = float(value)
    if math.isnan(value):
        return None
    if math.isinf(value):
        raise ValueError("The oracle gave an infinite value; choose other inputs.")
    return value


def _num(value):
    """Integral floats as ints, so that 27.0 is written 27."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


class Builder:
    """Collects cases without duplicates, in a fixed order."""

    def __init__(self, oracle: Oracle) -> None:
        self.oracle = oracle
        self.cases: dict = {}

    def add(self, key, age, height, sex, fev1, fvc, ethnicity):
        age, height = _num(age), _num(height)
        identity = (key, repr(age), repr(height), repr(sex), repr(fev1), repr(fvc), repr(ethnicity))
        if identity in self.cases:
            return self.cases[identity]["expected"]
        expected = self.oracle(key, age, height, sex, fev1, fvc, ethnicity)
        self.cases[identity] = {
            "equation": key,
            "subject": {
                "ageYears": age,
                "heightCm": height,
                "sexCode": sex,
                "fev1": fev1,
                "fvc": fvc,
            },
            "ethnicityCode": ethnicity,
            "expected": expected,
        }
        return expected

    def probe(self, key, age, height, sex, ethnicity):
        """Rows for a probe subject; the probe case is kept only when it errors."""
        expected = self.oracle(key, _num(age), _num(height), sex, PROBE_FEV1, PROBE_FVC, ethnicity)
        if isinstance(expected, dict):
            self.add(key, age, height, sex, PROBE_FEV1, PROBE_FVC, ethnicity)
        return expected

    def cell(self, key, sex, ethnicity, age, height, variants):
        """Add the cases of one (sex, ethnicity, age, height) cell.

        The probe call gives predicted values and limits; the variants set
        the observed values from them. A cell that errors is kept as one
        error case (the error does not depend on the observed values).
        """
        rows = self.probe(key, age, height, sex, ethnicity)
        if isinstance(rows, dict):
            return
        fev1, fvc, ratio = rows
        for variant in variants:
            values = _variant_values(variant, fev1, fvc, ratio)
            if values is None:
                continue
            self.add(key, age, height, sex, values[0], values[1], ethnicity)

    def ordered(self) -> list[dict]:
        return list(self.cases.values())


def _variant_values(variant, fev1, fvc, ratio):
    """(fev1, fvc) for a variant, from the probe rows; None if not defined."""
    if variant.startswith("p"):
        factor = float(variant[1:]) / 100
        return fev1["predicted"] * factor, fvc["predicted"] * factor
    if variant == "lln":
        if fev1["lln"] is None or fvc["lln"] is None:
            return None
        return fev1["lln"], fvc["lln"]
    if variant == "lln_fev1":
        if fev1["lln"] is None:
            return None
        return fev1["lln"], fvc["predicted"]
    if variant == "lln_fvc":
        if fvc["lln"] is None:
            return None
        return fev1["predicted"], fvc["lln"]
    if variant == "lln_ratio":
        if ratio["lln"] is None:
            return None
        return ratio["lln"] * fvc["predicted"], fvc["predicted"]
    raise ValueError(variant)


# --- grids ---------------------------------------------------------------


def _between(low, high, step):
    """Multiples of step strictly between low and high."""
    first = math.floor(low / step) * step + step
    values = []
    value = first
    while value < high:
        values.append(value)
        value += step
    return values


def age_grid(key, sex, step):
    """Limits, limit -/+ 0.01 and the multiples of step between them."""
    low, high, _exclusive = AGE_RANGES[key][sex]
    ages = [low, round(low - 0.01, 2), round(low + 0.01, 2)]
    ages += [high, round(high - 0.01, 2), round(high + 0.01, 2)]
    ages += _between(low, high, step)
    return sorted(set(ages))


def height_grid(key, sex, step):
    low, high = HEIGHT_RANGES[key][sex]
    return sorted({low, high, *_between(low, high, step)})


def variant_age_grid(key, sex):
    low, high, _ = AGE_RANGES[key][sex]
    return sorted(
        {low, round(low + 0.01, 2), round(high - 0.01, 2), high}
        | set(_between(low, high, VARIANT_AGE_STEP))
    )


def variant_height_grid(key, sex):
    low, high = HEIGHT_RANGES[key][sex]
    return sorted({low, high} | set(_between(low, high, VARIANT_HEIGHT_STEP)))


def ethnicity_codes(key):
    ethnicities = EQUATIONS[key].ethnicities
    return list(ethnicities.values()) if ethnicities else [None]


GRID_VARIANTS = ("p100",)
SUBGRID_VARIANTS = ("p60", "p80", "lln", "lln_ratio")


def add_grid(builder, age_step, height_step):
    for key in EQUATIONS:
        has_lln = EQUATIONS[key].has_lower_limit
        sub_variants = SUBGRID_VARIANTS if has_lln else ("p60", "p80")
        for sex in SEXES:
            ages = age_grid(key, sex, age_step)
            heights = height_grid(key, sex, height_step)
            vages = set(variant_age_grid(key, sex))
            vheights = set(variant_height_grid(key, sex))
            for ethnicity in ethnicity_codes(key):
                for age in ages:
                    for height in heights:
                        in_sub = age in vages and height in vheights
                        variants = GRID_VARIANTS + (sub_variants if in_sub else ())
                        builder.cell(key, sex, ethnicity, age, height, variants)


def add_fractional_ages(builder):
    for key in EQUATIONS:
        for sex in SEXES:
            low, high, _ = AGE_RANGES[key][sex]
            hlow, hhigh = HEIGHT_RANGES[key][sex]
            heights = sorted({max(hlow, 160), min(hhigh, 175), (hlow + hhigh) // 2})
            for ethnicity in ethnicity_codes(key):
                for age in (40.5, 33.33, 59.99, 70.25):
                    if not low <= age <= high:
                        continue
                    for height in heights:
                        builder.cell(key, sex, ethnicity, age, height, ("p100", "p80", "lln"))


def add_ties(builder):
    """Percent-of-predicted ties and near ties, for the rounding helpers."""
    for key in EQUATIONS:
        for sex in SEXES:
            low, high, _ = AGE_RANGES[key][sex]
            hlow, hhigh = HEIGHT_RANGES[key][sex]
            age = _num(float(min(max(45, low), high - 1)))
            for ethnicity in ethnicity_codes(key):
                for height in sorted({max(hlow, 165), (hlow + hhigh) // 2}):
                    rows = builder.probe(key, age, height, sex, ethnicity)
                    if isinstance(rows, dict):
                        continue
                    fev1, fvc, _ratio = rows
                    for index, percent in enumerate(TIE_PERCENTS):
                        other = TIE_PERCENTS[(index + 5) % len(TIE_PERCENTS)]
                        builder.add(
                            key, age, height, sex,
                            fev1["predicted"] * percent / 100,
                            fvc["predicted"] * max(percent, other) / 100,
                            ethnicity,
                        )  # fmt: skip


def add_nhanes3_change_points(builder):
    ages = (8, 17, 17.5, 17.99, 18, 18.01, 19, 19.5, 19.99, 20, 20.01)
    for sex in SEXES:
        for ethnicity in ethnicity_codes("nhanes3"):
            for age in ages:
                for height in (130, 150, 165, 180):
                    builder.cell("nhanes3", sex, ethnicity, age, height, ("p100", "p80", "lln"))


def add_eccs_floor(builder):
    for sex in SEXES:
        low, high = HEIGHT_RANGES["eccs_1993"][sex]
        for age in (18, 18.01, 20, 22.5, 24.99, 25, 25.01):
            for height in (low, (low + high) // 2, high):
                builder.cell("eccs_1993", sex, None, age, height, ("p100", "p60"))


def add_range_limits(builder):
    """Limits of the sex-specific ranges, one step outside, for the messages."""
    for key in EQUATIONS:
        for sex in SEXES:
            low, high, _exclusive = AGE_RANGES[key][sex]
            hlow, hhigh = HEIGHT_RANGES[key][sex]
            mid_age = (low + high) // 2
            mid_height = (hlow + hhigh) // 2
            for ethnicity in ethnicity_codes(key):
                for age in (low - 1, low - 0.01, low, high, high + 0.01, high + 1):
                    builder.cell(key, sex, ethnicity, _num(age), mid_height, ("p100",))
                for height in (hlow - 1, hlow - 0.01, hlow, hhigh, hhigh + 0.01, hhigh + 1):
                    builder.cell(key, sex, ethnicity, mid_age, _num(height), ("p100",))
    # Kubota women: 94 is rejected, 93.99 is accepted; men are accepted.
    for age in (93, 93.99, 94, 94.01, 95):
        for sex in SEXES:
            builder.cell("kubota_2014", sex, None, age, 160, ("p100", "lln"))


def _mid_subject(key, sex):
    low, high, _ = AGE_RANGES[key][sex]
    hlow, hhigh = HEIGHT_RANGES[key][sex]
    age = _num(float(min(max(45, low), high - 1)))
    height = max(hlow, min(hhigh, 170 if sex == 1 else 160))
    return age, height


def add_bad_inputs(builder):
    """Edge and invalid inputs, for every equation, sex and a few ethnicities."""
    for key in EQUATIONS:
        for sex in SEXES:
            age, height = _mid_subject(key, sex)
            rows = builder.probe(key, age, height, sex, ethnicity_codes(key)[0])
            ethnicity = ethnicity_codes(key)[0]
            fev1_pred = rows[0]["predicted"]
            fvc_pred = rows[1]["predicted"]

            def add(fev1, fvc, age=age, height=height, sex=sex, ethnicity=ethnicity):
                builder.add(key, age, height, sex, fev1, fvc, ethnicity)

            # FEV1 and FVC: ordering, equality, zero, negative, tiny, huge.
            add(fvc_pred + 0.5, fvc_pred)
            add(3.0000001, 3.0)
            add(fvc_pred * 1.5, fvc_pred * 1.2)
            add(3.0, 3.0)
            add(fvc_pred, fvc_pred)
            add(0, 3.0)
            add(3.0, 0)
            add(0, 0)
            add(-1.0, 3.0)
            add(2.0, -3.0)
            add(-2.0, -1.0)
            add(0.5, -0.0)
            add(TINY_VALUE, TINY_VALUE)
            add(TINY_VALUE, fvc_pred)
            add(TINY_VALUE, 1.0)
            add(fev1_pred, 5 * fvc_pred)
            for huge in HUGE_VALUES:
                add(huge, huge)
                add(fev1_pred, huge)
            add(0.01, 0.02)
            add(1.5, 2.0)
            # Not a number: null stands for NaN.
            add(None, 3.0)
            add(2.0, None)
            add(None, None)
            builder.add(key, None, height, sex, 2.0, 3.0, ethnicity)
            builder.add(key, age, None, sex, 2.0, 3.0, ethnicity)
            # Age and height outside the plausible ranges.
            for bad_age in BAD_AGES:
                builder.add(key, bad_age, height, sex, 2.0, 3.0, ethnicity)
            for bad_height in BAD_HEIGHTS:
                builder.add(key, age, bad_height, sex, 2.0, 3.0, ethnicity)
            # Two failures at once: the first check wins.
            builder.add(key, -5, 49, sex, 0, -1.0, ethnicity)
            builder.add(key, age, 49, sex, 4.0, 3.0, ethnicity)
            builder.add(key, age, height, 3, -1.0, 3.0, ethnicity)
            builder.add(key, age, height, 3, 4.0, 3.0, ethnicity)
            # Ethnicity given to an equation that takes none is ignored.
            if EQUATIONS[key].ethnicities is None:
                builder.add(key, age, height, sex, 2.0, 3.0, 1)
                builder.add(key, age, height, sex, 2.0, 3.0, 99)
        # Invalid sex codes.
        age, height = _mid_subject(key, 1)
        for bad_sex in BAD_SEX_CODES:
            builder.add(key, age, height, bad_sex, 2.0, 3.0, ethnicity_codes(key)[0])
        # Invalid ethnicity codes.
        if EQUATIONS[key].ethnicities is not None:
            for sex in SEXES:
                age, height = _mid_subject(key, sex)
                for bad in BAD_ETHNICITY_CODES:
                    builder.add(key, age, height, sex, 2.0, 3.0, bad)
                builder.add(key, age, height, sex, 4.0, 3.0, 99)


def add_pereira_limit_cases(builder):
    """Cells where the computed limit differs from the paper limit in the last bit.

    Pereira 2007 publishes the lower limit as a number with two decimals.
    The computed limit can differ from it in the last bit (a man of 27 years
    and 163 cm: 3.28 on paper, 3.2800000000000002 computed). For every cell
    of integer age and height where the limit lies within 1e-9 of a rounded
    value, the observed value is the rounded value, which is the paper limit.
    """
    key = "pereira_2007"
    # The case of the brief: man, 27 y, 163 cm, FEV1 3.28, FVC 4.0, and the
    # values one unit of 1e-9 each side of the limit.
    for fev1 in (3.28, 3.28 - 1e-9, 3.28 + 1e-9, math.nextafter(3.28, 0), math.nextafter(3.28, 9)):
        builder.add(key, 27, 163, 1, fev1, 4.0, None)
    found = 0
    for sex in SEXES:
        alow, ahigh, _ = AGE_RANGES[key][sex]
        hlow, hhigh = HEIGHT_RANGES[key][sex]
        for age in range(int(alow), int(ahigh) + 1):
            for height in range(int(hlow), int(hhigh) + 1):
                rows = builder.probe(key, age, height, sex, None)
                if isinstance(rows, dict):
                    continue
                fev1, fvc, ratio = rows
                # Paper limits: litres with two decimals, ratio in percent with one.
                paper_fev1 = round(fev1["lln"], 2)
                paper_fvc = round(fvc["lln"], 2)
                paper_ratio = round(ratio["lln"] * 100, 1)
                if abs(fev1["lln"] - paper_fev1) < 1e-9 and paper_fev1 < paper_fvc:
                    found += 1
                    builder.add(key, age, height, sex, paper_fev1, fvc["predicted"], None)
                    builder.add(key, age, height, sex, paper_fev1, paper_fvc, None)
                if abs(fvc["lln"] - paper_fvc) < 1e-9:
                    found += 1
                    builder.add(key, age, height, sex, fev1["predicted"] * 0.5, paper_fvc, None)
                if abs(ratio["lln"] * 100 - paper_ratio) < 1e-9:
                    found += 1
                    builder.add(key, age, height, sex, paper_ratio / 100 * 4.0, 4.0, None)
    return found


def build_cases(age_step: int, height_step: int, oracle: Oracle) -> list[dict]:
    builder = Builder(oracle)
    add_grid(builder, age_step, height_step)
    add_fractional_ages(builder)
    add_ties(builder)
    add_nhanes3_change_points(builder)
    add_eccs_floor(builder)
    add_range_limits(builder)
    add_bad_inputs(builder)
    add_pereira_limit_cases(builder)
    return builder.ordered()


# --- file ---------------------------------------------------------------


def _dumps(value) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


def render(meta: dict, cases: list[dict]) -> str:
    """One case for each line, so that a diff of the file stays readable."""
    lines = ",\n".join(_dumps(case) for case in cases)
    return f'{{"meta":{_dumps(meta)},\n"cases":[\n{lines}\n]}}\n'


def _git(*args: str) -> str:
    here = Path(__file__).resolve().parent
    return subprocess.run(
        ["git", *args], cwd=here, capture_output=True, text=True, check=True
    ).stdout.strip()


def app_commit() -> tuple[str, bool]:
    """Short hash of the Quadrant repository and whether streamlit/ is dirty."""
    try:
        commit = _git("rev-parse", "--short", "HEAD")
        dirty = bool(_git("status", "--porcelain", "--", str(Path(__file__).resolve().parents[1])))
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return commit, dirty


def count_by_equation(cases):
    counts = {key: {"cases": 0, "errors": 0} for key in EQUATIONS}
    for case in cases:
        counts[case["equation"]]["cases"] += 1
        if isinstance(case["expected"], dict):
            counts[case["equation"]]["errors"] += 1
    return counts


def build_document(date: str) -> tuple[str, dict]:
    oracle = Oracle()
    commit, dirty = app_commit()
    text = ""
    meta: dict = {}
    for level, (age_step, height_step) in enumerate(THINNING_LEVELS):
        cases = build_cases(age_step, height_step, oracle)
        meta = {
            "generator": GENERATOR,
            "pyspiroVersion": importlib.metadata.version("pyspiro"),
            "appCommit": commit,
            "appTreeDirty": dirty,
            "date": date,
            "caseCount": len(cases),
            "caseCounts": count_by_equation(cases),
            "thinning": {
                "ageStepYears": age_step,
                "heightStepCm": height_step,
                "thinned": level > 0,
                "maxBytes": MAX_BYTES,
                "note": (
                    "Full grid: ages at the limits, limit -/+ 0.01 and every 5 years; "
                    "heights at the limits and every 10 cm."
                    if level == 0
                    else f"The full grid is larger than {MAX_BYTES} bytes. The middle ages "
                    f"are every {age_step} years and the middle heights every "
                    f"{height_step} cm. The limits, limit -/+ 0.01 and all special cases "
                    "are kept."
                ),
            },
            "notes": [
                "Oracle: quadrant.registry.compute_equation. An exception becomes "
                "expected = { error: message }.",
                "Rows are in the order FEV1, FVC, FEV1FVC. FEV1FVC is a fraction.",
                "null in a number field means not a number. In a subject field it stands "
                "for a missing or non-numeric input.",
                "ethnicityCode is null for equations without ethnicity. A non-null "
                "code given to such an equation is ignored.",
                "percentPredicted rounding differs by family; see tools/EXPORT_FORMAT.md.",
                "Observed values are set from a first call of the oracle: 60, 80 and "
                "100 percent of predicted, the lower limit, and the ratio at its limit.",
            ],
        }
        text = render(meta, cases)
        if len(text.encode("utf-8")) <= MAX_BYTES:
            break
    else:
        raise RuntimeError("The thinnest grid is still larger than the cap.")
    return text, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="output file, for example golden.json")
    parser.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="date written in meta (default: today)",
    )
    args = parser.parse_args(argv)
    text, meta = build_document(args.date)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{out}: {len(text.encode('utf-8'))} bytes, {meta['caseCount']} cases")
    for key, counts in meta["caseCounts"].items():
        print(f"  {key}: {counts['cases']} cases, {counts['errors']} errors")
    thinning = meta["thinning"]
    print(f"  grid: ages every {thinning['ageStepYears']} y, heights every {thinning['heightStepCm']} cm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
