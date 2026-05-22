# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: nhanes3
# Purpose: Pure wrapper around the NHANES III reference equations
# (Hankinson et al. 1999, doi:10.1164/ajrccm.159.1.9712108) exposed by
# rspiro. Provides the pre-GLI comparator used by Quadrant's side-by-
# side view, so the operator can see how the classification of a single
# individual evolves between a 1999 and a 2012 reference equation.
# Shares the same return contract as the GLI-2012 wrapper. The helpers
# assemble_reference_table and validate_subject_inputs are defined in
# R/gli_2012.R and are reused here.

#' Compute NHANES III reference values for a single subject.
#'
#' Returns predicted, lower limit of normal, z-score, and percent of
#' predicted for FEV1, FVC, and FEV1/FVC using rspiro's NHANES III
#' implementation. The function is pure.
#'
#' @param age_years Age in years. Numeric, length 1.
#' @param height_cm Standing height in centimetres. Numeric, length 1.
#' @param sex_code Integer 1 for male, 2 for female, matching
#'   \code{SEX_CODES} in R/constants.R.
#' @param ethnicity_code Integer 1 to 3, matching
#'   \code{NHANES3_ETHNICITY}.
#' @param fev1 Observed FEV1 in litres. Numeric, length 1.
#' @param fvc Observed FVC in litres. Numeric, length 1.
#' @return A data.frame with columns parameter, observed, predicted,
#'   lln, z_score, percent_predicted. One row per parameter in the order
#'   defined by \code{SPIROMETRY_PARAMS}.
#' @keywords internal
compute_nhanes3 <- function(age_years, height_cm, sex_code, ethnicity_code,
                            fev1, fvc) {
  validate_subject_inputs(
    age_years = age_years,
    height_cm = height_cm,
    sex_code = sex_code,
    ethnicity_code = ethnicity_code,
    valid_ethnicity = NHANES3_ETHNICITY,
    fev1 = fev1,
    fvc = fvc
  )

  height_m <- height_cm / 100
  fev1_fvc_ratio <- fev1 / fvc

  pred <- rspiro::pred_NHANES3(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    param = SPIROMETRY_PARAMS
  )
  lln <- rspiro::LLN_NHANES3(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    param = SPIROMETRY_PARAMS
  )
  zscore <- rspiro::zscore_NHANES3(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )
  pctpred <- rspiro::pctpred_NHANES3(
    age = age_years, height = height_m, gender = sex_code,
    ethnicity = ethnicity_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )

  assemble_reference_table(
    observed = c(FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio),
    pred = pred, lln = lln, zscore = zscore, pctpred = pctpred
  )
}
