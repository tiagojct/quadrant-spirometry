# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for R/interpretation.R: ATS/ERS 2022 pattern classification and
# severity grading. Pattern function and severity function are tested
# in isolation; the integrating interpret_spirometry function is
# exercised with synthetic reference data.frames that match the long-
# form contract of the wrappers in R/gli_2012.R and friends.

test_that("classify_pattern returns 'normal' when every z-score is at or above LLN", {
  expect_equal(classify_pattern(fev1_z = 0,    fvc_z = 0,    fev1_fvc_z = 0),    "normal")
  expect_equal(classify_pattern(fev1_z = -1.0, fvc_z = -1.0, fev1_fvc_z = -1.0), "normal")
  expect_equal(classify_pattern(fev1_z = -1.645, fvc_z = -1.645, fev1_fvc_z = -1.645), "normal")
})

test_that("classify_pattern returns 'obstructive' when only FEV1/FVC is below LLN", {
  expect_equal(classify_pattern(fev1_z = -1.0, fvc_z = -1.0, fev1_fvc_z = -2.0), "obstructive")
  expect_equal(classify_pattern(fev1_z = -3.0, fvc_z = 0.0,  fev1_fvc_z = -3.0), "obstructive")
})

test_that("classify_pattern returns 'mixed pattern (suggestive)' when both ratio and FVC are below LLN", {
  expect_equal(classify_pattern(fev1_z = -3.0, fvc_z = -2.0, fev1_fvc_z = -2.0),
               "mixed pattern (suggestive)")
})

test_that("classify_pattern returns 'restrictive pattern (suggestive)' when FVC is below LLN but ratio is preserved", {
  expect_equal(classify_pattern(fev1_z = -2.0, fvc_z = -2.0, fev1_fvc_z = 0.0),
               "restrictive pattern (suggestive)")
  expect_equal(classify_pattern(fev1_z = -1.0, fvc_z = -2.0, fev1_fvc_z = 0.5),
               "restrictive pattern (suggestive)")
})

test_that("classify_pattern returns 'non-specific' when FEV1 is below LLN but FVC and ratio are preserved", {
  expect_equal(classify_pattern(fev1_z = -2.0, fvc_z = -1.0, fev1_fvc_z = -1.0),
               "non-specific")
})

test_that("classify_pattern is strict about the LLN boundary at -1.645", {
  # Exactly at LLN counts as normal; only strictly below LLN triggers a defect.
  expect_equal(
    classify_pattern(fev1_z = -1.645, fvc_z = -1.645, fev1_fvc_z = -1.645),
    "normal"
  )
  expect_equal(
    classify_pattern(fev1_z = -1.6451, fvc_z = -1.0, fev1_fvc_z = -1.0),
    "non-specific"
  )
})

test_that("classify_pattern rejects invalid inputs", {
  expect_error(classify_pattern(NA, 0, 0), "non-missing")
  expect_error(classify_pattern("low", 0, 0), "numeric")
  expect_error(classify_pattern(c(-1, -2), 0, 0), "single")
})

test_that("grade_severity follows the ATS/ERS 2022 five-band scheme", {
  expect_equal(grade_severity(-1.7),  "mild")
  expect_equal(grade_severity(-2.0),  "mild")
  expect_equal(grade_severity(-2.1),  "moderate")
  expect_equal(grade_severity(-2.5),  "moderate")
  expect_equal(grade_severity(-2.6),  "moderately severe")
  expect_equal(grade_severity(-3.0),  "moderately severe")
  expect_equal(grade_severity(-3.1),  "severe")
  expect_equal(grade_severity(-4.0),  "severe")
  expect_equal(grade_severity(-4.1),  "very severe")
  expect_equal(grade_severity(-6.0),  "very severe")
})

test_that("grade_severity returns 'mild' for any z-score at or above -2.0, including positive z-scores", {
  expect_equal(grade_severity(0.0),  "mild")
  expect_equal(grade_severity(1.5),  "mild")
})

test_that("grade_severity rejects invalid inputs", {
  expect_error(grade_severity(NA), "non-missing")
  expect_error(grade_severity("low"), "numeric")
  expect_error(grade_severity(c(-1, -2)), "single")
})

# Helper: build a synthetic reference_df that matches the wrapper contract.
make_reference_df <- function(fev1_z, fvc_z, fev1_fvc_z) {
  data.frame(
    parameter         = c("FEV1", "FVC", "FEV1FVC"),
    observed          = c(3.0, 4.0, 0.75),
    predicted         = c(3.5, 4.5, 0.80),
    lln               = c(2.8, 3.5, 0.70),
    z_score           = c(fev1_z, fvc_z, fev1_fvc_z),
    percent_predicted = c(86, 89, 94),
    stringsAsFactors  = FALSE,
    row.names         = NULL
  )
}

test_that("interpret_spirometry combines pattern and severity correctly", {
  normal <- interpret_spirometry(make_reference_df(0, 0, 0))
  expect_equal(normal$pattern,  "normal")
  expect_true(is.na(normal$severity))

  obstructive <- interpret_spirometry(make_reference_df(-2.7, -1.0, -3.0))
  expect_equal(obstructive$pattern,  "obstructive")
  expect_equal(obstructive$severity, "moderately severe")

  mixed <- interpret_spirometry(make_reference_df(-4.5, -2.0, -2.0))
  expect_equal(mixed$pattern,  "mixed pattern (suggestive)")
  expect_equal(mixed$severity, "very severe")

  restrictive <- interpret_spirometry(make_reference_df(-1.0, -2.0, 0.0))
  expect_equal(restrictive$pattern,  "restrictive pattern (suggestive)")
  expect_equal(restrictive$severity, "mild")

  non_specific <- interpret_spirometry(make_reference_df(-2.5, -1.0, -1.0))
  expect_equal(non_specific$pattern,  "non-specific")
  expect_equal(non_specific$severity, "moderate")
})

test_that("interpret_spirometry surfaces the per-parameter z-scores it used", {
  result <- interpret_spirometry(make_reference_df(-2.0, -3.0, -1.0))
  expect_equal(result$fev1_z, -2.0)
  expect_equal(result$fvc_z,  -3.0)
  expect_equal(result$fev1_fvc_z, -1.0)
})

test_that("interpret_spirometry fails loudly on a malformed reference_df", {
  bad <- data.frame(foo = 1, bar = 2)
  expect_error(interpret_spirometry(bad), "missing required columns")

  missing_param <- data.frame(
    parameter = c("FEV1", "FVC"),
    z_score   = c(-1, -1)
  )
  expect_error(interpret_spirometry(missing_param), "FEV1FVC")
})
