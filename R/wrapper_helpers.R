# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: wrapper_helpers
# Purpose: Shared helpers used by every reference equation wrapper:
# input validation and long-form data.frame assembly. Pure functions,
# no Shiny state, no side effects.

#' Validate subject-level inputs shared by every reference wrapper.
#'
#' Fails loudly with informative messages when inputs are missing,
#' wrong length, out of plausible physiological range, or refer to an
#' unsupported ethnicity code. The plausible ranges are loose by design:
#' rspiro itself enforces equation-specific age and height domains.
#'
#' Ethnicity is optional: race-neutral equations such as GLI-Global 2022
#' have no ethnicity argument. Pass \code{ethnicity_code = NULL} and
#' \code{valid_ethnicity = NULL} to skip that part of the check.
#' @keywords internal
validate_subject_inputs <- function(age_years, height_cm, sex_code,
                                    ethnicity_code = NULL,
                                    valid_ethnicity = NULL,
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
  if (!is.null(valid_ethnicity)) {
    if (is.null(ethnicity_code) || !(ethnicity_code %in% valid_ethnicity)) {
      stop(sprintf("ethnicity_code must be one of: %s.",
                   paste(valid_ethnicity, collapse = ", ")),
           call. = FALSE)
    }
  }
  invisible(TRUE)
}

#' Assemble the long-form data.frame returned by every wrapper.
#'
#' rspiro returns wide single-row data.frames with prefixed columns
#' (\code{pred.FEV1}, \code{LLN.FEV1}, etc). This helper reshapes those
#' into a long-form table keyed by parameter, matching the contract in
#' CLAUDE.md. Parameters missing from a given rspiro output are filled
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
