# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: ui_components
# Purpose: Reusable bslib UI fragments. Functions here return tag lists
# only; they do not register reactives or read inputs.

#' Input card for subject demographics and observed spirometry values.
#'
#' Ethnicity selectors are reference-equation-specific: GLI accepts five
#' categories, NHANES III three. Both are surfaced so the operator can
#' match the labels used in the respective source papers.
#'
#' @keywords internal
subject_input_card <- function() {
  bslib::card(
    bslib::card_header("Subject"),
    bslib::card_body(
      shiny::numericInput("age_years", "Age (years)",
                          value = 40, min = 3, max = 95, step = 1),
      shiny::numericInput("height_cm", "Height (cm)",
                          value = 170, min = 50, max = 230, step = 0.5),
      shiny::selectInput("sex_code", "Sex",
                         choices = SEX_CODES, selected = SEX_CODES[["Male"]]),
      shiny::selectInput("ethnicity_gli", "Ethnicity (GLI-2012)",
                         choices = GLI_ETHNICITY,
                         selected = GLI_ETHNICITY[["Caucasian"]]),
      shiny::selectInput("ethnicity_nhanes3", "Ethnicity (NHANES III)",
                         choices = NHANES3_ETHNICITY,
                         selected = NHANES3_ETHNICITY[["Caucasian"]]),
      shiny::numericInput("fev1", "Observed FEV1 (L)",
                          value = 3.20, min = 0.1, max = 8, step = 0.01),
      shiny::numericInput("fvc", "Observed FVC (L)",
                          value = 4.00, min = 0.1, max = 10, step = 0.01)
    )
  )
}

#' Card displaying one reference family's results in a tabular form.
#'
#' The card is populated by a Shiny output element identified by
#' \code{output_id}. The renderer in app.R produces an HTML table from
#' the long-form data.frame returned by the wrappers.
#' @keywords internal
results_card <- function(title, subtitle, output_id) {
  bslib::card(
    bslib::card_header(title),
    bslib::card_body(
      shiny::tags$p(subtitle, class = "text-muted small mb-2"),
      shiny::uiOutput(output_id)
    )
  )
}

#' Render a long-form reference result data.frame as an HTML table.
#'
#' Used inside renderUI in app.R. Returns an HTML table fragment with
#' rounded numeric columns. A row whose z-score sits below -1.645 is
#' flagged with a "below LLN" label in the parameter column; no other
#' interpretation is attached at this stage (full classification lives
#' in Phase 3).
#' @keywords internal
render_reference_table <- function(reference_df) {
  if (is.null(reference_df)) {
    return(shiny::tags$em("Enter values to compute results."))
  }
  flag_below_lln <- function(z) {
    !is.na(z) && z < -1.645
  }
  display <- data.frame(
    Parameter   = ifelse(
      vapply(reference_df$z_score, flag_below_lln, logical(1)),
      paste(reference_df$parameter, "(below LLN)"),
      reference_df$parameter
    ),
    Observed    = sprintf("%.2f", reference_df$observed),
    Predicted   = sprintf("%.2f", reference_df$predicted),
    LLN         = sprintf("%.2f", reference_df$lln),
    `Z-score`   = sprintf("%.2f", reference_df$z_score),
    `% pred`    = sprintf("%.1f", reference_df$percent_predicted),
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
  shiny::HTML(
    knitr_kable_or_fallback(display)
  )
}

#' Minimal HTML table builder.
#'
#' knitr is not a project dependency; this helper produces a small
#' bootstrap-styled table directly to avoid pulling in extra packages.
#' @keywords internal
knitr_kable_or_fallback <- function(df) {
  header_cells <- paste0("<th>", names(df), "</th>", collapse = "")
  body_rows <- vapply(seq_len(nrow(df)), function(i) {
    cells <- paste0("<td>", unlist(df[i, ]), "</td>", collapse = "")
    paste0("<tr>", cells, "</tr>")
  }, character(1))
  paste0(
    "<table class=\"table table-sm table-borderless\">",
    "<thead><tr>", header_cells, "</tr></thead>",
    "<tbody>", paste(body_rows, collapse = ""), "</tbody>",
    "</table>"
  )
}
