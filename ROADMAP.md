# Roadmap

Each phase is roughly one weekend of focused work. Do not start a new phase before the previous one is reviewed and accepted.

## Phase 0: Setup

- Initialise repo with renv
- Add LICENSE file containing the standard AGPL-3.0 text
- Create the directory structure from CLAUDE.md
- Minimal app.R that runs and shows a placeholder page with the standard disclaimer in the footer
- README.md and .gitignore
- First commit, push to GitHub

## Phase 1: GLI-2012 manual entry

- Input form: age, sex, height in cm, ethnicity, FEV1, FVC
- Compute predicted, LLN, ULN, z-score, percent of predicted for FEV1, FVC, and FEV1/FVC using rspiro (pred_GLI, LLN_GLI, zscore_GLI)
- Display a single results table
- Tests: 5 reference cases from GLI documentation, passing within 0.01 tolerance

## Phase 2: GLI-Global 2022

- Confirm rspiro version is 0.5 or newer
- Add a parallel calculation path using pred_GLIgl, LLN_GLIgl, zscore_GLIgl
- Side-by-side display of GLI-2012 and GLI-Global 2022 for the same input
- Visual cue when z-score or classification differs between the two
- Tests: 5 reference cases using rspiro outputs cross-checked against the official GLI calculator

## Phase 3: ATS/ERS 2022 interpretation

- Pattern classification: normal, obstructive, restrictive pattern, mixed, non-specific
- Severity grading by z-score: mild, moderate, moderately severe, severe, very severe
- Pure functions in R/interpretation.R, fully unit tested
- UI consumes these functions; no interpretation logic in the server

## Phase 4: Report export

- Quarto template for a one-page PDF and HTML report
- Includes inputs, both reference equation results, classification, disclaimer, timestamp
- Downloadable from the app

## Phase 5: Deploy

- Posit Connect Cloud account
- Deploy from GitHub main branch
- Smoke test on desktop, tablet, and phone widths
- Share with two trusted readers (one pulmonologist, one MIS student) for feedback

## Phase 6: PDF extraction (deferred)

- Out of scope until v1 is shipped, deployed, and used by at least three people for one month
- Implementation will be a separate Python tool that emits JSON; the Shiny app accepts JSON upload as an alternative to manual entry

## Explicitly out of scope for v1

- User accounts, authentication, multi-tenant features
- Database, longitudinal patient tracking, any persistence
- Bronchodilator response (candidate for Phase 7)
- DLCO, lung volumes, MIP/MEP
- Multi-language UI
- Mobile-native version
