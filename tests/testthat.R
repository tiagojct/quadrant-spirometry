# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# testthat entry point. Tests source the R/ files directly because
# Quadrant is a Shiny app, not an R package.

library(testthat)

# Run from the project root so that .Rprofile activates renv. Also
# works when started from tests/.
project_root <- normalizePath(getwd())
if (!dir.exists(file.path(project_root, "R"))) {
  project_root <- normalizePath(file.path(project_root, ".."))
}
r_dir <- file.path(project_root, "R")
for (f in list.files(r_dir, pattern = "\\.R$", full.names = TRUE)) {
  source(f, local = FALSE)
}

test_dir(file.path(project_root, "tests", "testthat"), reporter = "summary", stop_on_failure = TRUE)
