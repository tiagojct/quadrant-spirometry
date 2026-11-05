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
