"""Inline SVG renderers for the cross-family comparison chart.

Pure functions that return HTML strings. SVG is emitted as plain text,
so no plotting library is needed. Ported from R/visuals.R.
"""

from __future__ import annotations

from html import escape
from math import isnan

from .constants import (
    LLN_Z,
    SEVERITY_MILD_Z_MIN,
    SEVERITY_MODERATE_Z_MIN,
    SPIROMETRY_PARAMS,
)
from .charts import LEGEND_COLUMNS, PARAMETER_LABELS, _has_finite_z, style_for

Z_AXIS_MIN = -5
Z_AXIS_MAX = 3

# Severity bands in ascending z-score order: lower bound, upper bound,
# fill colour and label.
SEVERITY_BANDS = (
    {"z_lo": Z_AXIS_MIN, "z_hi": SEVERITY_MODERATE_Z_MIN, "fill": "#dc2626", "label": "severe"},
    {"z_lo": SEVERITY_MODERATE_Z_MIN, "z_hi": SEVERITY_MILD_Z_MIN, "fill": "#f59e0b", "label": "moderate"},
    {"z_lo": SEVERITY_MILD_Z_MIN, "z_hi": LLN_Z, "fill": "#facc15", "label": "mild"},
    {"z_lo": LLN_Z, "z_hi": Z_AXIS_MAX, "fill": "#86efac", "label": "normal"},
)

def z_to_x(z: float, pad_left: float, plot_width: float) -> float:
    """Map a z-score to an SVG x coordinate, clamped to the axis range."""
    clamped = max(min(z, Z_AXIS_MAX), Z_AXIS_MIN)
    fraction = (clamped - Z_AXIS_MIN) / (Z_AXIS_MAX - Z_AXIS_MIN)
    return pad_left + fraction * plot_width


def severity_bands_svg(
    y: float, height: float, pad_left: float, plot_width: float,
    band_opacity: float = 0.55,
) -> str:
    """Severity bands plus the dashed LLN line for one strip."""
    parts = []
    for band in SEVERITY_BANDS:
        x1 = z_to_x(band["z_lo"], pad_left, plot_width)
        x2 = z_to_x(band["z_hi"], pad_left, plot_width)
        parts.append(
            f'<rect x="{x1:.2f}" y="{y:.2f}" width="{x2 - x1:.2f}" '
            f'height="{height:.2f}" fill="{band["fill"]}" '
            f'fill-opacity="{band_opacity:.2f}" />'
        )
    lln_x = z_to_x(LLN_Z, pad_left, plot_width)
    parts.append(
        f'<line x1="{lln_x:.2f}" y1="{y:.2f}" x2="{lln_x:.2f}" '
        f'y2="{y + height:.2f}" stroke="#1f2937" stroke-width="1.2" '
        'stroke-dasharray="4,3" />'
    )
    return "".join(parts)


def z_axis_svg(y: float, pad_left: float, plot_width: float, font_size: int = 10) -> str:
    """Labelled axis ticks at integer z values plus an LLN label."""
    parts = []
    for z in range(Z_AXIS_MIN, Z_AXIS_MAX + 1):
        x = z_to_x(z, pad_left, plot_width)
        parts.append(
            f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x:.2f}" y2="{y + 4:.2f}" '
            'stroke="#94a3b8" stroke-width="1" />'
            f'<text x="{x:.2f}" y="{y + 4 + font_size + 2:.2f}" '
            f'font-size="{font_size}" text-anchor="middle" fill="#475569">{z}</text>'
        )
    lln_x = z_to_x(LLN_Z, pad_left, plot_width)
    parts.append(
        f'<text x="{lln_x:.2f}" y="{y - 4:.2f}" font-size="{font_size - 1}" '
        'text-anchor="middle" fill="#1f2937" font-style="italic">LLN</text>'
    )
    return "".join(parts)


def severity_legend_svg(y: float, pad_left: float, plot_width: float, font_size: int = 12) -> str:
    """Horizontal legend strip: one swatch and label per severity band."""
    step = plot_width / len(SEVERITY_BANDS)
    parts = []
    for i, band in enumerate(SEVERITY_BANDS):
        x_start = pad_left + i * step
        parts.append(
            f'<rect x="{x_start:.2f}" y="{y - 11:.2f}" width="14" height="14" '
            f'rx="3" fill="{band["fill"]}" fill-opacity="0.85" />'
            f'<text x="{x_start + 19:.2f}" y="{y:.2f}" font-size="{font_size}" '
            f'text-anchor="start" fill="#0f172a" font-weight="600">{band["label"]}</text>'
        )
    return "".join(parts)


def marker_svg(shape: str, cx: float, cy: float, r: float, colour: str, css_class: str) -> str:
    """One marker. The shape names follow the Vega shape names in charts.py."""
    common = f'class="{css_class}" fill="{colour}" stroke="white" stroke-width="2"'
    if shape == "circle":
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" {common} />'
    if shape == "square":
        return (f'<rect x="{cx - r:.2f}" y="{cy - r:.2f}" width="{2 * r:.2f}" '
                f'height="{2 * r:.2f}" {common} />')
    points = {
        "diamond": [(0, -1.25), (1.25, 0), (0, 1.25), (-1.25, 0)],
        "triangle-up": [(0, -1.2), (1.1, 0.9), (-1.1, 0.9)],
        "triangle-down": [(0, 1.2), (1.1, -0.9), (-1.1, -0.9)],
        "triangle-right": [(1.2, 0), (-0.9, 1.1), (-0.9, -1.1)],
        "triangle-left": [(-1.2, 0), (0.9, 1.1), (0.9, -1.1)],
        "cross": [(-0.4, -1.2), (0.4, -1.2), (0.4, -0.4), (1.2, -0.4), (1.2, 0.4),
                  (0.4, 0.4), (0.4, 1.2), (-0.4, 1.2), (-0.4, 0.4), (-1.2, 0.4),
                  (-1.2, -0.4), (-0.4, -0.4)],
    }[shape]
    coords = " ".join(f"{cx + x * r:.2f},{cy + y * r:.2f}" for x, y in points)
    return f'<polygon points="{coords}" {common} />'


def _has_z(df, parameter: str) -> float | None:
    z_values = df.loc[df["parameter"] == parameter, "z_score"]
    if z_values.empty or isnan(float(z_values.iloc[0])):
        return None
    return float(z_values.iloc[0])


def cross_family_chart_svg(family_tables: dict) -> str:
    """SVG chart with the three parameters on a shared z-axis.

    family_tables maps an equation name to its long-form table, or to None
    when the equation has no result. Equations without a result are left
    out, and so is a parameter with a missing z-score. The legend wraps
    after four entries. Returns a bare <svg> string, or an HTML prompt
    when no equation has a result. Use is_svg() to tell them apart.
    """
    styles = {name: style_for(i) for i, name in enumerate(family_tables)}
    active = {name: df for name, df in family_tables.items() if _has_finite_z(df)}
    if not active:
        return "<em>Enter values to render the comparison chart.</em>"

    n_equations = len(active)
    total_width = 1100
    pad_left, pad_right = 110, 20
    plot_width = total_width - pad_left - pad_right
    # Each equation needs its own lane inside a parameter strip.
    row_height, row_gap, top_pad = max(56, 18 * n_equations + 8), 14, 36

    band_labels = severity_legend_svg(top_pad - 14, pad_left, plot_width, font_size=13)

    rows = []
    for i, parameter in enumerate(SPIROMETRY_PARAMS):
        y = top_pad + i * (row_height + row_gap)
        bands = severity_bands_svg(y, row_height, pad_left, plot_width, band_opacity=0.6)
        label = (
            f'<text x="{pad_left - 12:.2f}" y="{y + row_height / 2 + 6:.2f}" '
            'font-size="16" text-anchor="end" fill="#0f172a" '
            f'font-weight="700">{PARAMETER_LABELS[parameter]}</text>'
        )
        markers = []
        for j, (family, df) in enumerate(active.items()):
            z = _has_z(df, parameter)
            if z is None:
                continue
            colour, shape = styles[family]
            cx = z_to_x(z, pad_left, plot_width)
            cy = y + (j + 0.5) * (row_height / n_equations)
            markers.append(
                marker_svg(shape, cx, cy, 7, colour, "marker")
                + f'<text x="{cx + 13:.2f}" y="{cy + 4:.2f}" font-size="12" '
                f'text-anchor="start" fill="#0f172a" font-weight="700">{z:.2f}</text>'
            )
        rows.append(bands + label + "".join(markers))

    axis_y = top_pad + len(SPIROMETRY_PARAMS) * (row_height + row_gap) + 6
    axis = z_axis_svg(axis_y, pad_left, plot_width, font_size=13)
    axis_label = (
        f'<text x="{pad_left - 12:.2f}" y="{axis_y + 16:.2f}" font-size="13" '
        'text-anchor="end" fill="#475569">z-score</text>'
    )

    legend_y = axis_y + 44
    legend_step = plot_width / LEGEND_COLUMNS
    legend = []
    for k, family in enumerate(active):
        colour, shape = styles[family]
        legend_x = pad_left + (k % LEGEND_COLUMNS) * legend_step
        row_y = legend_y + (k // LEGEND_COLUMNS) * 26
        legend.append(
            marker_svg(shape, legend_x, row_y, 6, colour, "legend-marker")
            + f'<text x="{legend_x + 14:.2f}" y="{row_y + 5:.2f}" font-size="13" '
            f'fill="#1f2937" font-weight="600">{escape(family)}</text>'
        )
    legend_rows = (n_equations - 1) // LEGEND_COLUMNS + 1
    total_height = legend_y + (legend_rows - 1) * 26 + 24

    # The white background keeps the dark labels readable on dark themes.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height:.0f}" '
        'style="display:block;width:100%;height:auto;'
        'font-family:system-ui,-apple-system,sans-serif;" role="img" '
        'aria-label="cross-family z-score comparison">'
        '<rect width="100%" height="100%" fill="#ffffff" />'
        f'{band_labels}{"".join(rows)}{axis}{axis_label}{"".join(legend)}'
        "</svg>"
    )


def is_svg(markup: str) -> bool:
    """True when the chart function returned an SVG and not the prompt."""
    return markup.startswith("<svg")
