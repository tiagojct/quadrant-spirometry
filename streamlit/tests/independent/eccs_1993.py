"""Independent implementation of the ECCS/ERS 1993 summary equations.

Written from the source, not from pyspiro:

    Quanjer PH, Tammeling GJ, Cotes JE, Pedersen OF, Peslin R, Yernault JC.
    Lung volumes and forced ventilatory flows. Report Working Party
    Standardization of Lung Function Tests, European Community for Steel
    and Coal. Official Statement of the European Respiratory Society.
    Eur Respir J 1993;6 Suppl 16:5-40. doi:10.1183/09041950.005s1693.

Source read on 2026-11-06 on the ERS publications site,
https://publications.ersnet.org/content/erj/6/suppl16/5 (full text, Table 6)
and the scanned PDF of the printed supplement,
https://publications.ersnet.org/content/erj/6/Suppl_16/5.full.pdf
(journal page 26, PDF page 22: Table 6; journal page 25, PDF page 21:
section 5.1). The two give the same values.

Table 6, "Summary equations for lung volumes and ventilatory flows for
adults aged 18-70 yr":
    predicted = height coefficient * H + age coefficient * A + constant
    H: standing height in metres. A: age in years.
The signs of the coefficients are part of the printed values.

Age floor: the title of Table 6 carries a footnote, "Between 18 and 25 yr
substitute 25 yr in the equations". Section 5.1 says: "between 18 and 25 yr
an age of 25 yr is to be entered into the various equations". The source
makes no exception by sex or by parameter, so the floor applies to every
equation here, for men and for women.

Height: section 5.1 says "The equations were derived from a height range
of 1.55-1.95 m in men, and 1.45-1.80 m in women".

Ratio: the ratio is in percent, as printed. Table 6 labels the men's row
"FEV1/VC" and the women's row "FEV1/FVC". Both rows are used here as the
FEV1/FVC equation of this module; the label difference is recorded in
docs/verification.md.

The table also prints the residual standard deviation (RSD) and 1.64 RSD.
They are not used here: this module gives the predicted value only.
"""

from __future__ import annotations

# Table 6, men. (height coefficient per metre, age coefficient, constant)
MALE_FVC = (5.76, -0.026, -4.34)
MALE_FEV1 = (4.30, -0.029, -2.49)
MALE_FEV1VC_PERCENT = (0.0, -0.18, 87.21)  # printed: FEV1/VC % = -0.18A + 87.21

# Table 6, women.
FEMALE_FVC = (4.43, -0.026, -2.89)
FEMALE_FEV1 = (3.95, -0.025, -2.60)
FEMALE_FEV1FVC_PERCENT = (0.0, -0.19, 89.10)  # printed: FEV1/FVC % = -0.19A + 89.10

# Table 6 title and section 5.1: adults aged 18 to 70 years; between 18 and
# 25 years an age of 25 years is entered.
AGE_RANGE_YEARS = (18, 70)
AGE_FLOOR_YEARS = 25

# Section 5.1: height range of the source data, in centimetres.
MALE_HEIGHT_RANGE_CM = (155, 195)
FEMALE_HEIGHT_RANGE_CM = (145, 180)

_TABLE = {
    ("male", "FVC"): MALE_FVC,
    ("male", "FEV1"): MALE_FEV1,
    ("male", "FEV1FVC"): MALE_FEV1VC_PERCENT,
    ("female", "FVC"): FEMALE_FVC,
    ("female", "FEV1"): FEMALE_FEV1,
    ("female", "FEV1FVC"): FEMALE_FEV1FVC_PERCENT,
}


def _row(sex: str, parameter: str) -> tuple:
    try:
        return _TABLE[(sex, parameter)]
    except KeyError:
        raise ValueError(f"No ECCS 1993 equation for {sex} {parameter}.") from None


def effective_age(age: float) -> float:
    """Age entered into the equations: 25 years for ages 18 to 25."""
    return max(age, AGE_FLOOR_YEARS)


def predicted(sex: str, age: float, height: float, parameter: str) -> float:
    """Predicted value. Height in cm. Litres for FVC and FEV1, percent for FEV1FVC."""
    height_coef, age_coef, constant = _row(sex, parameter)
    height_m = height / 100.0
    return height_coef * height_m + age_coef * effective_age(age) + constant
