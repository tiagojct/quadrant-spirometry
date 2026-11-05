# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for the pure UI helpers in R/ui_components.R.

test_that("input_notice is silent for usable or missing values", {
  expect_null(input_notice(3.0, 4.0))
  expect_null(input_notice(4.0, 4.0))
  expect_null(input_notice(NULL, 4.0))
  expect_null(input_notice(3.0, NA_real_))
})

test_that("input_notice explains FEV1 larger than FVC", {
  html <- as.character(input_notice(5.0, 4.0))
  expect_true(grepl("FEV1 is larger than FVC", html, fixed = TRUE))
  expect_true(grepl("alert-warning", html, fixed = TRUE))
})

test_that("input_notice explains non-positive values", {
  expect_true(grepl("greater than zero", as.character(input_notice(0, 4.0))))
  expect_true(grepl("greater than zero", as.character(input_notice(3.0, -1))))
})

test_that("render_reference_table shows the message instead of a table", {
  html <- as.character(render_reference_table(NULL, "age_years must be between 8 and 80 years."))
  expect_true(grepl("Not available for these inputs", html, fixed = TRUE))
  expect_true(grepl("between 8 and 80", html, fixed = TRUE))
  expect_false(grepl("<table", html, fixed = TRUE))
})

test_that("render_pattern_badge maps severity to a colour and a label", {
  normal <- as.character(render_pattern_badge(list(pattern = "normal", severity = NA_character_)))
  expect_true(grepl("NORMAL", normal, fixed = TRUE))
  severe <- as.character(render_pattern_badge(list(pattern = "obstructive", severity = "severe")))
  expect_true(grepl("OBSTRUCTIVE", severe, fixed = TRUE))
  expect_true(grepl("severe", severe, fixed = TRUE))
  expect_true(grepl("Enter values", as.character(render_pattern_badge(NULL)), fixed = TRUE))
})

test_that("render_gli_comparison reports a flip across the LLN", {
  make <- function(z) data.frame(parameter = SPIROMETRY_PARAMS, z_score = z)
  agree <- as.character(render_gli_comparison(make(c(0, 0, 0)), make(c(0, 0, 0))))
  expect_true(grepl("same side", agree, fixed = TRUE))
  flip <- as.character(render_gli_comparison(make(c(-1.0, 0, 0)), make(c(-2.0, 0, 0))))
  expect_true(grepl("Classification differs", flip, fixed = TRUE))
  expect_true(grepl("FEV1", flip, fixed = TRUE))
  expect_true(grepl("Enter values", as.character(render_gli_comparison(NULL, make(c(0, 0, 0)))), fixed = TRUE))
})
