"""HTML report export.

The report is a single self-contained HTML document built in memory.
Nothing is written to disk, so no input stays on the host after the
download. Quarto is not needed.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from .constants import DISCLAIMER_TEXT
from .fragments import (
    reference_table_html,
    render_interpretation,
    render_pattern_badge,
)
from .styles import BASE_CSS

# Display name, citation line and result key for each family, in the
# order shown on screen.
FAMILIES = (
    ("GLI-2012", "Quanjer et al., ERJ 2012", "gli_2012"),
    ("GLI-Global 2022 (race-neutral)", "Bowerman et al., AJRCCM 2023", "gli_2022"),
    ("NHANES III", "Hankinson et al., AJRCCM 1999", "nhanes3"),
)


def prepare_report_bundle(
    subject: dict,
    results: dict,
    interpretations: dict,
    chart_svg: str,
    comparison_html: str,
    timestamp: datetime | None = None,
) -> dict:
    """Collect everything the report needs, with HTML pre-rendered."""
    blocks = []
    for name, subtitle, key in FAMILIES:
        blocks.append(
            {
                "name": name,
                "subtitle": subtitle,
                "badge_html": render_pattern_badge(interpretations.get(key)),
                "table_html": reference_table_html(results.get(key)),
                "interpretation_html": render_interpretation(interpretations.get(key)),
            }
        )
    return {
        "subject": subject,
        "chart_svg": chart_svg,
        "comparison_html": comparison_html,
        "family_blocks": blocks,
        "timestamp": timestamp or datetime.now().astimezone(),
    }


def _subject_table(subject: dict) -> str:
    rows = (
        ("Age", f'{subject["age_years"]:g} years'),
        ("Sex", subject["sex_label"]),
        ("Height", f'{subject["height_cm"]:g} cm'),
        ("Ethnicity (GLI-2012)", subject["ethnicity_gli_label"]),
        ("Ethnicity (NHANES III)", subject["ethnicity_nhanes3_label"]),
        ("Observed FEV1", f'{subject["fev1"]:.2f} L'),
        ("Observed FVC", f'{subject["fvc"]:.2f} L'),
    )
    body = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in rows
    )
    return f'<table class="qd-table qd-subject">{body}</table>'


def render_report_html(bundle: dict) -> str:
    """Render the bundle to a complete HTML document."""
    stamp = bundle["timestamp"].strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    families = "".join(
        '<div class="qd-card">'
        f'<h3>{escape(block["name"])}</h3>'
        f'<p class="qd-muted">{escape(block["subtitle"])}</p>'
        f'{block["badge_html"]}{block["table_html"]}<hr>'
        f'{block["interpretation_html"]}</div>'
        for block in bundle["family_blocks"]
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Quadrant report</title>"
        f"<style>{BASE_CSS}</style></head><body><main>"
        "<h1>Quadrant report</h1>"
        f'<p class="qd-muted">Generated {escape(stamp)}</p>'
        f'<h2>Subject</h2>{_subject_table(bundle["subject"])}'
        "<h2>Cross-family z-score comparison</h2>"
        f'{bundle["chart_svg"]}{bundle["comparison_html"]}'
        f"<h2>Per-family results</h2>{families}"
        f'<hr><p class="qd-muted">{escape(DISCLAIMER_TEXT)}</p>'
        "</main></body></html>\n"
    )
