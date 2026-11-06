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
from pyspiro import BOWERMAN_2022, GLI_2012, HANKINSON_1999, KUBOTA_2014, PEREIRA_2007

from .constants import (
    GLI_AGE_RANGE_YEARS,
    GLI_ETHNICITY,
    HEIGHT_RANGE_CM,
    JRS_AGE_RANGE_YEARS,
    JRS_FEMALE_MAX_AGE_YEARS,
    NHANES3_AGE_RANGE_YEARS,
    NHANES3_ETHNICITY,
    PEREIRA_AGE_RANGE_YEARS,
    PEREIRA_FEMALE_AGE_RANGE_YEARS,
    PEREIRA_FEMALE_HEIGHT_RANGE_CM,
    PEREIRA_MALE_AGE_RANGE_YEARS,
    PEREIRA_MALE_HEIGHT_RANGE_CM,
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
_JRS_PARAM_CODES = {"FEV1": 1, "FVC": 2, "FEV1FVC": 4}
# Pereira 2007: the height and age models only (no _WT parameters).
_PEREIRA_PARAM_CODES = {"FEV1": 3, "FVC": 1, "FEV1FVC": 7}

# pyspiro codes sex as 1 = male, 0 = female. This project uses 1 and 2.
_PYSPIRO_SEX = {1: 1, 2: 0}

# NHANES III expresses FEV1/FVC as a percentage. The wrapper converts
# the ratio in and out so that every family returns the same units.
_NHANES3_RATIO_SCALE = 100.0

# Pereira 2007 also gives FEV1/FVC in percent.
_PEREIRA_RATIO_SCALE = 100.0

_GLI_2012 = GLI_2012()
_GLI_2022 = BOWERMAN_2022()
_NHANES3 = HANKINSON_1999()
_JRS_2014 = KUBOTA_2014()
_PEREIRA_2007 = PEREIRA_2007()


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
    limits_required: bool = True,
) -> pd.DataFrame:
    """Evaluate one reference object for every parameter.

    lead_args holds the arguments that come before the parameter code:
    (sex, age, height) or (sex, age, height, ethnicity). pyspiro returns
    NA outside the domain of an equation. That becomes a ValueError here
    so that the operator sees the reason.

    Some published equations have no lower limit. With
    limits_required=False, NaN is allowed in lln and z_score only.
    NaN in predicted or percent_predicted still raises.
    """
    rows = []
    for parameter in SPIROMETRY_PARAMS:
        scale = ratio_scale if parameter == "FEV1FVC" else 1.0
        args = (*lead_args, param_codes[parameter], observed[parameter] * scale)
        predicted = reference.lms(*args)[1]
        lln = reference.lln(*args)
        z_score = reference.zscore(*args)
        percent = reference.percent(*args)
        required = (predicted, percent)
        if limits_required:
            required = (predicted, lln, z_score, percent)
        if any(pd.isna(v) for v in required):
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


def _regression_table(
    reference,
    lead_args: tuple,
    param_codes: dict,
    observed: dict,
    family: str,
    ratio_scale: float = 1.0,
) -> pd.DataFrame:
    """Long-form table for a pyspiro regression equation without a z-score.

    _long_table reads the predicted value from lms(), which returns NA for
    regression classes such as PEREIRA_2007. This helper reads the
    predicted value and the lower limit from the regression result of
    pyspiro (_scalar_regression, pyspiro 1.0.0, pinned in uv.lock), with
    weight None. The tests compare the result with an independent
    implementation of the paper. z_score is NaN: the paper gives the lower
    limit as a percentile of the residuals and no residual standard
    deviation.
    """
    lead = (*lead_args[:3], None, None)  # sex, age, height, ethnicity, weight
    rows = []
    for parameter in SPIROMETRY_PARAMS:
        scale = ratio_scale if parameter == "FEV1FVC" else 1.0
        value = observed[parameter] * scale
        result = reference._scalar_regression(*lead, param_codes[parameter])
        percent = reference.percent(
            *lead_args[:3], parameter=param_codes[parameter], value=value
        )
        if result is None or any(
            v is None or pd.isna(v) for v in (result.pred, result.lln, percent)
        ):
            raise ValueError(
                f"{family} has no reference value for these inputs. The "
                "equation covers a limited range of age and height."
            )
        rows.append(
            {
                "parameter": parameter,
                "observed": float(observed[parameter]),
                "predicted": float(result.pred) / scale,
                "lln": float(result.lln) / scale,
                "z_score": float("nan"),
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


def compute_kubota_2014(age_years, height_cm, sex_code, fev1, fvc) -> pd.DataFrame:
    """JRS 2014 (Kubota) reference values for a single subject.

    The equations have no ethnicity argument. rspiro returns NA for women
    from 94 years, so the wrapper rejects that age for women.
    """
    validate_subject_inputs(
        age_years=age_years,
        age_range=JRS_AGE_RANGE_YEARS,
        height_cm=height_cm,
        sex_code=sex_code,
        fev1=fev1,
        fvc=fvc,
    )
    if sex_code == SEX_CODES["Female"] and age_years >= JRS_FEMALE_MAX_AGE_YEARS:
        raise ValueError(
            "for women the JRS 2014 equations are available below "
            f"{JRS_FEMALE_MAX_AGE_YEARS} years."
        )
    return _long_table(
        _JRS_2014,
        (_PYSPIRO_SEX[sex_code], age_years, height_cm),
        _JRS_PARAM_CODES,
        _observed(fev1, fvc),
        "JRS 2014",
    )


def compute_pereira_2007(age_years, height_cm, sex_code, fev1, fvc) -> pd.DataFrame:
    """Pereira 2007 reference values for one White Brazilian adult.

    Uses the height and age models of Tables 3 and 4 of the paper; the
    models with weight for men are not used. The sampled ranges differ by
    sex: men 26 to 86 years and 152 to 192 cm, women 20 to 85 years and
    137 to 182 cm. The paper gives the lower limit as the 5th percentile
    of the residuals and no residual standard deviation, so z_score is NaN.
    """
    validate_subject_inputs(
        age_years=age_years,
        age_range=PEREIRA_AGE_RANGE_YEARS,
        height_cm=height_cm,
        sex_code=sex_code,
        fev1=fev1,
        fvc=fvc,
    )
    if sex_code == SEX_CODES["Male"]:
        label, ages, heights = (
            "men",
            PEREIRA_MALE_AGE_RANGE_YEARS,
            PEREIRA_MALE_HEIGHT_RANGE_CM,
        )
    else:
        label, ages, heights = (
            "women",
            PEREIRA_FEMALE_AGE_RANGE_YEARS,
            PEREIRA_FEMALE_HEIGHT_RANGE_CM,
        )
    if not ages[0] <= age_years <= ages[1]:
        raise ValueError(
            f"for {label} the Pereira 2007 equations cover {ages[0]} to "
            f"{ages[1]} years."
        )
    if not heights[0] <= height_cm <= heights[1]:
        raise ValueError(
            f"for {label} the Pereira 2007 equations cover {heights[0]} to "
            f"{heights[1]} cm."
        )
    return _regression_table(
        _PEREIRA_2007,
        (_PYSPIRO_SEX[sex_code], age_years, height_cm),
        _PEREIRA_PARAM_CODES,
        _observed(fev1, fvc),
        "Pereira 2007",
        ratio_scale=_PEREIRA_RATIO_SCALE,
    )
