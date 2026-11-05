"""HTML fragments for the cards, badges and tables.

Every function returns an HTML string. Messages that come from outside
this module are escaped. Ported from R/ui_components.R. Used by both
the Streamlit app and the exported report.
"""

from __future__ import annotations

from html import escape

import pandas as pd

from .constants import LLN_Z

# Badge colours per severity level; "normal" is used when there is no
# severity. Visual emphasis only, no diagnostic semantics.
BADGE_PALETTE = {
    "normal": ("#86efac", "#0f172a"),
    "mild": ("#facc15", "#0f172a"),
    "moderate": ("#f59e0b", "#0f172a"),
    "severe": ("#dc2626", "#ffffff"),
}


def input_notice(fev1, fvc) -> str | None:
    """Warning block when the observed values cannot be used.

    Returns None when a value is missing, because an empty field is not
    an error, and also when the values are usable.
    """

    def present(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and not pd.isna(x)

    if not present(fev1) or not present(fvc):
        return None
    if fev1 <= 0 or fvc <= 0:
        message = "FEV1 and FVC must be greater than zero."
    elif fev1 > fvc:
        message = (
            "FEV1 is larger than FVC, so the ratio is above 1. Check the "
            "values. The results stay hidden until FEV1 is not larger than FVC."
        )
    else:
        return None
    return f'<div class="qd-alert" role="alert">{escape(message)}</div>'


def render_pattern_badge(interpretation: dict | None) -> str:
    """Coloured pill with the ATS/ERS 2022 pattern and severity."""
    if interpretation is None:
        return "<em>Enter values to classify.</em>"
    severity = interpretation["severity"]
    pattern = interpretation["pattern"]
    background, foreground = BADGE_PALETTE.get(
        severity if severity else "normal", ("#94a3b8", "#0f172a")
    )
    # Labels that already contain "pattern" do not repeat the word.
    if "pattern" in pattern:
        text = f"Consistent with {pattern}"
    else:
        text = f"Pattern consistent with {pattern}"
    label = text if severity is None else f"{text} · {severity}"
    return (
        f'<div class="qd-badge" style="background:{background};color:{foreground};">'
        f"{escape(label)}</div>"
    )


def render_interpretation(interpretation: dict | None) -> str:
    """Pattern and severity lines for one reference family."""
    if interpretation is None:
        return "<em>Enter values to interpret.</em>"
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


def reference_table_html(reference_df: pd.DataFrame | None, flag_below_lln: bool = False) -> str:
    """Long-form result table as an HTML fragment.

    With flag_below_lln, a parameter whose z-score is below the lower
    limit of normal gets a "(below LLN)" label.
    """
    if reference_df is None:
        return "<em>No data.</em>"
    names = [
        f"{p} (below LLN)" if flag_below_lln and z < LLN_Z else p
        for p, z in zip(reference_df["parameter"], reference_df["z_score"])
    ]
    display = pd.DataFrame(
        {
            "Parameter": names,
            "Obs.": [f"{v:.2f}" for v in reference_df["observed"]],
            "Pred.": [f"{v:.2f}" for v in reference_df["predicted"]],
            "LLN": [f"{v:.2f}" for v in reference_df["lln"]],
            "Z-score": [f"{v:.2f}" for v in reference_df["z_score"]],
            "% pred": [f"{v:.1f}" for v in reference_df["percent_predicted"]],
        }
    )
    return html_table(display)


def render_reference_table(reference_df: pd.DataFrame | None, message: str | None = None) -> str:
    """Results table for the screen, or the reason it is unavailable."""
    if message is not None:
        return (
            '<div class="qd-error">Not available for these inputs: '
            f"{escape(message)}</div>"
        )
    if reference_df is None:
        return "<em>Enter values to compute results.</em>"
    return reference_table_html(reference_df, flag_below_lln=True)


def render_gli_comparison(gli_2012_df: pd.DataFrame | None, gli_2022_df: pd.DataFrame | None) -> str:
    """Text note on parameters where GLI-2012 and GLI-Global 2022 differ."""
    if gli_2012_df is None or gli_2022_df is None:
        return "<em>Enter values to compare equations.</em>"
    below_2012 = (gli_2012_df["z_score"] < LLN_Z).tolist()
    below_2022 = (gli_2022_df["z_score"] < LLN_Z).tolist()
    flipped = [i for i, (a, b) in enumerate(zip(below_2012, below_2022)) if a != b]

    if not flipped:
        return (
            "<div><p>GLI-2012 and GLI-Global 2022 classify every parameter on "
            "the same side of the lower limit of normal.</p>"
            '<p class="qd-muted">Differences in z-score remain, even when '
            "classification agrees.</p></div>"
        )

    def side(below: bool) -> str:
        return "below LLN" if below else "within LLN"

    items = "".join(
        "<li>"
        f'{escape(gli_2012_df["parameter"].iloc[i])}: GLI-2012 z = '
        f'{gli_2012_df["z_score"].iloc[i]:.2f} ({side(below_2012[i])}); '
        f'GLI-Global 2022 z = {gli_2022_df["z_score"].iloc[i]:.2f} '
        f"({side(below_2022[i])})."
        "</li>"
        for i in flipped
    )
    return f"<div><p>Classification differs for:</p><ul>{items}</ul></div>"
