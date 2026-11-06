"""Quadrant: spirometry reference value calculator (Streamlit port).

License: AGPL-3.0-or-later

Run with: uv run streamlit run app.py

The app keeps no state between sessions and writes nothing to disk.
Session state holds only the current inputs and the chosen equations.
Colours and fonts come from .streamlit/config.toml.
"""

from __future__ import annotations

from datetime import datetime
from html import escape as html_escape

import streamlit as st

from quadrant.charts import comparison_chart, not_plotted_caption
from quadrant.constants import (
    DISCLAIMER_TEXT,
    GLI_AGE_RANGE_YEARS,
    HEIGHT_RANGE_CM,
    SEX_CODES,
)
from quadrant.fragments import (
    AGREE_NOTE,
    AGREE_TEXT,
    badge_colour,
    classification_summary,
    comparison_notes,
    input_problem,
    pattern_label,
    render_gli_comparison,
)
from quadrant.interpretation import interpret_spirometry
from quadrant.matrix import MATRIX_LEGEND, markdown_cells, matrix_frames
from quadrant.registry import DEFAULT_KEYS, EQUATIONS, Subject, compute_equation
from quadrant.report import prepare_report_bundle, render_report_html
from quadrant.visuals import cross_family_chart_svg

st.set_page_config(
    page_title="Quadrant",
    page_icon=":material/explore:",
    layout="wide",
)

CHART_ALT = (
    "Chart of the FEV1, FVC and FEV1/FVC z-scores for each selected reference "
    "equation, on one axis with the lower limit of normal marked at -1.645 "
    "and the severity bands shaded."
)

# Equation groups in the order of the selector, with their labels.
GROUPS = (
    ("recommended", "Recommended"),
    ("historical", "Historical"),
    ("regional", "Regional"),
)

GUARD_NOTE = "At least one equation must stay selected."
NOT_AVAILABLE_TITLE = "Not available for these inputs"


def group_key(group: str) -> str:
    """Session state key of the pills for one group."""
    return f"equations_{group}"


def selected_keys() -> list[str]:
    """Registry keys chosen in the pills, in registry order."""
    chosen = {
        key
        for group, _ in GROUPS
        for key in st.session_state.get(group_key(group)) or []
    }
    return [key for key in EQUATIONS if key in chosen]


def keep_one_selected() -> None:
    """Pills callback: put the previous choice back when none is left."""
    if selected_keys():
        st.session_state["selection_guard"] = False
        return
    previous = st.session_state.get("previous_selection") or list(DEFAULT_KEYS)
    for group, _ in GROUPS:
        st.session_state[group_key(group)] = [
            key for key in previous if EQUATIONS[key].group == group
        ]
    st.session_state["selection_guard"] = True


# The pills start at the default equations. Callbacks run before this
# line, so the selection read here is the current one.
for _group, _ in GROUPS:
    st.session_state.setdefault(
        group_key(_group),
        [key for key in DEFAULT_KEYS if EQUATIONS[key].group == _group],
    )
selection = selected_keys() or list(DEFAULT_KEYS)
st.session_state["previous_selection"] = selection
specs = [EQUATIONS[key] for key in selection]


# Sidebar inputs. Each widget has a key so that the tests can set it.
with st.sidebar:
    st.subheader("Subject", icon=":material/person:")
    age_col, height_col = st.columns(2)
    age_years = age_col.number_input(
        "Age (years)", key="age_years", value=40.0,
        min_value=float(GLI_AGE_RANGE_YEARS[0]),
        max_value=float(GLI_AGE_RANGE_YEARS[1]), step=1.0,
        help="Each equation covers its own age range. See the equation notes.",
    )
    height_cm = height_col.number_input(
        "Height (cm)", key="height_cm", value=170.0,
        min_value=float(HEIGHT_RANGE_CM[0]),
        max_value=float(HEIGHT_RANGE_CM[1]), step=0.5,
    )
    sex_label = st.segmented_control(
        "Sex", list(SEX_CODES), default="Male", required=True,
        key="sex", width="stretch",
    )
    # One ethnicity selector for each selected equation that uses one.
    ethnicity_labels = {
        spec.key: st.selectbox(
            f"Ethnicity ({spec.name})", list(spec.ethnicities),
            key=f"ethnicity_{spec.key}",
        )
        for spec in specs
        if spec.ethnicities
    }

    st.subheader("Spirometry", icon=":material/air:")
    fev1_col, fvc_col = st.columns(2)
    fev1 = fev1_col.number_input(
        "FEV1 (L)", key="fev1", value=3.20,
        min_value=0.0, max_value=8.0, step=0.01, format="%.2f",
    )
    fvc = fvc_col.number_input(
        "FVC (L)", key="fvc", value=4.00,
        min_value=0.0, max_value=10.0, step=0.01, format="%.2f",
    )
    if fvc > 0:
        st.caption(f"FEV1/FVC ratio: {fev1 / fvc:.2f}")

    st.subheader("Reference equations", icon=":material/functions:")
    for _group, _label in GROUPS:
        st.pills(
            _label,
            [key for key, spec in EQUATIONS.items() if spec.group == _group],
            selection_mode="multi",
            format_func=lambda key: EQUATIONS[key].name,
            key=group_key(_group),
            on_change=keep_one_selected,
        )
    if st.session_state.get("selection_guard"):
        st.caption(GUARD_NOTE)

problem = input_problem(fev1, fvc)
inputs_ready = 0 < fev1 <= fvc
subject = Subject(age_years, height_cm, SEX_CODES[sex_label], fev1, fvc)

# One result or one message for each selected equation. An equation that
# rejects the inputs does not stop the others.
tables: dict = {}
interpretations: dict = {}
messages: dict = {}
if inputs_ready:
    for spec in specs:
        code = spec.ethnicities[ethnicity_labels[spec.key]] if spec.ethnicities else None
        try:
            table = compute_equation(spec.key, subject, code)
            interpretations[spec.key] = interpret_spirometry(table)
            tables[spec.key] = table
        except ValueError as error:
            messages[spec.key] = str(error)

# Chart input keyed by name, with None for an equation without a result.
named_tables = {spec.name: tables.get(spec.key) for spec in specs}
not_plotted = not_plotted_caption(named_tables)
both_gli = "gli_2012" in selection and "gli_2022" in selection

# Report export, built in memory when the inputs are usable.
with st.sidebar:
    st.subheader("Report", icon=":material/description:")
    report_html = ""
    if inputs_ready:
        report_chart = cross_family_chart_svg(named_tables)
        if not_plotted:
            report_chart += f"<p>{html_escape(not_plotted)}</p>"
        bundle = prepare_report_bundle(
            subject={
                "age_years": age_years, "height_cm": height_cm,
                "sex_label": sex_label,
                "ethnicity_gli_label": ethnicity_labels.get("gli_2012", "Not selected"),
                "ethnicity_nhanes3_label": ethnicity_labels.get("nhanes3", "Not selected"),
                "fev1": fev1, "fvc": fvc,
            },
            results=tables,
            interpretations=interpretations,
            chart_svg=report_chart,
            comparison_html=(
                render_gli_comparison(tables.get("gli_2012"), tables.get("gli_2022"))
                if both_gli else ""
            ),
        )
        report_html = render_report_html(bundle)
    st.download_button(
        "Download HTML report",
        data=report_html,
        file_name=f"quadrant-report-{datetime.now():%Y%m%d-%H%M%S}.html",
        mime="text/html",
        icon=":material/download:",
        type="primary",
        disabled=not inputs_ready,
        width="stretch",
    )
    st.caption("For a PDF, use the browser's Print menu on the downloaded file.")

# Main page. Numbers in tables line up in columns.
st.html("<style>td, th { font-variant-numeric: tabular-nums; }</style>")

st.title("Quadrant", icon=":material/explore:")
st.caption(
    "Spirometry reference values for one subject, compared across the "
    "selected reference equations."
)

if problem:
    st.warning(problem, icon=":material/warning:")

# 1. The answer first: what each equation says, and whether they agree.
st.subheader("Classification")
with st.container(border=True):
    for spec in specs:
        name_col, result_col = st.columns([1, 3], vertical_alignment="top")
        name_col.markdown(spec.name)
        with result_col:
            if spec.key in messages:
                st.warning(
                    messages[spec.key], title=NOT_AVAILABLE_TITLE,
                    icon=":material/block:",
                )
            elif spec.key in tables:
                st.badge(
                    pattern_label(interpretations[spec.key]),
                    color=badge_colour(interpretations[spec.key]),
                )
            else:
                st.caption("Enter values to classify.")
            if spec.caveat:
                st.caption(spec.caveat)
    summary = classification_summary(interpretations)
    if summary:
        st.markdown(summary)

# 2. Where each value sits against the references.
with st.container(border=True):
    st.subheader("Z-scores by equation")
    screen_chart = comparison_chart(named_tables)
    if screen_chart is not None:
        st.altair_chart(screen_chart, width="stretch", alt=CHART_ALT)
        if not_plotted:
            st.caption(not_plotted)
    elif inputs_ready:
        st.caption(not_plotted)
    else:
        st.caption("Enter values to draw the comparison chart.")
    if both_gli:
        notes = comparison_notes(tables.get("gli_2012"), tables.get("gli_2022"))
        if notes is None:
            st.caption("Enter values to compare the GLI equations.")
        elif not notes:
            st.caption(f"{AGREE_TEXT} {AGREE_NOTE}")
        else:
            st.markdown("Classification differs between the GLI equations for:")
            st.markdown("\n".join(f"- {note}" for note in notes))

# 3. The numbers behind it: one table for each parameter.
st.subheader("Reference values")
if tables:
    frames = matrix_frames({spec.name: tables.get(spec.key) for spec in specs})
    observed = {"FEV1": f"{fev1:.2f} L", "FVC": f"{fvc:.2f} L", "FEV1/FVC": f"{fev1 / fvc:.2f}"}
    for tab, (title, frame) in zip(st.tabs(list(frames)), frames.items()):
        with tab:
            st.caption(f"Observed {title}: {observed[title]}")
            st.table(
                markdown_cells(frame).reset_index(),
                hide_index=True,
                alt=f"{title} predicted value, lower limit, z-score and percent "
                "of predicted for each selected equation.",
            )
    st.caption(MATRIX_LEGEND)
elif inputs_ready:
    st.caption("No selected equation covers these inputs.")
else:
    st.caption("Enter values to compute results.")

with st.expander("Equation notes", icon=":material/menu_book:"):
    for spec in specs:
        low, high = spec.age_range
        st.markdown(spec.name)
        st.caption(
            f"{spec.citation}. {spec.population.rstrip('.')}. "
            f"Age range: {low:g} to {high:g} years."
        )
        if spec.caveat:
            st.caption(spec.caveat)

with st.expander("How to read this page", icon=":material/info:"):
    st.markdown(
        "A z-score places the observed value against the reference equation. "
        "The lower limit of normal (LLN) is a z-score of -1.645.\n\n"
        "Severity uses the FEV1 z-score: mild from -2.5 upward, moderate from "
        "-2.5 to -4.0, severe below -4.0.\n\n"
        "Restrictive and mixed patterns are suggestive only. Confirming them "
        "needs static lung volumes, which Quadrant does not accept.\n\n"
        "An equation without a lower limit gives no z-score, so its result "
        "is not classified."
    )

st.caption(DISCLAIMER_TEXT)
