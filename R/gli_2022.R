# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: gli_2022
# Purpose: Pure wrapper around the GLI-Global 2022 race-neutral
# reference equations (Bowerman et al. 2023,
# doi:10.1164/rccm.202205-0963OC) exposed by rspiro as pred_GLIgl,
# LLN_GLIgl, zscore_GLIgl, and pctpred_GLIgl. Unlike GLI-2012 and
# NHANES III, this equation family has no ethnicity argument, by
# design. Shares the same return contract as the other wrappers.
# Helpers live in R/wrapper_helpers.R.

#' Compute GLI-Global 2022 reference values for a single subject.
#'
#' Returns predicted, lower limit of normal, z-score, and percent of
#' predicted for FEV1, FVC, and FEV1/FVC using rspiro's GLI-Global 2022
#' implementation. The function is pure and accepts no ethnicity
#' argument: the underlying equation is race-neutral.
#'
#' @param age_years Age in years. Numeric, length 1.
#' @param height_cm Standing height in centimetres. Numeric, length 1.
#' @param sex_code Integer 1 for male, 2 for female, matching
#'   \code{SEX_CODES} in R/constants.R.
#' @param fev1 Observed FEV1 in litres. Numeric, length 1.
#' @param fvc Observed FVC in litres. Numeric, length 1.
#' @return A data.frame with columns parameter, observed, predicted,
#'   lln, z_score, percent_predicted. One row per parameter in the order
#'   defined by \code{SPIROMETRY_PARAMS}.
#' @keywords internal
compute_gli_global_2022 <- function(age_years, height_cm, sex_code,
                                    fev1, fvc) {
  validate_subject_inputs(
    age_years       = age_years,
    height_cm       = height_cm,
    sex_code        = sex_code,
    ethnicity_code  = NULL,
    valid_ethnicity = NULL,
    fev1            = fev1,
    fvc             = fvc
  )

  height_m <- height_cm / 100
  fev1_fvc_ratio <- fev1 / fvc

  pred <- rspiro::pred_GLIgl(
    age = age_years, height = height_m, gender = sex_code,
    param = SPIROMETRY_PARAMS
  )
  lln <- rspiro::LLN_GLIgl(
    age = age_years, height = height_m, gender = sex_code,
    param = SPIROMETRY_PARAMS
  )
  zscore <- rspiro::zscore_GLIgl(
    age = age_years, height = height_m, gender = sex_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )
  pctpred <- rspiro::pctpred_GLIgl(
    age = age_years, height = height_m, gender = sex_code,
    FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio
  )

  assemble_reference_table(
    observed = c(FEV1 = fev1, FVC = fvc, FEV1FVC = fev1_fvc_ratio),
    pred = pred, lln = lln, zscore = zscore, pctpred = pctpred
  )
}
