# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for R/report.R. The end-to-end Quarto render is not exercised
# here: it depends on the quarto CLI being on the host, which is fine
# for interactive development but not guaranteed in every CI runner.
# These tests cover the pure bundle assembly and the helper utilities.

build_sample_results <- function() {
  list(
    gli_2012 = compute_gli_2012(40, 170, 1L, 1L, 2.7, 4.0),
    gli_2022 = compute_gli_global_2022(40, 170, 1L, 2.7, 4.0),
    nhanes3  = compute_nhanes3(40, 170, 1L, 1L, 2.7, 4.0)
  )
}

build_sample_interpretations <- function(results) {
  list(
    gli_2012 = interpret_spirometry(results$gli_2012),
    gli_2022 = interpret_spirometry(results$gli_2022),
    nhanes3  = interpret_spirometry(results$nhanes3)
  )
}

build_sample_subject <- function() {
  list(
    age_years = 40,
    height_cm = 170,
    sex_label = "Male",
    ethnicity_gli_label = "Caucasian",
    ethnicity_nhanes3_label = "Caucasian",
    fev1 = 2.7,
    fvc = 4.0
  )
}

test_that("sex_label_from_code and ethnicity_label_from_code round-trip", {
  expect_equal(sex_label_from_code(1L), "Male")
  expect_equal(sex_label_from_code(2L), "Female")
  expect_equal(ethnicity_label_from_code(1L, GLI_ETHNICITY),     "Caucasian")
  expect_equal(ethnicity_label_from_code(2L, GLI_ETHNICITY),     "African-American")
  expect_equal(ethnicity_label_from_code(3L, NHANES3_ETHNICITY), "Mexican-American")
})

test_that("ethnicity_label_from_code returns empty string for unknown codes", {
  expect_equal(ethnicity_label_from_code(99L, GLI_ETHNICITY), "")
  expect_equal(ethnicity_label_from_code(NA,  GLI_ETHNICITY), "")
})

test_that("to_html_string handles every expected input type", {
  expect_equal(to_html_string(NULL), "")
  expect_equal(to_html_string("plain text"), "plain text")
  expect_equal(to_html_string(c("a", "b")), "ab")
  tag <- shiny::tags$div("x")
  expect_true(grepl("<div>x</div>", to_html_string(tag), fixed = TRUE))
  expect_equal(to_html_string(shiny::HTML("<svg/>")), "<svg/>")
})

test_that("reference_table_html renders one row per parameter", {
  results <- build_sample_results()
  html <- reference_table_html(results$gli_2012)
  expect_true(grepl("FEV1",    html))
  expect_true(grepl("FVC",     html))
  expect_true(grepl("FEV1FVC", html))
  expect_true(grepl("<table",  html))
})

test_that("prepare_report_bundle assembles every required block", {
  results <- build_sample_results()
  interp  <- build_sample_interpretations(results)
  subject <- build_sample_subject()
  chart_svg <- "<svg/>"
  cmp <- shiny::tags$p("ok")

  bundle <- prepare_report_bundle(subject, results, interp,
                                  chart_svg, cmp)

  expect_named(bundle, c("subject", "chart_svg", "comparison_text_html",
                         "family_blocks", "timestamp"),
               ignore.order = TRUE)
  expect_equal(bundle$chart_svg, "<svg/>")
  expect_true(grepl("ok", bundle$comparison_text_html))
  expect_equal(length(bundle$family_blocks), 3)
  for (block in bundle$family_blocks) {
    expect_named(block, c("subtitle", "badge_html", "table_html",
                          "interpretation_html"),
                 ignore.order = TRUE)
    expect_true(nchar(block$badge_html) > 0)
    expect_true(nchar(block$table_html) > 0)
    expect_true(nchar(block$interpretation_html) > 0)
  }
  expect_s3_class(bundle$timestamp, "POSIXct")
})

test_that("render_quadrant_report rejects unknown output formats", {
  expect_error(
    render_quadrant_report(list(), output_format = "epub"),
    "html.*pdf"
  )
})
