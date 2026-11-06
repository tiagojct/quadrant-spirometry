"""Independent implementation of Pereira et al. 2007 (White Brazilian adults).

Written from the paper, not from pyspiro:

    Pereira CAC, Sato T, Rodrigues SC. Novos valores de referencia para
    espirometria forcada em brasileiros adultos de raca branca.
    J Bras Pneumol 2007;33(4):397-406. doi:10.1590/S1806-37132007000400008.

Source read on 2026-11-06: the English PDF from the journal site,
https://www.jornaldepneumologia.com.br/export-pdf/370/2007_33_4_8_english.pdf
(Table 3, men, page 402; Table 4, women, page 403). The Portuguese PDF of
the same article gives the same numbers.

Only the height and age models of FVC, FEV1 and FEV1/FVC are used. Table 3
also prints models with weight for men; the app collects no weight, so
they are not transcribed here.

Linear equations (footnote of Table 3, applied to Table 4 by its note):
    predicted = height coefficient * height_cm + age coefficient * age + constant
The signs of the coefficients are part of the printed values.

Lower limit: "The lower limits of regressions were calculated using the
5th percentile of the residual" (Methods). The tables print it as
"P - x", where P is the predicted value. The paper gives no residual
standard deviation, so this module has no z-score.

FEV1/FVC is in percent here, as in the paper (for example 82.7, not 0.827).
"""

from __future__ import annotations

# Table 3, men, 26-86 years, height 152-192 cm, n = 270.
# (height coefficient, age coefficient, constant, lower limit offset)
MALE_FVC = (0.0517, -0.0207, -3.18, 0.90)
MALE_FEV1 = (0.0338, -0.0252, -0.789, 0.76)
MALE_FEV1FVC_PERCENT = (-0.175, -0.197, 120.3, 7.6)

# Table 4, women, 20-85 years, height 137-182 cm, n = 373.
FEMALE_FVC = (0.0441, -0.0189, -2.848, 0.64)
FEMALE_FEV1 = (0.0314, -0.0203, -1.353, 0.61)
FEMALE_FEV1FVC_PERCENT = (-0.140, -0.158, 111.5, 8.50)

# Sampled ranges printed in the table headers.
MALE_AGE_RANGE_YEARS = (26, 86)
FEMALE_AGE_RANGE_YEARS = (20, 85)
MALE_HEIGHT_RANGE_CM = (152, 192)
FEMALE_HEIGHT_RANGE_CM = (137, 182)

_TABLE = {
    ("male", "FVC"): MALE_FVC,
    ("male", "FEV1"): MALE_FEV1,
    ("male", "FEV1FVC"): MALE_FEV1FVC_PERCENT,
    ("female", "FVC"): FEMALE_FVC,
    ("female", "FEV1"): FEMALE_FEV1,
    ("female", "FEV1FVC"): FEMALE_FEV1FVC_PERCENT,
}


def _row(sex: str, parameter: str) -> tuple:
    try:
        return _TABLE[(sex, parameter)]
    except KeyError:
        raise ValueError(f"No Pereira 2007 equation for {sex} {parameter}.") from None


def predicted(sex: str, age: float, height: float, parameter: str) -> float:
    """Predicted value. Litres for FVC and FEV1, percent for FEV1FVC."""
    height_coef, age_coef, constant, _ = _row(sex, parameter)
    return height_coef * height + age_coef * age + constant


def lower_limit(sex: str, age: float, height: float, parameter: str) -> float:
    """Lower limit: predicted value minus the 5th percentile of the residuals."""
    offset = _row(sex, parameter)[3]
    return predicted(sex, age, height, parameter) - offset


lln = lower_limit
