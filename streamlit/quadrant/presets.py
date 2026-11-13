"""Example inputs and the what-if comparison.

The examples are synthetic values for trying the app. They are not
patient data. Pure functions, no Streamlit state.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .fragments import MISSING_VALUE_TEXT
from .matrix import MATRIX_PARAMETERS

DELTA_COLUMN = "Change in z"


@dataclass(frozen=True)
class Preset:
    """One set of example inputs. Sex: 1 male, 2 female. FEV1 and FVC in litres."""

    label: str
    age_years: float
    height_cm: float
    sex_code: int
    fev1: float
    fvc: float


# Under GLI-2012 (Caucasian) the examples give, in order: normal,
# obstructive, restrictive pattern (suggestive) and normal. The tests
# check each one.
PRESETS: dict[str, Preset] = {
    "normal_adult": Preset("Example: normal adult", 40.0, 175.0, 1, 3.80, 4.75),
    "obstructive": Preset("Example: obstructive pattern", 62.0, 172.0, 1, 1.85, 3.70),
    "restrictive": Preset(
        "Example: restrictive pattern (suggestive)", 52.0, 162.0, 2, 1.85, 2.15
    ),
    "child": Preset("Example: child of 10 years", 10.0, 140.0, 2, 1.95, 2.25),
}


def _delta_text(current, pinned) -> str:
    """Signed change such as "+0.42" or "-1.10", or a hyphen for NaN."""
    if pd.isna(current) or pd.isna(pinned):
        return MISSING_VALUE_TEXT
    change = round(float(current) - float(pinned), 2)
    if change == 0:
        return "0.00"
    return f"{change:+.2f}"


def delta_frame(
    current: dict[str, pd.DataFrame | None], pinned: dict[str, pd.DataFrame | None]
) -> dict[str, pd.DataFrame]:
    """Change in z-score since the pin, one text table for each parameter.

    current and pinned are keyed like the input of matrix_frames (the
    equation name). Each value is a long-form table with at least the
    columns parameter and z_score, or None. Only names with a table in
    both get a row, in the order of current. The result is keyed "FEV1",
    "FVC" and "FEV1/FVC"; each frame has the index "Equation" and the
    column "Change in z", which holds current minus pinned with an
    explicit sign. A NaN on either side shows as a hyphen.
    """
    common = [
        name for name, table in current.items()
        if table is not None and pinned.get(name) is not None
    ]
    frames = {}
    for code, title in MATRIX_PARAMETERS.items():
        rows = {}
        for name in common:
            now = current[name].set_index("parameter")["z_score"]
            then = pinned[name].set_index("parameter")["z_score"]
            rows[name] = [_delta_text(now.get(code), then.get(code))]
        frame = pd.DataFrame.from_dict(rows, orient="index", columns=[DELTA_COLUMN])
        frame.index.name = "Equation"
        frames[title] = frame
    return frames


def pinned_tables(z_scores: dict[str, dict[str, float]]) -> dict[str, pd.DataFrame]:
    """Small long-form tables (parameter, z_score) from pinned z-scores.

    z_scores maps a key to {parameter code: z-score}. The keys stay as
    given, so the caller chooses names or registry keys.
    """
    return {
        key: pd.DataFrame(
            {"parameter": list(values), "z_score": list(values.values())}
        )
        for key, values in z_scores.items()
    }
