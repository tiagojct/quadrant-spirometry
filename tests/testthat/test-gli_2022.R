# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for the GLI-Global 2022 wrapper in R/gli_2022.R. Same structure
# as the GLI-2012 tests; see the header in test-gli_2012.R for the
# test strategy rationale. This family is race-neutral, so the wrapper
# takes no ethnicity_code argument and the fixture has no ethnicity
# column.

test_that("compute_gli_global_2022 reproduces every fixture case within 0.01", {
  fixture <- load_fixture("gli_global_2022_reference_cases.csv")
  case_ids <- unique(fixture$case_id)
  expect_gte(length(case_ids), 5)

  for (cid in case_ids) {
    case_rows <- fixture[fixture$case_id == cid, ]
    first <- case_rows[1, ]
    result <- compute_gli_global_2022(
      age_years = first$age_years,
      height_cm = first$height_cm,
      sex_code  = as.integer(first$sex_code),
      fev1      = first$fev1_input,
      fvc       = first$fvc_input
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

test_that("compute_gli_global_2022 returns one row per parameter in fixed order", {
  result <- compute_gli_global_2022(40, 170, 1L, fev1 = 3.5, fvc = 4.5)
  expect_equal(result$parameter, SPIROMETRY_PARAMS)
  expect_equal(nrow(result), length(SPIROMETRY_PARAMS))
})

test_that("compute_gli_global_2022 has no ethnicity argument", {
  expect_false("ethnicity_code" %in% names(formals(compute_gli_global_2022)))
})

test_that("compute_gli_global_2022 rejects implausible inputs", {
  expect_error(
    compute_gli_global_2022(age_years = 0, height_cm = 170, sex_code = 1L,
                            fev1 = 3, fvc = 4),
    "age_years"
  )
  expect_error(
    compute_gli_global_2022(40, 170, sex_code = 1L, fev1 = 5, fvc = 4),
    "fev1 cannot exceed fvc"
  )
})

test_that("GLI-2012 and GLI-Global 2022 diverge for a non-Caucasian subject", {
  # African-American (GLI-2012 ethnicity 2). GLI-Global 2022 is race-neutral.
  # For the same observed values, z-scores should differ between the two
  # equation families, which is exactly the comparison Quadrant exists to
  # surface to the operator.
  gli_2012 <- compute_gli_2012(40, 170, sex_code = 1L, ethnicity_code = 2L,
                               fev1 = 2.80, fvc = 3.50)
  gli_2022 <- compute_gli_global_2022(40, 170, sex_code = 1L,
                                      fev1 = 2.80, fvc = 3.50)
  fev1_z_2012 <- gli_2012$z_score[gli_2012$parameter == "FEV1"]
  fev1_z_2022 <- gli_2022$z_score[gli_2022$parameter == "FEV1"]
  expect_true(abs(fev1_z_2012 - fev1_z_2022) > 0.1)
})
