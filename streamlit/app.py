"""Quadrant: spirometry reference value calculator (Streamlit port).

License: AGPL-3.0-or-later

Run with: uv run streamlit run app.py

The app keeps no state between sessions and writes nothing to disk.
Colours and fonts come from .streamlit/config.toml.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from quadrant.constants import (
    DISCLAIMER_TEXT,
    GLI_AGE_RANGE_YEARS,
    GLI_ETHNICITY,
    HEIGHT_RANGE_CM,
    LLN_Z,
    NHANES3_ETHNICITY,
    SEX_CODES,
)
from quadrant.fragments import (
    AGREE_NOTE,
    AGREE_TEXT,
    BELOW_LLN_NOTE,
    badge_colour,
    comparison_notes,
    input_problem,
    pattern_label,
    render_gli_comparison,
    results_for_display,
)
from quadrant.interpretation import interpret_spirometry
from quadrant.report import prepare_report_bundle, render_report_html
from quadrant.visuals import cross_family_chart_svg, is_svg
from quadrant.wrappers import compute_gli_2012, compute_gli_global_2022, compute_nhanes3

st.set_page_config(
    page_title="Quadrant",
    page_icon=":material/explore:",
    layout="wide",
)

CHART_ALT = (
    "Chart of the FEV1, FVC and FEV1/FVC z-scores for each reference "
    "equation family, on one axis with the lower limit of normal marked "
    "at -1.645 and the severity bands shaded."
)


def compute_family(function, **kwargs):
    """Return (table, None) on success or (None, message) on failure."""
    try:
        return function(**kwargs), None
    except ValueError as error:
        return None, str(error)


# Sidebar inputs. Each widget has a key so that the tests can set it.
with st.sidebar:
    st.subheader("Subject", icon=":material/person:")
    age_col, height_col = st.columns(2)
    age_years = age_col.number_input(
        "Age (years)", key="age_years", value=40.0,
        min_value=float(GLI_AGE_RANGE_YEARS[0]),
        max_value=float(GLI_AGE_RANGE_YEARS[1]), step=1.0,
        help="GLI equations cover 3 to 95 years. NHANES III covers 8 to 80 years.",
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
    ethnicity_gli_label = st.selectbox(
        "Ethnicity (GLI-2012)", list(GLI_ETHNICITY), key="ethnicity_gli"
    )
    ethnicity_nhanes3_label = st.selectbox(
        "Ethnicity (NHANES III)", list(NHANES3_ETHNICITY), key="ethnicity_nhanes3",
        help="NHANES III has three categories. GLI-Global 2022 has none.",
    )

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

problem = input_problem(fev1, fvc)
inputs_ready = 0 < fev1 <= fvc
sex_code = SEX_CODES[sex_label]

calc = {"gli_2012": (None, None), "gli_2022": (None, None), "nhanes3": (None, None)}
if inputs_ready:
    calc["gli_2012"] = compute_family(
        compute_gli_2012, age_years=age_years, height_cm=height_cm,
        sex_code=sex_code, ethnicity_code=GLI_ETHNICITY[ethnicity_gli_label],
        fev1=fev1, fvc=fvc,
    )
    calc["gli_2022"] = compute_family(
        compute_gli_global_2022, age_years=age_years, height_cm=height_cm,
        sex_code=sex_code, fev1=fev1, fvc=fvc,
    )
    calc["nhanes3"] = compute_family(
        compute_nhanes3, age_years=age_years, height_cm=height_cm,
        sex_code=sex_code, ethnicity_code=NHANES3_ETHNICITY[ethnicity_nhanes3_label],
        fev1=fev1, fvc=fvc,
    )

results = {key: table for key, (table, _) in calc.items()}
messages = {key: message for key, (_, message) in calc.items()}
interpretations = {
    key: interpret_spirometry(table) if table is not None else None
    for key, table in results.items()
}
chart = cross_family_chart_svg(
    {
        "GLI-2012": results["gli_2012"],
        "GLI-Global 2022": results["gli_2022"],
        "NHANES III": results["nhanes3"],
    }
)

# Report export, built in memory when the inputs are usable.
with st.sidebar:
    st.subheader("Report", icon=":material/description:")
    report_html = ""
    if inputs_ready:
        bundle = prepare_report_bundle(
            subject={
                "age_years": age_years, "height_cm": height_cm,
                "sex_label": sex_label,
                "ethnicity_gli_label": ethnicity_gli_label,
                "ethnicity_nhanes3_label": ethnicity_nhanes3_label,
                "fev1": fev1, "fvc": fvc,
            },
            results=results,
            interpretations=interpretations,
            chart_svg=chart,
            comparison_html=render_gli_comparison(results["gli_2012"], results["gli_2022"]),
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

# Main page.
st.title("Quadrant", icon=":material/explore:")
st.caption(
    "Spirometry reference values for one subject, compared across three "
    "equation families."
)

if problem:
    st.warning(problem, icon=":material/warning:")

with st.container(border=True):
    st.subheader("Cross-family z-score comparison", icon=":material/query_stats:")
    if is_svg(chart):
        # st.html strips SVG, so the chart goes through st.image.
        st.image(chart, width="stretch", alt=CHART_ALT)
    else:
        st.caption("Enter values to draw the comparison chart.")
    notes = comparison_notes(results["gli_2012"], results["gli_2022"])
    if notes is None:
        st.caption("Enter values to compare equations.")
    elif not notes:
        st.markdown(AGREE_TEXT)
        st.caption(AGREE_NOTE)
    else:
        st.markdown("Classification differs for:")
        st.markdown("\n".join(f"- {note}" for note in notes))

CARDS = (
    ("gli_2012", "GLI-2012", "Quanjer et al., ERJ 2012"),
    ("gli_2022", "GLI-Global 2022", "Race-neutral. Bowerman et al., AJRCCM 2023"),
    ("nhanes3", "NHANES III", "Hankinson et al., AJRCCM 1999"),
)
for column, (key, title, subtitle) in zip(st.columns(3), CARDS):
    with column, st.container(border=True):
        st.subheader(title)
        st.caption(subtitle)
        if messages[key] is not None:
            st.warning(
                messages[key],
                title="Not available for these inputs",
                icon=":material/block:",
            )
        elif results[key] is None:
            st.caption("Enter values to compute results.")
        else:
            interpretation = interpretations[key]
            st.badge(
                pattern_label(interpretation),
                color=badge_colour(interpretation),
                width="stretch",
            )
            st.table(
                results_for_display(results[key]),
                hide_index=True,
                alt=f"{title} reference values for FEV1, FVC and FEV1/FVC.",
            )
            if (results[key]["z_score"] < LLN_Z).any():
                st.caption(BELOW_LLN_NOTE)
            severity = interpretation["severity"]
            st.markdown(f"Pattern: {interpretation['pattern']}")
            st.markdown(
                "Severity: not graded (pattern is normal)"
                if severity is None
                else f"Severity (by FEV1 z-score): {severity}"
            )

with st.expander("How to read this page", icon=":material/info:"):
    st.markdown(
        "A z-score places the observed value against the reference equation. "
        "The lower limit of normal (LLN) is a z-score of -1.645.\n\n"
        "Severity uses the FEV1 z-score: mild from -2.5 upward, moderate from "
        "-2.5 to -4.0, severe below -4.0.\n\n"
        "Restrictive and mixed patterns are suggestive only. Confirming them "
        "needs static lung volumes, which Quadrant does not accept."
    )

st.caption(DISCLAIMER_TEXT)
