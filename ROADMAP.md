# Roadmap

Each phase is roughly one weekend of focused work. Do not start a new phase before the previous one is reviewed and accepted.

## Phase 0: Setup

- Initialise repo with renv
- Add LICENSE file containing the standard AGPL-3.0 text
- Create the directory structure from CLAUDE.md
- Minimal app.R that runs and shows a placeholder page with the standard disclaimer in the footer
- README.md and .gitignore
- First commit, push to GitHub

## Phase 1: GLI-2012 manual entry, with NHANES III as the historic comparator

- Input form: age, sex, height in cm, ethnicity, FEV1, FVC
- Compute predicted, LLN, z-score, percent of predicted for FEV1, FVC, and FEV1/FVC using rspiro for two reference families:
  - GLI-2012 (pred_GLI, LLN_GLI, zscore_GLI, pctpred_GLI)
  - NHANES III, 1999 (pred_NHANES3, LLN_NHANES3, zscore_NHANES3, pctpred_NHANES3)
- Display the two result sets side by side so the operator can see how the classification of the same individual shifts between a 1999 and a 2012 reference equation
- Ethnicity dropdown is reference-equation-aware: GLI accepts 5 categories, NHANES III accepts 3. UI surfaces both with a short note when an exact match is unavailable
- Tests: 5 reference cases per family, stored under tests/testthat/fixtures/, passing within 0.01 tolerance. Cases trace to the published reference papers (Quanjer 2012 for GLI, Hankinson 1999 for NHANES III)
- Wishlist (not in this phase): ECSC 1993 (Quanjer) as a second historic comparator. Not provided by rspiro 0.5. Tracked separately

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
