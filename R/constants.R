# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: constants
# Purpose: Project-wide constants and lookup tables. No magic numbers in
# calculation code; everything named here. Lookup labels are taken
# verbatim from the source papers.

#' Sex codes used by rspiro.
#'
#' Both rspiro::pred_GLI and rspiro::pred_NHANES3 take an integer
#' \code{gender} argument with 1 = male, 2 = female. The labels here are
#' the strings displayed in the UI.
#' @keywords internal
SEX_CODES <- c(
  "Male"   = 1L,
  "Female" = 2L
)

#' GLI-2012 ethnicity codes.
#'
#' Labels are verbatim from Quanjer et al., ERJ 2012,
#' doi:10.1183/09031936.00080312, and from the rspiro::pred_GLI
#' documentation. Integer codes match rspiro's \code{ethnicity} argument.
#' @keywords internal
GLI_ETHNICITY <- c(
  "Caucasian"        = 1L,
  "African-American" = 2L,
  "NE Asian"         = 3L,
  "SE Asian"         = 4L,
  "Other/mixed"      = 5L
)

#' NHANES III ethnicity codes.
#'
#' Labels are verbatim from Hankinson et al., AJRCCM 1999,
#' doi:10.1164/ajrccm.159.1.9712108, and from the rspiro::pred_NHANES3
#' documentation. NHANES III recognises three categories. Integer codes
#' match rspiro's \code{ethnicity} argument.
#' @keywords internal
NHANES3_ETHNICITY <- c(
  "Caucasian"        = 1L,
  "African-American" = 2L,
  "Mexican-American" = 3L
)

#' Spirometry parameters reported by every reference equation wrapper.
#'
#' Order is intentional and is preserved in the long-form result
#' data.frame returned by the wrappers. FEV1FVC is the ratio of FEV1 to
#' FVC and is treated as a parameter in its own right, with its own
#' predicted value, LLN, and z-score.
#' @keywords internal
SPIROMETRY_PARAMS <- c("FEV1", "FVC", "FEV1FVC")

#' Age range in years supported by the GLI-2012 and GLI-Global 2022
#' equations. rspiro returns NA outside this range.
#' @keywords internal
GLI_AGE_RANGE_YEARS <- c(3, 95)

#' Age range in years of the NHANES III reference population
#' (Hankinson et al. 1999). rspiro does not stop outside this range and
#' extrapolates, so the wrapper enforces the range.
#' @keywords internal
NHANES3_AGE_RANGE_YEARS <- c(8, 80)

#' Plausible physiological age range in years. Used only as the default
#' check when a wrapper passes no equation-specific range.
#' @keywords internal
PLAUSIBLE_AGE_RANGE_YEARS <- c(0, 120)

#' Plausible standing height range in centimetres, also used by the UI.
#' @keywords internal
HEIGHT_RANGE_CM <- c(50, 250)

#' Path of the Quarto report template, relative to the app directory.
#' Shiny runs with the app directory as working directory.
#' @keywords internal
REPORT_TEMPLATE_PATH <- file.path("inst", "report_template.qmd")

#' Z-score cut-off used as the lower limit of normal in the ATS/ERS 2022
#' framework (the 5th percentile). The same threshold applies to FEV1,
#' FVC and FEV1/FVC. Every module reads this one value.
#' @keywords internal
LLN_Z <- -1.645

#' Lower z-score bound of the "mild" severity level (FEV1 z-score of
#' this value or higher is mild).
#' @keywords internal
SEVERITY_MILD_Z_MIN <- -2.5

#' Lower z-score bound of the "moderate" severity level. Below this
#' value the severity is "severe".
#' @keywords internal
SEVERITY_MODERATE_Z_MIN <- -4.0

#' Standard disclaimer shown in the UI footer and on exported reports.
#' @keywords internal
DISCLAIMER_TEXT <- "For research and educational purposes. Not for clinical decision-making."
