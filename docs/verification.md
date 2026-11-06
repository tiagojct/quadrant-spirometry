# Equation verification log

Each equation in `streamlit/quadrant/registry.py` has one row in this table. A test fails when a registered key has no row.

| key | source checked | how it was checked | date | result | status |
|---|---|---|---|---|---|
| gli_2012 | GLI-2012 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| gli_2022 | GLI Global 2022 reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| nhanes3 | NHANES III reference equations: Python wrapper compared with rspiro output | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures | verified |
| kubota_2014 | Kubota et al. 2014: Python wrapper compared with rspiro output (15 cases, tests/testthat/fixtures/jrs_reference_cases.csv) | R fixtures from rspiro in tests/testthat/fixtures, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Python output matches the fixtures. The fixture covers women only up to age 90. The edge ages 93.5 to 95 are covered by unit tests, not by the fixture (see JRS age facts) | verified |
| pereira_2007 | Pereira et al., J Bras Pneumol 2007;33(4):397-406, doi:10.1590/S1806-37132007000400008. Table 3 (men) and Table 4 (women), height and age models of FVC, FEV1 and FEV1/FVC. Read from https://www.jornaldepneumologia.com.br/export-pdf/370/2007_33_4_8_english.pdf (Portuguese PDF 2007_33_4_8_portugues.pdf gives the same values) | Python wrapper (pyspiro PEREIRA_2007) compared with an independent implementation written from Tables 3 and 4 (streamlit/tests/independent/pereira_2007.py), 16 cases, tolerance 0.005, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Predicted value and lower limit match the paper. No z-score: the paper gives no residual standard deviation (see Pereira 2007 notes) | verified |
| eccs_1993 | Quanjer et al., Lung volumes and forced ventilatory flows, Official Statement of the European Respiratory Society, Eur Respir J 1993;6 Suppl 16:5-40, doi:10.1183/09041950.005s1693. Original source: Table 6 (men and women, FVC, FEV1, FEV1/VC or FEV1/FVC) and section 5.1. Read from the full text at https://publications.ersnet.org/content/erj/6/suppl16/5 and the scanned print PDF https://publications.ersnet.org/content/erj/6/Suppl_16/5.full.pdf (journal pages 25 and 26, PDF pages 21 and 22); the two give the same values | Python wrapper (pyspiro ECCS_1993, with the age floor applied in the wrapper) compared with an independent implementation written from Table 6 (streamlit/tests/independent/eccs_1993.py), 32 cases (both sexes, ages 18, 25, 40 and 70, four heights per sex inside the source range), tolerance 0.005, tested by streamlit/tests/test_wrappers.py | 2026-11-06 | Predicted value and percent of predicted match the source. No lower limit and no z-score in this version. pyspiro does not apply the age floor of the source to FVC, FEV1 and FEV1/FVC in men; the wrapper corrects this (see ECCS 1993 notes) | verified |

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

## ECCS 1993 notes

Checked on 2026-11-06 against the original source, tier 1 of Ruling 10: the ERS statement itself, read on the ERS publications site in two forms (the HTML full text and the scanned PDF of the printed supplement). The automated download of erj.ersjournals.com and publications.ersnet.org returned HTTP 403, so the pages were read in a browser. The HTML table and the scanned table give the same values. No published reproduction was needed for the status. pyspiro data and docstrings were not used as a source.

- Source pages: section 5.1 "Predictions for adults of Caucasian descent" (journal page 25, PDF page 21) and Table 6 "Summary equations for lung volumes and ventilatory flows for adults aged 18-70 yr" (journal page 26, PDF page 22).
- Equations: predicted = height coefficient x H + age coefficient x A + constant, with H the standing height in metres and A the age in years. The signs are part of the printed coefficients.
  - Men: FVC = 5.76H - 0.026A - 4.34 (l). FEV1 = 4.30H - 0.029A - 2.49 (l). FEV1/VC = -0.18A + 87.21 (%).
  - Women: FVC = 4.43H - 0.026A - 2.89 (l). FEV1 = 3.95H - 0.025A - 2.60 (l). FEV1/FVC = -0.19A + 89.10 (%).
- What is given and what is not: Table 6 gives the predicted mean, the residual standard deviation (RSD) and 1.64 RSD for each equation. This version uses the predicted mean only. lln and z_score are NaN, and the pattern is not classified.
- Age floor: the title of Table 6 has a footnote, "Between 18 and 25 yr substitute 25 yr in the equations". Section 5.1 says that between 18 and 25 yr an age of 25 yr is to be entered into the various equations. The source names no exception by sex or by parameter. The floor applies to FVC, FEV1 and the ratio, for men and for women.
- pyspiro difference: pyspiro 1.0.0 (ECCS_1993) applies the floor to all parameters for women, but for men only to FEF75, FEF25_75, PEFR and FIVC. For men aged 18 to 25 its FVC, FEV1 and ratio use the real age. Example, man, 18 years, 170 cm: pyspiro FVC 4.984 l, source 4.802 l; FEV1 4.298 l, source 4.095 l; ratio 83.97 %, source 82.71 %. The wrapper passes max(age, 25) to pyspiro, so the result follows the source for both sexes. test_eccs_age_floor_below_25 pins this. The difference can be reported upstream.
- pyspiro check: a one-off check on 2026-11-06 with pyspiro 1.0.0, not a test in the suite. pyspiro holds the height coefficients per centimetre (the source values divided by 100). With the floored age, pyspiro and the independent module differ by less than 1e-14 over 288 evaluations (both sexes, eight ages from 18 to 70, six heights per sex including the range edges, three parameters).
- Ratio units: the source gives the ratio in percent. The wrapper returns the ratio and its predicted value as fractions.
- Ratio label: Table 6 labels the men's ratio "FEV1/VC" and the women's ratio "FEV1/FVC". The text of the statement uses FEV1/VC and recommends the inspiratory VC as the denominator. The wrapper uses both rows as the FEV1/FVC equation, as pyspiro does. For men the published equation is for FEV1/VC, so the predicted FEV1/FVC for men is an approximation of what the source defines. The maintainer can decide whether to keep the ratio row for men.
- Age and height: 18 to 70 years (Table 6 title and section 5.1). Section 5.1 says: "The equations were derived from a height range of 1.55-1.95 m in men, and 1.45-1.80 m in women". The wrapper rejects inputs outside these ranges with a message that names the equation (and the sex for height). The limits are inclusive. pyspiro uses the same ranges.
- Population: the source says the equations apply to men and women of European descent; the section heading says "Caucasian descent". The registry says "Adults of European descent".
- Predicted value: pyspiro lms() returns NA for this class, so the wrapper reads the predicted value from the pyspiro regression result (_scalar_regression, pyspiro 1.0.0, pinned to >=1.0,<1.1), as for Pereira 2007. It does not derive it from percent().
- Corrections: Europe PMC lists one comment on the statement (Eur Respir J 1994;7(6):1197-8) and no erratum.

Possible follow-up (not done in this task): Table 6 states that "The lower 5 or upper 95 percentiles are obtained by subtracting or adding the figure in the last column from the predicted mean" (the last column is 1.64 RSD). RSD and 1.64 RSD as printed: men FVC 0.61 and 1.00 l, FEV1 0.51 and 0.84 l, FEV1/VC 7.17 and 11.8 %; women FVC 0.43 and 0.71 l, FEV1 0.38 and 0.62 l, FEV1/FVC 6.51 and 10.7 %. With these, a lower limit (predicted minus 1.64 RSD) and a z-score ((observed minus predicted) / RSD) could be added. That is a decision for the maintainer.

## Pending

These equations have no row in the table yet. Add the row when the equation enters the registry.

- jian_2017: pending, status not decided.
- jo_2018: pending, status not decided.
- choi_2005: expected status excluded (plan recommendation: no lower limit, needs weight).
