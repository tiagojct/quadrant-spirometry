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

The operator selects the equations in the sidebar. The selector has three groups:

| group | equation | population | ages (years) | lower limit and z-score |
|---|---|---|---|---|
| recommended | GLI-2012 (Quanjer et al., ERJ 2012) | multi-ethnic, with an ethnicity choice | 3 to 95 | yes |
| recommended | GLI-Global 2022 (Bowerman et al., AJRCCM 2023) | race-neutral | 3 to 95 | yes |
| historical | NHANES III (Hankinson et al., AJRCCM 1999) | United States, with an ethnicity choice | 8 to 80 | yes |
| historical | ECCS/Quanjer 1993 (Eur Respir J 1993) | adults of European descent | 18 to 70 | no |
| regional | Kubota 2014, JRS (Respir Investig 2014) | Japanese adults | 17 to 95 | yes |
| regional | Pereira 2007 (J Bras Pneumol 2007) | White Brazilian adults | 26 to 86 (men), 20 to 85 (women) | lower limit only |

GLI-2012, GLI-Global 2022 and NHANES III are selected when the page opens. At least one equation stays selected. Each historical and regional set shows a short caveat. An equation without a z-score is shown as not classified, never as normal. The equation notes on the page give the citation, the population and the age range of each set.

Jian 2017 (China) and Jo 2018 (Korea) were examined and excluded: their published tables and figures disagree, so their lower limits cannot be traced to the papers. `../docs/verification.md` records how each equation was checked, and why these two were excluded.

The equations come from the `pyspiro` package (MIT licence), classes `GLI_2012`, `BOWERMAN_2022`, `HANKINSON_1999`, `ECCS_1993`, `KUBOTA_2014` and `PEREIRA_2007`. No coefficient is written by hand in this project. `quadrant/registry.py` describes each equation (name, citation, population, age range, ethnicities, group and caveat). `quadrant/wrappers.py` adapts the package:

- Sex codes: the app uses 1 for male and 2 for female. pyspiro uses 1 and 0.
- NHANES III, Pereira 2007 and ECCS 1993 express FEV1/FVC as a percentage, and NHANES III numbers its parameters differently. The wrappers convert them, so that every equation returns the same long-form table. The app always shows the ratio as a fraction.
- pyspiro returns NA outside the domain of an equation. The wrapper turns that into an error message. The page shows the message for that equation and computes the others.
- ECCS 1993: between 18 and 25 years the source enters an age of 25 years. The wrapper applies this age floor.

## Differences from the R app

- Report: the HTML report is built in memory and downloaded. It needs no Quarto and writes nothing to disk.
- NHANES III height range: pyspiro enforces the sampled height range for each sex, ethnicity and age group. rspiro extrapolates outside it. The Python app shows a message instead of an extrapolated value.
- Ages: each equation checks its own age range (see the table above). GLI-2012, GLI-Global 2022 and NHANES III use the same ranges as the R app.
- Equations: the R app has GLI-2012, GLI-Global 2022 and NHANES III only.

## Design

- Colours, fonts and corner radius are set in `.streamlit/config.toml`. The typeface is Source Sans 3 (SIL OFL), served from `static/fonts/` (see the README there for version and checksums). The app makes no request to an external font host. The themes are a light theme (chart paper and ink blue) and a dark theme (night blue and brass). The only CSS is one rule that gives table numbers equal-width digits.
- The page reads top down: the classification of each selected equation and whether they agree, then the z-score chart, then the comparison matrix (one table each for FEV1, FVC and FEV1/FVC, one row for each equation), then the equation notes. It uses native Streamlit elements: a sidebar for the inputs and the equation selector (`st.pills`), `st.badge` for the pattern, `st.tabs` and `st.table` for the matrix and `st.warning` for problems. In the matrix, a hyphen means that the equation publishes no value, and an asterisk marks a z-score below the lower limit of normal.
- The comparison chart is an Altair chart (`quadrant/charts.py`) that follows the light and dark theme. Markers differ in colour and shape, bands show the severity levels, a dashed line marks the lower limit of normal, and a tooltip gives the observed, predicted and lower-limit values. A z-score beyond the axis sits just inside the edge, and its label and tooltip keep the real value.
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
