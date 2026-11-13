"""ATS/ERS 2022 pattern classification and severity grading.

Stanojevic et al., ERJ 2022, doi:10.1183/13993003.01499-2021. Pure
functions with no Streamlit state. All wording is descriptive: outputs
name the spirometric pattern, not a diagnosis.

The pattern comes from z-scores when the equation gives them. An
equation that publishes a lower limit but no z-score (Pereira 2007) is
classified from the observed values against that lower limit, with the
same rule: only a value strictly below the limit counts as below the
lower limit of normal. Severity needs the FEV1 z-score, so it is not
graded on that basis.
"""

from __future__ import annotations

import math
import numbers

import pandas as pd

from .constants import (
    LIMIT_COMPARE_TOLERANCE,
    LLN_Z,
    SEVERITY_MILD_Z_MIN,
    SEVERITY_MODERATE_Z_MIN,
)


# Values of the "basis" field of interpret_spirometry.
BASIS_Z_SCORE = "z-score"
BASIS_LOWER_LIMIT = "lower limit"

PARAMETERS = ("FEV1", "FVC", "FEV1FVC")


def _check_number(value, function: str, what: str = "z-scores") -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or pd.isna(value)
    ):
        raise ValueError(f"{function} needs single non-missing numeric {what}.")


def _check_z(value, function: str) -> None:
    _check_number(value, function)


def is_below(value: float, limit: float) -> bool:
    """The one rule of both paths: strictly below the limit.

    A value equal to the limit is not below it, so a z-score of exactly
    -1.645 and an observed value equal to the lower limit both count as
    within the lower limit of normal. Equal means within
    LIMIT_COMPARE_TOLERANCE, so floating point error in a computed limit
    does not put a value that equals the printed limit below it.
    """
    return value < limit and not math.isclose(
        value, limit, rel_tol=0, abs_tol=LIMIT_COMPARE_TOLERANCE
    )


def _pattern_from_flags(fev1_low: bool, fvc_low: bool, ratio_low: bool) -> str:
    if ratio_low and fvc_low:
        return "mixed pattern (suggestive)"
    if ratio_low:
        return "obstructive"
    if fvc_low:
        return "restrictive pattern (suggestive)"
    if fev1_low:
        return "non-specific"
    return "normal"


def classify_pattern(fev1_z: float, fvc_z: float, fev1_fvc_z: float) -> str:
    """Classify the ventilatory pattern from spirometry z-scores alone.

    Returns one of "normal", "obstructive", "restrictive pattern
    (suggestive)", "mixed pattern (suggestive)" or "non-specific".
    Restrictive and mixed patterns need static lung volumes to confirm,
    which Quadrant does not accept, so they carry the qualifier.
    """
    for value in (fev1_z, fvc_z, fev1_fvc_z):
        _check_z(value, "classify_pattern")
    return _pattern_from_flags(
        is_below(fev1_z, LLN_Z), is_below(fvc_z, LLN_Z), is_below(fev1_fvc_z, LLN_Z)
    )


def classify_pattern_from_limits(observed: dict, lln: dict) -> str:
    """Classify the pattern from observed values against published lower limits.

    For an equation that publishes a lower limit but no z-score. observed
    and lln map "FEV1", "FVC" and "FEV1FVC" to numbers in the same units:
    litres for FEV1 and FVC, a fraction (not a percentage) for FEV1FVC.
    Returns the same labels as classify_pattern, with the same rule: only
    a value strictly below its limit counts. A missing value raises
    ValueError, so a missing limit never reads as normal.
    """
    flags = {}
    for parameter in PARAMETERS:
        for name, values in (("observed", observed), ("lln", lln)):
            if parameter not in values:
                raise ValueError(f"{name} has no value for {parameter}.")
            _check_number(
                values[parameter], "classify_pattern_from_limits",
                "observed values and lower limits",
            )
        flags[parameter] = is_below(observed[parameter], lln[parameter])
    return _pattern_from_flags(flags["FEV1"], flags["FVC"], flags["FEV1FVC"])


def grade_severity(fev1_z: float) -> str:
    """Grade severity by FEV1 z-score with the ATS/ERS 2022 three levels.

    Mild for a z-score of -2.5 or higher, moderate from -2.5 down to
    -4.0, severe below -4.0. Severity is a separate axis from the
    pattern label. Callers decide whether to show it.
    """
    _check_z(fev1_z, "grade_severity")
    if fev1_z >= SEVERITY_MILD_Z_MIN:
        return "mild"
    if fev1_z >= SEVERITY_MODERATE_Z_MIN:
        return "moderate"
    return "severe"


def interpret_spirometry(reference_df: pd.DataFrame) -> dict:
    """Interpret one reference family's long-form result table.

    Returns a dict with pattern, severity, basis, fev1_z, fvc_z and
    fev1_fvc_z. basis says how the pattern was found: "z-score",
    "lower limit" or None.

    - All three z-scores present: pattern from the z-scores, basis
      "z-score". Severity by FEV1 z-score, None when the pattern is normal.
    - All three z-scores missing and all three lower limits present (an
      equation that publishes a lower limit but no z-score): pattern from
      the observed values against the lower limits, basis "lower limit".
      Severity is None: it needs a FEV1 z-score.
    - All three z-scores and all three lower limits missing: pattern,
      severity and basis are None (not classified).

    A partly missing set of z-scores, or of lower limits when there is no
    z-score, raises ValueError.
    """
    missing = {"parameter", "z_score"} - set(reference_df.columns)
    if missing:
        raise ValueError(
            "reference_df is missing required columns: "
            + ", ".join(sorted(missing))
        )
    z = dict(zip(reference_df["parameter"], reference_df["z_score"]))
    for parameter in PARAMETERS:
        if parameter not in z:
            raise ValueError(f"reference_df is missing a z-score for {parameter}.")
    n_missing = sum(bool(pd.isna(z[p])) for p in PARAMETERS)
    if n_missing and n_missing != len(PARAMETERS):
        raise ValueError("The z-scores must be all present or all missing.")
    if n_missing:
        return _interpret_without_z(reference_df)

    pattern = classify_pattern(z["FEV1"], z["FVC"], z["FEV1FVC"])
    severity = None if pattern == "normal" else grade_severity(z["FEV1"])
    return {
        "pattern": pattern,
        "severity": severity,
        "basis": BASIS_Z_SCORE,
        "fev1_z": float(z["FEV1"]),
        "fvc_z": float(z["FVC"]),
        "fev1_fvc_z": float(z["FEV1FVC"]),
    }


def _interpret_without_z(reference_df: pd.DataFrame) -> dict:
    """Pattern for a table without z-scores: by lower limit, or none."""
    nan = float("nan")
    result = {
        "pattern": None,
        "severity": None,
        "basis": None,
        "fev1_z": nan,
        "fvc_z": nan,
        "fev1_fvc_z": nan,
    }
    if "lln" not in reference_df.columns:
        return result
    lln = dict(zip(reference_df["parameter"], reference_df["lln"]))
    n_missing = sum(bool(pd.isna(lln.get(p, nan))) for p in PARAMETERS)
    if n_missing == len(PARAMETERS):
        return result
    if n_missing:
        raise ValueError(
            "Without z-scores, the lower limits must be all present or all missing."
        )
    if "observed" not in reference_df.columns:
        raise ValueError(
            "reference_df needs the observed column to compare with the lower limits."
        )
    observed = dict(zip(reference_df["parameter"], reference_df["observed"]))
    result["pattern"] = classify_pattern_from_limits(observed, lln)
    result["basis"] = BASIS_LOWER_LIMIT
    return result
