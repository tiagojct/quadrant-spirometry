"""Stylesheet of the exported report.

The report is a document, so it has a light theme only. The colours are
the chart-room light palette of .streamlit/config.toml and the typeface
is Source Sans 3, embedded as base64 so that the file makes no request
to another host. The @media print rules fit the default selection on one
A4 page.
"""

from __future__ import annotations

from base64 import b64encode
from functools import lru_cache
from pathlib import Path

from .fragments import BADGE_PALETTE

FONT_DIR = Path(__file__).resolve().parents[1] / "static" / "fonts"

# File name and CSS weight of each embedded face. The README in FONT_DIR
# gives the release and the checksums.
FONT_FACES = (
    ("SourceSans3-Regular.woff2", 400),
    ("SourceSans3-Semibold.woff2", 600),
)

FONT_STACK = "'Source Sans 3', 'Source Sans Pro', Arial, sans-serif"

# Light palette of .streamlit/config.toml ([theme.light]).
PAPER = "#fbf9f4"
PAPER_DEEP = "#f1ede3"
INK = "#1a2233"
NAVY = "#1c3557"
RULE = "#d9d2c0"
# Secondary text. Contrast 5.8:1 on PAPER and 6.1:1 on white.
MUTED = "#5a6272"

# Pill colours for the results without a classification.
UNCLASSIFIED_PILL = ("#e2e8f0", "#334155")
REJECTED_PILL = (PAPER_DEEP, INK)


@lru_cache(maxsize=1)
def font_face_css() -> str:
    """One @font-face rule for each weight, with the font as a data URI."""
    rules = []
    for file_name, weight in FONT_FACES:
        data = b64encode((FONT_DIR / file_name).read_bytes()).decode("ascii")
        rules.append(
            "@font-face { font-family: 'Source Sans 3'; font-style: normal; "
            f"font-weight: {weight}; font-display: swap; "
            f"src: url(data:font/woff2;base64,{data}) format('woff2'); }}"
        )
    return "\n".join(rules)


def _pill_css() -> str:
    colours = dict(BADGE_PALETTE)
    colours["none"] = UNCLASSIFIED_PILL
    colours["rejected"] = REJECTED_PILL
    return "\n".join(
        f".qd-pill-{name} {{ background: {bg}; color: {fg}; }}"
        for name, (bg, fg) in colours.items()
    )


LAYOUT_CSS = f"""
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
html {{ font-size: 16px; -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; background: {PAPER}; color: {INK};
       font-family: {FONT_STACK}; font-weight: 400; line-height: 1.4;
       font-synthesis: style; }}
main {{ max-width: 62rem; margin: 0 auto; padding: 24px 16px 32px; }}
h1, h2, h3 {{ font-weight: 600; color: {NAVY}; line-height: 1.2; }}
h1 {{ font-size: 1.9rem; margin: 0; }}
h2 {{ font-size: 1.15rem; margin: 0 0 0.5rem; }}
h3 {{ font-size: 0.95rem; margin: 0 0 0.2rem; }}
p {{ margin: 0 0 0.35rem; }}
section {{ border-top: 1px solid {RULE}; padding: 0.8rem 0 0.6rem; }}
.qd-head + section {{ border-top: 0; }}
.qd-muted, .qd-caption {{ color: {MUTED}; }}
.qd-caption {{ font-size: 0.85rem; }}

.qd-head {{ display: flex; flex-wrap: wrap; align-items: baseline;
           justify-content: space-between; gap: 0.25rem 1.5rem;
           border-bottom: 2px solid {NAVY}; padding-bottom: 0.5rem;
           margin-bottom: 0.2rem; }}
.qd-kicker {{ margin: 0; font-size: 0.8rem; font-weight: 600;
             letter-spacing: 0.08em; text-transform: uppercase; color: {MUTED}; }}
.qd-stamp {{ margin: 0; font-size: 0.85rem; color: {MUTED};
            font-variant-numeric: tabular-nums; }}
.qd-head-note {{ flex-basis: 100%; margin: 0; font-size: 0.8rem; color: {INK}; }}

.qd-facts {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr));
            gap: 0.35rem 1rem; margin: 0; }}
.qd-facts div {{ min-width: 0; }}
.qd-facts dt {{ font-size: 0.75rem; color: {MUTED}; }}
.qd-facts dd {{ margin: 0; font-weight: 600; font-variant-numeric: tabular-nums;
               overflow-wrap: anywhere; }}

.qd-table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem;
            font-variant-numeric: tabular-nums; }}
.qd-table th, .qd-table td {{ text-align: left; padding: 0.3rem 0.4rem;
                             border-bottom: 1px solid {RULE}; vertical-align: top; }}
.qd-table thead th {{ font-weight: 600; color: {MUTED}; font-size: 0.75rem;
                     border-bottom: 1px solid {INK}; }}
.qd-table tbody th {{ font-weight: 600; }}
.qd-class-table tbody th {{ width: 34%; padding-left: 0; }}
.qd-reason {{ margin: 0.2rem 0 0; font-size: 0.8rem; color: {MUTED}; }}
.qd-pill {{ display: inline-block; border-radius: 0.7rem; padding: 0.1rem 0.6rem;
           font-weight: 600; font-size: 0.8rem; line-height: 1.35; }}
.qd-pill-rejected {{ border: 1px solid {RULE}; }}
.qd-pill-ungraded {{ border: 1px solid #1e3a8a; }}
{_pill_css()}
.qd-summary {{ margin-top: 0.45rem; font-size: 0.9rem; }}
.qd-summary ul {{ margin: 0.2rem 0 0; padding-left: 1.2rem; }}

.qd-figure {{ margin: 0; overflow-x: auto; background: #ffffff;
             border: 1px solid {RULE}; border-radius: 0.4rem; padding: 0.3rem; }}
.qd-figure svg {{ font-family: {FONT_STACK} !important; }}

.qd-matrix-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
                  gap: 0.6rem 1rem; }}
.qd-matrix-table caption {{ caption-side: top; text-align: left; font-weight: 600;
                           color: {NAVY}; padding-bottom: 0.15rem; }}
.qd-matrix-table caption span {{ font-weight: 400; color: {MUTED}; font-size: 0.8rem; }}
.qd-matrix-table td {{ text-align: right; white-space: nowrap; }}
.qd-matrix-table thead th:not(:first-child) {{ text-align: right; }}
.qd-matrix-table tbody th {{ padding-left: 0; }}

.qd-note-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
                gap: 0.5rem 1.2rem; }}
.qd-note p {{ font-size: 0.82rem; margin: 0 0 0.15rem; }}
.qd-note .qd-caveat {{ color: {MUTED}; }}

.qd-foot {{ border-top: 2px solid {NAVY}; margin-top: 0.4rem; padding-top: 0.5rem; }}
.qd-foot p {{ font-size: 0.8rem; color: {MUTED}; }}
.qd-foot .qd-disclaimer {{ font-size: 0.9rem; font-weight: 400; color: {INK}; }}

/* Phone: the chart keeps a readable text size and scrolls inside its frame. */
@media (max-width: 640px) {{
  h1 {{ font-size: 1.55rem; }}
  .qd-figure svg {{ min-width: 40rem; }}
  .qd-class-table tbody th {{ width: 40%; }}
}}
"""

PRINT_CSS = f"""
@page {{ size: A4; margin: 11mm 12mm 12mm; }}
@media print {{
  html {{ font-size: 8.6pt; }}
  body {{ background: #ffffff; }}
  main {{ max-width: none; padding: 0; }}
  * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  section {{ padding: 0.5rem 0 0.35rem; }}
  h2 {{ break-after: avoid; page-break-after: avoid; }}
  table, tr, figure, .qd-note, .qd-head, .qd-foot, .qd-inputs, .qd-pill {{
    break-inside: avoid; page-break-inside: avoid; }}
  .qd-figure {{ border: 0; padding: 0; overflow: visible; }}
  .qd-figure svg {{ min-width: 0; max-height: 105mm; }}
  .qd-facts {{ grid-template-columns: repeat(6, 1fr); }}
  .qd-matrix-grid {{ grid-template-columns: repeat(3, 1fr); gap: 0.4rem 0.8rem; }}
  .qd-matrix-table {{ font-size: 0.8rem; }}
  .qd-note-grid {{ grid-template-columns: 1fr 1fr; }}
}}
"""


def report_css() -> str:
    """Complete stylesheet of the report, with the embedded fonts."""
    return font_face_css() + LAYOUT_CSS + PRINT_CSS
