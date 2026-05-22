# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: interpretation
# Purpose: ATS/ERS 2022 pattern classification and severity grading
# (Stanojevic et al., ERJ 2022, doi:10.1183/13993003.01499-2021). Pure
# functions only, with no Shiny state and no side effects, so they can
# be tested in isolation and reused by both the UI and the Phase 4
# report renderer. All language is cautious: outputs describe the
# spirometric pattern, not a diagnosis.

#' Z-score cut-off used as the lower limit of normal in the
#' ATS/ERS 2022 framework. The same threshold is used for FEV1/FVC,
#' FVC, and FEV1.
#' @keywords internal
LLN_Z <- -1.645

#' Classify the ventilatory pattern from spirometry z-scores alone.
#'
#' Implements the spirometry-only branches of the ATS/ERS 2022
#' interpretive strategy. Definitive classification of restrictive or
#' mixed defects requires static lung volumes, which Quadrant does not
#' accept; spirometry-suggestive patterns are reported as such with a
#' "(suggestive)" qualifier.
#'
#' @param fev1_z Z-score for FEV1.
#' @param fvc_z Z-score for FVC.
#' @param fev1_fvc_z Z-score for the FEV1/FVC ratio.
#' @return A single character string, one of: "normal",
#'   "obstructive", "restrictive pattern (suggestive)",
#'   "mixed pattern (suggestive)", "non-specific".
#' @keywords internal
classify_pattern <- function(fev1_z, fvc_z, fev1_fvc_z) {
  for (val in list(fev1_z, fvc_z, fev1_fvc_z)) {
    if (length(val) != 1 || !is.numeric(val) || is.na(val)) {
      stop("classify_pattern needs single non-missing numeric z-scores.",
           call. = FALSE)
    }
  }
  ratio_low <- fev1_fvc_z < LLN_Z
  fvc_low   <- fvc_z      < LLN_Z
  fev1_low  <- fev1_z     < LLN_Z

  if (ratio_low && fvc_low)   return("mixed pattern (suggestive)")
  if (ratio_low)              return("obstructive")
  if (fvc_low)                return("restrictive pattern (suggestive)")
  if (fev1_low)               return("non-specific")
  "normal"
}

#' Grade the severity of an impairment by FEV1 z-score.
#'
#' Uses the five-band scheme reproduced from the ATS/ERS 2022 technical
#' standard table on severity grading by z-score. The cut-offs are
#' applied to the FEV1 z-score regardless of the pattern: severity is
#' a separate axis from the pattern label. Callers decide whether
#' severity should be displayed (it is conventionally hidden for a
#' normal pattern).
#'
#' @param fev1_z FEV1 z-score, single numeric.
#' @return One of "mild", "moderate", "moderately severe", "severe",
#'   "very severe".
#' @keywords internal
grade_severity <- function(fev1_z) {
  if (length(fev1_z) != 1 || !is.numeric(fev1_z) || is.na(fev1_z)) {
    stop("grade_severity needs a single non-missing numeric z-score.",
         call. = FALSE)
  }
  if (fev1_z >= -2.0) return("mild")
  if (fev1_z >= -2.5) return("moderate")
  if (fev1_z >= -3.0) return("moderately severe")
  if (fev1_z >= -4.0) return("severe")
  "very severe"
}

#' Interpret a single reference family's result.
#'
#' Combines classify_pattern and grade_severity into the per-family
#' summary consumed by the UI and the Phase 4 report. Severity is
#' returned as NA_character_ when the pattern is normal: the 2022
#' framework grades severity only in the presence of impairment.
#'
#' @param reference_df A long-form data.frame as returned by any
#'   wrapper in R/gli_2012.R, R/gli_2022.R, or R/nhanes3.R. Must contain
#'   rows for FEV1, FVC, and FEV1FVC.
#' @return A named list with elements pattern, severity, fev1_z, fvc_z,
#'   fev1_fvc_z.
#' @keywords internal
interpret_spirometry <- function(reference_df) {
  required <- c("parameter", "z_score")
  missing_cols <- setdiff(required, names(reference_df))
  if (length(missing_cols) > 0) {
    stop(sprintf("reference_df is missing required columns: %s",
                 paste(missing_cols, collapse = ", ")),
         call. = FALSE)
  }
  z <- setNames(reference_df$z_score, reference_df$parameter)
  for (p in c("FEV1", "FVC", "FEV1FVC")) {
    if (!(p %in% names(z)) || is.na(z[[p]])) {
      stop(sprintf("reference_df is missing a z-score for %s.", p),
           call. = FALSE)
    }
  }
  pattern <- classify_pattern(
    fev1_z = unname(z[["FEV1"]]),
    fvc_z = unname(z[["FVC"]]),
    fev1_fvc_z = unname(z[["FEV1FVC"]])
  )
  severity <- if (pattern == "normal") {
    NA_character_
  } else {
    grade_severity(unname(z[["FEV1"]]))
  }
  list(
    pattern    = pattern,
    severity   = severity,
    fev1_z     = unname(z[["FEV1"]]),
    fvc_z      = unname(z[["FVC"]]),
    fev1_fvc_z = unname(z[["FEV1FVC"]])
  )
}
