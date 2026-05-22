# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for the NHANES III wrapper in R/nhanes3.R. Same structure as
# the GLI-2012 tests; see the header in test-gli_2012.R for the test
# strategy rationale.

test_that("compute_nhanes3 reproduces every fixture case within 0.01", {
  fixture <- load_fixture("nhanes3_reference_cases.csv")
  case_ids <- unique(fixture$case_id)
  expect_gte(length(case_ids), 5)

  for (cid in case_ids) {
    case_rows <- fixture[fixture$case_id == cid, ]
    first <- case_rows[1, ]
    result <- compute_nhanes3(
      age_years      = first$age_years,
      height_cm      = first$height_cm,
      sex_code       = as.integer(first$sex_code),
      ethnicity_code = as.integer(first$ethnicity_code),
      fev1           = first$fev1_input,
      fvc            = first$fvc_input
    )
    for (param in SPIROMETRY_PARAMS) {
      actual <- result[result$parameter == param, ]
      expected <- case_rows[case_rows$parameter == param, ]
      expect_row_matches_fixture(actual, expected,
                                 info = sprintf("case=%s parameter=%s",
                                                cid, param))
    }
  }
})

test_that("compute_nhanes3 returns one row per parameter in fixed order", {
  result <- compute_nhanes3(40, 170, 1L, 1L, fev1 = 3.5, fvc = 4.5)
  expect_equal(result$parameter, SPIROMETRY_PARAMS)
  expect_equal(nrow(result), length(SPIROMETRY_PARAMS))
})

test_that("compute_nhanes3 rejects an out-of-range NHANES III ethnicity", {
  expect_error(
    compute_nhanes3(40, 170, sex_code = 1L, ethnicity_code = 5L,
                    fev1 = 3, fvc = 4),
    "ethnicity_code"
  )
})

test_that("GLI-2012 and NHANES III produce comparable but distinct values", {
  gli <- compute_gli_2012(30, 175, 1L, 1L, fev1 = 4.0, fvc = 5.0)
  nh  <- compute_nhanes3(30, 175, 1L, 1L, fev1 = 4.0, fvc = 5.0)
  fev1_gli <- gli$predicted[gli$parameter == "FEV1"]
  fev1_nh  <- nh$predicted [nh$parameter  == "FEV1"]
  expect_true(abs(fev1_gli - fev1_nh) > 0)
  expect_true(abs(fev1_gli - fev1_nh) < 0.5)
})
