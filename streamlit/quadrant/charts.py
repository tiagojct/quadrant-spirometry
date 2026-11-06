"""Interactive comparison chart for the Streamlit page.

The chart puts the FEV1, FVC and FEV1/FVC z-scores of every reference
family on one axis. Shaded bands show the severity levels, a dashed line
marks the lower limit of normal, and a tooltip on each marker gives the
observed, predicted and lower-limit values. The exported report keeps the
static SVG in visuals.py, because it must work as a standalone file.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from .constants import LLN_Z, SEVERITY_MILD_Z_MIN, SEVERITY_MODERATE_Z_MIN, SPIROMETRY_PARAMS

Z_AXIS_MIN = -5.0
Z_AXIS_MAX = 3.0

# An off-scale value is drawn this far inside the axis, so the marker is
# not cut in half. Its label and tooltip still show the real z-score.
EDGE_MARGIN = 0.15

PARAMETER_LABELS = {"FEV1": "FEV1", "FVC": "FVC", "FEV1FVC": "FEV1/FVC"}

# Marker colour and shape, in order of use. Every colour has a contrast
# of at least 3:1 on white, #fbf9f4 and #0d1522 (WCAG, checked in
# test_charts.py), e.g. #dc2626: 4.83, 4.59, 3.79; #64748b: 4.76, 4.52,
# 3.85; #4d7c0f: 4.99, 4.75, 3.67. The markers differ in shape too, so
# the chart stays readable without colour vision. Markers carry a white
# outline.
STYLES = (
    ("#2563eb", "circle"),
    ("#9333ea", "square"),
    ("#dc2626", "diamond"),
    ("#b45309", "triangle-up"),
    ("#0f766e", "triangle-down"),
    ("#64748b", "triangle-right"),
    ("#be185d", "triangle-left"),
    ("#4d7c0f", "cross"),
)

# Legend columns of the static SVG chart in the report (fixed width).
LEGEND_COLUMNS = 4

# Legend columns of the page chart. Vega legends do not wrap, so the
# legends keep two columns, which fit a 390 px phone screen.
CHART_LEGEND_COLUMNS = 2

# Chart height: a base plus one step for each plotted equation. Streamlit
# fits the legends and the axis (about 240 px) inside this height, so the
# base keeps three readable parameter rows for a single equation. The step
# also covers the extra legend row for every second equation.
CHART_BASE_HEIGHT = 340
CHART_EQUATION_HEIGHT = 60

# Z-score labels: dark text over a light halo, readable on every band in
# the light and the dark theme.
LABEL_COLOUR = "#0f172a"
LABEL_HALO = {"stroke": "#ffffff", "strokeWidth": 3, "strokeJoin": "round", "strokeOpacity": 0.85}


def style_for(index: int) -> tuple[str, str]:
    """Colour and shape for the equation at this position. Wraps after eight."""
    return STYLES[index % len(STYLES)]


# Severity bands from the lowest z-score up: lower bound, upper bound,
# legend label and colour.
BANDS = (
    (Z_AXIS_MIN, SEVERITY_MODERATE_Z_MIN, "Severe (below -4.0)", "#dc2626"),
    (SEVERITY_MODERATE_Z_MIN, SEVERITY_MILD_Z_MIN, "Moderate (-4.0 to -2.5)", "#f59e0b"),
    (SEVERITY_MILD_Z_MIN, LLN_Z, "Mild (-2.5 to LLN)", "#facc15"),
    (LLN_Z, Z_AXIS_MAX, "Normal (LLN and above)", "#4ade80"),
)

AXIS_TITLE = "z-score"

# Caption under the chart. The axis title stays short to fit a phone.
LLN_NOTE = "The dashed line marks the lower limit of normal (z = -1.645)."


def band_frame() -> pd.DataFrame:
    """One row for each severity band."""
    return pd.DataFrame(BANDS, columns=["z_lo", "z_hi", "band", "colour"])


def _has_finite_z(table) -> bool:
    return table is not None and bool(pd.to_numeric(table["z_score"], errors="coerce").notna().any())


def not_plotted_names(frames: dict) -> list[str]:
    """Names of equations that have a result but no finite z-score.

    An equation without a result (None) is left out: it rejected the
    inputs and the page shows its own message.
    """
    return [
        name for name, table in frames.items()
        if table is not None and not _has_finite_z(table)
    ]


def not_plotted_caption(frames: dict) -> str:
    """Short note under the chart, or an empty string when all are plotted."""
    names = not_plotted_names(frames)
    return f"Not plotted, no z-score: {', '.join(names)}" if names else ""


def points_frame(family_tables: dict) -> pd.DataFrame:
    """Long table with one row for each family and parameter.

    Families without a result and rows without a z-score are left out.
    z_plot is the z-score clamped to the axis, so an extreme value sits
    just inside the edge. The tooltip shows the real z-score.
    """
    rows = []
    for family, table in family_tables.items():
        if table is None:
            continue
        for row in table.itertuples(index=False):
            if pd.isna(row.z_score):
                continue
            rows.append(
                {
                    "family": family,
                    "parameter": PARAMETER_LABELS[row.parameter],
                    "z_score": float(row.z_score),
                    "z_plot": min(
                        max(float(row.z_score), Z_AXIS_MIN + EDGE_MARGIN),
                        Z_AXIS_MAX - EDGE_MARGIN,
                    ),
                    "z_text": f"{row.z_score:.2f}",
                    "observed": float(row.observed),
                    "predicted": float(row.predicted),
                    "lln": float(row.lln),
                    "percent_predicted": float(row.percent_predicted),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["family", "parameter", "z_score", "z_plot", "z_text", "observed",
                 "predicted", "lln", "percent_predicted"],
    )


def comparison_chart(family_tables: dict) -> alt.LayerChart | None:
    """Build the chart, or return None when no family has a result."""
    points = points_frame(family_tables)
    if points.empty:
        return None

    bands = band_frame()
    # The style follows the position in the input, so an equation keeps its
    # colour when another has no plotted point. An equation with only
    # missing z-scores is not plotted and has no legend entry.
    plotted = set(points["family"])
    styles = {name: style_for(i) for i, name in enumerate(family_tables)}
    families = [name for name in family_tables if name in plotted]
    parameters = [PARAMETER_LABELS[p] for p in SPIROMETRY_PARAMS]

    x_scale = alt.Scale(domain=[Z_AXIS_MIN, Z_AXIS_MAX], nice=False)
    x_axis = alt.Axis(
        title=AXIS_TITLE,
        values=list(range(int(Z_AXIS_MIN), int(Z_AXIS_MAX) + 1)),
        grid=False,
        labelFontSize=12,
        titleFontSize=12,
        titleFontWeight="normal",
    )

    band_layer = (
        alt.Chart(bands)
        .mark_rect(opacity=0.38)
        .encode(
            x=alt.X("z_lo:Q", scale=x_scale, axis=x_axis),
            x2="z_hi:Q",
            fill=alt.Fill(
                "band:N",
                scale=alt.Scale(domain=list(bands["band"]), range=list(bands["colour"])),
                legend=alt.Legend(
                    title="Severity band (FEV1 z-score)",
                    orient="bottom",
                    direction="horizontal",
                    columns=CHART_LEGEND_COLUMNS,
                    symbolOpacity=0.6,
                    labelFontSize=12,
                    titleFontSize=12,
                ),
            ),
        )
    )

    lln_layer = (
        alt.Chart(pd.DataFrame({"z": [LLN_Z]}))
        .mark_rule(strokeDash=[6, 4], strokeWidth=2, color="#94a3b8")
        .encode(x=alt.X("z:Q", scale=x_scale))
    )

    y = alt.Y(
        "parameter:N",
        sort=parameters,
        axis=alt.Axis(
            title=None, domain=False, ticks=False, labelFontSize=14,
            labelPadding=10, grid=True, tickBand="extent",
            gridColor="#94a3b8", gridOpacity=0.7, gridWidth=1.2,
        ),
        scale=alt.Scale(paddingInner=0, paddingOuter=0),
    )
    y_offset = alt.YOffset("family:N", sort=families)
    family_scale_colour = alt.Scale(
        domain=families, range=[styles[f][0] for f in families]
    )
    family_scale_shape = alt.Scale(
        domain=families, range=[styles[f][1] for f in families]
    )

    marker_layer = (
        alt.Chart(points)
        .mark_point(filled=True, size=200, opacity=1, stroke="white", strokeWidth=1.6)
        .encode(
            x=alt.X("z_plot:Q", scale=x_scale),
            y=y,
            yOffset=y_offset,
            color=alt.Color(
                "family:N",
                scale=family_scale_colour,
                legend=alt.Legend(
                    title="Reference equation",
                    orient="top",
                    direction="horizontal",
                    columns=CHART_LEGEND_COLUMNS,
                    labelFontSize=12,
                    titleFontSize=12,
                    symbolSize=160,
                ),
            ),
            shape=alt.Shape("family:N", scale=family_scale_shape, legend=None),
            tooltip=[
                alt.Tooltip("family:N", title="Equation"),
                alt.Tooltip("parameter:N", title="Parameter"),
                alt.Tooltip("z_score:Q", title="Z-score", format=".2f"),
                alt.Tooltip("observed:Q", title="Observed", format=".2f"),
                alt.Tooltip("predicted:Q", title="Predicted", format=".2f"),
                alt.Tooltip("lln:Q", title="LLN", format=".2f"),
                alt.Tooltip("percent_predicted:Q", title="% predicted", format=".1f"),
            ],
        )
    )

    label_encoding = {
        "x": alt.X("z_plot:Q", scale=x_scale),
        "y": y,
        "yOffset": y_offset,
        "text": "z_text:N",
    }
    halo_layer = (
        alt.Chart(points)
        .mark_text(align="left", dx=13, fontSize=12, **LABEL_HALO)
        .encode(**label_encoding)
    )
    label_layer = (
        alt.Chart(points)
        .mark_text(align="left", dx=13, fontSize=12, color=LABEL_COLOUR)
        .encode(**label_encoding)
    )

    return (
        alt.layer(band_layer, lln_layer, halo_layer, label_layer, marker_layer)
        .resolve_scale(color="independent", fill="independent", shape="independent")
        .properties(height=CHART_BASE_HEIGHT + CHART_EQUATION_HEIGHT * len(families))
        .configure_view(stroke=None)
        .configure_legend(padding=6)
    )
