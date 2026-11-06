"""HTML fragments for the cards, badges and tables.

Every function returns an HTML string. Messages that come from outside
this module are escaped. Ported from R/ui_components.R. Used by both
the Streamlit app and the exported report.
"""

from __future__ import annotations

from html import escape

import pandas as pd

from .charts import PARAMETER_LABELS
from .constants import LLN_Z
from .interpretation import BASIS_LOWER_LIMIT, is_below
from .registry import EQUATIONS

# Badge colours per severity level; "normal" is used when there is no
# severity. "ungraded" is a pattern below the lower limit without a
# severity grade (classified by lower limit, no z-score). Visual emphasis
# only, no diagnostic semantics.
BADGE_PALETTE = {
    "normal": ("#86efac", "#0f172a"),
    "mild": ("#facc15", "#0f172a"),
    "moderate": ("#f59e0b", "#0f172a"),
    "severe": ("#dc2626", "#ffffff"),
    "ungraded": ("#bfdbfe", "#1e3a8a"),
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


# Streamlit badge colour for each severity level. "ungraded": a pattern
# below the lower limit, classified by lower limit, without a severity.
BADGE_COLOURS = {
    None: "green", "mild": "yellow", "moderate": "orange", "severe": "red",
    "ungraded": "blue",
}

NOT_CLASSIFIED_LABEL = "Not classified (no lower limit and no z-score for this equation)"

# Wording for a result classified from observed values against a
# published lower limit (an equation without a z-score, Pereira 2007).
LOWER_LIMIT_SUFFIX = ", by lower limit"
LOWER_LIMIT_BASIS_TEXT = "from observed values against the published lower limit"
SEVERITY_NOT_GRADED_TEXT = "Severity not graded (no z-score for this equation)"
SEVERITY_DIFFERS_TEXT = "Severity differs among the z-score equations."
LOWER_LIMIT_NOTE = (
    f"Pattern {LOWER_LIMIT_BASIS_TEXT}. {SEVERITY_NOT_GRADED_TEXT}."
)


def by_lower_limit(interpretation: dict) -> bool:
    """True for a result classified by lower limit, without a z-score."""
    return (
        interpretation["pattern"] is not None
        and interpretation.get("basis") == BASIS_LOWER_LIMIT
    )


def severity_key(interpretation: dict) -> str | None:
    """Key of BADGE_COLOURS and BADGE_PALETTE for a classified result.

    The severity level, None for a normal pattern, or "ungraded" for a
    pattern below the lower limit that has no severity grade.
    """
    if by_lower_limit(interpretation) and interpretation["pattern"] != "normal":
        return "ungraded"
    return interpretation["severity"]


def pattern_label(interpretation: dict) -> str:
    """Descriptive label, for example "Pattern consistent with obstructive · moderate".

    The wording is descriptive, never diagnostic. Labels that already
    contain "pattern" do not repeat the word. A result classified by
    lower limit ends with ", by lower limit" and has no severity.
    """
    pattern = interpretation["pattern"]
    severity = interpretation["severity"]
    if pattern is None:
        return NOT_CLASSIFIED_LABEL
    if "pattern" in pattern:
        text = f"Consistent with {pattern}"
    else:
        text = f"Pattern consistent with {pattern}"
    if by_lower_limit(interpretation):
        return f"{text}{LOWER_LIMIT_SUFFIX}"
    return text if severity is None else f"{text} · {severity}"


def basis_note(interpretation: dict) -> str | None:
    """Note under the badge for a result classified by lower limit, else None."""
    return LOWER_LIMIT_NOTE if by_lower_limit(interpretation) else None


def badge_colour(interpretation: dict) -> str:
    """Streamlit badge colour that matches the severity level."""
    if interpretation["pattern"] is None:
        return "gray"
    return BADGE_COLOURS[severity_key(interpretation)]


def render_pattern_badge(interpretation: dict | None) -> str:
    """Coloured pill with the ATS/ERS 2022 pattern and severity (report)."""
    if interpretation is None:
        return "<em>Enter values to classify.</em>"
    if interpretation["pattern"] is None:
        background, foreground = ("#e2e8f0", "#334155")
    else:
        background, foreground = BADGE_PALETTE.get(
            severity_key(interpretation) or "normal", ("#94a3b8", "#0f172a")
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
            '<p class="qd-line qd-muted">This equation gives no lower limit '
            "and no z-score, so the result is not classified.</p></div>"
        )
    pattern_line = (
        '<p class="qd-line"><span class="qd-muted">Pattern: </span>'
        f'<span>{escape(interpretation["pattern"])}</span></p>'
    )
    if by_lower_limit(interpretation):
        return (
            f"<div>{pattern_line}"
            '<p class="qd-line"><span class="qd-muted">Basis: </span>'
            f"<span>{LOWER_LIMIT_BASIS_TEXT}</span></p>"
            '<p class="qd-line"><span class="qd-muted">Severity: </span>'
            "<span>not graded (no z-score for this equation)</span></p></div>"
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
    return f"{z:.2f} *" if is_below(z, LLN_Z) else f"{z:.2f}"


def _lln_text(lln, z, observed) -> str:
    """LLN text. Without a z-score, an observed value below it adds an asterisk.

    The asterisk goes on the LLN cell only for an equation that publishes
    a lower limit but no z-score; with a z-score the mark is on the
    z-score cell. The rule is the one of the classifier (is_below).
    """
    text = _number(lln)
    if (
        pd.isna(z)
        and not pd.isna(lln)
        and observed is not None
        and not pd.isna(observed)
        and is_below(observed, lln)
    ):
        return f"{text} *"
    return text


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


def comparison_notes(gli_2012_df: pd.DataFrame | None, gli_2022_df: pd.DataFrame | None) -> list[str] | None:
    """Sentences on parameters where GLI-2012 and GLI-Global 2022 differ.

    Returns None when either table is missing, an empty list when the
    two equations agree on every parameter, and one sentence for each
    parameter that flips across the lower limit of normal.
    """
    if gli_2012_df is None or gli_2022_df is None:
        return None
    below_2012 = [is_below(z, LLN_Z) for z in gli_2012_df["z_score"]]
    below_2022 = [is_below(z, LLN_Z) for z in gli_2022_df["z_score"]]

    def side(below: bool) -> str:
        return "below LLN" if below else "within LLN"

    return [
        f'{PARAMETER_LABELS[gli_2012_df["parameter"].iloc[i]]}: GLI-2012 z = '
        f'{gli_2012_df["z_score"].iloc[i]:.2f} ({side(below_2012[i])}); '
        f'GLI-Global 2022 z = {gli_2022_df["z_score"].iloc[i]:.2f} '
        f"({side(below_2022[i])})."
        for i in range(len(below_2012))
        if below_2012[i] != below_2022[i]
    ]


AGREE_TEXT = (
    "GLI-2012 and GLI-Global 2022 put every parameter on the same side "
    "of the lower limit of normal."
)
AGREE_NOTE = "Their z-scores still differ, so the severity grade can differ."
DIFFER_HEADING = (
    "GLI-2012 and GLI-Global 2022 put these parameters on different sides "
    "of the lower limit of normal:"
)


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
    return f"<div><p>{DIFFER_HEADING}</p><ul>{items}</ul></div>"


def short_label(interpretation: dict) -> str:
    """Short classification such as "obstructive \u00b7 moderate" or "normal".

    A result classified by lower limit has no severity, so it is the
    pattern alone.
    """
    severity = interpretation["severity"]
    pattern = interpretation["pattern"]
    if pattern is None:
        return "not classified"
    return pattern if severity is None else f"{pattern} \u00b7 {severity}"


def _names(names: list[str]) -> str:
    """"A", "A and B", "A, B and C"."""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def classification_summary(interpretations: dict) -> str | None:
    """One sentence on whether the equations give the same classification.

    interpretations is keyed by registry key; the sentence uses the
    registry names. An equation that rejected the inputs (None) is left
    out. An equation without a classification (pattern None) is named at
    the end, and the sentence then speaks of the classified equations.
    Returns None when fewer than two equations have a result. The text
    says that equations agree only when two or more are classified.

    When an equation is classified by lower limit (no z-score, so no
    severity), the sentence compares the patterns only, lists the result
    of each equation, and names the equations classified by lower limit.
    When two or more z-score equations are classified and their severities
    differ (None for a normal pattern counts as a value), it says so.
    """
    results = {
        EQUATIONS[key].name: value
        for key, value in interpretations.items()
        if value is not None
    }
    if len(results) < 2:
        return None
    classified = {n: v for n, v in results.items() if v["pattern"] is not None}
    unclassified = [n for n, v in results.items() if v["pattern"] is None]
    tail = f" Not classified: {', '.join(unclassified)}." if unclassified else ""
    by_limit = [n for n, v in classified.items() if by_lower_limit(v)]
    if not classified:
        return f"No equation is classified.{tail}"
    if len(classified) == 1:
        basis = f", {LOWER_LIMIT_BASIS_TEXT}" if by_limit else ""
        return f"Only {next(iter(classified))} is classified{basis}.{tail}"
    subject = "The classified equations" if unclassified else "The equations"
    detail = "; ".join(f"{name}: {short_label(v)}" for name, v in classified.items())
    if by_limit:
        if len({v["pattern"] for v in classified.values()}) == 1:
            verdict = f"{subject} give the same pattern."
        else:
            verdict = f"{subject} give different patterns."
        verb = "is" if len(by_limit) == 1 else "are"
        basis = (
            f"{_names(by_limit)} {verb} classified {LOWER_LIMIT_BASIS_TEXT}, "
            "with no severity grade."
        )
        by_z = [v["severity"] for v in classified.values() if not by_lower_limit(v)]
        severity = (
            f" {SEVERITY_DIFFERS_TEXT}" if len(by_z) >= 2 and len(set(by_z)) > 1 else ""
        )
        return f"{verdict} {detail}.{severity} {basis}{tail}"
    if len({short_label(v) for v in classified.values()}) == 1:
        return f"{subject} agree on the classification.{tail}"
    return f"{subject} differ in classification. {detail}.{tail}"
