"""Comparison matrix: one table for each parameter, one row for each equation.

Pure functions, no Streamlit state. The values are formatted as text, so
the page and the tests see the same strings.
"""

from __future__ import annotations

import pandas as pd

from .fragments import MISSING_VALUE_TEXT, _number, _z_text

# Long-form parameter code and the title of its table.
MATRIX_PARAMETERS = {"FEV1": "FEV1", "FVC": "FVC", "FEV1FVC": "FEV1/FVC"}

MATRIX_COLUMNS = ["Pred.", "LLN", "Z-score", "% pred"]

# Legend for the matrix caption. The backslash stops Markdown from reading
# the asterisk as emphasis.
MATRIX_LEGEND = (
    f"A hyphen ({MISSING_VALUE_TEXT}) means that the equation publishes no "
    "value. An asterisk (\\*) marks a z-score below -1.645, the lower limit "
    "of normal."
)


def matrix_frames(tables: dict[str, pd.DataFrame | None]) -> dict[str, pd.DataFrame]:
    """Three text tables, keyed "FEV1", "FVC" and "FEV1/FVC".

    tables maps an equation name to its long-form table. A name with no
    table (None) gets no row. Each frame has the index "Equation" and the
    columns Pred., LLN, Z-score and % pred. A missing value shows as a
    hyphen; a z-score below the lower limit of normal ends with " *".
    """
    frames = {}
    for code, title in MATRIX_PARAMETERS.items():
        rows = {}
        for name, table in tables.items():
            if table is None:
                continue
            row = table.loc[table["parameter"] == code].iloc[0]
            rows[name] = [
                _number(row["predicted"]),
                _number(row["lln"]),
                _z_text(row["z_score"]),
                _number(row["percent_predicted"], ".1f"),
            ]
        frame = pd.DataFrame.from_dict(rows, orient="index", columns=MATRIX_COLUMNS)
        frame.index.name = "Equation"
        frames[title] = frame
    return frames


def _escape_cell(text: str) -> str:
    if text == MISSING_VALUE_TEXT:
        return "\\" + MISSING_VALUE_TEXT
    return text.replace("*", "\\*")


def markdown_cells(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy of a matrix frame that st.table shows as written.

    st.table reads each cell as Markdown, so a lone hyphen would become a
    list bullet. The hyphen and the asterisk get a backslash.
    """
    return frame.map(_escape_cell)
