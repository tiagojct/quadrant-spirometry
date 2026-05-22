# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: visuals
# Purpose: Inline SVG renderers for the cross-family comparison chart
# and the per-family mini-gauge. Pure functions returning HTML strings
# (wrapped in shiny::HTML by the UI). No new R dependencies: SVG is
# emitted as plain text so the app continues to rely only on shiny,
# bslib, rspiro, and testthat.

#' Z-score axis range used by every visual.
#' @keywords internal
Z_AXIS_MIN <- -5
Z_AXIS_MAX <-  3

#' Z-score boundary used as the lower limit of normal.
#' @keywords internal
LLN_Z_VISUAL <- -1.645

#' Severity band definitions, in ascending z-score order. Each entry
#' carries the lower z bound, upper z bound, fill colour, and the
#' label shown in the top axis of the comparison chart. Labels are
#' lower-case to match the wording used in the interpretation block.
#' @keywords internal
SEVERITY_BANDS <- list(
  list(z_lo = Z_AXIS_MIN,  z_hi = -4.0,         fill = "#b91c1c", label = "very severe"),
  list(z_lo = -4.0,        z_hi = -3.0,         fill = "#dc2626", label = "severe"),
  list(z_lo = -3.0,        z_hi = -2.5,         fill = "#ea580c", label = "moderately severe"),
  list(z_lo = -2.5,        z_hi = -2.0,         fill = "#f59e0b", label = "moderate"),
  list(z_lo = -2.0,        z_hi = LLN_Z_VISUAL, fill = "#facc15", label = "mild"),
  list(z_lo = LLN_Z_VISUAL, z_hi = Z_AXIS_MAX,  fill = "#86efac", label = "normal")
)

#' Marker colours per reference equation family.
#' @keywords internal
FAMILY_COLOURS <- c(
  "GLI-2012"        = "#1e3a8a",
  "GLI-Global 2022" = "#7c2d12",
  "NHANES III"      = "#0f172a"
)

#' Map a z-score to an SVG x coordinate.
#'
#' Linear, clamped to the axis range so an extreme z-score sits at the
#' edge of the gauge instead of escaping the SVG view box.
#' @keywords internal
z_to_x <- function(z, pad_left, plot_width) {
  z_clamped <- max(min(z, Z_AXIS_MAX), Z_AXIS_MIN)
  fraction <- (z_clamped - Z_AXIS_MIN) / (Z_AXIS_MAX - Z_AXIS_MIN)
  pad_left + fraction * plot_width
}

#' Severity bands plus the dashed LLN line for a single strip.
#'
#' Returns one rect per band and a dashed vertical line at z = LLN.
#' Bands use a moderate fill opacity so the markers on top remain
#' readable.
#' @keywords internal
severity_bands_svg <- function(y, height, pad_left, plot_width, band_opacity = 0.55) {
  rects <- vapply(SEVERITY_BANDS, function(b) {
    x1 <- z_to_x(b$z_lo, pad_left, plot_width)
    x2 <- z_to_x(b$z_hi, pad_left, plot_width)
    sprintf(
      '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" fill-opacity="%.2f" />',
      x1, y, x2 - x1, height, b$fill, band_opacity
    )
  }, character(1))
  lln_x <- z_to_x(LLN_Z_VISUAL, pad_left, plot_width)
  lln_line <- sprintf(
    '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#1f2937" stroke-width="1.2" stroke-dasharray="4,3" />',
    lln_x, y, lln_x, y + height
  )
  paste(c(rects, lln_line), collapse = "")
}

#' Labelled axis ticks at integer z values plus an LLN tick label.
#' @keywords internal
z_axis_svg <- function(y, pad_left, plot_width, font_size = 10) {
  ticks <- seq(Z_AXIS_MIN, Z_AXIS_MAX, by = 1)
  tick_marks <- vapply(ticks, function(z) {
    x <- z_to_x(z, pad_left, plot_width)
    sprintf(
      '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#94a3b8" stroke-width="1" />
       <text x="%.2f" y="%.2f" font-size="%d" text-anchor="middle" fill="#475569">%d</text>',
      x, y, x, y + 4, x, y + 4 + font_size + 2, font_size, z
    )
  }, character(1))
  lln_x <- z_to_x(LLN_Z_VISUAL, pad_left, plot_width)
  lln_label <- sprintf(
    '<text x="%.2f" y="%.2f" font-size="%d" text-anchor="middle" fill="#1f2937" font-style="italic">LLN</text>',
    lln_x, y - 4, font_size - 1
  )
  paste(c(tick_marks, lln_label), collapse = "")
}

#' Horizontal legend strip showing the severity gradient.
#'
#' One colour swatch + label per severity band, packed into a single
#' row above the chart. Replaces the previous in-place band labels
#' which collided when the narrow moderate/moderately severe/mild
#' bands sat too close together on the axis.
#' @keywords internal
severity_legend_svg <- function(y, pad_left, plot_width, font_size = 12) {
  n <- length(SEVERITY_BANDS)
  step <- plot_width / n
  parts <- vapply(seq_along(SEVERITY_BANDS), function(i) {
    b <- SEVERITY_BANDS[[i]]
    x_start <- pad_left + (i - 1) * step
    sprintf(
      '<rect x="%.2f" y="%.2f" width="14" height="14" rx="3" fill="%s" fill-opacity="0.85" />
       <text x="%.2f" y="%.2f" font-size="%d" text-anchor="start" fill="#0f172a" font-weight="600">%s</text>',
      x_start, y - 11, b$fill,
      x_start + 19, y, font_size, b$label
    )
  }, character(1))
  paste(parts, collapse = "")
}

#' SVG cross-family comparison chart.
#'
#' Three rows (FEV1, FVC, FEV1FVC) on a shared z-axis with severity
#' bands behind one colour-coded marker per reference family per row.
#' A label strip across the top names every band so the gradient is
#' self-documenting. A small legend strip at the bottom keys the
#' markers to their families. Sized with width 100 percent and CSS
#' height auto.
#' @keywords internal
cross_family_chart_svg <- function(family_dfs) {
  active <- Filter(Negate(is.null), family_dfs)
  if (length(active) == 0) {
    return("<em>Enter values to render the comparison chart.</em>")
  }
  total_width  <- 1100
  total_height <- 360
  pad_left  <- 110
  pad_right <- 20
  plot_width <- total_width - pad_left - pad_right
  row_height <- 56
  row_gap    <- 14
  top_pad    <- 36

  band_labels <- severity_legend_svg(top_pad - 14, pad_left, plot_width, font_size = 13)

  rows_svg <- character(length(SPIROMETRY_PARAMS))
  for (i in seq_along(SPIROMETRY_PARAMS)) {
    param <- SPIROMETRY_PARAMS[i]
    y <- top_pad + (i - 1) * (row_height + row_gap)
    bands <- severity_bands_svg(y, row_height, pad_left, plot_width, band_opacity = 0.6)
    label <- sprintf(
      '<text x="%.2f" y="%.2f" font-size="16" text-anchor="end" fill="#0f172a" font-weight="700">%s</text>',
      pad_left - 12, y + row_height / 2 + 6, param
    )
    markers <- character()
    n_families <- length(active)
    for (j in seq_along(active)) {
      fam_label <- names(active)[j]
      df <- active[[j]]
      z <- df$z_score[df$parameter == param]
      if (length(z) == 0 || is.na(z)) next
      colour <- FAMILY_COLOURS[[fam_label]]
      cx <- z_to_x(z, pad_left, plot_width)
      cy <- y + (j - 0.5) * (row_height / n_families)
      markers <- c(markers, sprintf(
        '<circle cx="%.2f" cy="%.2f" r="9" fill="%s" stroke="white" stroke-width="2.5" />
         <text x="%.2f" y="%.2f" font-size="12" text-anchor="middle" fill="%s" font-weight="700">%.2f</text>',
        cx, cy, colour, cx, cy - 13, colour, z
      ))
    }
    rows_svg[i] <- paste0(bands, label, paste(markers, collapse = ""))
  }

  axis_y <- top_pad + length(SPIROMETRY_PARAMS) * (row_height + row_gap) + 6
  axis <- z_axis_svg(axis_y, pad_left, plot_width, font_size = 13)
  axis_label <- sprintf(
    '<text x="%.2f" y="%.2f" font-size="13" fill="#475569">z-score</text>',
    pad_left - 12, axis_y + 16
  )

  legend_y <- axis_y + 44
  legend_items <- character()
  legend_x_start <- pad_left
  legend_spacing <- 220
  for (k in seq_along(active)) {
    fam_label <- names(active)[k]
    colour <- FAMILY_COLOURS[[fam_label]]
    legend_x <- legend_x_start + (k - 1) * legend_spacing
    legend_items <- c(legend_items, sprintf(
      '<circle cx="%.2f" cy="%.2f" r="7" fill="%s" />
       <text x="%.2f" y="%.2f" font-size="13" fill="#1f2937" font-weight="600">%s</text>',
      legend_x, legend_y, colour,
      legend_x + 12, legend_y + 5, fam_label
    ))
  }

  sprintf(
    '<div style="width:100%%;"><svg viewBox="0 0 %d %d" style="display:block;width:100%%;height:auto;" role="img" aria-label="cross-family z-score comparison">%s%s%s%s%s</svg></div>',
    total_width, total_height,
    band_labels,
    paste(rows_svg, collapse = ""),
    axis, axis_label,
    paste(legend_items, collapse = "")
  )
}
