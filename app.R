# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later

library(shiny)
library(bslib)

disclaimer_text <- "For research and educational purposes. Not for clinical decision-making."

ui <- page_fillable(
  theme = bs_theme(version = 5),
  title = "Quadrant",
  card(
    card_header("Quadrant"),
    card_body(
      p("Phase 0 ready.")
    ),
    card_footer(
      tags$small(disclaimer_text)
    )
  )
)

server <- function(input, output, session) {
}

shinyApp(ui, server)
