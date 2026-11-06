"""HTML report export.

The report is a single self-contained HTML document built in memory.
Nothing is written to disk, so no input stays on the host after the
download. The typeface is embedded and the file holds no URL, so it
opens and prints without a network. Quarto is not needed.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd

from .charts import LLN_NOTE, not_plotted_caption
from .constants import DISCLAIMER_TEXT
from .fragments import (
    AGREE_NOTE,
    AGREE_TEXT,
    DIFFER_HEADING,
    MISSING_VALUE_TEXT,
    classification_summary,
    comparison_notes,
    pattern_label,
)
from .interpretation import interpret_spirometry
from .matrix import MATRIX_LEGEND, matrix_frames
from .registry import EQUATIONS
from .styles import report_css
from .visuals import is_svg

REPORT_TITLE = "Quadrant report"

# The legend of the page matrix escapes the asterisk for Markdown. The
# report is HTML, so the backslash goes.
REPORT_MATRIX_LEGEND = MATRIX_LEGEND.replace("\\*", "*")

REJECTED_LABEL = "Not available for these inputs"

NO_CHART_TEXT = "No equation in this report has a z-score to plot."

# Inline SVG in HTML needs no namespace. Without it the report holds no
# URL at all.
SVG_NAMESPACE = ' xmlns="http://www.w3.org/2000/svg"'

STANDARD_NOTE = (
    "Pattern and severity follow the ATS/ERS 2022 interpretation strategy "
    "(Stanojevic et al., ERJ 2022). Severity is graded by the FEV1 z-score. "
    "Restrictive and mixed patterns are suggestive only, because they need "
    "static lung volumes to confirm."
)


def prepare_report_bundle(
    subject: dict,
    equations: list[str],
    results: dict,
    interpretations: dict,
    chart_svg: str,
    timestamp: datetime | None = None,
) -> dict:
    """Collect everything the report needs, as plain values.

    subject has age_years, height_cm, sex_label, fev1 and fvc, and
    optionally ethnicities: the ethnicity label used for each registry key
    whose equation has one.

    equations lists the registry keys of the report, in display order.
    results maps every one of these keys to the long-form table, or to a
    string: the message of the ValueError with which the equation rejected
    the inputs. A rejected equation stays in the report with its message;
    it has no row in the matrix and no point in the chart. A key without a
    result raises ValueError.

    interpretations maps a key with a table to interpret_spirometry() of
    that table; a key that is not given is interpreted here.

    chart_svg is the SVG from visuals.cross_family_chart_svg. It is trusted
    markup, so it is not escaped. Every other value is escaped by
    render_report_html. Pinned what-if values are not an input.
    """
    missing = [key for key in equations if key not in results]
    if missing:
        raise ValueError(f"No result for: {', '.join(missing)}.")

    entries = []
    named_tables: dict[str, pd.DataFrame | None] = {}
    tables: dict[str, pd.DataFrame] = {}
    interpreted: dict[str, dict] = {}
    for key in equations:
        spec = EQUATIONS[key]
        result = results[key]
        entry = {
            "key": key,
            "name": spec.name,
            "citation": spec.citation,
            "population": spec.population.rstrip("."),
            "age_range": spec.age_range,
            "caveat": spec.caveat,
            "message": None,
            "label": None,
            "severity": None,
        }
        if isinstance(result, str):
            entry.update(status="rejected", label=REJECTED_LABEL, message=result)
            named_tables[spec.name] = None
        else:
            interpretation = interpretations.get(key) or interpret_spirometry(result)
            interpreted[key] = interpretation
            tables[key] = result
            named_tables[spec.name] = result
            classified = interpretation["pattern"] is not None
            entry.update(
                status="classified" if classified else "unclassified",
                label=pattern_label(interpretation),
                severity=interpretation["severity"] if classified else None,
            )
        entries.append(entry)

    ethnicities = subject.get("ethnicities") or {}
    fev1, fvc = subject["fev1"], subject["fvc"]
    inputs = [
        ("Age", f'{subject["age_years"]:g} years'),
        ("Height", f'{subject["height_cm"]:g} cm'),
        ("Sex", str(subject["sex_label"])),
        ("FEV1", f"{fev1:.2f} L"),
        ("FVC", f"{fvc:.2f} L"),
        ("FEV1/FVC", f"{fev1 / fvc:.2f}" if fvc else MISSING_VALUE_TEXT),
    ]
    inputs += [
        (f"Ethnicity ({EQUATIONS[key].name})", str(ethnicities.get(key, "Not given")))
        for key in equations
        if EQUATIONS[key].ethnicities
    ]

    with_tables = {name: t for name, t in named_tables.items() if t is not None}
    return {
        "timestamp": timestamp or datetime.now().astimezone(),
        "inputs": inputs,
        "equations": entries,
        "summary": classification_summary(interpreted),
        "gli_notes": comparison_notes(tables.get("gli_2012"), tables.get("gli_2022")),
        "chart_svg": chart_svg,
        "not_plotted": not_plotted_caption(named_tables),
        "matrix": matrix_frames(with_tables) if with_tables else {},
        "observed": {
            "FEV1": f"{fev1:.2f} L",
            "FVC": f"{fvc:.2f} L",
            "FEV1/FVC": f"{fev1 / fvc:.2f}" if fvc else MISSING_VALUE_TEXT,
        },
    }


def _inputs_html(bundle: dict) -> str:
    facts = "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
        for label, value in bundle["inputs"]
    )
    return f'<section class="qd-inputs"><h2>Inputs</h2><dl class="qd-facts">{facts}</dl></section>'


def _pill_class(entry: dict) -> str:
    if entry["status"] == "rejected":
        return "rejected"
    if entry["status"] == "unclassified":
        return "none"
    return entry["severity"] or "normal"


def _classification_html(bundle: dict) -> str:
    rows = []
    for entry in bundle["equations"]:
        reason = (
            f'<p class="qd-reason">{escape(entry["message"])}</p>'
            if entry["message"] else ""
        )
        rows.append(
            f'<tr><th scope="row">{escape(entry["name"])}</th><td>'
            f'<span class="qd-pill qd-pill-{_pill_class(entry)}">'
            f'{escape(entry["label"])}</span>{reason}</td></tr>'
        )
    extra = []
    if bundle["summary"]:
        extra.append(f'<p>{escape(bundle["summary"])}</p>')
    # None: the report lacks one of the two GLI equations. An empty list:
    # they agree, and the report says so, as the page does.
    if bundle["gli_notes"]:
        items = "".join(f"<li>{escape(note)}</li>" for note in bundle["gli_notes"])
        extra.append(
            f"<p>{escape(DIFFER_HEADING)}</p>"
            f"<ul>{items}</ul>"
        )
    elif bundle["gli_notes"] == []:
        extra.append(f"<p>{escape(AGREE_TEXT)} {escape(AGREE_NOTE)}</p>")
    summary = f'<div class="qd-summary">{"".join(extra)}</div>' if extra else ""
    return (
        '<section class="qd-classification"><h2>Classification</h2>'
        '<table class="qd-table qd-class-table"><tbody>'
        f'{"".join(rows)}</tbody></table>{summary}</section>'
    )


def _chart_html(bundle: dict) -> str:
    svg = bundle["chart_svg"]
    if is_svg(svg):
        figure = f'<figure class="qd-figure">{svg.replace(SVG_NAMESPACE, "", 1)}</figure>'
        notes = [LLN_NOTE]
    else:
        figure = ""
        notes = [NO_CHART_TEXT]
    if bundle["not_plotted"]:
        notes.append(bundle["not_plotted"])
    captions = "".join(f'<p class="qd-caption">{escape(n)}</p>' for n in notes)
    return (
        '<section class="qd-chart"><h2>Z-scores by equation</h2>'
        f"{figure}{captions}</section>"
    )


def _matrix_table(title: str, frame: pd.DataFrame, observed: str) -> str:
    header = "".join(
        f'<th scope="col">{escape(str(c))}</th>' for c in [frame.index.name, *frame.columns]
    )
    body = "".join(
        f'<tr><th scope="row">{escape(str(name))}</th>'
        + "".join(f"<td>{escape(str(v))}</td>" for v in row)
        + "</tr>"
        for name, row in zip(frame.index, frame.itertuples(index=False))
    )
    return (
        '<table class="qd-table qd-matrix-table">'
        f"<caption>{escape(title)} <span>observed {escape(observed)}</span></caption>"
        f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
    )


def _matrix_html(bundle: dict) -> str:
    if not bundle["matrix"]:
        return ""
    tables = "".join(
        _matrix_table(title, frame, bundle["observed"][title])
        for title, frame in bundle["matrix"].items()
    )
    return (
        '<section class="qd-matrix"><h2>Reference values</h2>'
        f'<div class="qd-matrix-grid">{tables}</div>'
        f'<p class="qd-caption">{escape(REPORT_MATRIX_LEGEND)}</p></section>'
    )


def _notes_html(bundle: dict) -> str:
    notes = []
    for entry in bundle["equations"]:
        caveat = (
            f'<p class="qd-caveat">{escape(entry["caveat"])}</p>' if entry["caveat"] else ""
        )
        notes.append(
            f'<div class="qd-note"><h3>{escape(entry["name"])}</h3>'
            f'<p>{escape(entry["citation"])}. {escape(entry["population"])}.</p>'
            f"{caveat}</div>"
        )
    return (
        '<section class="qd-notes"><h2>Equation notes</h2>'
        f'<div class="qd-note-grid">{"".join(notes)}</div></section>'
    )


def render_report_html(bundle: dict) -> str:
    """Render the bundle to a complete HTML document."""
    stamp = bundle["timestamp"].strftime("%Y-%m-%d %H:%M %Z").strip()
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        f"<title>{REPORT_TITLE}</title>"
        f"<style>{report_css()}</style></head><body><main>"
        '<header class="qd-head"><div><p class="qd-kicker">Quadrant</p>'
        "<h1>Spirometry reference values</h1></div>"
        f'<p class="qd-stamp">Generated {escape(stamp)}</p>'
        # A copy of the disclaimer, so that page 1 has it when the footer
        # goes to page 2.
        f'<p class="qd-head-note">{escape(DISCLAIMER_TEXT)}</p></header>'
        f"{_inputs_html(bundle)}{_classification_html(bundle)}{_chart_html(bundle)}"
        f"{_matrix_html(bundle)}{_notes_html(bundle)}"
        '<footer class="qd-foot">'
        f'<p class="qd-disclaimer">{escape(DISCLAIMER_TEXT)}</p>'
        f"<p>{escape(STANDARD_NOTE)}</p></footer>"
        "</main></body></html>\n"
    )
