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

#' Standard disclaimer shown in the UI footer and on exported reports.
#' @keywords internal
DISCLAIMER_TEXT <- "For research and educational purposes. Not for clinical decision-making."
