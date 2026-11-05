"""ATS/ERS 2022 pattern classification and severity grading.

Stanojevic et al., ERJ 2022, doi:10.1183/13993003.01499-2021. Pure
functions with no Streamlit state. All wording is descriptive: outputs
name the spirometric pattern, not a diagnosis.
"""

from __future__ import annotations

import numbers

import pandas as pd

from .constants import LLN_Z, SEVERITY_MILD_Z_MIN, SEVERITY_MODERATE_Z_MIN


def _check_z(value, function: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, numbers.Real)
        or pd.isna(value)
    ):
        raise ValueError(f"{function} needs single non-missing numeric z-scores.")


def classify_pattern(fev1_z: float, fvc_z: float, fev1_fvc_z: float) -> str:
    """Classify the ventilatory pattern from spirometry z-scores alone.

    Returns one of "normal", "obstructive", "restrictive pattern
    (suggestive)", "mixed pattern (suggestive)" or "non-specific".
    Restrictive and mixed patterns need static lung volumes to confirm,
    which Quadrant does not accept, so they carry the qualifier.
    """
    for value in (fev1_z, fvc_z, fev1_fvc_z):
        _check_z(value, "classify_pattern")
    ratio_low = fev1_fvc_z < LLN_Z
    fvc_low = fvc_z < LLN_Z
    fev1_low = fev1_z < LLN_Z

    if ratio_low and fvc_low:
        return "mixed pattern (suggestive)"
    if ratio_low:
        return "obstructive"
    if fvc_low:
        return "restrictive pattern (suggestive)"
    if fev1_low:
        return "non-specific"
    return "normal"


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

    Returns a dict with pattern, severity, fev1_z, fvc_z and fev1_fvc_z.
    Severity is None when the pattern is normal.
    """
    missing = {"parameter", "z_score"} - set(reference_df.columns)
    if missing:
        raise ValueError(
            "reference_df is missing required columns: "
            + ", ".join(sorted(missing))
        )
    z = dict(zip(reference_df["parameter"], reference_df["z_score"]))
    for parameter in ("FEV1", "FVC", "FEV1FVC"):
        if parameter not in z or pd.isna(z[parameter]):
            raise ValueError(f"reference_df is missing a z-score for {parameter}.")

    pattern = classify_pattern(z["FEV1"], z["FVC"], z["FEV1FVC"])
    severity = None if pattern == "normal" else grade_severity(z["FEV1"])
    return {
        "pattern": pattern,
        "severity": severity,
        "fev1_z": float(z["FEV1"]),
        "fvc_z": float(z["FVC"]),
        "fev1_fvc_z": float(z["FEV1FVC"]),
    }
