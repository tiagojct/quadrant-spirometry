# Quadrant

## What this is

Quadrant is an R Shiny app for spirometry reference value calculation and interpretation. It compares GLI-2012 and GLI-Global 2022 reference equations side by side, classifies results per ATS/ERS 2022 standards, and exports a structured report.

Quadrant is a reference value calculator and decision support tool, not a medical device. Outputs use language such as "predicted values", "z-score", and "below lower limit of normal". The app makes no diagnostic claims.

For research and educational purposes. Not for clinical decision-making.

## Current status

Phase 1: manual entry with side-by-side GLI-2012 and NHANES III calculations.

The app accepts age, sex, height in centimetres, ethnicity (with separate dropdowns for the GLI and NHANES III category systems, since they differ), and observed FEV1 and FVC. It returns predicted, lower limit of normal, z-score, and percent of predicted for FEV1, FVC, and FEV1/FVC under each reference equation, displayed side by side so the operator can see how the classification of the same subject shifts between a 1999 and a 2012 reference equation.

Pattern classification (ATS/ERS 2022) and PDF export arrive in Phase 3 and Phase 4 respectively. Subsequent phases are described in ROADMAP.md.

## How to run locally

Requirements:

- R 4.4 or newer
- The renv package, installed once with `install.packages("renv")`

Steps, from the repository root:

```r
renv::restore()
shiny::runApp()
```

`renv::restore()` installs the package versions recorded in `renv.lock` into a project-local library. `shiny::runApp()` reads `app.R` and serves the app at a local URL printed to the R console.

## How to run the tests

```r
setwd("tests")
source("testthat.R")
```

The suite sources the files in `R/` directly (Quadrant is a Shiny app, not an R package) and runs the calculation-layer tests against fixtures in `tests/testthat/fixtures/`.

## License

AGPL-3.0-or-later. See the LICENSE file for the full text. Any derivative work, including network-deployed forks, must remain open under the same terms.
