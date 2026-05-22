# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later

library(shiny)
library(bslib)

source("R/constants.R")
source("R/wrapper_helpers.R")
source("R/gli_2012.R")
source("R/gli_2022.R")
source("R/nhanes3.R")
source("R/ui_components.R")

ui <- page_sidebar(
  theme = bs_theme(version = 5),
  title = "Quadrant",
  sidebar = sidebar(
    title = "Inputs",
    width = 320,
    subject_input_card()
  ),
  layout_columns(
    col_widths = c(4, 4, 4),
    results_card(
      title    = "GLI-2012",
      subtitle = "Quanjer et al., ERJ 2012",
      output_id = "results_gli_2012"
    ),
    results_card(
      title    = "GLI-Global 2022 (race-neutral)",
      subtitle = "Bowerman et al., AJRCCM 2023",
      output_id = "results_gli_2022"
    ),
    results_card(
      title    = "NHANES III",
      subtitle = "Hankinson et al., AJRCCM 1999",
      output_id = "results_nhanes3"
    )
  ),
  gli_comparison_panel(),
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

  output$results_gli_2012 <- renderUI({
    render_reference_table(results_gli_2012())
  })
  output$results_gli_2022 <- renderUI({
    render_reference_table(results_gli_2022())
  })
  output$results_nhanes3 <- renderUI({
    render_reference_table(results_nhanes())
  })
  output$gli_comparison_text <- renderUI({
    render_gli_comparison(results_gli_2012(), results_gli_2022())
  })
}

shinyApp(ui, server)
