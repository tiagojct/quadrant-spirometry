# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later

library(shiny)
library(bslib)

source("R/constants.R")
source("R/wrapper_helpers.R")
source("R/gli_2012.R")
source("R/gli_2022.R")
source("R/nhanes3.R")
source("R/interpretation.R")
source("R/visuals.R")
source("R/ui_components.R")
source("R/report.R")

ui <- page_sidebar(
  theme = bs_theme(version = 5),
  title = "Quadrant",
  fillable = FALSE,
  sidebar = sidebar(
    title = "Inputs",
    width = 320,
    subject_input_card(),
    tags$hr(),
    tags$h6("Report", class = "mt-2 mb-2"),
    downloadButton("download_html", "Download HTML report",
                   class = "btn-sm w-100"),
    tags$p(
      class = "text-muted small mt-2 mb-0",
      "PDF: use the browser's Print menu on the downloaded HTML."
    )
  ),
  gli_comparison_panel(),
  layout_columns(
    col_widths = c(4, 4, 4),
    results_card(
      title    = "GLI-2012",
      subtitle = "Quanjer et al., ERJ 2012",
      badge_output_id = "badge_gli_2012",
      output_id = "results_gli_2012",
      interpretation_output_id = "interpretation_gli_2012"
    ),
    results_card(
      title    = "GLI-Global 2022 (race-neutral)",
      subtitle = "Bowerman et al., AJRCCM 2023",
      badge_output_id = "badge_gli_2022",
      output_id = "results_gli_2022",
      interpretation_output_id = "interpretation_gli_2022"
    ),
    results_card(
      title    = "NHANES III",
      subtitle = "Hankinson et al., AJRCCM 1999",
      badge_output_id = "badge_nhanes3",
      output_id = "results_nhanes3",
      interpretation_output_id = "interpretation_nhanes3"
    )
  ),
  tags$footer(
    class = "border-top mt-3 pt-2 text-muted small",
    DISCLAIMER_TEXT
  )
)

server <- function(input, output, session) {
  inputs_ready <- reactive({
    all(
      isTruthy(input$age_years),
      isTruthy(input$height_cm),
      isTruthy(input$sex_code),
      isTruthy(input$ethnicity_gli),
      isTruthy(input$ethnicity_nhanes3),
      isTruthy(input$fev1),
      isTruthy(input$fvc),
      is.numeric(input$fev1), input$fev1 > 0,
      is.numeric(input$fvc),  input$fvc  > 0,
      input$fev1 <= input$fvc
    )
  })

  results_gli_2012 <- reactive({
    if (!inputs_ready()) return(NULL)
    tryCatch(
      compute_gli_2012(
        age_years      = input$age_years,
        height_cm      = input$height_cm,
        sex_code       = as.integer(input$sex_code),
        ethnicity_code = as.integer(input$ethnicity_gli),
        fev1           = input$fev1,
        fvc            = input$fvc
      ),
      error = function(e) {
        message("GLI-2012 wrapper error: ", conditionMessage(e))
        NULL
      }
    )
  })

  results_gli_2022 <- reactive({
    if (!inputs_ready()) return(NULL)
    tryCatch(
      compute_gli_global_2022(
        age_years = input$age_years,
        height_cm = input$height_cm,
        sex_code  = as.integer(input$sex_code),
        fev1      = input$fev1,
        fvc       = input$fvc
      ),
      error = function(e) {
        message("GLI-Global 2022 wrapper error: ", conditionMessage(e))
        NULL
      }
    )
  })

  results_nhanes <- reactive({
    if (!inputs_ready()) return(NULL)
    tryCatch(
      compute_nhanes3(
        age_years      = input$age_years,
        height_cm      = input$height_cm,
        sex_code       = as.integer(input$sex_code),
        ethnicity_code = as.integer(input$ethnicity_nhanes3),
        fev1           = input$fev1,
        fvc            = input$fvc
      ),
      error = function(e) {
        message("NHANES III wrapper error: ", conditionMessage(e))
        NULL
      }
    )
  })

  interpretation_for <- function(reactive_df) {
    df <- reactive_df()
    if (is.null(df)) return(NULL)
    tryCatch(interpret_spirometry(df),
             error = function(e) {
               message("Interpretation error: ", conditionMessage(e))
               NULL
             })
  }

  interpretation_gli_2012 <- reactive({ interpretation_for(results_gli_2012) })
  interpretation_gli_2022 <- reactive({ interpretation_for(results_gli_2022) })
  interpretation_nhanes3  <- reactive({ interpretation_for(results_nhanes)  })

  output$results_gli_2012 <- renderUI({
    render_reference_table(results_gli_2012())
  })
  output$results_gli_2022 <- renderUI({
    render_reference_table(results_gli_2022())
  })
  output$results_nhanes3 <- renderUI({
    render_reference_table(results_nhanes())
  })

  output$interpretation_gli_2012 <- renderUI({
    render_interpretation(interpretation_gli_2012())
  })
  output$interpretation_gli_2022 <- renderUI({
    render_interpretation(interpretation_gli_2022())
  })
  output$interpretation_nhanes3 <- renderUI({
    render_interpretation(interpretation_nhanes3())
  })

  output$badge_gli_2012 <- renderUI({
    render_pattern_badge(interpretation_gli_2012())
  })
  output$badge_gli_2022 <- renderUI({
    render_pattern_badge(interpretation_gli_2022())
  })
  output$badge_nhanes3 <- renderUI({
    render_pattern_badge(interpretation_nhanes3())
  })

  output$comparison_chart <- renderUI({
    shiny::HTML(cross_family_chart_svg(list(
      "GLI-2012"        = results_gli_2012(),
      "GLI-Global 2022" = results_gli_2022(),
      "NHANES III"      = results_nhanes()
    )))
  })
  output$gli_comparison_text <- renderUI({
    render_gli_comparison(results_gli_2012(), results_gli_2022())
  })

  output$download_html <- downloadHandler(
    filename = function() {
      sprintf("quadrant-report-%s.html", format(Sys.time(), "%Y%m%d-%H%M%S"))
    },
    content = function(file) {
      validate(need(inputs_ready(), "Enter complete values before exporting."))

      subject <- list(
        age_years              = input$age_years,
        height_cm              = input$height_cm,
        sex_label              = sex_label_from_code(input$sex_code),
        ethnicity_gli_label    = ethnicity_label_from_code(input$ethnicity_gli, GLI_ETHNICITY),
        ethnicity_nhanes3_label = ethnicity_label_from_code(input$ethnicity_nhanes3, NHANES3_ETHNICITY),
        fev1                   = input$fev1,
        fvc                    = input$fvc
      )
      results <- list(
        gli_2012 = results_gli_2012(),
        gli_2022 = results_gli_2022(),
        nhanes3  = results_nhanes()
      )
      interpretations <- list(
        gli_2012 = interpretation_gli_2012(),
        gli_2022 = interpretation_gli_2022(),
        nhanes3  = interpretation_nhanes3()
      )
      chart_svg <- cross_family_chart_svg(list(
        "GLI-2012"        = results$gli_2012,
        "GLI-Global 2022" = results$gli_2022,
        "NHANES III"      = results$nhanes3
      ))
      comparison_text <- render_gli_comparison(results$gli_2012, results$gli_2022)

      bundle <- prepare_report_bundle(subject, results, interpretations,
                                      chart_svg, comparison_text)
      rendered <- render_quadrant_report(bundle, output_format = "html")
      file.copy(rendered, file, overwrite = TRUE)
    },
    contentType = "text/html"
  )
}

shinyApp(ui, server)
