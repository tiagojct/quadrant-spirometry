# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# testthat entry point. Tests source the R/ files directly because
# Quadrant is a Shiny app, not an R package.

library(testthat)

project_root <- normalizePath(file.path(getwd(), ".."))
r_dir <- file.path(project_root, "R")
for (f in list.files(r_dir, pattern = "\\.R$", full.names = TRUE)) {
  source(f, local = FALSE)
}

test_dir("testthat", reporter = "summary", stop_on_failure = TRUE)
