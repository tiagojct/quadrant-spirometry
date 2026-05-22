# Quadrant

## What this is

Quadrant is an R Shiny app for spirometry reference value calculation and interpretation. It compares GLI-2012 and GLI-Global 2022 reference equations side by side, classifies results per ATS/ERS 2022 standards, and exports a structured report.

Quadrant is a reference value calculator and decision support tool, not a medical device. Outputs use language such as "predicted values", "z-score", and "below lower limit of normal". The app makes no diagnostic claims.

For research and educational purposes. Not for clinical decision-making.

## Current status

Phase 3: side-by-side comparison across three reference equation families, each with its own ATS/ERS 2022 pattern label and severity grade.

The app accepts age, sex, height in centimetres, ethnicity (with separate dropdowns for the GLI-2012 and NHANES III category systems, since they differ; GLI-Global 2022 is race-neutral and uses neither), and observed FEV1 and FVC. It returns predicted, lower limit of normal, z-score, and percent of predicted for FEV1, FVC, and FEV1/FVC under each of:

- GLI-2012 (Quanjer et al., ERJ 2012)
- GLI-Global 2022 race-neutral (Bowerman et al., AJRCCM 2023)
- NHANES III (Hankinson et al., AJRCCM 1999)

Each results panel carries an interpretation block under the table, using the ATS/ERS 2022 interpretive strategy (Stanojevic et al., ERJ 2022). Patterns are labelled normal, obstructive, restrictive pattern (suggestive), mixed pattern (suggestive), or non-specific. Restrictive and mixed labels are explicitly marked as suggestive because confirming them requires static lung volumes that Quadrant does not accept. Severity is graded by FEV1 z-score in five bands when impairment is present, and reported as "not graded (pattern is normal)" otherwise. A comparison panel below the cards flags any parameter where the above or below LLN classification disagrees between GLI-2012 and GLI-Global 2022.

PDF export arrives in Phase 4. Subsequent phases are described in ROADMAP.md.

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
