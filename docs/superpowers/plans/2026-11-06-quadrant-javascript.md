# Quadrant in JavaScript, inside Tryworks: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Quadrant as a bilingual (English, European Portuguese) browser app at `/quadrant/` and `/pt/quadrant/` in the Tryworks site, with a switchable main chart (Spread, Plate, Grid) and the six verified reference equations of the Python app.

**Architecture:** Vanilla ES modules in `src/assets/quadrant/`, served as they are (no bundler), like The Line. A pure engine (equations, interpretation, matrix, presets) with no DOM, a chart layer (one model, three renderers), and a thin UI layer. Equation tables are exported from pyspiro to JSON by scripts in the Quadrant repository and committed to Tryworks. The Python app on `streamlit-port` is the reference: its outputs, written to a golden fixture, are the test oracle.

**Tech Stack:** JavaScript ES modules, hand-drawn SVG, Eleventy 3 (Nunjucks pages), `node --test`, jsdom (dev only). Python 3.11+, uv, pyspiro 1.0.x for the export and golden scripts only.

**Spec:** `docs/superpowers/specs/2026-11-06-quadrant-javascript-design.md` (Quadrant repo, branch `streamlit-port`). Read it with this plan. Reference behaviour: `streamlit/` and `docs/verification.md` on `streamlit-port`.

## Global Constraints

- Tryworks conventions of The Line: vanilla ES modules, no bundler, files served from `src/assets/`, relative imports get `?v=<hash>` (`lib/assets.js`), page in `src/<name>/index.njk` with `noAnalytics: true`, no `fetch` to another host, no cookies, no external request.
- Pages at `/quadrant/` (English) and `/pt/quadrant/` (European Portuguese); texts outside the code; a test checks that every string has a Portuguese text of the same shape and no Brazilian forms.
- Tests in `lib/quadrant-*.test.js`, run by `npm test` (`node --test lib/*.test.js ...`). jsdom is a dev dependency only. `npm run check:html` and `npm run check:links` pass. No new run-time dependency.
- Coefficients and tables are never typed by hand: exported from pyspiro 1.0.x by script, with the source file and the pyspiro version in a header of each JSON file. NHANES III follows the paper: young equations below 20 years (men) and 18 years (women).
- Equation outputs match the golden fixture within 1e-6 (predicted, lower limit, z-score). Percent predicted within 1e-4. Out-of-range inputs give the same reason text as the Python app, in English.
- Rules of the Python app carry over: z-score cut-off -1.645; severity mild at -2.5 or higher, moderate down to -4.0, severe below; a value is below a limit only when strictly below with a tolerance of 1e-9; Pereira 2007 is classified from observed values against its published lower limit (basis "lower limit", no severity); ECCS 1993 is "not classified"; NaN never prints as text and never reads as normal; FEV1/FVC is a fraction everywhere.
- Text rules: no emojis, no em dashes, no exclamation marks, no bold emphasis in UI text, descriptive wording only, never diagnostic. Disclaimer on the page and on every export: "For research and educational purposes. Not for clinical decision-making." (Portuguese text in the language file).
- Licence: the Quadrant code lives in `src/assets/quadrant/` with its own `LICENSE` (AGPL-3.0-or-later). pyspiro is MIT: attribution in the data headers and the page footer.
- Colours and type come from `packages/design` (tokens, Literata, Atkinson Hyperlegible Next). Contrast WCAG AA or better in light and dark. Layout works at 390 px.
- Work happens in a git worktree of Tryworks made from local `main` (it carries the Portuguese Line commits). Nothing is pushed or merged to `main` without the maintainer, because a push to `main` deploys the site. The Quadrant repository work goes on branch `streamlit-port` or a new branch from it.
- Commits: author Tiago Jacinto <tiagojct@icloud.com>, no Claude, co-author or session lines, no emojis.

## Review Focus

1. Decimal comma. A Portuguese keyboard types "40,5". Expected: it reads as 40.5, and a letter or an empty field shows an empty-state message, not an error or NaN. (Task 11)
2. Partly filled form. Typing one field at a time must never throw; the chart shows the example or a clear "enter values" state. (Task 11)
3. Chart edge cases: one equation selected, eight selected, an equation that rejected the inputs, an equation with only NaN z-scores. Expected: every mode draws what computed, lists what did not, and never prints "nan". (Tasks 2, 3)
4. Local storage blocked (private window). Expected: the page works, the mode falls back to Spread, no exception. (Task 12)
5. Phone width 390 px and print. Expected: no sideways page scroll, legends complete, the report prints on A4 with the disclaimer on page 1. (Tasks 3, 14)

---

### Task 1: Worktree and skeleton

**Files:**
- Create (Tryworks worktree): `src/assets/quadrant/LICENSE`, `src/assets/quadrant/README.md`, `src/assets/quadrant/engine/constants.js`, `lib/quadrant-constants.test.js`

**Interfaces:**
- Produces: `engine/constants.js` exports `LLN_Z = -1.645`, `SEVERITY_MILD_Z_MIN = -2.5`, `SEVERITY_MODERATE_Z_MIN = -4.0`, `LIMIT_COMPARE_TOLERANCE = 1e-9`, `SEX_CODES = { Male: 1, Female: 2 }`, `PARAMETERS = ["FEV1", "FVC", "FEV1FVC"]`, `DISCLAIMER_TEXT`.

- [ ] Step 1: From `~/quarterdeck/teaching/tryworks` run `git worktree add ~/worktrees/tryworks-quadrant -b quadrant main` (the worktree is outside the workspace tree). Run `npm ci` there and `npm test` to record the baseline.
- [ ] Step 2: Write `lib/quadrant-constants.test.js` asserting each constant value above and that `DISCLAIMER_TEXT` equals the sentence in Global Constraints. Run it: fail.
- [ ] Step 3: Create the files. `LICENSE` is the AGPL-3.0 text from the Quadrant repository root. `README.md` states the folder purpose, the licence and the pyspiro attribution.
- [ ] Step 4: `npm test`: pass. Commit "Add the Quadrant folder, licence and constants".

### Task 2: Chart model and marks

**Files:**
- Create: `src/assets/quadrant/chart/model.js`, `src/assets/quadrant/chart/marks.js`, `lib/quadrant-chart-model.test.js`

**Interfaces:**
- Consumes: `PARAMETERS`, `LLN_Z` from `engine/constants.js`.
- Produces: `styleFor(index) -> { colour: string, shape: "circle"|"square"|"diamond"|"triangle-up"|"triangle-left"|"triangle-right"|"cross"|"hexagon" }` (8 distinct pairs, index 8 wraps to 0; the first three are Prussian blue circle, sap green square, gamboge diamond from the Tryworks palette). `chartModel(results) -> { equations: {key, name, style}[], parameters: { name: "FEV1"|"FVC"|"FEV1/FVC", points: { key, z: number, text: string }[], spread: number }[], notPlotted: {key, name}[] }` where `results` is `{ key, name, table: Row[] | null }[]` in selection order, `Row = { parameter, zScore }`. A point exists only for a finite z-score. `notPlotted` holds equations with no finite z-score or no table. `text` is the z-score with a sign and two decimals (`+0.42`, `-1.10`). `spread` is max minus min of the point z-scores, 0 for fewer than two points.

- [ ] Step 1: Write failing tests: `eight styles are distinct`, `style 8 wraps to style 0`, `every style colour has at least 3:1 contrast on the light and dark paper colours` (read both paper colours from `packages/design/css/tokens.css`), `a NaN z-score gives no point and lists the equation in notPlotted`, `spread is max minus min`, `text has an explicit sign and two decimals`, `an equation with a null table is in notPlotted`.
- [ ] Step 2: Run: fail. Step 3: Implement. Pick colours from the design tokens (names in `tokens.css`); where eight distinct colours are not available, derive from the tokens and record the choice in a comment. Step 4: pass.
- [ ] Step 5: Commit "Add the chart model and mark styles".

### Task 3: Three chart renderers and the prototype page (chart milestone)

**Files:**
- Create: `src/assets/quadrant/chart/scales.js`, `chart/spread.js`, `chart/plate.js`, `chart/grid.js`, `chart/render.js`, `src/assets/css/quadrant.css`, `src/quadrant/prototype.njk`, `lib/quadrant-chart-render.test.js`
- Reference: `.superpowers/brainstorm/*/content/chart-directions.html` in the Quadrant repository (the maintainer's sketches of the three modes).

**Interfaces:**
- Consumes: `chartModel` output from Task 2.
- Produces: `renderChart(mode, model, mount, text) -> void` with `mode` one of `"spread"`, `"plate"`, `"grid"`; draws an SVG into `mount` using design tokens through CSS custom properties (theme aware). `chartSvgString(mode, model, text) -> string` returns a standalone SVG with literal light-theme colours and no external reference, for the report. `text` is the language object `{ title, parameterNames, bands: {severe, moderate, mild, within}, lln, spread, notPlotted }`. Every chart has `role="img"`, an `aria-label`, and an SVG `<title>`; its data table form is the matrix on the page.

- [ ] Step 1: Write failing tests (jsdom): `each mode draws one mark per point`, `the lower limit line is at z = -1.645 on the scale`, `scale maps z -5 to 3 across the width`, `a model with notPlotted renders a note and no nan text`, `chartSvgString has no http reference and no theme variables`, `eight equations fit without overlapping labels in spread mode` (assert label boxes from the layout function do not intersect), `no text node contains "nan"`.
- [ ] Step 2: Run: fail. Step 3: Implement the three renderers over shared `scales.js` and the marks of Task 2. Spread is the default look: one thin track for each parameter, a rule joining the equations, the spread written above, the lower limit marked, severity washes quiet. Plate and Grid follow the sketches. Fonts: Literata for parameter names, Atkinson Hyperlegible Next for numbers (from the design package).
- [ ] Step 4: Create `src/quadrant/prototype.njk` (permalink `/quadrant/prototype/`, `noindex`) that shows the three modes with a mode switch, light and dark, using the four preset subjects' z-scores typed as a static fixture in the page data (these numbers are for the prototype only). Run the Tryworks build and check the page in a browser at 390 px and desktop, light and dark. Save screenshots next to the plan notes.
- [ ] Step 5: Commit "Draw the Quadrant chart in three modes (prototype)".
- [ ] **GATE:** stop. The maintainer reviews `/quadrant/prototype/` and approves, or asks for changes. Tasks 4 onward start only after approval. Remove the prototype page in Task 15.

### Task 4: Export the equation tables (Quadrant repository, Python)

**Files:**
- Create: `streamlit/tools/export_tables.py`, `streamlit/tests/test_export_tables.py`
- Output (Tryworks worktree): `src/assets/quadrant/data/gli2012.json`, `gli2022.json`, `nhanes3.json`, `kubota2014.json`, `pereira2007.json`, `eccs1993.json`

**Interfaces:**
- Produces: `export_tables.py --out <dir>` writes one JSON file per equation: `{ "meta": { "source": "<pyspiro file and csv names>", "pyspiroVersion": "1.0.0", "licence": "MIT (pyspiro)", "equation": key }, "tables": { ... } }`. The shape of `tables` follows the pyspiro CSVs (splines and coefficients for the LMS sets; coefficients for the regression sets). Numbers are written with full float precision. Keys are sorted so that two runs give identical files.

- [ ] Step 1: Write failing tests: `export is deterministic` (two runs equal), `meta is present in every file`, `row counts equal the CSV row counts`, `values equal the CSV values to full precision` (spot check ten cells for each file), `NHANES III file has the child and adult groups for both sexes`.
- [ ] Step 2: Run: fail. Step 3: Implement by reading the CSV files through pyspiro's own loaders (`pyspiro/data`), not by re-typing. Step 4: Run the export into the worktree and check file sizes; the total must stay below 2 MB (report the sizes; if above, compact the spline tables with fixed precision that keeps the 1e-6 contract and say so in `meta`).
- [ ] Step 5: Commit in both repositories: "Export the equation tables to JSON" (Quadrant) and "Add the equation tables" (Tryworks worktree).

### Task 5: Golden fixture from the Python app (Quadrant repository, Python)

**Files:**
- Create: `streamlit/tools/make_golden.py`, `streamlit/tests/test_make_golden.py`
- Output (Tryworks worktree): `lib/fixtures/quadrant/golden.json`

**Interfaces:**
- Produces: `golden.json` = `{ meta: { generator, pyspiroVersion, appCommit, date }, cases: { equation: string, subject: { ageYears, heightCm, sexCode, fev1, fvc }, ethnicityCode: number | null, expected: Row[] | { error: string } }[] }` produced by `quadrant.registry.compute_equation`. `Row = { parameter, observed, predicted, lln, zScore, percentPredicted }` with `null` for NaN.
- The grid for each equation: both sexes; every ethnicity the equation offers; ages at the range limits, limit minus 0.01, limit plus 0.01 and every 5 years between; heights at the limits and every 10 cm; observed values at 60, 80 and 100 percent of predicted and exactly at the lower limit; plus the cases of `streamlit/tests` for the age 17.5, 18, 19, 19.5, 20 split of NHANES III, the Pereira limits (man 27 y, 163 cm, FEV1 3.28), FEV1 greater than FVC, and out-of-range cases for every error message of `wrappers.py`.

- [ ] Step 1: Write failing tests: `golden has cases for all six equations`, `every error message of the wrappers appears at least once`, `the file is deterministic`, `a sample of 20 cases equals a direct compute_equation call`.
- [ ] Step 2: Run: fail. Step 3: Implement. Cap the file at 5 MB; if the grid is larger, thin the middle ages and say so in `meta`. Step 4: pass.
- [ ] Step 5: Commit in both repositories ("Add the golden fixture generator", "Add the golden fixture").

### Task 6: Engine core: validation, limits, interpretation

**Files:**
- Create: `src/assets/quadrant/engine/limits.js`, `engine/subject.js`, `engine/interpretation.js`, `engine/errors.js`, `lib/quadrant-engine-core.test.js`

**Interfaces:**
- Produces: `isBelow(value, limit) -> boolean` (strict, tolerance `LIMIT_COMPARE_TOLERANCE`; false when either is not finite). `class EquationError extends Error` with a stable `code` string (for example `age-range`, `height-range`, `sex-range`, `partly-missing`) and a `params` object for the numbers in the message (message is user-facing text in English, sentence case, full stop, no internal names; Task 13 maps `code` and `params` to each language). `validateSubject({ageYears, heightCm, sexCode, fev1, fvc}, ageRange) -> void` throws `EquationError` with the messages of `streamlit/quadrant/wrappers.py` (copy the texts from that file, do not reword). `classifyPattern(fev1Z, fvcZ, ratioZ)` and `classifyPatternFromLimits(observed, lln)` -> `"normal" | "obstructive" | "restrictive pattern (suggestive)" | "mixed pattern (suggestive)" | "non-specific"`; `gradeSeverity(fev1Z) -> "mild"|"moderate"|"severe"`; `interpretSpirometry(table) -> { pattern: string|null, severity: string|null, basis: "z-score"|"lower limit"|null, fev1Z, fvcZ, fev1FvcZ }`. Rules as in `streamlit/quadrant/interpretation.py` on `streamlit-port`: all-NaN z with finite limits gives basis "lower limit" and no severity; neither gives `pattern: null`; a partly missing set throws `EquationError`.

- [ ] Step 1: Port the Python test cases for these rules (read `streamlit/tests/test_interpretation.py`): `-1.645 exactly is normal`, `3.28 vs 3.2800000000000002 is not below`, `partly missing z-scores throw`, `all-NaN z without limits is not classified`, `Pereira-style limits classify by observed`, `severity bands at -2.5 and -4.0`, `isBelow is false for NaN`. Run: fail.
- [ ] Step 2: Implement. Step 3: pass. Commit "Add the engine core".

### Task 7: GLI-2012 and GLI-Global 2022

**Files:**
- Create: `src/assets/quadrant/engine/lms.js`, `engine/equations/gli2012.js`, `engine/equations/gli2022.js`, `lib/quadrant-gli.test.js`
- Reference: `pyspiro` `GLI_2012.py`, `BOWERMAN_2022.py` and their base classes; `streamlit/quadrant/wrappers.py` (`compute_gli_2012`, `compute_gli_global_2022`).

**Interfaces:**
- Produces: `lms.js`: `interpolateSpline(table, age) -> {l, m, s}` per the GLI method and `lmsZ(value, l, m, s)`, `lmsPredicted(l, m, s, z)`. `gli2012(subject, ethnicityCode) -> Row[]` and `gli2022(subject) -> Row[]` (rows for FEV1, FVC, FEV1FVC in that order; ratio as a fraction). They throw `EquationError` outside age 3 to 95 years or with invalid input, with the Python messages.

- [ ] Step 1: Write the test that loads `golden.json` and `data/gli*.json` and asserts every GLI case within the contract (a table-driven test with the case index in the failure message), plus `age 2.99 and 95.01 throw` and `the ratio is a fraction`. Add a check of 5 published cases from `tests/testthat/fixtures` of the Quadrant repository (copy the fixture file into `lib/fixtures/quadrant/`). Run: fail.
- [ ] Step 2: Implement from the pyspiro source and the GLI papers (doi in `streamlit/quadrant/constants.py`). Step 3: pass. Commit "Add GLI-2012 and GLI-Global 2022".

### Task 8: NHANES III

**Files:** Create `engine/equations/nhanes3.js`, `lib/quadrant-nhanes3.test.js`. Copy the independent paper values from `streamlit/tests/independent/nhanes3_1999.py` into the test as constants.

**Interfaces:** Produces `nhanes3(subject, ethnicityCode) -> Row[]` (ethnicity 1 to 3; age 8 to 80). Change points: below 20 years for men and below 18 years for women use the young equation, as the paper does (Tables 4 and 5).

- [ ] Step 1: Tests: all golden cases; `man 19.5 y 172 cm uses the young equation (FEV1 4.327 L)`; `woman 17.5 y uses the young equation`; `woman 19 y uses the adult equation`; ranges 7.99 and 80.01 throw. Run: fail. Step 2: Implement. Step 3: pass. Commit "Add NHANES III".

### Task 9: Kubota 2014 (JRS)

**Files:** Create `engine/equations/kubota2014.js`, `lib/quadrant-kubota.test.js`.

**Interfaces:** Produces `kubota2014(subject) -> Row[]`. Age 17 to 95 for men; for women the limit is exclusive at 94 years (messages as in `compute_kubota_2014`).

- [ ] Step 1: Tests: golden cases, the rspiro fixture `tests/testthat/fixtures/jrs_reference_cases.csv` (copy into the JS fixtures), `woman 93.99 computes and 94 throws`. Run: fail. Step 2: Implement. Step 3: pass. Commit "Add Kubota 2014".

### Task 10: Pereira 2007 and ECCS 1993

**Files:** Create `engine/equations/pereira2007.js`, `engine/equations/eccs1993.js`, `lib/quadrant-pereira-eccs.test.js`. Copy the paper-table checks from `streamlit/tests/independent/pereira_2007.py` and `eccs_1993.py`.

**Interfaces:**
- Produces: `pereira2007(subject) -> Row[]` with a finite `lln` and `zScore: NaN`; ranges by sex (men 26 to 86 years and 152 to 192 cm, women 20 to 85 years and 137 to 182 cm). `eccs1993(subject) -> Row[]` with `lln` and `zScore` NaN; age 18 to 70, age 25 used for ages 18 to 25 in the men's volumes, heights 155 to 195 cm (men) and 145 to 180 cm (women).

- [ ] Step 1: Tests: golden cases; independent paper cases; `man 27 y 163 cm FEV1 3.28 reads normal by limit` through `interpretSpirometry`; `ECCS interpretation is pattern null`. Run: fail. Step 2: Implement. Step 3: pass. Commit "Add Pereira 2007 and ECCS 1993".

### Task 11: Registry, inputs parser, matrix, presets, what-if

**Files:**
- Create: `engine/registry.js`, `engine/parse-number.js`, `engine/matrix.js`, `engine/presets.js`, `engine/delta.js`, `lib/quadrant-model.test.js`

**Interfaces:**
- Produces: `EQUATIONS: { key, name, citation, population, group: "recommended"|"historical"|"regional", ethnicities: {label, code}[] | null, caveat: string|null, hasLowerLimit: boolean, compute(subject, ethnicityCode) -> Row[] }[]` in the order gli_2012, gli_2022, nhanes3, kubota_2014, pereira_2007, eccs_1993; `DEFAULT_KEYS = ["gli_2012", "gli_2022", "nhanes3"]`; `computeEquation(key, subject, ethnicityCode)`. The names, citations, populations, caveats and ethnicity labels are copied from `streamlit/quadrant/registry.py` and `constants.py` (English; the Portuguese words go in the language file, Task 13). `parseNumber(text) -> number | null` accepts a decimal point or comma, trims spaces, returns null for empty or non-numeric text. `matrixFrames(results) -> { FEV1, FVC, "FEV1/FVC": { equation, pred, lln, z, pct }[] }` with text cells: "-" for missing; " *" after the z-score when it is below -1.645, and after the lower limit when the equation has no z-score and the observed value is below it (same `isBelow`). `PRESETS` (four synthetic subjects with a normal adult, an obstructive pattern, a restrictive pattern (suggestive), a child of 10 years; the values of `streamlit/quadrant/presets.py`). `deltaFrames(current, pinned) -> frames` with the change in z as a signed text (`+0.42`, `-1.10`, `0.00`), "-" for NaN, only for equations in both.

- [ ] Step 1: Port the Python tests (`test_matrix.py`, `test_presets.py`, `test_registry.py`): `one row per equation`, `asterisk rule for z and for lower limits`, `"-" for missing`, `each preset gives its stated pattern under GLI-2012`, `delta subtracts pinned from current`, `selection order is kept`. Add `parseNumber("40,5") === 40.5`, `parseNumber("") === null`, `parseNumber("abc") === null`, `parseNumber(" 1.8 ") === 1.8`. Run: fail.
- [ ] Step 2: Implement. Step 3: pass. Commit "Add the registry, matrix, presets and what-if".

### Task 12: Page UI and wiring

**Files:**
- Create: `src/assets/quadrant/main.js`, `ui/inputs.js`, `ui/selector.js`, `ui/classification.js`, `ui/matrix-view.js`, `ui/mode-switch.js`, `ui/store.js`, `ui/notes.js`, `lib/quadrant-ui.test.js`
- Modify: `src/assets/css/quadrant.css`

**Interfaces:**
- Consumes: Tasks 2, 3, 6 to 11.
- Produces: `main.js` mounts the app into `#quadrant-app`. `ui/store.js` exports `loadMode()` and `saveMode(mode)` over local storage key `tryworks.quadrant.v1`, with every access in try/catch and the default `"spread"`. The page: a one-sentence purpose, a filled example (the "normal adult" preset is not used; the example is the obstructive preset so the chart shows divergence) before the visitor types, a chart titled with the question the chart answers, the mode switch (three buttons, keyboard operable, `aria-pressed`), inputs (age, height, sex, FEV1, FVC, ethnicity for each selected equation that has them), the equation selector grouped by `group` (at least one stays selected; the guard note clears on the next change), the classification list (one line for each equation: name, badge or "Not classified (no lower limit and no z-score for this equation)" or "Pattern ... , by lower limit" with "Severity not graded (no z-score for this equation)"), the summary sentence rules of `streamlit/quadrant/fragments.py` (`classification_summary`), the chart, the matrix with its asterisk legend, the equation notes (citation, population, caveat), the presets menu, the pin and clear-pin buttons with a "Change in z" column, the FEV1 greater than FVC notice, and the disclaimer. An equation that rejects the inputs shows its reason; the others compute. All words come from the language object passed by the page (Task 13).

- [ ] Step 1: Write failing jsdom tests: `the page opens with the example and a drawn chart`, `typing 40,5 in age is read as 40.5`, `an empty field shows the empty state and no exception`, `the last equation cannot be deselected`, `selecting Kubota adds a matrix row and a caveat`, `age 5 with NHANES III, Kubota and GLI-2012 shows two messages and one result`, `ECCS shows the unclassified label and no "nan" in the page text`, `six equations render`, `the mode persists after reload` and `a throwing local storage does not break the page`, `pin then change adds the Change in z column; clear removes it`, `FEV1 greater than FVC shows the notice`, `changing the mode changes no number in the matrix`.
- [ ] Step 2: Run: fail. Step 3: Implement. State is held in one plain object in `main.js`; nothing but the mode and nothing personal is written to local storage. Step 4: pass.
- [ ] Step 5: Commit "Build the Quadrant page UI".

### Task 13: Languages

**Files:**
- Create: `src/_data/quadrantText.js`, `src/assets/quadrant/i18n.js`, `lib/quadrant-i18n.test.js`
- Reference: `lib/line-i18n.test.js` (pattern for the Brazilian-forms check), `src/_data/lineText.js`.

**Interfaces:**
- Produces: `quadrantText = { en: {...}, "pt-PT": {...} }` with every string of the page, the chart, the matrix, the notes, the equation names and captions that are translated (equation citations and journal names are not translated), the report and the error messages shown by the UI (the engine messages stay English and are mapped by a stable `code` on `EquationError`: `EquationError.code` and `params` from Task 6 select a template in `errorText[code]` in each language). The page passes `text` to `main.js` as JSON in a `data-` attribute or inline script.

- [ ] Step 1: Tests: `both languages have the same keys and the same placeholder tokens`, `no string is empty`, `Portuguese strings have no Brazilian forms` (reuse the word list of `line-i18n.test.js`), `every EquationError code has a text in both languages`, `no string contains an em dash or an exclamation mark`. Run: fail.
- [ ] Step 2: Write the texts. Portuguese is European Portuguese (for example "ecrã", "ficheiro", "utilizador", "limite inferior da normalidade"). Medical and spirometry terms follow the Portuguese practice of the maintainer. Step 3: pass. Commit "Add the English and Portuguese texts".

### Task 14: Report

**Files:**
- Create: `src/assets/quadrant/ui/report.js`, `lib/quadrant-report.test.js`

**Interfaces:**
- Produces: `buildReportHtml({ subject, selection, results, interpretations, mode, text, fonts }) -> string` where `results` maps each selected key to a table or an error message, `fonts` is `{ literata, atkinson }` base64 strings. The report is a standalone HTML file: embedded fonts, inline CSS with `@media print` for A4, the chart through `chartSvgString(mode, model, text)`, the classification for every selected equation (rejected equations with their reason), the matrix with the asterisk legend, the equation notes, the pin is not included, a header with the timestamp, a one-line copy of the disclaimer under the header and the disclaimer in the footer, and all values escaped. `downloadReport()` in `ui/notes.js` builds a Blob and an object URL for the download; the fonts are read from the page's own font files (same origin) once and cached.

- [ ] Step 1: Tests: `lists every selected equation`, `has the disclaimer twice`, `has the citations`, `embeds the fonts and has no http inside src: url( href or link`, `marks unclassified equations`, `escapes a label with <script> and &`, `rejected equations show their reason`, `the size is under 400 KB`, `the report text follows the language`, `no "nan"`. Run: fail.
- [ ] Step 2: Implement. Step 3: pass. Step 4: print the report with a headless Chrome to A4 PDF for 1, 3 and 6 equations; the default selection fits one page; six may use two with a clean break; text extracted from the PDF has no doubled characters.
- [ ] Step 5: Commit "Add the report".

### Task 15: Pages, catalogue and navigation

**Files:**
- Create: `src/quadrant/index.njk`, `src/pt/quadrant/index.njk`, `src/_includes/quadrant-app.njk`
- Modify: `src/_data/resources.json`, `lib/assets.js` (the folder `assets/quadrant` gets the `?v=` hash like `assets/line`; add a test in `lib/assets.test.js`), the sitemap and tests that list pages if any
- Delete: `src/quadrant/prototype.njk` (it is the maintainer's prototype from Task 3; delete it only after the maintainer approved the final page)

**Interfaces:**
- Produces: the two pages with front matter like `src/line/index.njk` (`permalink`, `bodyClass: quadrant-page`, `noAnalytics: true`, `quadrantLang`, `alt`, `altLang`, `altLabel`, `contentLicense: AGPL-3.0-or-later` for the app); a footer note with the pyspiro attribution and the disclaimer; a resource entry `{ id: "tool-quadrant", type: "tool", internal: true, stage: ["reproduce"], url: "/quadrant/" }` with English and Portuguese titles and descriptions in the same shape the Line entry uses.

- [ ] Step 1: Tests: `the page exists in both languages and links to each other`, `resources.json has the entry and the Portuguese mirror`, `the built page includes the module script with the version hash`, `the built HTML has no external host in src, href or url(` (host of the site excepted). Run: fail.
- [ ] Step 2: Implement. Step 3: `npm run build` in the worktree: `check:links` and `check:html` pass. Step 4: commit "Add the Quadrant pages and catalogue entry".

### Task 16: Verification and final checks

**Files:** Create `lib/quadrant-offline.test.js`, `src/assets/quadrant/VERIFICATION.md`.

- [ ] Step 1: Tests: `no module of src/assets/quadrant calls fetch with an absolute URL or XMLHttpRequest or navigator.sendBeacon`, `the only local storage key is tryworks.quadrant.v1`, `no cookie is written`, `the built page contains no analytics script`. Run: fail, then pass after any fix.
- [ ] Step 2: `VERIFICATION.md` records, for each equation, the golden case count, the rspiro cases, the paper cases and the pyspiro version and date, in the same table form as `docs/verification.md` of the Quadrant repository, and the NHANES III difference from rspiro.
- [ ] Step 3: Browser check (claude-in-chrome): both languages, three modes, light and dark, 390 px and desktop, 1 / 3 / 6 / 8 equations, the impaired presets, age 5, a decimal comma, local storage blocked, the report download and print. List anything wrong; fix in this task.
- [ ] Step 4: Run `npm test` and `npm run build` in the worktree; all pass. Commit "Record the Quadrant verification".
- [ ] Step 5: One whole-branch review by a fresh reviewer with the spec, this plan and `VERIFICATION.md` as input. Then stop: the maintainer decides on pushing and on merging into `main` (a push to `main` deploys the site; the 12 earlier unpushed Line commits go with it).
