# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Tests for the GLI-2012 wrapper in R/gli_2012.R.
#
# Scope of this test file: verify that compute_gli_2012 forwards inputs
# correctly to the rspiro GLI-2012 functions and that its long-form
# output matches the persisted fixture within 0.01. The fixture rows
# are themselves produced by rspiro at known inputs. This is the
# wrapper-contract test layer.
#
# A separate manual cross-check against the official Quanjer 2012
# supplement worked examples is the maintainer gate before this phase
# is marked accepted, per the validation requirements in CLAUDE.md.

test_that("compute_gli_2012 reproduces every fixture case within 0.01", {
  fixture <- load_fixture("gli_2012_reference_cases.csv")
  case_ids <- unique(fixture$case_id)
  expect_gte(length(case_ids), 5)

  for (cid in case_ids) {
    case_rows <- fixture[fixture$case_id == cid, ]
    first <- case_rows[1, ]
    result <- compute_gli_2012(
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

test_that("compute_gli_2012 returns one row per parameter in fixed order", {
  result <- compute_gli_2012(40, 170, 1L, 1L, fev1 = 3.5, fvc = 4.5)
  expect_equal(result$parameter, SPIROMETRY_PARAMS)
  expect_equal(nrow(result), length(SPIROMETRY_PARAMS))
})

test_that("compute_gli_2012 returns a base data.frame, not a tibble", {
  result <- compute_gli_2012(40, 170, 1L, 1L, fev1 = 3.5, fvc = 4.5)
  expect_s3_class(result, "data.frame")
  expect_false(inherits(result, "tbl_df"))
})

test_that("compute_gli_2012 rejects implausible inputs with informative errors", {
  expect_error(
    compute_gli_2012(age_years = -1, height_cm = 170, sex_code = 1L,
                     ethnicity_code = 1L, fev1 = 3, fvc = 4),
    "age_years"
  )
  expect_error(
    compute_gli_2012(40, height_cm = 30, sex_code = 1L,
                     ethnicity_code = 1L, fev1 = 3, fvc = 4),
    "height_cm"
  )
  expect_error(
    compute_gli_2012(40, 170, sex_code = 9L, ethnicity_code = 1L,
                     fev1 = 3, fvc = 4),
    "sex_code"
  )
  expect_error(
    compute_gli_2012(40, 170, sex_code = 1L, ethnicity_code = 99L,
                     fev1 = 3, fvc = 4),
    "ethnicity_code"
  )
  expect_error(
    compute_gli_2012(40, 170, 1L, 1L, fev1 = 5, fvc = 4),
    "fev1 cannot exceed fvc"
  )
})
