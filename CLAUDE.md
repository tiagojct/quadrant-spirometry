# Quadrant

R Shiny app for spirometry reference value calculation and interpretation. Compares GLI-2012 and GLI-Global 2022 reference equations side by side, classifies per ATS/ERS 2022 standards, and exports a structured report.

Codename: quadrant, after Chapter 118 of Moby Dick. A quadrant is a navigational instrument that positions a measurement against an external reference. So does this app.

## Scope and boundaries

This is a reference value calculator and decision support tool, NOT a medical device.

- No diagnostic claims in UI text, exports, or documentation.
- Outputs use language such as "predicted values", "z-score", "below lower limit of normal", and "pattern consistent with...", never "the patient has...".
- A disclaimer appears in the UI footer and on every exported report: "For research and educational purposes. Not for clinical decision-making."

## License

AGPL-3.0-or-later. A LICENSE file containing the standard AGPL-3.0 text lives at the repo root. Any derivative work, including network-deployed forks, must remain open under the same terms.

## Audience

- Primary: pulmonologists and respiratory medicine residents
- Secondary: MIS (Mestrado em Informática da Saúde) students at FMUP, and the wider ERS audience
- Operator workflow: clinician enters values manually. PDF extraction is out of scope for v1.

## Stack

- R 4.4 or newer
- Shiny 1.9 or newer, bslib for theming
- rspiro 0.5 or newer for both GLI-2012 (pred_GLI, LLN_GLI, zscore_GLI) and GLI-Global 2022 race-neutral (pred_GLIgl, LLN_GLIgl, zscore_GLIgl). Reference: Bowerman et al., AJRCCM 2023, doi:10.1164/rccm.202205-0963OC.
- Reports: quarto
- Tests: testthat for calculation logic; shinytest2 only if a specific UI bug requires it
- Reproducibility: renv
- Hosting target: Posit Connect Cloud as primary, shinyapps.io as backup

## Repository structure

```
quadrant/
├── CLAUDE.md
├── ROADMAP.md
├── README.md
├── LICENSE
├── .gitignore
├── renv.lock
├── app.R
├── R/
│   ├── gli_2012.R
│   ├── gli_2022.R
│   ├── interpretation.R
│   ├── report.R
│   ├── constants.R
│   └── ui_components.R
├── inst/
│   └── report_template.qmd
├── data-raw/
├── data/
└── tests/
    └── testthat/
```

## Coding conventions

- tidyverse style, snake_case throughout
- Pure functions for all calculation logic. No Shiny session state inside R/ files.
- Every reference equation wrapper takes named arguments and returns a tibble with columns: predicted, lln, uln, z_score, percent_predicted.
- No magic numbers in code. Constants live in R/constants.R; lookup tables in data/.
- Comments in English. User-facing text in English at first; Portuguese later via shiny.i18n.
- Function headers in roxygen2 style even though this is not a package.

## Style rules for all text the assistant generates

- No emojis anywhere (code, comments, UI, README, commit messages).
- No em-dashes. Use commas, colons, or restructure.
- No bold for emphasis in UI text; rely on layout hierarchy.
- No marketing language ("seamlessly", "effortlessly", "powerful", "leverage", "robust"). Plain descriptive English only.
- No exclamation marks in UI text or documentation.

## Validation requirements

Every reference equation wrapper must:

- Reproduce at least 5 reference cases per equation family from official GLI documentation, stored under tests/testthat/fixtures/
- Match the official GLI calculator output to within 0.01 for predicted, LLN, ULN, and z-score
- Fail loudly with informative messages when inputs fall outside supported age, height, or ethnicity ranges

## What NOT to do

- Do not introduce a database. Inputs are session-scoped only and discarded on session end.
- Do not store patient data anywhere, in any form, at any time.
- Do not add user accounts, authentication, analytics, or telemetry.
- Do not output text that claims a diagnosis or recommends clinical action.
- Do not invent reference equation coefficients. Rely on rspiro. If a discrepancy with the official GLI calculator appears, stop and ask.
- Do not add dependencies beyond shiny, bslib, rspiro, quarto, testthat, and renv without proposing it first and waiting for approval.
- Do not start a new phase from ROADMAP.md without explicit confirmation that the previous phase is accepted.

## Decisions log

Append-only. Date format YYYY-MM-DD. New entries at the bottom.

- 2026-05-21: Project initialised. Codename: quadrant. License: AGPL-3.0-or-later. Stack chosen: R Shiny, bslib, rspiro >= 0.5, quarto, renv. rspiro confirmed to support both GLI-2012 and GLI-Global 2022 natively, removing the need for hand-implemented coefficients.
