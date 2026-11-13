# Quadrant in JavaScript, inside Tryworks (design)

Date: 2026-11-06. Status: draft for approval. Author of the decisions: Tiago Jacinto. Calls made by the assistant are marked "Assistant call".

## Intent and why

Quadrant shows how the same spirometry result is read by different reference equations, and where the conclusions diverge. Two apps exist today, in R (Shiny) and in Python (Streamlit, branch `streamlit-port`, pull request 1). Both are limited in design. The main chart in Streamlit cannot be drawn the way the maintainer wants, and neither app carries the Tryworks identity.

This project builds a third version in plain JavaScript that lives inside the Tryworks site (`teaching/tryworks`), next to The Line. It gives full control of the design, runs in the browser with no server, and exists in English and in European Portuguese.

The first thing a visitor must understand is what the page is for. The page says it in its first line: it shows how the same spirometry is read by different reference equations, and where the conclusions diverge.

## Goals

1. Purpose at first sight. A one-sentence purpose at the top, in plain words. An example is already filled in when the page opens, so the chart shows something before the visitor types a number. The chart title asks the question it answers (for example "How much do the equations agree?").
2. A main chart with three modes that the visitor can switch, over one data model:
   - Spread (default): one thin track for each parameter, a rule that joins the equations, the spread in z-score written above it, the lower limit of normal marked.
   - Plate: one band for each parameter, severity washes behind the marks, a value beside each mark.
   - Grid: equations down, parameters across, a large z-score and a small bar with the lower limit tick in each cell.
   The mode is kept in the browser (local storage, every access in try/catch) and is the mode used in the report. Switching modes never changes a number.
3. The same six equations as the Python app, with the same rules: GLI-2012, GLI-Global 2022, NHANES III (change points of the paper: 20 years for men, 18 years for women), Kubota 2014 (JRS), Pereira 2007 and ECCS/Quanjer 1993.
4. The same behaviour as the Python app (see `streamlit/` and `docs/verification.md` on `streamlit-port` for the reference):
   - ATS/ERS 2022 pattern, with severity from the FEV1 z-score (mild at -2.5 or higher, moderate to -4.0, severe below).
   - Pereira 2007 is classified from observed values against its published lower limit, with no severity grade. ECCS 1993 is "not classified". No equation without a z-score or lower limit ever reads as normal.
   - A value counts as below a limit only when it is strictly below, with a tolerance of 1e-9.
   - An equation that rejects the inputs shows its reason and the others still compute.
   - Equation selector (at least one stays selected), per-equation ethnicity selectors, caveats for regional and historical sets, the comparison matrix (asterisk rule included), four synthetic presets, the what-if pin, the FEV1 greater than FVC notice, and the disclaimer.
   - A report with an A4 print layout, with the typeface embedded, no external URL, and the disclaimer on every export.
5. Two languages, English and European Portuguese, from the first release. Texts are outside the code. A test checks that every string has a Portuguese text of the same shape and that the Portuguese has no Brazilian forms, as the Line does.
6. The Tryworks design: tokens and components of `packages/design`, Literata and Atkinson Hyperlegible Next self-hosted, light and dark themes, contrast at WCAG AA or better (the design check already tests colour contrast), keyboard use, a layout that works at 390 px, and a text alternative for the chart (the matrix is the table form of the same data).
7. Verification of every number (see Verification).

## Non-goals

- No server, no database, no accounts.
- No new equations in this version. Jian 2017 and Jo 2018 stay excluded and Choi 2005 is not added (reasons in `docs/verification.md`).
- No replacement of the R and Python apps. They stay in the repository as the reference and the cross-check.
- No chart library at run time. The chart is drawn by hand in SVG.
- No PDF library. The report is HTML that prints to PDF from the browser.
- No diagnostic claims anywhere. Wording is descriptive.

## Anti-goals (what would make it a failure even if it works)

- A visitor cannot say what the page is for after ten seconds.
- Any number differs from the verified Python output beyond the stated tolerance.
- A chart mode changes what the numbers say, or hides an equation that did not compute.
- The page looks like a generic chart widget and not like Tryworks.
- Any text that reads as a diagnosis or as advice for a clinical decision.
- Any data leaves the browser, or any patient-like data is stored.

## Constraints

- Follow the Tryworks conventions for The Line: vanilla ES modules, no bundler, served from `src/assets/`, `?v=<hash>` on relative imports, a page in `src/<name>/index.njk` with `noAnalytics: true`, no `fetch` to other hosts, no cookies, no external request. Tests in `lib/*.test.js` run by `npm test`; jsdom is a dev dependency only. `check:html` and `check:links` must pass.
- Pages at `/quadrant/` and `/pt/quadrant/`. (Assistant call.)
- Licence: the Quadrant code keeps AGPL-3.0-or-later, in its own folder with its own LICENSE file, as the design package has its own. The rest of Tryworks keeps its licence. (Assistant call; to confirm.)
- Coefficients and lookup tables are never typed by hand. They are exported from pyspiro (version pinned, 1.0.x) by a script that records the source of each table, and the NHANES III age split follows the paper. Every equation is tested three ways: against golden outputs of the Python app, against the rspiro fixtures that exist in the repository, and against the published tables through the independent implementations in `streamlit/tests/independent/`. (Assistant call.)
- Text rules of the project: no emojis, no em dashes, no exclamation marks, no bold emphasis in UI text, descriptive wording, the disclaimer sentence "For research and educational purposes. Not for clinical decision-making." on the page and on every export.
- Portuguese is European Portuguese.
- The Tryworks working tree has unpushed commits and uncommitted files. The work starts on a branch. A push to `main` deploys the site, so nothing is pushed to `main` without the maintainer's approval.

## Decided by the maintainer

- Built in JavaScript, inside Tryworks, in English and Portuguese.
- The main chart is the thing to get right. The Spread mode is the favourite, and the visitor can switch modes.
- The design follows Tryworks closely.
- Its objective must be clear.

## Left to the builder

- The module layout inside `src/assets/quadrant/`, and how the data files are shaped and loaded (JSON files or JS modules, one file for each equation or one for all) as long as there is no run-time request to another host and the page stays light.
- How the chart code is organised: one data model and three thin renderers, with shared marks, colours, scales and text alternatives.
- The exact colours and shapes of the marks for up to eight equations, within the Tryworks palette and the contrast rules (the Python app uses eight colour and shape pairs).
- Whether the state of the page (inputs, selection, mode) is also written to the URL hash. No personal data may go in the URL by default. If it is added, it must be the same synthetic-example data only.
- The wording of the purpose line, the chart titles and the Portuguese texts, within the rules above.

## Assistant calls to check

- Spread is the default mode. The mode is saved in local storage.
- The chart is hand-drawn SVG, with no chart library.
- Pages at `/quadrant/` and `/pt/quadrant/`.
- The AGPL code is kept in its own folder with its own LICENSE.
- Python and R stay as the reference. Golden outputs from the Python app are the main test source.
- The first release has no URL state.

## Further calls from the builder check (Assistant calls)

- Chart gate. The plan has an early chart milestone: a static prototype of the three modes with the preset data, in the Tryworks design, and a stop for the maintainer's approval before the equations, the languages and the report are built. This is the same rule as the project CLAUDE.md (no new phase without explicit acceptance). The three sketches in `.superpowers/brainstorm/` (file `chart-directions.html`) are the starting reference.
- Base of the Tryworks branch. The branch starts from local `main`, because the Portuguese version of The Line, the i18n tests and the `/pt/` page pattern are only there (12 unpushed commits). The Quadrant branch is not merged and nothing is pushed until the maintainer has pushed those commits.
- Reference and scripts. The Python app on `streamlit-port` is the frozen reference once pull request 1 is merged. The export script and the golden generator live in the Quadrant repository (they need Python, uv and pyspiro 1.0.x). Their JSON output is committed to Tryworks, with the script and the pyspiro version recorded in a header of each file. If the Python app changes, the fixtures are regenerated. The rspiro check skips NHANES III women from 18 to below 20 years, where the Python output (the paper) is the target.
- Licence. The maintainer agreed to AGPL-3.0-or-later code in its own folder. pyspiro is MIT, which is compatible. The builder confirms the licence text of pyspiro and records the attribution in the data headers and in the page footer.
- The report is the standalone HTML file of the Python app: fonts embedded as base64, inline CSS, a static SVG chart that does not depend on the theme. It is the only export. Printing to PDF is done by the browser.
- Catalogue. The page is listed in `src/_data/resources.json` as a tool, like The Line (id `tool-quadrant`, stage `reproduce`, internal, with an English and a Portuguese description), so the home, tools pages, sitemap and `check:links` include it.

## Verification

- Golden test: a script runs the Python app's calculation code over a grid of inputs (ages, heights, both sexes, ethnicities, values around the limits) for the six equations and writes the expected outputs as a fixture. The JavaScript equations must match within 1e-6 for predicted values, lower limits and z-scores. Out-of-range inputs must give the same error reason in both.
- rspiro fixtures and the paper tables are checked as in the Python app.
- Behaviour tests cover the classification rules, the below-limit rule, the unclassified cases, the presets, the pin, the report and the language files.
- A check that the page makes no request to another host and writes nothing except the mode and the language to local storage.
- A visual check in a browser: three modes, light and dark, 390 px and desktop, both languages, and the print layout of the report.
