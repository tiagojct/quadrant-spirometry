# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for the SVG helpers in R/visuals.R.

test_that("z_to_x maps the axis ends to the plot edges and clamps outside values", {
  expect_equal(z_to_x(Z_AXIS_MIN, 100, 800), 100)
  expect_equal(z_to_x(Z_AXIS_MAX, 100, 800), 900)
  expect_equal(z_to_x(Z_AXIS_MIN - 10, 100, 800), 100)
  expect_equal(z_to_x(Z_AXIS_MAX + 10, 100, 800), 900)
})

test_that("severity bands cover the z axis without gaps or overlaps", {
  los <- vapply(SEVERITY_BANDS, function(b) b$z_lo, numeric(1))
  his <- vapply(SEVERITY_BANDS, function(b) b$z_hi, numeric(1))
  expect_equal(los[1], Z_AXIS_MIN)
  expect_equal(his[length(his)], Z_AXIS_MAX)
  expect_equal(los[-1], his[-length(his)])
})

test_that("severity band edges agree with the interpretation cut-offs", {
  edges <- vapply(SEVERITY_BANDS, function(b) b$z_hi, numeric(1))
  expect_true(all(c(SEVERITY_MODERATE_Z_MIN, SEVERITY_MILD_Z_MIN, LLN_Z) %in% edges))
  labels <- vapply(SEVERITY_BANDS, function(b) b$label, character(1))
  expect_equal(labels, c("severe", "moderate", "mild", "normal"))
})

test_that("cross_family_chart_svg draws one marker per family and parameter", {
  make <- function(z) data.frame(parameter = SPIROMETRY_PARAMS, z_score = z)
  svg <- cross_family_chart_svg(list(
    "GLI-2012"        = make(c(-1, -2, -3)),
    "GLI-Global 2022" = make(c(-1, -2, -3)),
    "NHANES III"      = make(c(0, 0, 0))
  ))
  expect_true(grepl("^<div", svg))
  expect_true(grepl("<svg", svg, fixed = TRUE))
  for (fam in names(FAMILY_COLOURS)) {
    expect_true(grepl(fam, svg, fixed = TRUE))
  }
  # Nine markers in the rows plus three legend circles.
  expect_equal(lengths(regmatches(svg, gregexpr("<circle", svg))), 12)
})

test_that("cross_family_chart_svg skips families without results", {
  make <- function(z) data.frame(parameter = SPIROMETRY_PARAMS, z_score = z)
  svg <- cross_family_chart_svg(list(
    "GLI-2012"   = make(c(-1, -2, -3)),
    "NHANES III" = NULL
  ))
  expect_false(grepl("NHANES III", svg, fixed = TRUE))
  expect_true(grepl("GLI-2012", svg, fixed = TRUE))
})

test_that("cross_family_chart_svg returns a prompt when no family has results", {
  out <- cross_family_chart_svg(list("GLI-2012" = NULL, "NHANES III" = NULL))
  expect_true(grepl("Enter values", out, fixed = TRUE))
  expect_false(grepl("<svg", out, fixed = TRUE))
})
