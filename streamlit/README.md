# Quadrant, Streamlit port

Python and Streamlit version of Quadrant, the spirometry reference value calculator. The R Shiny app in the parent folder is the reference. This port keeps the same three reference families, the same ATS/ERS 2022 interpretation and the same wording rules.

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

The equations come from the `pyspiro` package (MIT licence): GLI-2012, GLI-Global 2022 (race-neutral, class `BOWERMAN_2022`) and NHANES III (class `HANKINSON_1999`). No coefficient is written by hand in this project. `quadrant/wrappers.py` adapts the package:

- Sex codes: the app uses 1 for male and 2 for female. pyspiro uses 1 and 0.
- NHANES III expresses FEV1/FVC as a percentage and numbers its parameters differently. The wrapper converts both, so that every family returns the same long-form table.
- pyspiro returns NA outside the domain of an equation. The wrapper turns that into an error message that the card shows.

## Differences from the R app

- Report: the HTML report is built in memory and downloaded. It needs no Quarto and writes nothing to disk.
- NHANES III height range: pyspiro enforces the sampled height range for each sex, ethnicity and age group. rspiro extrapolates outside it. The Python app shows a message instead of an extrapolated value.
- Ages: 3 to 95 years for GLI-2012 and GLI-Global 2022, 8 to 80 years for NHANES III, as in the R app.

## Design

- Colours, fonts and corner radius are set in `.streamlit/config.toml`, with a light theme (chart paper and ink blue) and a dark theme (night blue and brass). The only CSS is one rule that gives table numbers equal-width digits.
- The page reads top down: the classification of each equation and whether they agree, then the z-score chart, then the reference values. It uses native Streamlit elements: a sidebar for the inputs, `st.badge` for the pattern, `st.table` for the values and `st.warning` for problems.
- The comparison chart is an Altair chart (`quadrant/charts.py`) that follows the light and dark theme. Markers differ in colour and shape, bands show the severity levels, a dashed line marks the lower limit of normal, and a tooltip gives the observed, predicted and lower-limit values. A z-score beyond the axis sits just inside the edge, and its label and tooltip keep the real value.
- The app turns off Streamlit usage analytics (`gatherUsageStats = false`).
- The exported report keeps its own HTML, CSS and static SVG chart (`quadrant/visuals.py`), because it must work as a file outside Streamlit.

## Layout

- `app.py`: the Streamlit page.
- `quadrant/constants.py`: constants and lookup tables.
- `quadrant/wrappers.py`: validation and the three reference wrappers.
- `quadrant/interpretation.py`: pattern and severity.
- `quadrant/charts.py`: interactive chart for the page.
- `quadrant/visuals.py`: static SVG chart for the report.
- `quadrant/fragments.py`: HTML fragments.
- `quadrant/report.py`: report export.
- `tests/`: pytest suite.

## License

AGPL-3.0-or-later, as the parent project.
