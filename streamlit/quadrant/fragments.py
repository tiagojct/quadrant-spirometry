"""HTML fragments for the cards, badges and tables.

Every function returns an HTML string. Messages that come from outside
this module are escaped. Ported from R/ui_components.R. Used by both
the Streamlit app and the exported report.
"""

from __future__ import annotations

from html import escape

import pandas as pd

from .constants import LLN_Z
from .registry import EQUATIONS

# Badge colours per severity level; "normal" is used when there is no
# severity. Visual emphasis only, no diagnostic semantics.
BADGE_PALETTE = {
    "normal": ("#86efac", "#0f172a"),
    "mild": ("#facc15", "#0f172a"),
    "moderate": ("#f59e0b", "#0f172a"),
    "severe": ("#dc2626", "#ffffff"),
}


def input_problem(fev1, fvc) -> str | None:
    """Message when the observed values cannot be used, else None.

    Returns None when a value is missing, because an empty field is not
    an error, and also when the values are usable.
    """

    def present(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and not pd.isna(x)

    if not present(fev1) or not present(fvc):
        return None
    if fev1 <= 0 or fvc <= 0:
        return "FEV1 and FVC must be greater than zero."
    if fev1 > fvc:
        return (
            "FEV1 is larger than FVC, so the ratio is above 1. Check the "
            "values. The results stay hidden until FEV1 is not larger than FVC."
        )
    return None


# Streamlit badge colour for each severity level.
BADGE_COLOURS = {None: "green", "mild": "yellow", "moderate": "orange", "severe": "red"}

NOT_CLASSIFIED_LABEL = "Not classified (no z-score for this equation)"


def pattern_label(interpretation: dict) -> str:
    """Descriptive label, for example "Pattern consistent with obstructive · moderate".

    The wording is descriptive, never diagnostic. Labels that already
    contain "pattern" do not repeat the word.
    """
    pattern = interpretation["pattern"]
    severity = interpretation["severity"]
    if pattern is None:
        return NOT_CLASSIFIED_LABEL
    if "pattern" in pattern:
        text = f"Consistent with {pattern}"
    else:
        text = f"Pattern consistent with {pattern}"
    return text if severity is None else f"{text} · {severity}"


def badge_colour(interpretation: dict) -> str:
    """Streamlit badge colour that matches the severity level."""
    if interpretation["pattern"] is None:
        return "gray"
    return BADGE_COLOURS[interpretation["severity"]]


def render_pattern_badge(interpretation: dict | None) -> str:
    """Coloured pill with the ATS/ERS 2022 pattern and severity (report)."""
    if interpretation is None:
        return "<em>Enter values to classify.</em>"
    if interpretation["pattern"] is None:
        background, foreground = ("#e2e8f0", "#334155")
    else:
        background, foreground = BADGE_PALETTE.get(
            interpretation["severity"] or "normal", ("#94a3b8", "#0f172a")
        )
    return (
        f'<div class="qd-badge" style="background:{background};color:{foreground};">'
        f"{escape(pattern_label(interpretation))}</div>"
    )


def render_interpretation(interpretation: dict | None) -> str:
    """Pattern and severity lines for one reference family."""
    if interpretation is None:
        return "<em>Enter values to interpret.</em>"
    if interpretation["pattern"] is None:
        return (
            '<div><p class="qd-line"><span class="qd-muted">Pattern: </span>'
            "<span>Not classified</span></p>"
            '<p class="qd-line qd-muted">This equation gives no z-score, '
            "so the result is not classified.</p></div>"
        )
    pattern_line = (
        '<p class="qd-line"><span class="qd-muted">Pattern: </span>'
        f'<span>{escape(interpretation["pattern"])}</span></p>'
    )
    if interpretation["severity"] is None:
        severity_line = (
            '<p class="qd-line"><span class="qd-muted">Severity: </span>'
            "<span>not graded (pattern is normal)</span></p>"
        )
    else:
        severity_line = (
            '<p class="qd-line"><span class="qd-muted">Severity (by FEV1 z-score): </span>'
            f'<span>{escape(interpretation["severity"])}</span></p>'
        )
    return f"<div>{pattern_line}{severity_line}</div>"


def html_table(df: pd.DataFrame) -> str:
    """Small HTML table without extra dependencies."""
    header = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
        for row in df.itertuples(index=False)
    )
    return (
        '<div class="qd-scroll"><table class="qd-table"><thead><tr>'
        f"{header}</tr></thead><tbody>{body}</tbody></table></div>"
    )


# Shown in place of a value that the equation does not give (NaN).
MISSING_VALUE_TEXT = "-"


def _number(value, spec: str = ".2f") -> str:
    """Formatted number, or a hyphen when the value is missing."""
    if pd.isna(value):
        return MISSING_VALUE_TEXT
    return format(value, spec)


def _z_text(z) -> str:
    """Z-score text. A z-score below the LLN ends with an asterisk."""
    if pd.isna(z):
        return MISSING_VALUE_TEXT
    return f"{z:.2f} *" if z < LLN_Z else f"{z:.2f}"


def reference_table_html(reference_df: pd.DataFrame | None) -> str:
    """Long-form result table as an HTML fragment (report)."""
    if reference_df is None:
        return "<em>No data.</em>"
    display = pd.DataFrame(
        {
            "Parameter": reference_df["parameter"],
            "Obs.": [f"{v:.2f}" for v in reference_df["observed"]],
            "Pred.": [f"{v:.2f}" for v in reference_df["predicted"]],
            "LLN": [_number(v) for v in reference_df["lln"]],
            "Z-score": [_number(v) for v in reference_df["z_score"]],
            "% pred": [f"{v:.1f}" for v in reference_df["percent_predicted"]],
        }
    )
    return html_table(display)


# The backslash stops Markdown from reading the asterisk as a list marker.
BELOW_LLN_NOTE = "\\* Below the lower limit of normal (z-score under -1.645)."


def results_for_display(reference_df: pd.DataFrame) -> pd.DataFrame:
    """Result table for st.table, as formatted text.

    The observed values are left out: they are inputs and the same for
    every family. A z-score below the lower limit of normal ends with an
    asterisk. Numbers are rounded to two decimals, percent of predicted
    to one. A value the equation does not give (NaN) is shown as a
    hyphen, without an asterisk.
    """
    return pd.DataFrame(
        {
            "Parameter": list(reference_df["parameter"]),
            "Pred.": [f"{v:.2f}" for v in reference_df["predicted"]],
            "LLN": [_number(v) for v in reference_df["lln"]],
            "Z-score": [_z_text(z) for z in reference_df["z_score"]],
            "% pred": [f"{v:.1f}" for v in reference_df["percent_predicted"]],
        }
    )


def comparison_notes(gli_2012_df: pd.DataFrame | None, gli_2022_df: pd.DataFrame | None) -> list[str] | None:
    """Sentences on parameters where GLI-2012 and GLI-Global 2022 differ.

    Returns None when either table is missing, an empty list when the
    two equations agree on every parameter, and one sentence for each
    parameter that flips across the lower limit of normal.
    """
    if gli_2012_df is None or gli_2022_df is None:
        return None
    below_2012 = (gli_2012_df["z_score"] < LLN_Z).tolist()
    below_2022 = (gli_2022_df["z_score"] < LLN_Z).tolist()

    def side(below: bool) -> str:
        return "below LLN" if below else "within LLN"

    return [
        f'{gli_2012_df["parameter"].iloc[i]}: GLI-2012 z = '
        f'{gli_2012_df["z_score"].iloc[i]:.2f} ({side(below_2012[i])}); '
        f'GLI-Global 2022 z = {gli_2022_df["z_score"].iloc[i]:.2f} '
        f"({side(below_2022[i])})."
        for i in range(len(below_2012))
        if below_2012[i] != below_2022[i]
    ]


AGREE_TEXT = (
    "GLI-2012 and GLI-Global 2022 classify every parameter on the same side "
    "of the lower limit of normal."
)
AGREE_NOTE = "Differences in z-score remain, even when classification agrees."


def render_gli_comparison(gli_2012_df: pd.DataFrame | None, gli_2022_df: pd.DataFrame | None) -> str:
    """HTML version of the comparison notes (report)."""
    notes = comparison_notes(gli_2012_df, gli_2022_df)
    if notes is None:
        return "<em>Enter values to compare equations.</em>"
    if not notes:
        return (
            f"<div><p>{AGREE_TEXT}</p>"
            f'<p class="qd-muted">{AGREE_NOTE}</p></div>'
        )
    items = "".join(f"<li>{escape(note)}</li>" for note in notes)
    return f"<div><p>Classification differs for:</p><ul>{items}</ul></div>"


def short_label(interpretation: dict) -> str:
    """Short classification such as "obstructive \u00b7 moderate" or "normal"."""
    severity = interpretation["severity"]
    pattern = interpretation["pattern"]
    if pattern is None:
        return "not classified"
    return pattern if severity is None else f"{pattern} \u00b7 {severity}"


def classification_summary(interpretations: dict) -> str | None:
    """One sentence on whether the equations give the same classification.

    interpretations is keyed by registry key; the sentence uses the
    registry names. Equations without a classification are skipped.
    Returns None when
    fewer than two equations have a result. When the
    equations differ, the sentence names each one.
    """
    available = {
        EQUATIONS[key].name: value
        for key, value in interpretations.items()
        if value is not None and value["pattern"] is not None
    }
    if len(available) < 2:
        return None
    if len({short_label(v) for v in available.values()}) == 1:
        return "The equations agree on the classification."
    detail = "; ".join(f"{name}: {short_label(v)}" for name, v in available.items())
    return f"The equations differ in classification. {detail}."
