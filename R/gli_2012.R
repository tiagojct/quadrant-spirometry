# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: gli_2012
# Purpose: Pure wrapper around the GLI-2012 reference equations exposed
# by the rspiro package. The wrapper accepts inputs in operator-friendly
# units (height in centimetres, sex and ethnicity as integer codes from
# R/constants.R) and returns a long-form data.frame, one row per
# spirometry parameter, with the columns required by the wrapper
# contract documented in CLAUDE.md. Shared validation and assembly
# helpers live in R/wrapper_helpers.R.

#' Compute GLI-2012 reference values for a single subject.
#'
#' Returns predicted, lower limit of normal, z-score, and percent of
#' predicted for FEV1, FVC, and FEV1/FVC, using rspiro's GLI-2012
#' implementation. The function is pure: it has no side effects, does
#' not read or write files, and does not depend on Shiny session state.
#'
#' @param age_years Age in years. Numeric, length 1.
#' @param height_cm Standing height in centimetres. Numeric, length 1.
#' @param sex_code Integer 1 for male, 2 for female, matching
#'   \code{SEX_CODES} in R/constants.R.
#' @param ethnicity_code Integer 1 to 5, matching \code{GLI_ETHNICITY}.
#' @param fev1 Observed FEV1 in litres. Numeric, length 1.
#' @param fvc Observed FVC in litres. Numeric, length 1.
#' @return A data.frame with columns parameter, observed, predicted,
#'   lln, z_score, percent_predicted. One row per parameter in the order
#'   defined by \code{SPIROMETRY_PARAMS}.
#' @keywords internal
compute_gli_2012 <- function(age_years, height_cm, sex_code, ethnicity_code,
                             fev1, fvc) {
  validate_subject_inputs(
    age_years = age_years,
    height_cm = height_cm,
    sex_code = sex_code,
    ethnicity_code = ethnicity_code,
    valid_ethnicity = GLI_ETHNICITY,
    fev1 = fev1,
    fvc = fvc
  )

  height_m <- height_cm / 100
  fev1_fvc_ratio <- fev1 / fvc

  pred <- rspiro::pred_GLI(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    param = SPIROMETRY_PARAMS
  )
  lln <- rspiro::LLN_GLI(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    param = SPIROMETRY_PARAMS
  )
  zscore <- rspiro::zscore_GLI(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )
  pctpred <- rspiro::pctpred_GLI(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )

  assemble_reference_table(
    observed = c(FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio),
    pred = pred, lln = lln, zscore = zscore, pctpred = pctpred
  )
}
