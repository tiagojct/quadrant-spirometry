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

#' Card displaying one reference family's results.
#'
#' The card is populated by three Shiny output elements: a coloured
#' classification badge (\code{badge_output_id}) that surfaces the
#' ATS/ERS 2022 pattern and severity grade at a glance, the results
#' table (\code{output_id}), and the full interpretation block
#' (\code{interpretation_output_id}). The per-family mini-gauge that
#' lived here previously was retired: the hero cross-family chart at
#' the top of the page already shows the same z-scores in higher
#' detail, and the duplication was crowding the card.
#' @keywords internal
results_card <- function(title, subtitle, badge_output_id, output_id,
                         interpretation_output_id) {
  bslib::card(
    bslib::card_header(title),
    bslib::card_body(
      shiny::tags$p(subtitle, class = "text-muted small mb-1"),
      shiny::uiOutput(badge_output_id),
      shiny::uiOutput(output_id),
      shiny::tags$hr(class = "my-2"),
      shiny::uiOutput(interpretation_output_id)
    )
  )
}

#' Render the classification badge for one reference family.
#'
#' Produces a coloured pill that displays the ATS/ERS 2022 pattern,
#' and, when impairment is present, the severity grade. The pill
#' background colour matches the severity band the FEV1 z-score sits
#' in; a normal pattern uses the same green as the normal band on the
#' chart. Visual emphasis only, no diagnostic semantics.
#' @keywords internal
render_pattern_badge <- function(interpretation) {
  if (is.null(interpretation)) {
    return(shiny::tags$em("Enter values to classify."))
  }
  severity <- interpretation$severity
  pattern  <- interpretation$pattern

  palette <- list(
    normal              = list(bg = "#86efac", fg = "#0f172a"),
    mild                = list(bg = "#facc15", fg = "#0f172a"),
    moderate            = list(bg = "#f59e0b", fg = "#0f172a"),
    `moderately severe` = list(bg = "#ea580c", fg = "#ffffff"),
    severe              = list(bg = "#dc2626", fg = "#ffffff"),
    `very severe`       = list(bg = "#b91c1c", fg = "#ffffff")
  )
  key <- if (is.na(severity)) "normal" else severity
  colours <- palette[[key]]
  if (is.null(colours)) colours <- list(bg = "#94a3b8", fg = "#0f172a")

  label <- if (is.na(severity)) {
    toupper(pattern)
  } else {
    sprintf("%s · %s", toupper(pattern), severity)
  }

  shiny::tags$div(
    style = paste(
      "background:", colours$bg, ";",
      "color:", colours$fg, ";",
      "border-radius: 9999px;",
      "padding: 6px 14px;",
      "display: inline-block;",
      "font-weight: 700;",
      "font-size: 0.95rem;",
      "letter-spacing: 0.02em;",
      "margin: 6px 0 10px 0;"
    ),
    label
  )
}

#' Render the per-family interpretation block.
#'
#' Displays the ATS/ERS 2022 pattern label and, where applicable, the
#' severity grade by FEV1 z-score. Wording stays cautious: there is no
#' diagnostic language, and patterns that require static lung volumes
#' to confirm are flagged as suggestive in the label itself.
#' @keywords internal
render_interpretation <- function(interpretation) {
  if (is.null(interpretation)) {
    return(shiny::tags$em("Enter values to interpret."))
  }
  pattern_line <- shiny::tags$p(
    shiny::tags$span("Pattern: ", class = "text-muted small"),
    shiny::tags$span(interpretation$pattern),
    class = "mb-1"
  )
  severity_line <- if (is.na(interpretation$severity)) {
    shiny::tags$p(
      shiny::tags$span("Severity: ", class = "text-muted small"),
      shiny::tags$span("not graded (pattern is normal)"),
      class = "mb-0"
    )
  } else {
    shiny::tags$p(
      shiny::tags$span("Severity (by FEV1 z-score): ", class = "text-muted small"),
      shiny::tags$span(interpretation$severity),
      class = "mb-0"
    )
  }
  shiny::div(pattern_line, severity_line)
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

#' Comparison panel showing all three reference families on a shared
#' z-axis, plus a brief text note when GLI-2012 and GLI-Global 2022
#' disagree on the above or below LLN classification.
#' @keywords internal
gli_comparison_panel <- function() {
  bslib::card(
    bslib::card_header("Cross-family z-score comparison"),
    bslib::card_body(
      shiny::uiOutput("comparison_chart"),
      shiny::tags$hr(class = "my-2"),
      shiny::uiOutput("gli_comparison_text")
    )
  )
}

#' Render the body of the GLI-2012 vs GLI-Global 2022 text note.
#'
#' Highlights any spirometry parameter where the above or below LLN
#' classification differs between the two GLI families. The chart
#' above already conveys the magnitudes; this note exists to surface
#' the categorical flip in words.
#' @keywords internal
render_gli_comparison <- function(gli_2012_df, gli_2022_df) {
  if (is.null(gli_2012_df) || is.null(gli_2022_df)) {
    return(shiny::tags$em("Enter values to compare equations."))
  }
  threshold <- -1.645
  below_lln_2012 <- gli_2012_df$z_score < threshold
  below_lln_2022 <- gli_2022_df$z_score < threshold
  flipped <- below_lln_2012 != below_lln_2022

  if (!any(flipped)) {
    return(shiny::div(
      shiny::tags$p(
        "GLI-2012 and GLI-Global 2022 classify every parameter on the same side of the lower limit of normal."
      ),
      shiny::tags$p(class = "text-muted small",
                    "Differences in z-score remain, even when classification agrees.")
    ))
  }

  rows <- vapply(which(flipped), function(i) {
    sprintf(
      "%s: GLI-2012 z = %.2f (%s); GLI-Global 2022 z = %.2f (%s).",
      gli_2012_df$parameter[i],
      gli_2012_df$z_score[i],
      if (below_lln_2012[i]) "below LLN" else "within LLN",
      gli_2022_df$z_score[i],
      if (below_lln_2022[i]) "below LLN" else "within LLN"
    )
  }, character(1))

  shiny::div(
    shiny::tags$p("Classification differs for:"),
    shiny::tags$ul(lapply(rows, shiny::tags$li))
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
