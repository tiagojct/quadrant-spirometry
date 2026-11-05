"""Quadrant: spirometry reference value calculator (Streamlit port).

License: AGPL-3.0-or-later

Run with: uv run streamlit run app.py

The app keeps no state between sessions and writes nothing to disk.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from quadrant.constants import (
    DISCLAIMER_TEXT,
    GLI_AGE_RANGE_YEARS,
    GLI_ETHNICITY,
    HEIGHT_RANGE_CM,
    NHANES3_ETHNICITY,
    SEX_CODES,
)
from quadrant.fragments import (
    input_notice,
    render_gli_comparison,
    render_interpretation,
    render_pattern_badge,
    render_reference_table,
)
from quadrant.interpretation import interpret_spirometry
from quadrant.report import prepare_report_bundle, render_report_html
from quadrant.styles import COMPONENT_CSS
from quadrant.visuals import cross_family_chart_svg, is_svg
from quadrant.wrappers import compute_gli_2012, compute_gli_global_2022, compute_nhanes3

st.set_page_config(page_title="Quadrant", layout="wide")
st.markdown(f"<style>{COMPONENT_CSS}</style>", unsafe_allow_html=True)


def compute_family(function, **kwargs):
    """Return (table, None) on success or (None, message) on failure."""
    try:
        return function(**kwargs), None
    except ValueError as error:
        return None, str(error)


# Sidebar inputs. Each widget has a key so that the tests can set it.
with st.sidebar:
    st.header("Inputs")
    age_years = st.number_input(
        "Age (years)", key="age_years", value=40.0,
        min_value=float(GLI_AGE_RANGE_YEARS[0]),
        max_value=float(GLI_AGE_RANGE_YEARS[1]), step=1.0,
    )
    height_cm = st.number_input(
        "Height (cm)", key="height_cm", value=170.0,
        min_value=float(HEIGHT_RANGE_CM[0]),
        max_value=float(HEIGHT_RANGE_CM[1]), step=0.5,
    )
    sex_label = st.selectbox("Sex", list(SEX_CODES), key="sex")
    ethnicity_gli_label = st.selectbox(
        "Ethnicity (GLI-2012)", list(GLI_ETHNICITY), key="ethnicity_gli"
    )
    ethnicity_nhanes3_label = st.selectbox(
        "Ethnicity (NHANES III)", list(NHANES3_ETHNICITY), key="ethnicity_nhanes3"
    )
    fev1 = st.number_input(
        "Observed FEV1 (L)", key="fev1", value=3.20,
        min_value=0.0, max_value=8.0, step=0.01, format="%.2f",
    )
    fvc = st.number_input(
        "Observed FVC (L)", key="fvc", value=4.00,
        min_value=0.0, max_value=10.0, step=0.01, format="%.2f",
    )

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

# Report export, built in memory when the inputs are usable.
with st.sidebar:
    st.divider()
    st.subheader("Report")
    report_html = ""
    if inputs_ready:
        chart_svg = cross_family_chart_svg(
            {
                "GLI-2012": results["gli_2012"],
                "GLI-Global 2022": results["gli_2022"],
                "NHANES III": results["nhanes3"],
            }
        )
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
            chart_svg=chart_svg,
            comparison_html=render_gli_comparison(results["gli_2012"], results["gli_2022"]),
        )
        report_html = render_report_html(bundle)
    st.download_button(
        "Download HTML report",
        data=report_html,
        file_name=f"quadrant-report-{datetime.now():%Y%m%d-%H%M%S}.html",
        mime="text/html",
        disabled=not inputs_ready,
        use_container_width=True,
    )
    st.caption("PDF: use the browser's Print menu on the downloaded HTML.")

st.title("Quadrant")

notice = input_notice(fev1, fvc)
if notice:
    st.html(notice)

with st.container(border=True):
    st.subheader("Cross-family z-score comparison")
    chart = cross_family_chart_svg(
        {
            "GLI-2012": results["gli_2012"],
            "GLI-Global 2022": results["gli_2022"],
            "NHANES III": results["nhanes3"],
        }
    )
    if is_svg(chart):
        # st.html strips SVG, so the chart goes through st.image.
        st.image(chart, use_container_width=True)
    else:
        st.html(chart)
    st.html(render_gli_comparison(results["gli_2012"], results["gli_2022"]))

CARDS = (
    ("gli_2012", "GLI-2012", "Quanjer et al., ERJ 2012"),
    ("gli_2022", "GLI-Global 2022", "Race-neutral. Bowerman et al., AJRCCM 2023"),
    ("nhanes3", "NHANES III", "Hankinson et al., AJRCCM 1999"),
)
for column, (key, title, subtitle) in zip(st.columns(3), CARDS):
    with column, st.container(border=True):
        st.subheader(title)
        st.html(f'<p class="qd-muted">{subtitle}</p>')
        if messages[key] is None:
            st.html(render_pattern_badge(interpretations[key]))
        st.html(render_reference_table(results[key], messages[key]))
        if messages[key] is None:
            st.divider()
            st.html(render_interpretation(interpretations[key]))

st.divider()
st.caption(DISCLAIMER_TEXT)
