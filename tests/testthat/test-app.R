# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Server-logic tests for app.R, run with shiny::testServer. They check
# what the operator sees for usable, out-of-range and invalid inputs.

load_app <- function() {
  root <- normalizePath(file.path(getwd(), "..", ".."))
  old_wd <- setwd(root)
  withr::defer(setwd(old_wd), envir = parent.frame())
  suppressMessages({
    library(shiny)
    library(bslib)
  })
  source("app.R", local = TRUE)$value
}

set_inputs <- function(session, ...) {
  defaults <- list(age_years = 40, height_cm = 170, sex_code = "1",
                   ethnicity_gli = "1", ethnicity_nhanes3 = "1",
                   fev1 = 3.2, fvc = 4.0)
  do.call(session$setInputs, modifyList(defaults, list(...)))
}

test_that("all three families are computed for usable inputs", {
  skip_if_not_installed("shiny")
  skip_if_not_installed("bslib")
  app <- load_app()
  shiny::testServer(app, {
    set_inputs(session)
    expect_true(inputs_ready())
    expect_s3_class(results_gli_2012(), "data.frame")
    expect_s3_class(results_gli_2022(), "data.frame")
    expect_s3_class(results_nhanes(), "data.frame")
    expect_null(calc_nhanes3()$message)
  })
})

test_that("a family outside its age range reports why, the others still compute", {
  skip_if_not_installed("shiny")
  skip_if_not_installed("bslib")
  app <- load_app()
  shiny::testServer(app, {
    set_inputs(session, age_years = 5, height_cm = 110, fev1 = 1.2, fvc = 1.5)
    expect_s3_class(results_gli_2012(), "data.frame")
    expect_null(results_nhanes())
    expect_match(calc_nhanes3()$message, "between 8 and 80")
    expect_match(as.character(output$results_nhanes3$html),
                 "between 8 and 80")
  })
})

test_that("FEV1 above FVC hides the results and shows a notice", {
  skip_if_not_installed("shiny")
  skip_if_not_installed("bslib")
  app <- load_app()
  shiny::testServer(app, {
    set_inputs(session, fev1 = 5.0, fvc = 4.0)
    expect_false(inputs_ready())
    expect_null(results_gli_2012())
    expect_match(as.character(output$input_notice$html),
                 "FEV1 is larger than FVC")
  })
})
