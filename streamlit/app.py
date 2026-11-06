"""Quadrant: spirometry reference value calculator (Streamlit port).

License: AGPL-3.0-or-later

Run with: uv run streamlit run app.py

The app keeps no state between sessions and writes nothing to disk.
Session state holds only the current inputs, the chosen equations and,
after "Pin these results", the pinned z-scores with a short summary of
the pinned inputs.
Colours and fonts come from .streamlit/config.toml.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from quadrant.charts import LLN_NOTE, comparison_chart, not_plotted_caption
from quadrant.constants import (
    DISCLAIMER_TEXT,
    GLI_AGE_RANGE_YEARS,
    HEIGHT_RANGE_CM,
    SEX_CODES,
)
from quadrant.fragments import (
    AGREE_NOTE,
    AGREE_TEXT,
    DIFFER_HEADING,
    MISSING_VALUE_TEXT,
    badge_colour,
    classification_summary,
    comparison_notes,
    input_problem,
    pattern_label,
)
from quadrant.interpretation import interpret_spirometry
from quadrant.matrix import MATRIX_LEGEND, markdown_cells, matrix_frames
from quadrant.presets import DELTA_COLUMN, PRESETS, delta_frame, pinned_tables
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
    """Pills callback: put the previous choice back when none is left.

    It sets a one-run flag, so the note shows only on the run that follows
    the callback.
    """
    if selected_keys():
        return
    previous = st.session_state.get("previous_selection") or list(DEFAULT_KEYS)
    for group, _ in GROUPS:
        st.session_state[group_key(group)] = [
            key for key in previous if EQUATIONS[key].group == group
        ]
    st.session_state["selection_guard"] = True


# Example inputs. The selector writes the input keys in a callback, so
# the values are in place before the widgets are drawn. Editing an input
# afterwards puts the selector back to "Custom values" and is not undone.
CUSTOM = "custom"
PRESET_KEYS = (CUSTOM, *PRESETS)
SEX_LABELS = {code: label for label, code in SEX_CODES.items()}
INPUT_DEFAULTS = {
    "age_years": 40.0, "height_cm": 170.0, "sex": "Male", "fev1": 3.20, "fvc": 4.00,
}


def preset_label(key: str) -> str:
    return "Custom values" if key == CUSTOM else PRESETS[key].label


def apply_preset() -> None:
    """Selector callback: write the example values in the input keys."""
    key = st.session_state.get("preset", CUSTOM)
    if key == CUSTOM:
        return
    preset = PRESETS[key]
    st.session_state["age_years"] = preset.age_years
    st.session_state["height_cm"] = preset.height_cm
    st.session_state["sex"] = SEX_LABELS[preset.sex_code]
    st.session_state["fev1"] = preset.fev1
    st.session_state["fvc"] = preset.fvc


def mark_custom() -> None:
    """Input callback: an edited value is no longer the example."""
    st.session_state["preset"] = CUSTOM


def request_pin() -> None:
    """Pin button callback. The pin is taken later in the run, from the
    results of the current inputs."""
    st.session_state["pin_requested"] = True


def clear_pin() -> None:
    st.session_state.pop("pin", None)


# The inputs get their start values here, not through value= or
# default=, so that the callbacks can set them without a conflict.
for _key, _value in INPUT_DEFAULTS.items():
    st.session_state.setdefault(_key, _value)
st.session_state.setdefault("preset", CUSTOM)

# The pills start at the default equations. Callbacks run before this
# line, so the selection read here is the current one.
for _group, _ in GROUPS:
    st.session_state.setdefault(
        group_key(_group),
        [key for key in DEFAULT_KEYS if EQUATIONS[key].group == _group],
    )
# The guard flag lives for one run only: an unrelated change clears it.
show_guard_note = st.session_state.pop("selection_guard", False)
selection = selected_keys() or list(DEFAULT_KEYS)
st.session_state["previous_selection"] = selection
specs = [EQUATIONS[key] for key in selection]


# Sidebar inputs. Each widget has a key so that the tests can set it.
with st.sidebar:
    st.selectbox(
        "Example inputs", PRESET_KEYS, format_func=preset_label,
        key="preset", on_change=apply_preset,
    )
    st.caption("The examples are synthetic values for trying the app. They are not patient data.")
    st.subheader("Subject", icon=":material/person:")
    age_col, height_col = st.columns(2)
    age_years = age_col.number_input(
        "Age (years)", key="age_years", on_change=mark_custom,
        min_value=float(GLI_AGE_RANGE_YEARS[0]),
        max_value=float(GLI_AGE_RANGE_YEARS[1]), step=1.0,
        help="Each equation covers its own age range. See the equation notes.",
    )
    height_cm = height_col.number_input(
        "Height (cm)", key="height_cm", on_change=mark_custom,
        min_value=float(HEIGHT_RANGE_CM[0]),
        max_value=float(HEIGHT_RANGE_CM[1]), step=0.5,
    )
    sex_label = st.segmented_control(
        "Sex", list(SEX_CODES), required=True,
        key="sex", width="stretch", on_change=mark_custom,
    )
    # One ethnicity selector for each selected equation that uses one.
    # Streamlit drops the value of a widget that is not drawn, so the choice
    # is also kept under a second key and put back when the equation is
    # selected again.
    ethnicity_labels = {}
    for spec in specs:
        if not spec.ethnicities:
            continue
        widget_key, kept_key = f"ethnicity_{spec.key}", f"kept_ethnicity_{spec.key}"
        if widget_key not in st.session_state and kept_key in st.session_state:
            st.session_state[widget_key] = st.session_state[kept_key]
        ethnicity_labels[spec.key] = st.selectbox(
            f"Ethnicity ({spec.name})", list(spec.ethnicities), key=widget_key,
        )
        st.session_state[kept_key] = ethnicity_labels[spec.key]

    st.subheader("Spirometry", icon=":material/air:")
    fev1_col, fvc_col = st.columns(2)
    fev1 = fev1_col.number_input(
        "FEV1 (L)", key="fev1", on_change=mark_custom,
        min_value=0.0, max_value=8.0, step=0.01, format="%.2f",
    )
    fvc = fvc_col.number_input(
        "FVC (L)", key="fvc", on_change=mark_custom,
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
    if show_guard_note:
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

# What-if pin: only the z-scores of each equation with a result, keyed by
# registry key, and a short summary of the inputs for the caption.
if st.session_state.pop("pin_requested", False) and tables:
    summary = (
        f"age {age_years:g} years, height {height_cm:g} cm, {sex_label.lower()}, "
        f"FEV1 {fev1:.2f} L, FVC {fvc:.2f} L"
    )
    summary += "".join(
        f", {EQUATIONS[key].name} ethnicity {label}"
        for key, label in ethnicity_labels.items()
    )
    st.session_state["pin"] = {
        "z_scores": {
            key: {p: float(z) for p, z in zip(table["parameter"], table["z_score"])}
            for key, table in tables.items()
        },
        "inputs": summary,
    }
pin = st.session_state.get("pin")

# Chart input keyed by name, with None for an equation without a result.
named_tables = {spec.name: tables.get(spec.key) for spec in specs}
not_plotted = not_plotted_caption(named_tables)
both_gli = "gli_2012" in selection and "gli_2022" in selection

# Report export, built in memory when the inputs are usable.
with st.sidebar:
    st.subheader("Report", icon=":material/description:")
    report_html = ""
    if inputs_ready:
        # Every selected equation is in the report: a rejected one with its
        # message. The pinned what-if values are not part of the report.
        bundle = prepare_report_bundle(
            subject={
                "age_years": age_years, "height_cm": height_cm,
                "sex_label": sex_label, "fev1": fev1, "fvc": fvc,
                "ethnicities": dict(ethnicity_labels),
            },
            equations=selection,
            results={**tables, **messages},
            interpretations=interpretations,
            chart_svg=cross_family_chart_svg(named_tables),
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
# Rows are further apart than the name and the badge inside a row, so on a
# phone, where the columns stack, each name still reads with its badge.
with st.container(border=True, gap="medium"):
    for spec in specs:
        name_col, result_col = st.columns([1, 3], gap="xsmall", vertical_alignment="top")
        name_col.markdown(spec.name)
        with result_col.container(gap="xsmall"):
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
        st.caption(LLN_NOTE)
        if not_plotted:
            st.caption(not_plotted)
    elif inputs_ready:
        st.caption(not_plotted or "No selected equation covers these inputs.")
    else:
        st.caption("Enter values to draw the comparison chart.")
    if both_gli:
        notes = comparison_notes(tables.get("gli_2012"), tables.get("gli_2022"))
        if notes is None:
            st.caption("Enter values to compare the GLI equations.")
        elif not notes:
            st.caption(f"{AGREE_TEXT} {AGREE_NOTE}")
        else:
            st.markdown(DIFFER_HEADING)
            st.markdown("\n".join(f"- {note}" for note in notes))

# 3. The numbers behind it: one table for each parameter.
st.subheader("Reference values")
with st.container(horizontal=True):
    st.button(
        "Pin these results", key="pin_button", icon=":material/push_pin:",
        on_click=request_pin, disabled=not tables,
        help="Keep the current z-scores, then change a value to see the change in z.",
    )
    st.button(
        "Clear pin", key="clear_pin", icon=":material/close:",
        on_click=clear_pin, disabled=pin is None,
    )
if tables:
    named_current = {spec.name: tables.get(spec.key) for spec in specs}
    frames = matrix_frames(named_current)
    if pin is not None:
        named_pinned = {
            EQUATIONS[key].name: table
            for key, table in pinned_tables(pin["z_scores"]).items()
        }
        deltas = delta_frame(named_current, named_pinned)
        frames = {
            title: frame.join(deltas[title]).fillna(MISSING_VALUE_TEXT)
            for title, frame in frames.items()
        }
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
    if pin is not None:
        st.caption(
            f"Compared with the pinned values: {pin['inputs']}. {DELTA_COLUMN} is "
            "the current z-score minus the pinned z-score. A hyphen in that "
            "column means that one of the two z-scores is missing or the "
            "equation was not pinned."
        )
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
