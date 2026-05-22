# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Module: report
# Purpose: Assemble the data needed for the Quarto report at
# inst/report_template.qmd and drive the rendering call. The
# template itself is a thin shell that reads a pre-built RDS bundle;
# all HTML fragments (tables, badges, interpretation blocks, chart
# SVG) are produced here so the template stays free of R dependencies
# beyond base R.

#' Convert a shiny tag, HTML object, or character string into a plain
#' HTML character string.
#' @keywords internal
to_html_string <- function(x) {
  if (is.null(x))                      return("")
  if (is.character(x))                 return(paste(x, collapse = ""))
  if (inherits(x, "shiny.tag"))        return(as.character(htmltools::as.tags(x)))
  if (inherits(x, "shiny.tag.list"))   return(as.character(htmltools::as.tags(x)))
  if (inherits(x, "html"))             return(as.character(x))
  as.character(x)
}

#' Build a long-form reference data.frame into an HTML table fragment
#' that matches the on-screen table.
#' @keywords internal
reference_table_html <- function(reference_df) {
  if (is.null(reference_df)) return("<em>No data.</em>")
  display <- data.frame(
    Parameter   = reference_df$parameter,
    Observed    = sprintf("%.2f", reference_df$observed),
    Predicted   = sprintf("%.2f", reference_df$predicted),
    LLN         = sprintf("%.2f", reference_df$lln),
    `Z-score`   = sprintf("%.2f", reference_df$z_score),
    `% pred`    = sprintf("%.1f", reference_df$percent_predicted),
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
  knitr_kable_or_fallback(display)
}

#' Resolve the integer code used by rspiro back to the operator-facing
#' label defined in R/constants.R.
#' @keywords internal
ethnicity_label_from_code <- function(code, table) {
  if (is.null(code) || is.na(code)) return("")
  match <- names(table)[table == as.integer(code)]
  if (length(match) == 0) "" else match[[1]]
}

#' Resolve the integer sex code back to its operator-facing label.
#' @keywords internal
sex_label_from_code <- function(code) {
  ethnicity_label_from_code(code, SEX_CODES)
}

#' Assemble the bundle consumed by the Quarto template.
#'
#' The bundle is the only data the template sees. Every HTML fragment
#' is pre-rendered, so the template needs no R packages other than
#' base R to expand it.
#' @keywords internal
prepare_report_bundle <- function(subject, results, interpretations,
                                  chart_svg, comparison_text) {
  family_blocks <- list()
  family_subtitles <- list(
    "GLI-2012"                       = "Quanjer et al., ERJ 2012",
    "GLI-Global 2022 (race-neutral)" = "Bowerman et al., AJRCCM 2023",
    "NHANES III"                     = "Hankinson et al., AJRCCM 1999"
  )
  family_keys <- list(
    "GLI-2012"                       = "gli_2012",
    "GLI-Global 2022 (race-neutral)" = "gli_2022",
    "NHANES III"                     = "nhanes3"
  )
  for (display_name in names(family_subtitles)) {
    key <- family_keys[[display_name]]
    family_blocks[[display_name]] <- list(
      subtitle = family_subtitles[[display_name]],
      badge_html = to_html_string(render_pattern_badge(interpretations[[key]])),
      table_html = reference_table_html(results[[key]]),
      interpretation_html = to_html_string(render_interpretation(interpretations[[key]]))
    )
  }
  list(
    subject = subject,
    chart_svg = chart_svg,
    comparison_text_html = to_html_string(comparison_text),
    family_blocks = family_blocks,
    timestamp = Sys.time()
  )
}

#' Render the Quadrant report to a file.
#'
#' Writes the bundle to a temp RDS, copies the Quarto template into
#' the same directory, and asks Quarto to render it. Returns the
#' absolute path to the rendered output file.
#'
#' @param bundle The list produced by \code{prepare_report_bundle}.
#' @param output_format One of "html" or "pdf". HTML is always
#'   available; PDF requires a working Quarto PDF backend on the
#'   host (Typst or a LaTeX distribution).
#' @return Absolute path to the rendered file.
#' @keywords internal
render_quadrant_report <- function(bundle, output_format = "html") {
  if (!output_format %in% c("html", "pdf")) {
    stop("output_format must be 'html' or 'pdf'.", call. = FALSE)
  }
  workdir <- tempfile("quadrant_report_")
  dir.create(workdir)
  bundle_path <- file.path(workdir, "bundle.rds")
  saveRDS(bundle, bundle_path)

  template_src <- "inst/report_template.qmd"
  template_dst <- file.path(workdir, "report.qmd")
  file.copy(template_src, template_dst, overwrite = TRUE)

  quarto::quarto_render(
    input = template_dst,
    output_format = output_format,
    execute_params = list(bundle_path = bundle_path),
    quiet = TRUE
  )

  ext <- output_format
  rendered <- file.path(workdir, paste0("report.", ext))
  if (!file.exists(rendered)) {
    stop(sprintf("Report rendering did not produce a file at %s.",
                 rendered),
         call. = FALSE)
  }
  rendered
}
