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

- rspiro 0.5 confirmed
- Parallel calculation path using pred_GLIgl, LLN_GLIgl, zscore_GLIgl, pctpred_GLIgl, with no ethnicity argument since the equation is race-neutral
- Side-by-side display of GLI-2012, GLI-Global 2022, and the historic NHANES III comparator on the same input
- Comparison panel below the three result cards that flags any parameter where the above/below LLN classification differs between GLI-2012 and GLI-Global 2022
- Tests: 5 reference cases per family, stored under tests/testthat/fixtures/. The maintainer cross-check against the official upstream calculator remains the acceptance gate

## Phase 3: ATS/ERS 2022 interpretation

- Pattern classification: normal, obstructive, restrictive pattern (suggestive), mixed pattern (suggestive), non-specific. Source: Stanojevic et al., ERJ 2022, doi:10.1183/13993003.01499-2021. Boundary at z = -1.645 is inclusive of normal.
- Severity grading by FEV1 z-score: mild, moderate, moderately severe, severe, very severe, using the five-band table reproduced from the same statement.
- Pure functions in R/interpretation.R: classify_pattern, grade_severity, interpret_spirometry. Fully unit tested across every branch and the LLN boundary.
- UI consumes these functions only. The server passes the wrapper output to interpret_spirometry; no interpretation logic lives in the server itself. Each per-family results card carries its own interpretation block.

## Phase 4: Report export

- Quarto template at inst/report_template.qmd renders a one-page HTML report
- Report bundle assembled in R/report.R: subject inputs, all three reference equation results, the cross-family SVG chart embedded inline, the per-family classification badges, the interpretation blocks, the comparison text, and a timestamp
- Disclaimer footer carried over from the UI verbatim
- Download button in the sidebar; downloadHandler in the server calls render_quadrant_report and serves the rendered file
- PDF output deferred to Phase 4b. The default Quarto PDF backend needs a LaTeX distribution that is not assumed to be present; the Typst backend works without LaTeX but would require a parallel Typst-native template. Browser print-to-PDF on the downloaded HTML covers the immediate need

## Phase 4b: PDF report (deferred)

- Decide between TinyTeX (Quarto's recommended LaTeX bundle, a few hundred MB) and a Typst-native parallel template
- Add a Download PDF button alongside Download HTML
- Add an integration test that renders a sample PDF in CI when the backend is available, and skips it otherwise

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
