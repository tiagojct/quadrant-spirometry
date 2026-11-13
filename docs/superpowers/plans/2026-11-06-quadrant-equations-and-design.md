# Quadrant Streamlit: more equations and a stronger design, implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add verified reference equations to the Streamlit app and rebuild its page around an equation selector, a comparison matrix, a self-hosted typeface, a matching report, presets and a what-if comparison.

**Architecture:** A registry (`quadrant/registry.py`) describes every equation and computes it through one interface. Each equation has an adapter over `pyspiro` and a verification record. The page, chart and report loop over the selected equations, so the number of equations is not fixed.

**Tech Stack:** Python 3.11+, Streamlit 1.67, pyspiro 1.0, Altair 6, pytest. R with rspiro only to make cross-check fixtures.

**Spec:** `docs/superpowers/specs/2026-11-06-quadrant-equations-and-design-spec.md`

## Global Constraints

- Work in `streamlit/` on branch `streamlit-port`. Do not change the R app.
- No coefficient is invented. Coefficients come from `pyspiro` and are checked against a published source. A set that cannot be verified is not added; record it in `docs/verification.md`.
- Dependency rule: no new Python dependency without approval. Approved: streamlit, pyspiro, pytest. The font files are approved (Source Sans 3, SIL OFL, official Adobe Fonts release).
- Wrapper tolerance: predicted value, lower limit of normal and z-score within 0.01 of the reference. Percent of predicted within 0.05.
- Sex codes in the app: 1 male, 2 female. `pyspiro` uses 1 and 0.
- FEV1/FVC is a fraction in every table. Convert from percent inside the adapter.
- LLN z-score is -1.645. Severity: mild from -2.5 up, moderate from -2.5 to -4.0, severe below -4.0.
- Text rules: no emojis, no em dashes, no exclamation marks, no bold emphasis in UI text, no marketing words, sentence case. Wording is descriptive, never diagnostic. The disclaimer "For research and educational purposes. Not for clinical decision-making." is on the page and on every export.
- Keep no patient data on disk. Session state holds only the current inputs and the pinned what-if values.
- No external request at run time: no Google Fonts, no CDN, no analytics.
- Commits: author Tiago Jacinto, no Claude author or session lines, one commit for each task. Do not push without the maintainer.

## Review Focus

- An equation that gives no z-score (ECCS 1993 has no lower limit; Pereira 2007 has a lower limit but no z-score): the z-score must show as "not available", never as `nan`, and the classification must read "not classified", never "normal". Test in Task 1, Task 4 and Task 5.
- A subject outside one equation's age or height range: that equation shows its own message and the others still compute. Test in Task 3, Task 4 and Task 9.
- FEV1/FVC units: a ratio of 0.75 must give a predicted ratio near 0.8 in every family, never 80. Test in Task 3, Task 4, Task 5 and Task 6.
- Sex mapping: for every equation the predicted FEV1 of a 170 cm man is higher than that of a 170 cm woman of the same age. Test in Task 3, Task 4, Task 5 and Task 6.
- Population mismatch: a regional or historical set shows its population and a caveat, and is never in the default selection. Test in Task 1 and Task 9.
- Fonts offline: the config and the report contain no `http` font URL. Test in Task 7 and Task 11.

---

### Task 1: Registry and a contract that allows missing limits

**Files:**
- Create: `streamlit/quadrant/registry.py`
- Modify: `streamlit/quadrant/wrappers.py`, `streamlit/quadrant/interpretation.py`, `streamlit/quadrant/fragments.py`
- Test: `streamlit/tests/test_registry.py`, `streamlit/tests/test_interpretation.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Subject: age_years: float; height_cm: float; sex_code: int; fev1: float; fvc: float`
  - `@dataclass(frozen=True) class EquationSpec: key: str; name: str; citation: str; population: str; age_range: tuple[float, float]; ethnicities: dict[str, int] | None; has_lower_limit: bool; group: str; caveat: str | None; compute: Callable[[Subject, int | None], pd.DataFrame]`. `group` is one of `"recommended"`, `"historical"`, `"regional"`.
  - `EQUATIONS: dict[str, EquationSpec]` in display order. `DEFAULT_KEYS = ("gli_2012", "gli_2022", "nhanes3")`.
  - `compute_equation(key: str, subject: Subject, ethnicity_code: int | None = None) -> pd.DataFrame`
  - `interpret_spirometry` returns `pattern=None` and `severity=None` when any z-score is NaN. `pattern_label(None-pattern)` returns "Not classified (no z-score for this equation)". `badge_colour` returns `"gray"` for it. `classification_summary` skips equations whose pattern is None.

- [ ] **Step 1: Write failing tests** in `test_registry.py`: `test_default_keys_are_the_three_current_equations`, `test_every_spec_has_population_citation_and_group`, `test_regional_and_historical_sets_are_not_default`, `test_compute_equation_matches_the_direct_wrapper` (gli_2012 for 40 y, 170 cm, male, FEV1 3.0, FVC 4.0). In `test_interpretation.py`: `test_a_table_with_nan_limits_is_not_classified` asserts `interpret_spirometry(df)["pattern"] is None`; in `test_fragments_visuals.py`: `test_pattern_label_for_an_unclassified_result` and `test_badge_colour_is_gray_when_not_classified`.
- [ ] **Step 2: Run** `cd streamlit && uv run pytest -q`. Expected: the new tests fail.
- [ ] **Step 3: Implement** `registry.py` with the three current equations, each `compute` calling the existing wrapper. In `wrappers._long_table` add parameter `limits_required: bool = True`. When False, NaN is allowed in `lln` and `z_score` only; NaN in `predicted` or `percent_predicted` still raises `ValueError`. `z_score` may be NaN only for an equation that publishes no z-score or no lower limit; `lln` may be NaN only when the equation publishes no lower limit. Update `interpret_spirometry`, `pattern_label`, `badge_colour`, `classification_summary` as stated.
- [ ] **Step 4: Run** the full suite. Expected: all pass.
- [ ] **Step 5: Commit** "Add an equation registry and allow missing lower limits".

### Task 2: Verification log and cross-check tooling

**Files:**
- Create: `docs/verification.md`, `streamlit/tests/r/make_jrs_fixtures.R`, `tests/testthat/fixtures/jrs_reference_cases.csv`, `streamlit/tests/independent/__init__.py`
- Test: `streamlit/tests/test_verification_log.py`

**Interfaces:**
- Produces: `docs/verification.md` holds one table row for each equation: key, source checked, how it was checked, date, result, status (`verified`, `single source`, `excluded`). A test fails when a registered equation has no row.
- Produces: `jrs_reference_cases.csv` with the same columns as `nhanes3_reference_cases.csv` minus ethnicity. 15 cases: both sexes, ages 17, 18, 30, 50, 80, 95, heights 150 to 190 cm.

- [ ] **Step 1: Write failing test** `test_every_registered_equation_has_a_verification_row`: parse `docs/verification.md`, assert every key in `EQUATIONS` appears, and that status is one of the three allowed values.
- [ ] **Step 2: Run** it. Expected: fail, file missing.
- [ ] **Step 3: Write** `make_jrs_fixtures.R` using `rspiro::pred_JRS`, `LLN_JRS`, `zscore_JRS`, `pctpred_JRS` (check the argument names with `?pred_JRS`). Run it with `Rscript` from the repo root. Write the log with rows for the three current equations (status `verified`: rspiro fixtures) and a placeholder row template.
- [ ] **Step 3b:** Record the rspiro argument names and the fixture command in `docs/verification.md`.
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5: Commit** "Add the verification log and JRS fixtures".

### Task 3: Kubota 2014 (JRS)

**Files:**
- Modify: `streamlit/quadrant/wrappers.py`, `streamlit/quadrant/registry.py`, `streamlit/quadrant/constants.py`
- Test: `streamlit/tests/test_wrappers.py`

**Interfaces:**
- Consumes: `Subject`, `EquationSpec`, `_long_table`.
- Produces: `compute_kubota_2014(age_years, height_cm, sex_code, fev1, fvc) -> pd.DataFrame`; `JRS_AGE_RANGE_YEARS = (17, 95)`; registry key `"kubota_2014"`, group `"regional"`, population "Japanese adults, 17 to 95 years". pyspiro parameter codes: FEV1 1, FVC 2, FEV1FVC 4. The ratio is a fraction.

- [ ] **Step 1: Write failing tests:** `test_kubota_2014_matches_rspiro` parametrized over the 15 fixture cases (pred, lln, z within 0.01; percent within 0.05); `test_kubota_age_range_is_17_to_95`; `test_kubota_ratio_is_a_fraction` (ratio 0.75 gives predicted between 0.7 and 0.9); `test_kubota_sex_mapping` (male FEV1 greater than female).
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** the wrapper with age floored by pyspiro as rspiro does. Add the registry row. If a case differs by more than the tolerance, stop and report; do not loosen the tolerance.
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5:** Update the verification row (status `verified`: rspiro). **Commit** "Add Kubota 2014 (JRS)".

### Task 4: Pereira 2007 (Brazil, White adults)

**Files:**
- Create: `streamlit/tests/independent/pereira_2007.py`
- Modify: `streamlit/quadrant/wrappers.py`, `streamlit/quadrant/registry.py`, `streamlit/quadrant/constants.py`, `docs/verification.md`
- Test: `streamlit/tests/test_wrappers.py`

**Interfaces:**
- Produces: `compute_pereira_2007(age_years, height_cm, sex_code, fev1, fvc) -> pd.DataFrame` using the height and age models only (no weight); `PEREIRA_AGE_RANGE_YEARS = (20, 86)`; key `"pereira_2007"`, group `"regional"`, population "White Brazilian adults, 20 to 86 years".
- Produces: `independent/pereira_2007.py` with `predicted(sex, age, height, parameter) -> float` and `lln(...)`, written from the coefficients in Table 3 of the paper (J Bras Pneumol 2007;33(4):397-406, open access on SciELO). Read the paper; do not copy values from pyspiro's CSV.

- [ ] **Step 1: Fetch the paper** (SciELO full text). Transcribe Table 3 coefficients and the lower-limit rule into `independent/pereira_2007.py`. Record the URL in `docs/verification.md`. If the paper cannot be read, stop: status `excluded`, reason recorded.
- [ ] **Step 2: Write failing tests:** `test_pereira_matches_the_published_equations` (12 cases, both sexes, ages 20, 40, 60, 86, heights 150 to 185: wrapper against the independent module, tolerance 0.005); `test_pereira_age_range`; `test_pereira_ratio_is_a_fraction`; `test_pereira_sex_mapping`; `test_pereira_does_not_use_weight`.
- [ ] **Step 3: Run** them. Expected: fail.
- [ ] **Step 4: Implement** the wrapper and registry row. If the wrapper and the independent module disagree, find the cause. If pyspiro is wrong, exclude the set and record it.
- [ ] **Step 5: Run** the suite; **commit** "Add Pereira 2007".

### Task 5: ECCS/Quanjer 1993 (predicted value and percent only)

**Files:**
- Create: `streamlit/tests/independent/eccs_1993.py`
- Modify: `streamlit/quadrant/wrappers.py`, `streamlit/quadrant/registry.py`, `streamlit/quadrant/constants.py`, `docs/verification.md`
- Test: `streamlit/tests/test_wrappers.py`

**Interfaces:**
- Produces: `compute_eccs_1993(...) -> pd.DataFrame` with `lln` and `z_score` NaN; key `"eccs_1993"`, `has_lower_limit=False`, group `"historical"`; age range (18, 70); caveat "Predicted values and percent of predicted only. No lower limit is published in the source used."
- Produces: `independent/eccs_1993.py` from the published table (Quanjer et al., Eur Respir J 1993;6 Suppl 16:5-40).

- [ ] **Step 1: Find the published coefficient table** in an accessible source and transcribe it. If no source is readable, status `excluded`.
- [ ] **Step 2: Write failing tests:** `test_eccs_matches_the_published_table` (both sexes, ages 18, 25, 40, 70, heights 150 to 190; tolerance 0.005); `test_eccs_has_no_lower_limit` (lln and z_score are NaN, percent is finite); `test_eccs_age_floor_below_25` (documented rule: predicted at 18 equals predicted at 25 where the paper says so); `test_eccs_ratio_is_a_fraction`; `test_eccs_sex_mapping`; `test_eccs_result_is_not_classified` (`interpret_spirometry(...)["pattern"] is None`).
- [ ] **Step 3: Run** them. Expected: fail.
- [ ] **Step 4: Implement** with `limits_required=False`. If the maintainer later supplies the verified residual standard deviations, a lower limit can be added; do not add it now.
- [ ] **Step 5: Run** the suite; **commit** "Add ECCS/Quanjer 1993 without lower limits".

### Task 6: Jian 2017 and Jo 2018 (gated)

**Files:**
- Create: `streamlit/tests/independent/jian_2017.py`, `streamlit/tests/independent/jo_2018.py` (only if verified)
- Modify: `streamlit/quadrant/wrappers.py`, `streamlit/quadrant/registry.py`, `docs/verification.md`
- Test: `streamlit/tests/test_wrappers.py`

**Interfaces:**
- Produces: `compute_jian_2017(...)` (age range (4, 80); FEV1/FVC converted from percent to fraction) and `compute_jo_2018(...)` (age range (19, 90)); keys `"jian_2017"` and `"jo_2018"`, group `"regional"`.

- [ ] **Step 1: Spike.** For each paper, find published predicted values for stated ages and heights (tables in the article or its open supplement). Collect at least 5 values for each sex.
- [ ] **Step 2: Decide.** Add the set only if the wrapper matches the published values within the paper's rounding. Otherwise set status `excluded` in `docs/verification.md` with the reason, and skip Steps 3 to 5 for that set.
- [ ] **Step 3: Write failing tests** with the collected published values: `test_<set>_matches_published_values`, `test_<set>_age_range`, `test_<set>_ratio_is_a_fraction`, `test_<set>_sex_mapping`.
- [ ] **Step 4: Implement** the wrapper and registry row.
- [ ] **Step 5: Run** the suite; **commit** one commit for each set that passes.

### Task 7: Typeface and offline guarantee

**Files:**
- Create: `streamlit/static/fonts/SourceSans3-Regular.woff2`, `SourceSans3-Semibold.woff2`, `OFL.txt`, `streamlit/tests/test_offline.py`
- Modify: `streamlit/.streamlit/config.toml`, `streamlit/README.md`

**Interfaces:**
- Produces: config keys `[server] enableStaticServing = true`, `[[theme.fontFaces]]` entries pointing at `app/static/fonts/...`, `font = "Source Sans 3"` and `headingFont = "Source Sans 3"`, plus the type scale: `baseFontSize`, `headingFontSizes` (title 2.6rem, section 1.6rem, card 1.2rem) and `headingFontWeights` (600 for all headings).

- [ ] **Step 1: Write failing test** `test_config_has_no_external_font_url`: no `http://` or `https://` in `.streamlit/config.toml`; the font files and `OFL.txt` exist.
- [ ] **Step 2: Run** it. Expected: fail.
- [ ] **Step 3: Download** the official release (`gh release view` in `adobe-fonts/source-sans`), take the WOFF2 Regular and Semibold files and the licence. Record the version and SHA-256 in `static/fonts/README.md`. Edit the config. Check the page in a browser: the font loads from `/app/static/fonts/`, no request leaves localhost.
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5: Commit** "Self-host Source Sans 3".

### Task 8: Chart and SVG for any number of equations

**Files:**
- Modify: `streamlit/quadrant/charts.py`, `streamlit/quadrant/visuals.py`
- Test: `streamlit/tests/test_charts.py`, `streamlit/tests/test_fragments_visuals.py`

**Interfaces:**
- Produces: `FAMILY_STYLE` replaced by `style_for(index: int) -> tuple[str, str]` (colour, shape) with at least 8 distinct pairs; chart and SVG take `dict[str, DataFrame | None]` keyed by equation name; rows with NaN z-score are left out; the chart height grows with the number of equations: `height = 120 + 64 * n_equations`.

- [ ] **Step 1: Write failing tests:** `test_style_pairs_are_distinct_for_eight_equations`; `test_chart_skips_nan_z_scores`; `test_chart_height_grows_with_equations`; `test_svg_has_one_marker_per_equation_and_parameter_for_six_equations`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement.** Keep the legend readable at eight entries (wrap on two rows).
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5: Commit** "Draw the comparison for any number of equations".

### Task 9: Page rebuild: selector, classification list, matrix

**Files:**
- Create: `streamlit/quadrant/matrix.py`
- Modify: `streamlit/app.py`, `streamlit/quadrant/fragments.py`
- Test: `streamlit/tests/test_matrix.py`, `streamlit/tests/test_app.py`

**Interfaces:**
- Produces: `matrix_frames(tables: dict[str, DataFrame]) -> dict[str, DataFrame]`: keys `"FEV1"`, `"FVC"`, `"FEV1/FVC"`; each frame has the index `Equation` and the columns `Pred.`, `LLN`, `Z-score`, `% pred`, formatted as text; NaN shows as an en-dash placeholder `-`; a z-score below -1.645 ends with ` *`.
- Produces: the page lists the selected equations with `st.pills(selection_mode="multi")`, grouped by `group`; default `DEFAULT_KEYS`; at least one equation must stay selected. A caveat caption appears for a selected regional or historical set. An ethnicity selector appears for each selected equation that has ethnicities.

- [ ] **Step 1: Write failing tests:** `test_matrix_has_one_row_for_each_equation`; `test_matrix_marks_values_below_the_lln`; `test_matrix_shows_a_dash_for_missing_limits`; AppTest: `test_default_selection_is_the_three_current_equations`, `test_selecting_kubota_adds_a_row_and_a_caveat`, `test_an_equation_outside_its_range_shows_a_message_and_the_rest_compute` (age 5 with NHANES III, Kubota and GLI-2012 selected), `test_the_last_selected_equation_cannot_be_removed`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** `matrix.py` and rebuild `app.py` to loop over the selected specs. Order on the page: classification list, chart, matrix, equation notes (citation, population, caveat) in an expander.
- [ ] **Step 4: Run** the suite and check the page in a browser at one, three and six equations, light and dark.
- [ ] **Step 5: Commit** "Rebuild the page around an equation selector and a comparison matrix".

### Task 10: Presets, input checks and what-if

**Files:**
- Create: `streamlit/quadrant/presets.py`
- Modify: `streamlit/app.py`
- Test: `streamlit/tests/test_presets.py`, `streamlit/tests/test_app.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Preset: label: str; age_years: float; height_cm: float; sex_code: int; fev1: float; fvc: float`; `PRESETS: dict[str, Preset]` with 4 entries: a normal adult, an obstructive pattern, a restrictive pattern (suggestive), a child of 10 years.
- Produces: `delta_frame(current: dict[str, DataFrame], pinned: dict[str, DataFrame]) -> dict[str, DataFrame]` with the column `Change in z`.

- [ ] **Step 1: Write failing tests:** `test_each_preset_gives_its_stated_pattern_under_gli_2012`; `test_preset_values_are_inside_the_gli_ranges`; `test_delta_frame_subtracts_pinned_z_scores`; AppTest: `test_choosing_a_preset_sets_the_inputs`, `test_pinning_adds_a_change_column`, `test_clearing_the_pin_removes_it`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** presets through an `on_change` callback that writes the widget keys in `st.session_state`. Pin and clear use buttons. Nothing is written to disk.
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5: Commit** "Add presets and a what-if comparison".

### Task 11: Report and print redesign

**Files:**
- Modify: `streamlit/quadrant/report.py`, `streamlit/quadrant/styles.py`
- Test: `streamlit/tests/test_report.py`

**Interfaces:**
- Consumes: `matrix_frames`, `EQUATIONS`, the SVG chart from Task 8.
- Produces: `prepare_report_bundle(subject, equations, results, interpretations, chart_svg, timestamp=None)` for any number of equations; `render_report_html(bundle) -> str`: one A4 page when possible, `@media print` rules, the typeface embedded as base64 `@font-face` (no URL), the disclaimer, one equation-notes block with citation and population.

- [ ] **Step 1: Write failing tests:** `test_report_lists_every_selected_equation`; `test_report_has_the_disclaimer_and_citations`; `test_report_embeds_the_font_and_has_no_external_url` (no `http` inside `src:` or `url(`); `test_report_marks_unclassified_equations`; `test_report_escapes_labels`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement.** Check the file in a browser and in print preview.
- [ ] **Step 4: Run** the suite. Expected: pass.
- [ ] **Step 5: Commit** "Redesign the report for any number of equations".

### Task 12: Documentation and final checks

**Files:**
- Modify: `streamlit/README.md`, `docs/verification.md`, `.github/workflows/streamlit.yaml` (only if paths change)

- [ ] **Step 1:** Update the README: equations table with population, range and verification status; design notes; how to add an equation.
- [ ] **Step 2:** Run `uv run pytest -q` and the page in a browser, light and dark, at 1, 3 and 6 equations, with an impaired preset and an out-of-range input.
- [ ] **Step 3:** Run the R app tests (`Rscript tests/testthat.R`) to confirm nothing changed there.
- [ ] **Step 4:** Ask for one review of the whole branch by a fresh reviewer, with the spec and `docs/verification.md` as input.
- [ ] **Step 5: Commit** "Document the equations and verification".
