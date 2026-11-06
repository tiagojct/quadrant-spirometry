# Equation verification log

Each equation in `streamlit/quadrant/registry.py` has one row in this table. A test fails when a registered key has no row.

| key | source checked | how it was checked | date | result | status |
|---|---|---|---|---|---|
| gli_2012 | GLI-2012 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| gli_2022 | GLI Global 2022 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| nhanes3 | NHANES III reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| kubota_2014 | Kubota et al. 2014: Python wrapper compared with rspiro output (15 cases, tests/testthat/fixtures/jrs_reference_cases.csv) | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures. The fixture covers women only up to age 90. The edge ages 93.5 to 95 are covered by unit tests, not by the fixture (see JRS age facts) | verified |
| pereira_2007 | Pereira et al., J Bras Pneumol 2007;33(4):397-406, doi:10.1590/S1806-37132007000400008. Table 3 (men) and Table 4 (women), height and age models of FVC, FEV1 and FEV1/FVC. Read from https://www.jornaldepneumologia.com.br/export-pdf/370/2007_33_4_8_english.pdf (Portuguese PDF 2007_33_4_8_portugues.pdf gives the same values) | Python wrapper (pyspiro PEREIRA_2007) compared with an independent implementation written from Tables 3 and 4 (streamlit/tests/independent/pereira_2007.py), 16 cases, tolerance 0.005, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Predicted value and lower limit match the paper. No z-score: the paper gives no residual standard deviation (see Pereira 2007 notes) | verified |

Allowed status values: `verified`, `single source`, `excluded`.

Template for a new row (copy it into the table above):

```
| key | source checked | how it was checked | date (YYYY-MM-DD) | result | verified / single source / excluded |
```

## Policy

An equation is added only when it matches a published source. A set that cannot be checked is excluded and listed here.

For gli_2012, gli_2022 and nhanes3, the published papers are the original source. rspiro is the independent implementation used for the check.

## How to regenerate the JRS fixtures

Run this command from the repo root, so that .Rprofile activates renv:

```
Rscript streamlit/tests/r/make_jrs_fixtures.R
```

The script stops if it is not run from the repo root or if any value is NA. The script prints the rspiro version when it runs. Version used for the current fixture: rspiro 0.5. The script writes tests/testthat/fixtures/jrs_reference_cases.csv. All numbers come from rspiro. The file has 15 cases with 3 rows each (FEV1, FVC, FEV1FVC).

## JRS age facts

Checked on 2026-11-06 with rspiro 0.5 and pyspiro (class KUBOTA_2014). Both return the same values, and both return NA at the same ages.

- Men: a value for ages 17 to 95 (95 is valid, 95.01 is NA). NA at 16 and from 95.01.
- Women: a value for ages 17 to 93.99. NA from 94 (93.5 and 93.99 are valid, 94 and 95 are NA). NA at 16 and 96 for both sexes.
- The wrapper rejects an age where rspiro returns NA. For women the message says: for women the JRS 2014 equations are available below 94 years. The limit is exclusive (94 rejected, 93.99 accepted). The registry age_range stays (17, 95).
- Non-integer ages: rspiro floors the age only for the spline lookup. The LMS terms use the exact age. Age 30.7 gives a different value from age 30 (men, 170 cm, FEV1: 3.8351 L and 3.8623 L). The wrapper agrees with rspiro. test_kubota_non_integer_age_matches_rspiro pins this.
- rspiro takes height in metres. The wrapper takes centimetres.

## rspiro arguments

- `pred_JRS(age, height, gender = 1, param = "FEV1")`
- `LLN_JRS(age, height, gender = 1, param = "FEV1")`
- `zscore_JRS(age, height, gender = 1, FEV1 = NULL, FVC = NULL, VC = NULL, FEV1FVC = NULL)`
- `pctpred_JRS(age, height, gender = 1, FEV1 = NULL, FVC = NULL, VC = NULL, FEV1FVC = NULL)`
- Sex: `gender` is 1 for male and 2 for female.
- Height is in metres. Age is in years.
- FEV1/FVC is a fraction, not a percentage.
- `param` takes one of "FEV1", "FVC", "FEV1FVC".
- The fixture covers ages 17 to 95. rspiro returns NA for females older than 93, so the oldest female case is 90.

## Pereira 2007 notes

Checked on 2026-11-06 against the English and Portuguese PDFs of the paper and the Table 4 image on the journal site. The three sources give the same values.

- Equations: linear in height (cm) and age (years), predicted = height coefficient x height + age coefficient x age + constant. The signs are part of the printed coefficients. Men are in Table 3, women in Table 4.
- Lower limit: the paper says that the lower limits "were calculated using the 5th percentile of the residual". The tables print it as P - x (men: FVC 0.90 L, FEV1 0.76 L, FEV1/FVC 7.6; women: FVC 0.64 L, FEV1 0.61 L, FEV1/FVC 8.50).
- No z-score: the lower limit is an empirical percentile, not predicted minus 1.645 times a residual standard deviation, and the paper gives no residual standard deviation. The wrapper does not derive a z-score. z_score is NaN, lln is set, and the pattern is not classified. pyspiro also returns NA for zscore() and lms() for this class.
- Ratio units: the paper gives FEV1/FVC in percent. The wrapper returns the ratio, its predicted value and its lower limit as fractions.
- Weight: Table 3 also gives models with weight for men. The app collects no weight, so the wrapper uses the height and age models only (pyspiro parameters 1, 3 and 7, not the _WT parameters).
- Age and height: the registry range is 20 to 86 years. The sampled ranges differ by sex: men 26 to 86 years and 152 to 192 cm, women 20 to 85 years and 137 to 182 cm. The wrapper rejects inputs outside the range for the sex, with a message that names the sex and the limit. The limits are inclusive on the exact value. The rejection of a woman aged 85.5 is the pyspiro limit, which the wrapper follows. It is not a limit from the paper: the paper gives age at last birthday, so a woman aged 85.5 was 85 in the paper's terms.
- Predicted value: pyspiro lms() returns NA for this class, so the wrapper reads the predicted value from the pyspiro regression result (_scalar_regression, pyspiro 1.0.0). It does not derive it from percent(). Because this method is private, streamlit/pyproject.toml pins pyspiro to >=1.0,<1.1.
- pyspiro check: a one-off check on 2026-11-06 with pyspiro 1.0.0, not a test in the suite. Over 180 evaluations (both sexes, the age and height edges, three parameters) pyspiro and the independent module differ by less than 1e-13. The suite compares the wrapper with the independent module in 16 cases, including the height edges of the paper (men 152 and 192 cm, women 137 and 182 cm).

## Pending

These equations have no row in the table yet. Add the row when the equation enters the registry.

- eccs_1993: pending, status not decided.
- jian_2017: pending, status not decided.
- jo_2018: pending, status not decided.
- choi_2005: expected status excluded (plan recommendation: no lower limit, needs weight).
