# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: gli_2012
# Purpose: Pure wrapper around the GLI-2012 reference equations exposed
# by the rspiro package. The wrapper accepts inputs in operator-friendly
# units (height in centimetres, sex and ethnicity as integer codes from
# R/constants.R) and returns a long-form data.frame, one row per
# spirometry parameter, with the columns required by the wrapper
# contract documented in CLAUDE.md.

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

#' Validate subject-level inputs shared by every reference wrapper.
#'
#' Fails loudly with informative messages when inputs are missing,
#' wrong length, out of plausible physiological range, or refer to an
#' unsupported ethnicity code. The plausible ranges are loose by design:
#' rspiro itself enforces equation-specific age and height domains.
#' @keywords internal
validate_subject_inputs <- function(age_years, height_cm, sex_code,
                                    ethnicity_code, valid_ethnicity,
                                    fev1, fvc) {
  scalar_numeric <- function(x, label) {
    if (length(x) != 1 || !is.numeric(x) || is.na(x)) {
      stop(sprintf("%s must be a single non-missing numeric value.", label),
           call. = FALSE)
    }
  }
  scalar_numeric(age_years, "age_years")
  scalar_numeric(height_cm, "height_cm")
  scalar_numeric(fev1, "fev1")
  scalar_numeric(fvc, "fvc")

  if (age_years <= 0 || age_years > 120) {
    stop("age_years must be a plausible age in years (0 to 120).",
         call. = FALSE)
  }
  if (height_cm < 50 || height_cm > 250) {
    stop("height_cm must be a plausible standing height in centimetres (50 to 250).",
         call. = FALSE)
  }
  if (fev1 <= 0 || fvc <= 0) {
    stop("fev1 and fvc must be positive values in litres.", call. = FALSE)
  }
  if (fev1 > fvc) {
    stop("fev1 cannot exceed fvc; check the inputs.", call. = FALSE)
  }
  if (!(sex_code %in% SEX_CODES)) {
    stop(sprintf("sex_code must be one of: %s.",
                 paste(SEX_CODES, collapse = ", ")),
         call. = FALSE)
  }
  if (!(ethnicity_code %in% valid_ethnicity)) {
    stop(sprintf("ethnicity_code must be one of: %s.",
                 paste(valid_ethnicity, collapse = ", ")),
         call. = FALSE)
  }
  invisible(TRUE)
}

#' Assemble the long-form data.frame returned by every wrapper.
#'
#' rspiro returns wide single-row data.frames with prefixed columns
#' (\code{pred.FEV1}, \code{LLN.FEV1}, etc). This helper reshapes those
#' into a long-form table keyed by parameter, matching the contract in
#' CLAUDE.md. Parameters missing from a given rspiro output (for
#' instance, FEV1FVC is not always provided by every helper) are filled
#' with NA so downstream UI code can render a consistent table.
#' @keywords internal
assemble_reference_table <- function(observed, pred, lln, zscore, pctpred) {
  pull <- function(df, prefix, param) {
    column <- paste0(prefix, ".", param)
    if (column %in% names(df)) df[[column]] else NA_real_
  }
  data.frame(
    parameter         = SPIROMETRY_PARAMS,
    observed          = as.numeric(observed[SPIROMETRY_PARAMS]),
    predicted         = vapply(SPIROMETRY_PARAMS, pull, numeric(1),
                               df = pred, prefix = "pred"),
    lln               = vapply(SPIROMETRY_PARAMS, pull, numeric(1),
                               df = lln, prefix = "LLN"),
    z_score           = vapply(SPIROMETRY_PARAMS, pull, numeric(1),
                               df = zscore, prefix = "z.score"),
    percent_predicted = vapply(SPIROMETRY_PARAMS, pull, numeric(1),
                               df = pctpred, prefix = "pctpred"),
    stringsAsFactors  = FALSE,
    row.names         = NULL
  )
}
