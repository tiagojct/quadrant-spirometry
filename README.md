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

Each results panel carries an interpretation block under the table, using the ATS/ERS 2022 interpretive strategy (Stanojevic et al., ERJ 2022). Patterns are labelled normal, obstructive, restrictive pattern (suggestive), mixed pattern (suggestive), or non-specific. Restrictive and mixed labels are explicitly marked as suggestive because confirming them requires static lung volumes that Quadrant does not accept. Severity is graded by FEV1 z-score in five bands when impairment is present, and reported as "not graded (pattern is normal)" otherwise.

A cross-family comparison chart sits at the top of the page as the hero visual. It shows all three reference families on a common z-axis, one row per parameter, with a horizontal legend strip naming the severity bands and a dashed line at the lower limit of normal. A short text note beneath the chart flags any parameter where GLI-2012 and GLI-Global 2022 disagree on the above or below LLN classification.

Each per-family card below carries a coloured classification badge at the top, labelled with the ATS/ERS 2022 pattern and severity grade (for example, OBSTRUCTIVE · severe on a red pill, NORMAL on a green pill). The pill colour matches the severity band the FEV1 z-score sits in. Visual emphasis only, no diagnostic semantics.

A "Download HTML report" button in the sidebar exports a self-contained HTML file with the inputs, the embedded cross-family SVG chart, the per-family tables, badges, and interpretation blocks, the disclaimer, and a timestamp. Use the browser's Print menu on the downloaded HTML to produce a PDF. Native PDF export is deferred to a follow-up phase to avoid requiring a LaTeX or Typst toolchain on every host.

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

## Deploy to Posit Connect Cloud

Quadrant is set up to deploy to Posit Connect Cloud (PCC) directly from this repository's main branch.

Prerequisites:

- A Posit Connect Cloud account (free tier available at https://connect.posit.cloud)
- The GitHub repository connected to your PCC account

Steps:

1. Sign in to https://connect.posit.cloud
2. Choose "Publish" then "GitHub repository"
3. Select `tiagojct/quadrant-spirometry`, branch `main`, entry point `app.R`
4. Confirm and publish

PCC reads `renv.lock`, restores the package library, and serves the Shiny app. The Quarto CLI is required by the Download HTML report feature; PCC's content images ship with a recent Quarto.

Smoke test after each deploy:

- Open the deployed URL in a desktop browser, verify the hero chart, the per-family cards, the classification badges, and the Download HTML report flow
- Resize to tablet (around 1024 pixels wide) and phone (around 375 pixels wide) widths and verify the layout reflows without clipping content
- Confirm the disclaimer is visible in the footer

## Continuous integration

A GitHub Actions workflow in `.github/workflows/check.yaml` runs the testthat suite on every push to `main` and every pull request. It restores the package library from `renv.lock` and executes `tests/testthat.R`. The Quarto CLI is not required by the test suite, so the workflow does not install it.

## License

AGPL-3.0-or-later. See the LICENSE file for the full text. Any derivative work, including network-deployed forks, must remain open under the same terms.
