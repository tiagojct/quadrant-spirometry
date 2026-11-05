"""Reference equation wrappers.

Each wrapper takes operator-friendly units (height in centimetres, sex
and ethnicity as integer codes from constants.py) and returns a pandas
DataFrame in long form with the columns parameter, observed, predicted,
lln, z_score and percent_predicted. One row per parameter, in the order
of SPIROMETRY_PARAMS. The equations come from the pyspiro package; no
coefficient is written by hand in this project.

The functions are pure: no side effects and no Streamlit state.
"""

from __future__ import annotations

import numbers

import pandas as pd
from pyspiro import BOWERMAN_2022, GLI_2012, HANKINSON_1999

from .constants import (
    GLI_AGE_RANGE_YEARS,
    GLI_ETHNICITY,
    HEIGHT_RANGE_CM,
    NHANES3_AGE_RANGE_YEARS,
    NHANES3_ETHNICITY,
    PLAUSIBLE_AGE_RANGE_YEARS,
    SEX_CODES,
    SPIROMETRY_PARAMS,
)

TABLE_COLUMNS = (
    "parameter",
    "observed",
    "predicted",
    "lln",
    "z_score",
    "percent_predicted",
)

# Parameter codes differ between the pyspiro classes.
_GLI_PARAM_CODES = {"FEV1": 1, "FVC": 2, "FEV1FVC": 3}
_NHANES3_PARAM_CODES = {"FEV1": 2, "FVC": 1, "FEV1FVC": 3}

# pyspiro codes sex as 1 = male, 0 = female. This project uses 1 and 2.
_PYSPIRO_SEX = {1: 1, 2: 0}

# NHANES III expresses FEV1/FVC as a percentage. The wrapper converts
# the ratio in and out so that every family returns the same units.
_NHANES3_RATIO_SCALE = 100.0

_GLI_2012 = GLI_2012()
_GLI_2022 = BOWERMAN_2022()
_NHANES3 = HANKINSON_1999()


def validate_subject_inputs(
    *,
    age_years,
    height_cm,
    sex_code,
    fev1,
    fvc,
    ethnicity_code=None,
    valid_ethnicity=None,
    age_range=PLAUSIBLE_AGE_RANGE_YEARS,
) -> None:
    """Validate subject-level inputs shared by every wrapper.

    Raises ValueError with an informative message when an input is
    missing, not a single number, outside its range, or refers to an
    unsupported code. Ethnicity is optional: the race-neutral GLI-Global
    2022 equation has none, so pass valid_ethnicity=None to skip it.
    """

    def scalar(value, label):
        if (
            isinstance(value, bool)
            or not isinstance(value, numbers.Real)
            or pd.isna(value)
        ):
            raise ValueError(f"{label} must be a single non-missing numeric value.")

    scalar(age_years, "age_years")
    scalar(height_cm, "height_cm")
    scalar(fev1, "fev1")
    scalar(fvc, "fvc")

    if age_years < age_range[0] or age_years > age_range[1]:
        raise ValueError(
            f"age_years must be between {age_range[0]:g} and {age_range[1]:g} "
            "years for this reference equation."
        )
    if height_cm < HEIGHT_RANGE_CM[0] or height_cm > HEIGHT_RANGE_CM[1]:
        raise ValueError(
            "height_cm must be a plausible standing height in centimetres "
            f"({HEIGHT_RANGE_CM[0]:g} to {HEIGHT_RANGE_CM[1]:g})."
        )
    if fev1 <= 0 or fvc <= 0:
        raise ValueError("fev1 and fvc must be positive values in litres.")
    if fev1 > fvc:
        raise ValueError("fev1 cannot exceed fvc; check the inputs.")
    if sex_code not in SEX_CODES.values():
        codes = ", ".join(str(c) for c in SEX_CODES.values())
        raise ValueError(f"sex_code must be one of: {codes}.")
    if valid_ethnicity is not None:
        if ethnicity_code not in valid_ethnicity.values():
            codes = ", ".join(str(c) for c in valid_ethnicity.values())
            raise ValueError(f"ethnicity_code must be one of: {codes}.")


def _long_table(
    reference,
    lead_args: tuple,
    param_codes: dict,
    observed: dict,
    family: str,
    ratio_scale: float = 1.0,
) -> pd.DataFrame:
    """Evaluate one reference object for every parameter.

    lead_args holds the arguments that come before the parameter code:
    (sex, age, height) or (sex, age, height, ethnicity). pyspiro returns
    NA outside the domain of an equation. That becomes a ValueError here
    so that the operator sees the reason.
    """
    rows = []
    for parameter in SPIROMETRY_PARAMS:
        scale = ratio_scale if parameter == "FEV1FVC" else 1.0
        args = (*lead_args, param_codes[parameter], observed[parameter] * scale)
        predicted = reference.lms(*args)[1]
        lln = reference.lln(*args)
        z_score = reference.zscore(*args)
        percent = reference.percent(*args)
        if any(pd.isna(v) for v in (predicted, lln, z_score, percent)):
            raise ValueError(
                f"{family} has no reference value for these inputs. The "
                "equation covers a limited range of age and height."
            )
        rows.append(
            {
                "parameter": parameter,
                "observed": float(observed[parameter]),
                "predicted": float(predicted) / scale,
                "lln": float(lln) / scale,
                "z_score": float(z_score),
                "percent_predicted": float(percent),
            }
        )
    return pd.DataFrame(rows, columns=list(TABLE_COLUMNS))


def _observed(fev1: float, fvc: float) -> dict:
    return {"FEV1": fev1, "FVC": fvc, "FEV1FVC": fev1 / fvc}


def compute_gli_2012(
    age_years, height_cm, sex_code, ethnicity_code, fev1, fvc
) -> pd.DataFrame:
    """GLI-2012 reference values for a single subject."""
    validate_subject_inputs(
        age_years=age_years,
        age_range=GLI_AGE_RANGE_YEARS,
        height_cm=height_cm,
        sex_code=sex_code,
        ethnicity_code=ethnicity_code,
        valid_ethnicity=GLI_ETHNICITY,
        fev1=fev1,
        fvc=fvc,
    )
    return _long_table(
        _GLI_2012,
        (_PYSPIRO_SEX[sex_code], age_years, height_cm, ethnicity_code),
        _GLI_PARAM_CODES,
        _observed(fev1, fvc),
        "GLI-2012",
    )


def compute_gli_global_2022(
    age_years, height_cm, sex_code, fev1, fvc
) -> pd.DataFrame:
    """GLI-Global 2022 (race-neutral) reference values for one subject."""
    validate_subject_inputs(
        age_years=age_years,
        age_range=GLI_AGE_RANGE_YEARS,
        height_cm=height_cm,
        sex_code=sex_code,
        fev1=fev1,
        fvc=fvc,
    )
    return _long_table(
        _GLI_2022,
        (_PYSPIRO_SEX[sex_code], age_years, height_cm),
        _GLI_PARAM_CODES,
        _observed(fev1, fvc),
        "GLI-Global 2022",
    )


def compute_nhanes3(
    age_years, height_cm, sex_code, ethnicity_code, fev1, fvc
) -> pd.DataFrame:
    """NHANES III reference values for a single subject."""
    validate_subject_inputs(
        age_years=age_years,
        age_range=NHANES3_AGE_RANGE_YEARS,
        height_cm=height_cm,
        sex_code=sex_code,
        ethnicity_code=ethnicity_code,
        valid_ethnicity=NHANES3_ETHNICITY,
        fev1=fev1,
        fvc=fvc,
    )
    return _long_table(
        _NHANES3,
        (_PYSPIRO_SEX[sex_code], age_years, height_cm, ethnicity_code),
        _NHANES3_PARAM_CODES,
        _observed(fev1, fvc),
        "NHANES III",
        ratio_scale=_NHANES3_RATIO_SCALE,
    )
