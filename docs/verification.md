# Equation verification log

Each equation in `streamlit/quadrant/registry.py` has one row in this table. A test fails when a registered key has no row.

| key | source checked | how it was checked | date | result | status |
|---|---|---|---|---|---|
| gli_2012 | GLI-2012 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| gli_2022 | GLI Global 2022 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| nhanes3 | NHANES III reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| kubota_2014 | Kubota et al. 2014: Python wrapper compared with rspiro output (15 cases, tests/testthat/fixtures/jrs_reference_cases.csv) | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures. The fixture covers women only up to age 90. The edge ages 93.5 to 95 are covered by unit tests, not by the fixture (see JRS age facts) | verified |

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

## Pending

These equations have no row in the table yet. Add the row when the equation enters the registry.

- pereira_2007: pending, status not decided.
- eccs_1993: pending, status not decided.
- jian_2017: pending, status not decided.
- jo_2018: pending, status not decided.
- choi_2005: expected status excluded (plan recommendation: no lower limit, needs weight).
