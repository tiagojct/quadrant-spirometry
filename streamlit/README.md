# Quadrant, Streamlit port

Python and Streamlit version of Quadrant, the spirometry reference value calculator. The R Shiny app in the parent folder is the reference. This port keeps the ATS/ERS 2022 interpretation and the wording rules of the R app. It adds more reference equations and a selector to compare them for one subject.

For research and educational purposes. Not for clinical decision-making.

## Run

```sh
cd streamlit
uv sync
uv run streamlit run app.py
```

## Test

```sh
cd streamlit
uv run pytest
```

The wrapper tests read the CSV fixtures in `../tests/testthat/fixtures/`. Those fixtures hold the rspiro output, so the tests check that the Python equations match the R ones to within 0.01 for the predicted value, the lower limit of normal and the z-score.

## Reference equations

The operator selects the equations in the sidebar. The selector has three groups: recommended, historical and regional. Verification status comes from `../docs/verification.md`: verified means the Python result matches rspiro fixtures or an independent implementation written from the paper; single source means one source only; excluded means the set is not in the app.

| equation | group | population | ages (years) | lower limit and z-score | status |
|---|---|---|---|---|---|
| GLI-2012 (Quanjer et al., ERJ 2012) | recommended | multi-ethnic, with an ethnicity choice | 3 to 95 | yes | verified |
| GLI-Global 2022 (Bowerman et al., AJRCCM 2023) | recommended | race-neutral | 3 to 95 | yes | verified |
| NHANES III (Hankinson et al., AJRCCM 1999) | historical | United States, with an ethnicity choice | 8 to 80 | yes | verified |
| ECCS/Quanjer 1993 (Eur Respir J 1993) | historical | adults of European descent | 18 to 70 | no | verified |
| Kubota 2014, JRS (Respir Investig 2014) | regional | Japanese adults | 17 to 95 (men), 17 to below 94 (women) | yes | verified |
| Pereira 2007 (J Bras Pneumol 2007) | regional | White Brazilian adults | 26 to 86 (men), 20 to 85 (women) | lower limit only, no z-score | verified |
| Jian 2017 (China) | not in the app | Chinese, 4 to 80 years | not applicable | not applicable | excluded |
| Jo 2018 (Korea) | not in the app | Korean adults | not applicable | not applicable | excluded |

Jian 2017 is excluded because 9 of 36 published predicted values differ from the implementation by more than the print rounding, and the lower limit of FVC in men cannot be traced to the paper. Jo 2018 is excluded because the printed lower limit of FEV1/FVC in women contradicts the paper's own figures and text. See `../docs/verification.md` for the checks.

GLI-2012, GLI-Global 2022 and NHANES III are selected when the page opens. At least one equation stays selected. Each historical and regional set shows a short caveat. An equation without a z-score is shown as not classified, never as normal. The equation notes on the page give the citation, the population and the age range of each set.

Jian 2017 (China) and Jo 2018 (Korea) were examined and excluded: their published tables and figures disagree, so their lower limits cannot be traced to the papers. `../docs/verification.md` records how each equation was checked, and why these two were excluded.

The equations come from the `pyspiro` package (MIT licence), classes `GLI_2012`, `BOWERMAN_2022`, `HANKINSON_1999`, `ECCS_1993`, `KUBOTA_2014` and `PEREIRA_2007`. No coefficient is written by hand in this project. `quadrant/registry.py` describes each equation (name, citation, population, age range, ethnicities, group and caveat). `quadrant/wrappers.py` adapts the package:

- Sex codes: the app uses 1 for male and 2 for female. pyspiro uses 1 and 0.
- NHANES III, Pereira 2007 and ECCS 1993 express FEV1/FVC as a percentage, and NHANES III numbers its parameters differently. The wrappers convert them, so that every equation returns the same long-form table. The app always shows the ratio as a fraction.
- pyspiro returns NA outside the domain of an equation. The wrapper turns that into an error message. The page shows the message for that equation and computes the others.
- ECCS 1993: between 18 and 25 years the source enters an age of 25 years. The wrapper applies this age floor.

## How to add an equation

1. Check the equation against the published paper. Read the tables and the lower-limit rule. Do not take a package as the source: check its output against the paper.
2. Add a wrapper in `quadrant/wrappers.py`. It validates the inputs, uses sex codes 1 (male) and 2 (female), and returns the same long-form table as the other wrappers. Keep fractions for FEV1/FVC. Raise a `ValueError` with a clear message outside the domain.
3. Add the age and height ranges and any lookup tables to `quadrant/constants.py`.
4. Add an `EquationSpec` to `_SPECS` in `quadrant/registry.py`: key, name, citation, population, age range, ethnicities, group, caveat and the adapter. Add the key to `DEFAULT_KEYS` only for a recommended set.
5. Write a test that compares the wrapper with an independent implementation written from the paper (see `tests/independent/`). Add rspiro fixtures in `../tests/testthat/fixtures/` when rspiro has the equation.
6. Add a row to the table in `../docs/verification.md` with the source, the check, the date, the result and the status. `tests/test_verification_log.py` fails when a registered key has no row.
7. Add the equation to the table above.
8. Run `uv run pytest`.

## Differences from the R app

- Report: the HTML report is built in memory and downloaded. It needs no Quarto and writes nothing to disk. It lists every selected equation, also one that rejected the inputs, with the reason. The font is embedded and the file holds no URL. With the default equations it prints on one A4 page. The pinned what-if values are not in the report.
- NHANES III height range: pyspiro enforces the sampled height range for each sex, ethnicity and age group. rspiro extrapolates outside it. The Python app shows a message instead of an extrapolated value.
- NHANES III change point: the paper changes from the younger to the older equations at 20 years for men and 18 years for women. rspiro, and so the R app, changes at 20 years for both sexes. For women aged 18 to below 20 the Python app uses the older equation, as the paper says, and the R app the younger one (woman 19 years, 165 cm, Caucasian: FEV1 predicted 3.42 L, R app 3.50 L). For a fractional age just below the change point (men older than 19 and younger than 20 years, women older than 17 and younger than 18 years) the Python app uses the older equation and the paper and the R app the younger one (man 19.5 years, 172 cm, Caucasian: 4.40 L, R app 4.33 L). This comes from pyspiro and is open for the maintainer. See the NHANES III notes in `../docs/verification.md`.
- Ages: each equation checks its own age range (see the table above). GLI-2012, GLI-Global 2022 and NHANES III use the same ranges as the R app.
- Equations: the R app has GLI-2012, GLI-Global 2022 and NHANES III only.

## Design

- Colours, fonts and corner radius are set in `.streamlit/config.toml`. The typeface is Source Sans 3 (SIL OFL), served from `static/fonts/` (see the README there for version and checksums). The app makes no request to an external font host. The themes are a light theme (chart paper and ink blue) and a dark theme (night blue and brass). The only CSS is one rule that gives table numbers equal-width digits.
- The page reads top down: the classification of each selected equation and whether they agree, then the z-score chart, then the comparison matrix (one table each for FEV1, FVC and FEV1/FVC, one row for each equation), then the equation notes. It uses native Streamlit elements: a sidebar for the inputs and the equation selector (`st.pills`), `st.badge` for the pattern, `st.tabs` and `st.table` for the matrix and `st.warning` for problems. In the matrix, a hyphen means that the equation publishes no value, and an asterisk marks a z-score below the lower limit of normal.
- The comparison chart is an Altair chart (`quadrant/charts.py`) that follows the light and dark theme. Markers differ in colour and shape, bands show the severity levels, a dashed line marks the lower limit of normal, and a tooltip gives the observed, predicted and lower-limit values. A z-score beyond the axis sits just inside the edge, and its label and tooltip keep the real value.
- Example inputs, the equation selection, the ethnicity choices and the pinned what-if values live in the Streamlit session only. The app writes none of them to disk. Closing the tab clears them.
- The app holds no patient data. The example inputs are synthetic values for trying the app: normal adult, obstructive pattern, restrictive pattern (suggestive) and child.
- The report is an HTML file with its own CSS, an embedded font and a static chart. It prints from the browser Print menu.
- The app turns off Streamlit usage analytics (`gatherUsageStats = false`).
- The exported report keeps its own HTML, CSS and static SVG chart (`quadrant/visuals.py`), because it must work as a file outside Streamlit.

## Layout

- `app.py`: the Streamlit page.
- `quadrant/constants.py`: constants and lookup tables.
- `quadrant/registry.py`: the list of equations and how to compute each one.
- `quadrant/wrappers.py`: validation and the reference wrappers.
- `quadrant/matrix.py`: the comparison matrix.
- `quadrant/interpretation.py`: pattern and severity.
- `quadrant/charts.py`: interactive chart for the page.
- `quadrant/visuals.py`: static SVG chart for the report.
- `quadrant/fragments.py`: HTML fragments.
- `quadrant/report.py`: report export.
- `tests/`: pytest suite.

## License

AGPL-3.0-or-later, as the parent project.
