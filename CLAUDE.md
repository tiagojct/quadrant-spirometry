# Quadrant

R Shiny app for spirometry reference value calculation and interpretation. Compares modern (GLI-2012, GLI-Global 2022) and older (NHANES III) reference equations side by side, classifies per ATS/ERS 2022 standards, and exports a structured report. The side-by-side view lets the operator see how the classification of a single individual evolves across reference equation generations.

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
- rspiro 0.5 or newer for:
  - GLI-2012: pred_GLI, LLN_GLI, zscore_GLI, pctpred_GLI. Reference: Quanjer et al., ERJ 2012, doi:10.1183/09031936.00080312.
  - GLI-Global 2022 race-neutral: pred_GLIgl, LLN_GLIgl, zscore_GLIgl, pctpred_GLIgl. Reference: Bowerman et al., AJRCCM 2023, doi:10.1164/rccm.202205-0963OC.
  - NHANES III: pred_NHANES3, LLN_NHANES3, zscore_NHANES3, pctpred_NHANES3. Reference: Hankinson et al., AJRCCM 1999, doi:10.1164/ajrccm.159.1.9712108.
- ECSC 1993 (Quanjer) is not provided by rspiro 0.5. Tracked as a wishlist item; would require either an upstream rspiro contribution or a separately vetted implementation. Not in v1 scope.
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
│   ├── constants.R
│   ├── wrapper_helpers.R
│   ├── gli_2012.R
│   ├── gli_2022.R
│   ├── nhanes3.R
│   ├── interpretation.R
│   ├── report.R
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
- Every reference equation wrapper takes named arguments and returns a base R data.frame in long form with columns: parameter, observed, predicted, lln, z_score, percent_predicted. One row per spirometry parameter (FEV1, FVC, FEV1FVC). Rationale for base data.frame: rspiro itself returns base data.frames; introducing tibble would be a new dependency without practical gain.
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

- Reproduce at least 5 reference cases per equation family, stored under tests/testthat/fixtures/. For GLI families, cases must trace to official GLI documentation. For NHANES III, cases trace to Hankinson et al. 1999 (doi:10.1164/ajrccm.159.1.9712108) or the GLI documentation comparison tables.
- Match the official calculator output to within 0.01 for predicted, LLN, and z-score. The 5-case fixture is the wrapper contract layer; an end-to-end cross-check against the official upstream calculator is a manual gate the maintainer signs off on before each phase is marked accepted.
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
- 2026-05-22: Phase 1 scope amended. NHANES III added alongside GLI-2012 so the side-by-side comparison can show the evolution of normality classification from a pre-GLI to a modern reference equation. ECSC 1993 considered and rejected for v1: not provided by rspiro 0.5, and hand-implementing coefficients would violate the no-hand-implementation rule. Tracked as a wishlist item.
- 2026-05-22: Wrapper return type changed from tibble to base R data.frame in long form (one row per parameter). Reason: rspiro itself returns base data.frames, and adopting tibble would introduce a new dependency without practical gain.
- 2026-05-22: ULN column removed from the wrapper contract. The GLI 2012 paper does not define an upper limit of normal; reporting it would require either an unblessed symmetric mirror of LLN or a redefinition. Z-score remains as the directional indicator and is sufficient for the ATS/ERS 2022 interpretation rules in Phase 3.
- 2026-05-22: Phase 2 shipped. GLI-Global 2022 (race-neutral) added as a third side-by-side panel alongside GLI-2012 and NHANES III. The race-neutral equation takes no ethnicity argument, so the wrapper compute_gli_global_2022 omits it. A comparison panel under the three result cards flags any spirometry parameter where the above/below LLN classification differs between GLI-2012 and GLI-Global 2022. Shared input validation and long-form table assembly extracted from R/gli_2012.R into R/wrapper_helpers.R so all three wrappers can reuse them without circular sourcing.
- 2026-05-22: Phase 3 shipped. ATS/ERS 2022 interpretive strategy (Stanojevic et al., ERJ 2022, doi:10.1183/13993003.01499-2021) implemented as pure functions in R/interpretation.R: classify_pattern returns one of normal, obstructive, restrictive pattern (suggestive), mixed pattern (suggestive), non-specific, using only the FEV1, FVC, and FEV1/FVC z-scores. grade_severity returns the five-band scheme (mild, moderate, moderately severe, severe, very severe) by FEV1 z-score. The integrating interpret_spirometry consumes the long-form data.frame from any wrapper and returns a list with pattern and severity. The boundary at z = -1.645 is inclusive of "normal": only values strictly below LLN trigger a defect label. Restrictive and mixed patterns are explicitly labelled "(suggestive)" because confirming them requires static lung volumes that Quadrant does not accept. Severity is reported as NA when the pattern is normal; the UI shows "not graded (pattern is normal)" in that case. Each per-family results card now carries its own interpretation block below the table, so the operator can see how the pattern label itself, not just the z-scores, shifts across reference equation generations. No new dependencies.
