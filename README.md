# Quadrant

## What this is

Quadrant is an R Shiny app for spirometry reference value calculation and interpretation. It compares GLI-2012 and GLI-Global 2022 reference equations side by side, classifies results per ATS/ERS 2022 standards, and exports a structured report.

Quadrant is a reference value calculator and decision support tool, not a medical device. Outputs use language such as "predicted values", "z-score", and "below lower limit of normal". The app makes no diagnostic claims.

For research and educational purposes. Not for clinical decision-making.

## Current status

Phase 0: project scaffold. The app launches a minimal Shiny page with a placeholder card and the standard disclaimer. No calculation logic is wired up yet. Subsequent phases are described in ROADMAP.md.

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

## License

AGPL-3.0-or-later. See the LICENSE file for the full text. Any derivative work, including network-deployed forks, must remain open under the same terms.
