"""Export the pyspiro equation tables to JSON for the Quadrant JavaScript app.

Usage:
    uv run python tools/export_tables.py --out <directory>

Writes gli2012.json, gli2022.json, nhanes3.json, kubota2014.json,
pereira2007.json and eccs1993.json. The shape of each file is described in
meta.shape and in tools/EXPORT_FORMAT.md.

Nothing is typed by hand. The tables are read from the objects that pyspiro
builds from its own data folder (pyspiro/data/*.csv), and the ranges and
codes are read from the pyspiro classes and from quadrant/constants.py and
quadrant/wrappers.py. Two numbers exist only inside method bodies and are
not exported as data: the z-value 1.645 of the lower limit (pyspiro
LMSReference.lln and HANKINSON_1999._result) and the rounding of percent
of predicted to two decimals (Reference._percent and LMSReference.percent).
EXPORT_FORMAT.md states both. tests/test_export_tables.py checks them by
reproducing the wrapper output from the JSON alone.

The files are deterministic: keys are sorted, floats are written with
repr() (the shortest text that reads back to the same float), NaN becomes
null, and the layout does not depend on the dictionary order.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import math
import sys
from pathlib import Path

# Allow "python tools/export_tables.py" from the streamlit folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from pyspiro import (  # noqa: E402
    BOWERMAN_2022,
    ECCS_1993,
    GLI_2012,
    HANKINSON_1999,
    KUBOTA_2014,
    PEREIRA_2007,
)

from quadrant import constants as C  # noqa: E402
from quadrant import wrappers as W  # noqa: E402

LICENCE = "MIT (pyspiro)"

# Units are facts about the equations, not coefficients.
_UNITS_LMS = {
    "age": "years",
    "height": "cm",
    "FEV1": "L",
    "FVC": "L",
    "FEV1FVC": "fraction (ratio FEV1/FVC)",
}
_UNITS_PERCENT = {
    "age": "years",
    "height": "cm",
    "FEV1": "L",
    "FVC": "L",
    "FEV1FVC": "percent in the tables and in pyspiro; the app divides by ratioScale to a fraction",
}


# --- conversion and writing ---------------------------------------------


def _clean(value):
    """Python scalars, lists and dicts; NaN and NA become None."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if value is None or value is pd.NA:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if hasattr(value, "item") and not isinstance(value, (int, float)):
        value = value.item()
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            raise ValueError("Infinity cannot be written to JSON")
        return float(value)
    raise TypeError(f"Cannot export {type(value).__name__}")


def _scalar_text(value) -> str:
    import json

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return json.dumps(value, ensure_ascii=True)


def _dump(value, level: int = 0) -> str:
    """Pretty JSON with sorted keys; lists of numbers stay on one line."""
    pad = "  " * level
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [
            f'{pad}  {_scalar_text(str(key))}: {_dump(value[key], level + 1)}'
            for key in sorted(value)
        ]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(value, list):
        if any(isinstance(v, (dict, list)) for v in value):
            raise TypeError("Lists must hold scalars only")
        return "[" + ",".join(_scalar_text(v) for v in value) + "]"
    return _scalar_text(value)


def render(document: dict) -> str:
    """JSON text of one document (ends with a newline)."""
    return _dump(_clean(document)) + "\n"


# --- helpers --------------------------------------------------------------


def _version() -> str:
    return importlib.metadata.version("pyspiro")


def _enum_codes(enum) -> dict:
    return {member.name: member.value for member in enum}


def _columns(frame: pd.DataFrame) -> dict:
    """{column: [values]} in row order."""
    return {str(c): frame[c].tolist() for c in frame.columns}


def _coefficients_by_column(frame: pd.DataFrame) -> dict:
    """{column: {var: value}} for a var-indexed coefficient table."""
    frame = frame.loc[:, [c for c in frame.columns if not str(c).startswith("Unnamed")]]
    return {str(c): {str(v): frame.at[v, c] for v in frame.index} for c in frame.columns}


def _app_block(
    *,
    age_range,
    ratio_scale: float,
    ethnicity: dict | None,
    sex_suffix: str,
    ethnicity_enum=None,
    extra: dict | None = None,
) -> dict:
    """What the Quadrant wrapper adds to the pyspiro class."""
    sex_enum = GLI_2012.Sex
    block = {
        "ageRangeYears": list(age_range),
        "parameters": list(C.SPIROMETRY_PARAMS),
        "ratioScale": float(ratio_scale),
        "sexCodes": dict(C.SEX_CODES),
        "sexKeyByAppCode": {
            str(code): sex_enum(W._PYSPIRO_SEX[code]).name.lower() + sex_suffix
            for code in C.SEX_CODES.values()
        },
        "sexToPyspiroCode": {str(k): v for k, v in W._PYSPIRO_SEX.items()},
    }
    if ethnicity is not None:
        block["ethnicityCodes"] = dict(ethnicity)
    if ethnicity_enum is not None:
        block["ethnicityKeyByCode"] = {
            str(member.value): member.name.lower() for member in ethnicity_enum
        }
    if extra:
        block.update(extra)
    return block


def _meta(equation: str, files: list[str], module: str, cls: str, shape: dict) -> dict:
    sources = ", ".join(f"pyspiro/data/{name}" for name in files)
    return {
        "equation": equation,
        "licence": LICENCE,
        "pyspiroClass": cls,
        "pyspiroVersion": _version(),
        "shape": shape,
        "source": f"{sources}; class {cls} in pyspiro/src/spirometry/{module}.py",
    }


# --- the six equations ----------------------------------------------------

_SHAPE_SPLINE_COMMON = {
    "ages": "Array of the ages (years) of the spline rows, from the age column of the CSV. The step is ageStepYears.",
    "ageStepYears": "Number. Step between two rows in years (pyspiro SplineReference._AGE_STEP).",
    "app": "Object. What the Quadrant wrapper adds: age range, parameter names, ratioScale (1 = the ratio is a fraction), sex codes of the app, sexKeyByAppCode (app sex code to the column infix), ethnicityCodes (labels of the app), sexToPyspiroCode.",
    "codes": "Object. The Enum codes of pyspiro: parameter, sex, and for GLI-2012 ethnicity.",
    "coefficients": "Object {column: {var: number or null}} from the coefficient CSV. column is <parameter>_<males|females>. var is one of a0..a6, p0..p5, q0, q1. null marks an empty cell.",
    "splineAgeRangesYears": "Object {<parameter>_<males|females>: [first age, last age]}. The ages for which the Mspline column of that parameter and sex has values.",
    "splines": "Object {column: array of numbers or null}. column is <parameter>_<males|females>_<Lspline|Mspline|Sspline>. Each array has one entry per row of ages. null marks an empty cell.",
    "units": "Object. Units of the inputs and of the outputs of pyspiro.",
}


def build_gli2012() -> dict:
    ref = GLI_2012()
    tables = {
        "ages": ref._lookup.index.tolist(),
        "ageStepYears": ref._AGE_STEP,
        "app": _app_block(
            age_range=C.GLI_AGE_RANGE_YEARS,
            ratio_scale=1.0,
            ethnicity=C.GLI_ETHNICITY,
            sex_suffix="s",
            ethnicity_enum=GLI_2012.Ethnicity,
        ),
        "codes": {
            "ethnicity": _enum_codes(GLI_2012.Ethnicity),
            "parameter": _enum_codes(GLI_2012.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": _coefficients_by_column(ref._coefficients),
        "splineAgeRangesYears": {k: list(v) for k, v in ref._spline_age_ranges.items()},
        "splines": _columns(ref._lookup),
        "units": _UNITS_LMS,
    }
    return {
        "meta": _meta(
            "gli_2012",
            ["gli_2012_splines.csv", "gli_2012_coefficients.csv"],
            "GLI_2012",
            "GLI_2012",
            dict(_SHAPE_SPLINE_COMMON),
        ),
        "tables": tables,
    }


def build_gli2022() -> dict:
    ref = BOWERMAN_2022()
    shape = dict(_SHAPE_SPLINE_COMMON)
    shape["coefficients"] = (
        "Object {column: {var: number or null}} from the coefficient CSV (the unnamed "
        "row-number column is dropped). column is <parameter>_<males|females>. var is "
        "a0, a1, a2, p0, p1, q0, q1. null marks an empty cell (q1 of FEV1 and FVC)."
    )
    shape["codes"] = "Object. The Enum codes of pyspiro: parameter and sex. The equation has no ethnicity."
    tables = {
        "ages": ref._lookup.index.tolist(),
        "ageStepYears": ref._AGE_STEP,
        "app": _app_block(
            age_range=C.GLI_AGE_RANGE_YEARS,
            ratio_scale=1.0,
            ethnicity=None,
            sex_suffix="s",
        ),
        "codes": {
            "parameter": _enum_codes(BOWERMAN_2022.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": _coefficients_by_column(ref._coefficients),
        "splineAgeRangesYears": {k: list(v) for k, v in ref._spline_age_ranges.items()},
        "splines": _columns(ref._lookup),
        "units": _UNITS_LMS,
    }
    return {
        "meta": _meta(
            "gli_2022",
            ["bowerman_2022_splines.csv", "bowerman_2022_coefficients.csv"],
            "BOWERMAN_2022",
            "BOWERMAN_2022",
            shape,
        ),
        "tables": tables,
    }


def _nested(frame: pd.DataFrame) -> dict:
    """Nested dict from a MultiIndex frame: {k1: {k2: ... {column: value}}}."""
    result: dict = {}
    for key, row in frame.iterrows():
        node = result
        for part in key[:-1]:
            node = node.setdefault(str(part), {})
        node[str(key[-1])] = {str(c): row[c] for c in frame.columns}
    return result


def build_nhanes3() -> dict:
    ref = HANKINSON_1999()
    heights: dict = {}
    for (sex, eth, group), rng in ref._HEIGHT_RANGES.items():
        heights.setdefault(sex, {}).setdefault(eth, {})[group] = list(rng)
    shape = {
        "app": "Object. What the Quadrant wrapper adds: age range, parameter names, ratioScale (100: pyspiro and the tables give FEV1/FVC in percent), sex and ethnicity codes of the app, sexKeyByAppCode, ethnicityKeyByCode, sexToPyspiroCode.",
        "ageRangeYears": "Array [first, last]. Ages of the equations in years (HANKINSON_1999._AGE_RANGE).",
        "changePointYears": "Object {male, female}. Age in years below which the young (child) equations apply: the paper (Tables 4 and 5), from quadrant/constants.py. The test is age < change point.",
        "codes": "Object. The Enum codes of pyspiro: parameter, sex, ethnicity.",
        "coefficients": "Object {t4t5, t6}. t4t5[parameter][sex][ethnicity][ageGroup] = {a0_pred, a1_age, a2_age2, a3_ht2_pred, a3_ht2_lln} for FEV1 and FVC (and FEV6, FEF25_75, PEF, not used by the app). t6[parameter][sex][ethnicity] = {a0_pred, a0_lln, a1_age} for FEV1FVC (and FEV1FEV6, not used). parameter, sex, ethnicity and ageGroup are the lower-case names of the CSV: male|female, caucasian|african_american|mexican_american, child|adult.",
        "heightRangesCm": "Object [sex][ethnicity][ageGroup] = [lowest, highest] height in cm for Tables 4 and 5 (HANKINSON_1999._HEIGHT_RANGES). Table 6 has no height range.",
        "pyspiroChildMaxAgeYears": "Object {male, female}. The change point of pyspiro itself (child when age <= value). Not used by the app, which follows the paper. Listed to show the difference.",
        "units": "Object. Units of the inputs and of the outputs of pyspiro.",
    }
    tables = {
        "app": _app_block(
            age_range=C.NHANES3_AGE_RANGE_YEARS,
            ratio_scale=W._NHANES3_RATIO_SCALE,
            ethnicity=C.NHANES3_ETHNICITY,
            sex_suffix="",
            ethnicity_enum=HANKINSON_1999.Ethnicity,
        ),
        "ageRangeYears": list(ref._AGE_RANGE),
        "changePointYears": {
            "female": C.NHANES3_FEMALE_CHANGE_POINT_YEARS,
            "male": C.NHANES3_MALE_CHANGE_POINT_YEARS,
        },
        "codes": {
            "ethnicity": _enum_codes(HANKINSON_1999.Ethnicity),
            "parameter": _enum_codes(HANKINSON_1999.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": {
            "t4t5": _nested(ref._coeff_t45),
            "t6": _nested(ref._coeff_t6),
        },
        "heightRangesCm": heights,
        "pyspiroChildMaxAgeYears": {
            "female": ref._CHILD_MAX_AGE_FEMALE,
            "male": ref._CHILD_MAX_AGE_MALE,
        },
        "units": _UNITS_PERCENT,
    }
    return {
        "meta": _meta(
            "nhanes3",
            [
                "hankinson_1999_coefficients_t4_t5.csv",
                "hankinson_1999_coefficients_t6.csv",
            ],
            "HANKINSON_1999",
            "HANKINSON_1999",
            shape,
        ),
        "tables": tables,
    }


def build_kubota2014() -> dict:
    ref = KUBOTA_2014()
    splines = {}
    for (name, gender), table in ref._spline_tables.items():
        sex_member = next(
            m for m in GLI_2012.Sex if ref._sex_to_gender(m.value) == gender
        )
        sex = sex_member.name.lower() + "s"
        splines[f"{name}_{sex}"] = {
            "agebound": table.index.tolist(),
            "Lspline": table["Lspline"].tolist(),
            "Mspline": table["Mspline"].tolist(),
            "Sspline": table["Sspline"].tolist(),
        }
    shape = {
        "app": "Object. What the Quadrant wrapper adds: age range, parameter names, ratioScale (1: the ratio is a fraction), sex codes of the app, sexKeyByAppCode, sexToPyspiroCode, femaleMaxAgeYearsExclusive (women of this age or older are rejected).",
        "ageRangeYears": "Array [first, last]. Ages of the equations in years (KUBOTA_2014._AGE_RANGE).",
        "codes": "Object. The Enum codes of pyspiro: parameter and sex. The equation has no ethnicity.",
        "coefficients": "Object {column: {var: number}} from the coefficient CSV. column is <parameter>_<males|females>. var is a0, a1, a2, p0, p1, q0, q1.",
        "splines": "Object {<parameter>_<males|females>: {agebound, Lspline, Mspline, Sspline}}. Each of the four is an array with one entry per whole year of age. agebound holds the whole years. null marks an empty Lspline cell (no L spline for that row). The tables are indexed by whole years of age, not by quarter years.",
        "units": "Object. Units of the inputs and of the outputs of pyspiro.",
    }
    tables = {
        "app": _app_block(
            age_range=C.JRS_AGE_RANGE_YEARS,
            ratio_scale=1.0,
            ethnicity=None,
            sex_suffix="s",
            extra={"femaleMaxAgeYearsExclusive": C.JRS_FEMALE_MAX_AGE_YEARS},
        ),
        "ageRangeYears": list(ref._AGE_RANGE),
        "codes": {
            "parameter": _enum_codes(KUBOTA_2014.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": _coefficients_by_column(ref._coefficients),
        "splines": splines,
        "units": _UNITS_LMS,
    }
    return {
        "meta": _meta(
            "kubota_2014",
            ["kubota_2014_splines.csv", "kubota_2014_coefficients.csv"],
            "KUBOTA_2014",
            "KUBOTA_2014",
            shape,
        ),
        "tables": tables,
    }


def _coefficients_by_parameter(frame: pd.DataFrame) -> dict:
    """{parameter: {sex: {column: value}}} for a (parameter, sex) indexed frame."""
    return _nested(frame)


def build_pereira2007() -> dict:
    ref = PEREIRA_2007()
    shape = {
        "app": "Object. What the Quadrant wrapper adds: age range, parameter names, ratioScale (100: pyspiro and the tables give FEV1/FVC in percent), sex codes of the app, sexKeyByAppCode, sexToPyspiroCode.",
        "codes": "Object. The Enum codes of pyspiro: parameter and sex. The app uses FVC, FEV1 and FEV1FVC (the height and age models), never the _WT models.",
        "coefficients": "Object [parameter][sex] = {kind, a0, a_ht, a_age, a_wt, lln}. parameter is the name of the CSV (FVC, FEV1, FEV1FVC, ...). sex is male|female. kind is linear or log. lln is an offset (linear) or a factor (log). The app uses FVC, FEV1 and FEV1FVC; a_wt is 0 there.",
        "ranges": "Object [sex] = {ageYears: [first, last], heightCm: [lowest, highest]}. The ranges of PEREIRA_2007 outside which pyspiro returns NA.",
        "units": "Object. Units of the inputs and of the outputs of pyspiro.",
    }
    tables = {
        "app": _app_block(
            age_range=C.PEREIRA_AGE_RANGE_YEARS,
            ratio_scale=W._PEREIRA_RATIO_SCALE,
            ethnicity=None,
            sex_suffix="",
        ),
        "codes": {
            "parameter": _enum_codes(PEREIRA_2007.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": _coefficients_by_parameter(ref._coefficients),
        "ranges": {
            "female": {
                "ageYears": list(PEREIRA_2007._AGE_RANGE_FEMALE),
                "heightCm": list(PEREIRA_2007._HEIGHT_RANGE_FEMALE),
            },
            "male": {
                "ageYears": list(PEREIRA_2007._AGE_RANGE_MALE),
                "heightCm": list(PEREIRA_2007._HEIGHT_RANGE_MALE),
            },
        },
        "units": _UNITS_PERCENT,
    }
    return {
        "meta": _meta(
            "pereira_2007",
            ["pereira_2007_coefficients.csv"],
            "PEREIRA_2007",
            "PEREIRA_2007",
            shape,
        ),
        "tables": tables,
    }


def build_eccs1993() -> dict:
    ref = ECCS_1993()
    shape = {
        "app": "Object. What the Quadrant wrapper adds: age range, parameter names, ratioScale (100: pyspiro and the tables give FEV1/FVC in percent), sex codes of the app, sexKeyByAppCode, sexToPyspiroCode, ageFloorYears (the wrapper enters this age for younger subjects, for every parameter and both sexes).",
        "ageFloorYears": "Number. ECCS_1993._FEF_AGE_MIN, the age floor of pyspiro for the parameters in pyspiroAgeClampParameters.",
        "ageRangeYears": "Array [first, last]. ECCS_1993._AGE_RANGE.",
        "codes": "Object. The Enum codes of pyspiro: parameter and sex.",
        "coefficients": "Object [parameter][sex] = {a0, a_ht, a_age}. parameter is the name of the CSV (FVC, FEV1, FEV1FVC, ...). sex is male|female. All equations are linear. There is no lower limit and no residual SD in the tables.",
        "heightRangesCm": "Object {male, female}. Each is [lowest, highest] height in cm (ECCS_1993._HEIGHT_MALE_RANGE and _HEIGHT_FEMALE_RANGE).",
        "pyspiroAgeClampParameters": "Object {male, female}. The parameters for which pyspiro floors the age at ageFloorYears. The app wrapper floors the age for every parameter before it calls pyspiro, so these lists do not change the app result.",
        "units": "Object. Units of the inputs and of the outputs of pyspiro.",
    }
    tables = {
        "app": _app_block(
            age_range=C.ECCS_AGE_RANGE_YEARS,
            ratio_scale=W._ECCS_RATIO_SCALE,
            ethnicity=None,
            sex_suffix="",
            extra={"ageFloorYears": C.ECCS_AGE_FLOOR_YEARS},
        ),
        "ageFloorYears": ECCS_1993._FEF_AGE_MIN,
        "ageRangeYears": list(ECCS_1993._AGE_RANGE),
        "codes": {
            "parameter": _enum_codes(ECCS_1993.Parameters),
            "sex": _enum_codes(GLI_2012.Sex),
        },
        "coefficients": _coefficients_by_parameter(ref._coefficients),
        "heightRangesCm": {
            "female": list(ECCS_1993._HEIGHT_FEMALE_RANGE),
            "male": list(ECCS_1993._HEIGHT_MALE_RANGE),
        },
        "pyspiroAgeClampParameters": {
            "female": sorted(ECCS_1993._FEMALE_AGE_CLAMP_PARAMS),
            "male": sorted(ECCS_1993._MALE_AGE_CLAMP_PARAMS),
        },
        "units": _UNITS_PERCENT,
    }
    return {
        "meta": _meta(
            "eccs_1993",
            ["eccs_1993_coefficients.csv"],
            "ECCS_1993",
            "ECCS_1993",
            shape,
        ),
        "tables": tables,
    }


BUILDERS = {
    "gli2012.json": build_gli2012,
    "gli2022.json": build_gli2022,
    "nhanes3.json": build_nhanes3,
    "kubota2014.json": build_kubota2014,
    "pereira2007.json": build_pereira2007,
    "eccs1993.json": build_eccs1993,
}


def build_all() -> dict:
    """{file name: document} for the six equations."""
    return {name: build() for name, build in BUILDERS.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="output directory")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, document in build_all().items():
        text = render(document)
        (out / name).write_text(text, encoding="utf-8", newline="\n")
        size = len(text.encode("utf-8"))
        total += size
        print(f"{name}: {size} bytes")
    print(f"total: {total} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
