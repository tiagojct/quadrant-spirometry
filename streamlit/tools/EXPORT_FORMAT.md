# Format of the exported equation tables

`tools/export_tables.py --out <dir>` writes six JSON files. The files are the input of the JavaScript engine of Quadrant (Tryworks, `src/assets/quadrant/data/`). This note describes the shape of each file and the formulas that use it. Read it together with the pyspiro 1.0.0 source and `streamlit/quadrant/wrappers.py`. The Python wrappers are the reference. The golden fixture comes from them.

The test `tests/test_export_tables.py` holds a Python evaluator that uses only the JSON files and the formulas of this note. It reproduces the output of all six wrappers (predicted, lower limit, z-score, percent predicted) within 1e-9 for a set of subjects. So the JSON contains everything the evaluation needs.

## Files

| file | `meta.equation` | pyspiro class | CSV files |
|---|---|---|---|
| gli2012.json | gli_2012 | GLI_2012 | gli_2012_splines.csv, gli_2012_coefficients.csv |
| gli2022.json | gli_2022 | BOWERMAN_2022 | bowerman_2022_splines.csv, bowerman_2022_coefficients.csv |
| nhanes3.json | nhanes3 | HANKINSON_1999 | hankinson_1999_coefficients_t4_t5.csv, hankinson_1999_coefficients_t6.csv |
| kubota2014.json | kubota_2014 | KUBOTA_2014 | kubota_2014_splines.csv, kubota_2014_coefficients.csv |
| pereira2007.json | pereira_2007 | PEREIRA_2007 | pereira_2007_coefficients.csv |
| eccs1993.json | eccs_1993 | ECCS_1993 | eccs_1993_coefficients.csv |

## General rules of the files

- Top level: `{ "meta": {...}, "tables": {...} }`. All keys are sorted. Floats are written with the shortest text that reads back to the same number (Python `repr`). The files are the same on every run.
- `meta` has `equation`, `licence` ("MIT (pyspiro)"), `pyspiroClass`, `pyspiroVersion` ("1.0.0"), `shape` and `source`. `meta.shape` has one sentence for each key of `tables`.
- `null` replaces an empty CSV cell. The JSON has no NaN and no Infinity.
- The data are the values that pyspiro loads from its own CSV files. The coefficients are not typed by hand. The test compares every cell with the CSV (read with the csv module).
- Every file has the same helper keys in `tables`:
  - `app`: what the Quadrant wrapper adds to the pyspiro class (see below).
  - `codes`: the Enum codes of pyspiro (parameter, sex, ethnicity). For information. The tables are keyed by names, not by these codes.
  - `units`: units of the inputs and outputs of pyspiro.

### The `app` block

| field | meaning |
|---|---|
| `ageRangeYears` | Age range of the wrapper, in years, both ends included. |
| `parameters` | `["FEV1", "FVC", "FEV1FVC"]`. This is the row order of the output. |
| `ratioScale` | 1 for GLI-2012, GLI-Global 2022 and Kubota. 100 for NHANES III, Pereira and ECCS. See "FEV1/FVC" below. |
| `sexCodes` | Sex codes of the app: `{"Female": 2, "Male": 1}`. |
| `sexKeyByAppCode` | App sex code to the key used in the tables. GLI and Kubota: `males`, `females`. NHANES III, Pereira and ECCS: `male`, `female`. |
| `sexToPyspiroCode` | App sex code to the pyspiro code (1 male, 0 female). The tables do not need it. |
| `ethnicityCodes` | Labels and codes of the app (GLI-2012 and NHANES III only). |
| `ethnicityKeyByCode` | NHANES III only. Code to the key in the tables (`caucasian`, `african_american`, `mexican_american`). |

Extra fields: `femaleMaxAgeYearsExclusive` (Kubota), `ageFloorYears` (ECCS).

## Rules for all equations

Inputs: age in years, height in cm, FEV1 and FVC in litres. Sex is the app code (1 male, 2 female).

FEV1/FVC. The observed value is `fev1 / fvc`, a fraction. The wrapper multiplies the observed ratio by `ratioScale` before the equation. After the equation it divides `predicted` and `lln` by `ratioScale`. The z-score and the percent predicted do not change with the scale. The output ratio is always a fraction. For FEV1 and FVC the scale is 1.

Percent predicted. `percent = round(value / predicted * 100, 2)`. Value and predicted are in the units of pyspiro (for the ratio, both are multiplied by `ratioScale`). pyspiro rounds to two decimals with Python `round`. In JavaScript use `Number((x).toFixed(2))`. Do not use `Math.round(x * 100) / 100`: it can differ in the second decimal for values near a half. This gives a difference of 0.01, which is larger than the contract tolerance of 1e-4.

Lower limit constant. The 5th percentile uses the number 1.645. It is written inside method bodies of pyspiro (`LMSReference.lln`, `HANKINSON_1999._result`) and is not a table value. It is not in the JSON. Use `LLN_Z = 1.645` in the formulas below. (The app constant `LLN_Z = -1.645` for classification is the same number with a sign.)

Out of range. pyspiro returns NA for an input outside the range of a table. The wrapper turns NA into an error. Ranges include both ends. The checks of the wrapper (`validate_subject_inputs` and the extra range checks) come first. The messages are in `wrappers.py`.

Row order and output. The output has three rows (FEV1, FVC, FEV1FVC) with `observed`, `predicted`, `lln`, `z_score`, `percent_predicted`. Equations without a z-score give NaN there. Python uses NaN, the golden fixture uses `null`.

### LMS equations (GLI-2012, GLI-Global 2022, Kubota)

For a value `v` and the triplet `L`, `M`, `S`:

- predicted = `M`
- z-score = `((v / M)^L - 1) / (L * S)` (pyspiro `LMSReference.zscore`)
- lower limit = `exp( ln(1 - 1.645 * L * S) / L + ln(M) )` (pyspiro `LMSReference.lln`)
- percent = `round(v / M * 100, 2)` (pyspiro `LMSReference.percent`)

How `L`, `M`, `S` come from the JSON differs by equation.

## gli2012.json (GLI_2012)

Mirrors `GLI_2012.lms`, `SplineReference._age_and_splines`, `_interpolated_splines` and `GLI_2012._lms_equation`. Applies to FEV1, FVC and FEV1FVC. The other columns of the CSV (FEF25_75, FEF75, FEV075, FEV075FVC) are exported but the app does not use them.

Fields:

- `ages`: the ages of the spline rows (3, 3.25, ... 95). `ageStepYears` is 0.25.
- `splines["<param>_<sexKey>_<Lspline|Mspline|Sspline>"]`: array with one value for each entry of `ages`. Example: `splines["FEV1_males_Mspline"]`.
- `splineAgeRangesYears["<param>_<sexKey>"]`: `[first, last]` age for that parameter and sex. For FEV1, FVC and FEV1FVC it is `[3, 95]`.
- `coefficients["<param>_<sexKey>"]` is an object with `a0..a6`, `p0..p5`, `q0`, `q1`.
- `app.sexKeyByAppCode` gives `males` or `females`.

Steps:

1. `prefix = param + "_" + sexKey`. If age is outside `splineAgeRangesYears[prefix]` the result is NA.
2. `lower = floor(age / 0.25) * 0.25` and `weight = (age - lower) / 0.25`.
3. Row index of an age `a` is `(a - ages[0]) / 0.25`. Take `S`, `M`, `L` splines at `lower`. If `weight == 0` use them as they are. Otherwise take the splines at `upper = min(lower + 0.25, last)` and use `(1 - weight) * lowerValue + weight * upperValue` for each of the three.
4. Call the interpolated values `Sspline`, `Mspline`, `Lspline`. The closed-form terms use the exact age (not `lower`). Let `c` be `coefficients[prefix]`. Let `AfrAm`, `NEAsia`, `SEAsia`, `Other` be 1 when ethnicity is 2, 3, 4, 5 respectively, otherwise 0. (Ethnicity 1 gives all four as 0.)
5. `L = q0 + q1 * ln(age) + Lspline`
6. `M = exp( a0 + a1 * ln(height) + a2 * ln(age) + a3 * AfrAm + a4 * NEAsia + a5 * SEAsia + a6 * Other + Mspline )`
7. `S = exp( p0 + p1 * ln(age) + p2 * AfrAm + p3 * NEAsia + p4 * SEAsia + p5 * Other + Sspline )`
8. Use the LMS formulas above. Ratio scale is 1.

Ethnicity must be 1 to 5 (`app.ethnicityCodes`). Height has no range check in pyspiro. The wrapper range for height is a plausible range in `HEIGHT_RANGE_CM` (50 to 250 cm).

## gli2022.json (BOWERMAN_2022, GLI-Global 2022 race-neutral)

Mirrors `BOWERMAN_2022._lms_equation` with the same spline method as GLI-2012 (steps 1 to 3 above; `ages`, `splines`, `splineAgeRangesYears`, `coefficients` have the same shape). There is no ethnicity.

Steps 4 onwards, with `c = coefficients[prefix]`:

- `L = q0` for FEV1 and FVC. `L = q0 + q1 * ln(age)` for FEV1FVC. (`q1` is `null` for FEV1 and FVC and must not be used.)
- `M = exp( a0 + a1 * ln(height) + a2 * ln(age) + Mspline )`
- `S = exp( p0 + p1 * ln(age) + Sspline )`
- Spline `Lspline` is 0 in the table and is not added.

Ratio scale is 1.

## kubota2014.json (KUBOTA_2014, JRS 2014)

Mirrors `IntegerAgeLMSReference.lms` and `_equation`. Applies to FEV1, FVC and FEV1FVC. The VC column is exported but not used.

Fields:

- `ageRangeYears`: `[17, 95]`.
- `splines["<param>_<sexKey>"]` = `{ agebound, Lspline, Mspline, Sspline }`. Four arrays of the same length. The tables have one row for each whole year of age.
- `coefficients["<param>_<sexKey>"]` has `a0, a1, a2, p0, p1, q0, q1`.
- `app.femaleMaxAgeYearsExclusive`: 94. The wrapper rejects women of 94 years or more (pyspiro and rspiro return NA there).

Steps:

1. If age is outside `ageRangeYears` the result is NA.
2. `i = index of floor(age) in agebound`. If there is no such row, or `Mspline` or `Sspline` is `null`, the result is NA. The age floor is only for the table row. The closed-form terms use the exact age.
3. `L = q0 + q1 * ln(age) + Lspline`. Add `Lspline` only when it is not `null`.
4. `M = exp( a0 + a1 * ln(height) + a2 * ln(age) + Mspline )`
5. `S = exp( p0 + p1 * ln(age) + Sspline )`
6. Use the LMS formulas. Ratio scale is 1.

## nhanes3.json (HANKINSON_1999 with the change point of the paper)

Mirrors `HANKINSON_1999._regression`, `_result`, `percent`, `zscore`, `lln`. The wrapper class `_Hankinson1999PaperChangePoint` in `wrappers.py` changes only the age group.

Fields:

- `ageRangeYears`: `[8, 80]`.
- `changePointYears`: `{ male: 20, female: 18 }`. These are the values of the paper. `pyspiroChildMaxAgeYears` (19, 17, with the test `age <= value`) is the pyspiro rule and is not used by the app.
- `coefficients.t4t5[param][sex][ethnicity][ageGroup]` = `{ a0_pred, a1_age, a2_age2, a3_ht2_pred, a3_ht2_lln }` for `param` in FEV1, FVC.
- `coefficients.t6[param][sex][ethnicity]` = `{ a0_pred, a0_lln, a1_age }` for `param` = FEV1FVC.
- `heightRangesCm[sex][ethnicity][ageGroup]` = `[lowest, highest]`. Used for the FEV1 and FVC equations only.
- `sex` is `male` or `female`. `ethnicity` is `caucasian`, `african_american` or `mexican_american` (`app.ethnicityKeyByCode`). `ageGroup` is `child` or `adult`.

Steps for FEV1 and FVC (Tables 4 and 5):

1. If age is outside `ageRangeYears` the result is NA.
2. `ageGroup = "child"` when `age < changePointYears[sex]`, otherwise `"adult"`.
3. If height is outside `heightRangesCm[sex][ethnicity][ageGroup]` the result is NA.
4. `base = a0_pred + a1_age * age + a2_age2 * age^2`
5. `predicted = base + a3_ht2_pred * height^2`
6. `lln = base + a3_ht2_lln * height^2`

Steps for FEV1FVC (Table 6, in percent):

1. Same age check. No age group, no height check.
2. `predicted = a0_pred + a1_age * age`
3. `lln = a0_lln + a1_age * age`

Then, for all three:

- `SEE = (predicted - lln) / 1.645`
- z-score = `(v - predicted) / SEE`
- percent = `round(v / predicted * 100, 2)`
- For FEV1FVC: `v = (fev1 / fvc) * 100`. Divide `predicted` and `lln` by 100 for the output.
- pyspiro `lms` returns NA when `predicted == lln`. The tables do not contain that case.

The paper change point differs from rspiro for women from 18 to below 20 years. The Python app follows the paper. See `docs/verification.md`.

## pereira2007.json (PEREIRA_2007)

Mirrors `PEREIRA_2007._regression` and the wrapper helper `_regression_table` (which reads the predicted value and the lower limit from pyspiro `_scalar_regression`). The app uses the height and age models only: FEV1, FVC, FEV1FVC. The weight models (names ending in `_WT`) are never used.

Fields:

- `ranges[sex]` = `{ ageYears: [first, last], heightCm: [lowest, highest] }`. Men 26 to 86 years and 152 to 192 cm. Women 20 to 85 years and 137 to 182 cm. Ends are included. Outside the range the result is NA. The wrapper range check comes first and has its own messages.
- `coefficients[param][sex]` = `{ kind, a0, a_ht, a_age, a_wt, lln }`. `kind` is `linear` or `log`.

Steps:

- `kind = "linear"`: `predicted = a0 + a_ht * height + a_age * age`. `a_wt` is 0 for the three parameters of the app. `lln = predicted - lln` (the field `lln` is an offset in litres or percent).
- `kind = "log"`: `predicted = exp( a0 + a_ht * ln(height) + a_age * ln(age) )`. `lln = predicted * lln` (the field `lln` is a factor).
- z-score is NaN. The paper gives no residual SD.
- percent = `round(v / predicted * 100, 2)`.
- For FEV1FVC: `v = (fev1 / fvc) * 100`. Divide `predicted` and `lln` by 100 for the output.

The lower limit is the 5th percentile of the residuals of the paper. The app classifies against it from observed values (see the plan).

## eccs1993.json (ECCS_1993)

Mirrors `ECCS_1993._regression` and the wrapper helper `_regression_table` with `limits_required=False`.

Fields:

- `ageRangeYears`: `[18, 70]`. `heightRangesCm`: `{ male: [155, 195], female: [145, 180] }`.
- `coefficients[param][sex]` = `{ a0, a_ht, a_age }`.
- `ageFloorYears`: 25 (pyspiro). `app.ageFloorYears`: 25 (wrapper).
- `pyspiroAgeClampParameters`: the parameters for which pyspiro floors the age. Not needed by the app: the wrapper floors the age for every parameter.

Steps:

1. The ranges of the wrapper (age 18 to 70, height by sex) come first. Outside them the result is NA.
2. `equationAge = max(age, ageFloorYears)`. This holds for every parameter and for both sexes. (pyspiro alone applies the floor to all parameters for women but only to the flow parameters for men. The wrapper corrects this to the source, which enters 25 years for ages 18 to 25 in every equation.)
3. `predicted = a0 + a_ht * height + a_age * equationAge`
4. `lln` is NaN. `z_score` is NaN. The source gives no lower limit in the tables.
5. percent = `round(v / predicted * 100, 2)`.
6. For FEV1FVC: `v = (fev1 / fvc) * 100`. Divide `predicted` by 100 for the output.

## What is not in the JSON

- The number 1.645 and the rounding of percent predicted to two decimals exist only inside method bodies of pyspiro. They are stated above. The test checks them by reproducing the wrapper output.
- The error messages of the wrappers. They are catalogued in Task 6.
- The classification rules (ATS/ERS 2022). They belong to the engine.
