"""Independent implementation of part of the NHANES III equations.

Written from the paper, not from pyspiro or rspiro:

    Hankinson JL, Odencrantz JR, Fedan KB. Spirometric reference values
    from a sample of the general U.S. population. Am J Respir Crit Care
    Med 1999;159(1):179-187. doi:10.1164/ajrccm.159.1.9712108.

Source read on 2026-11-06 from the PDF on CDC Stacks,
https://stacks.cdc.gov/view/cdc/198173/cdc_198173_DS1.pdf (journal pages
183 and 184: Table 4, Table 5 and the text on the change point).

Scope: FEV1 and FVC for Caucasian subjects only. The module is used to
check which age group the wrapper uses around the change point. It is not
a full implementation.

Change point: the text on journal page 184 says that "20 yr was the best
change point for males and 18 yr for females". Table 4 (male subjects)
has the rows "Caucasian < 20 yr of age" and "Caucasian >= 20 yr of age".
Table 5 (female subjects) has the rows "Caucasian < 18 yr of age" and
"Caucasian >= 18 yr of age".

Equation (1), journal page 185:
    parameter = b0 + b1 * age + b2 * age^2 + b3 * height^2
    height in cm. HtPRD is b3 for the predicted value, HtLLN replaces it for
    the lower limit of normal. An empty Age2 cell is 0.
"""

# Change point in years: the younger equations apply below this age.
CHANGE_POINT_YEARS = {"male": 20, "female": 18}

# (Intercept, Age, Age2, HtPRD, HtLLN), as printed. Signs are part of the
# printed values.
_TABLE = {
    # Table 4, male subjects, Caucasian.
    ("male", "younger", "FEV1"): (-0.7453, -0.04106, 0.004477, 0.00014098, 0.00011607),
    ("male", "younger", "FVC"): (-0.2584, -0.20415, 0.010133, 0.00018642, 0.00015695),
    ("male", "older", "FEV1"): (0.5536, -0.01303, -0.000172, 0.00014098, 0.00011607),
    ("male", "older", "FVC"): (-0.1933, 0.00064, -0.000269, 0.00018642, 0.00015695),
    # Table 5, female subjects, Caucasian.
    ("female", "younger", "FEV1"): (-0.8710, 0.06537, 0.0, 0.00011496, 0.00009283),
    ("female", "younger", "FVC"): (-1.2082, 0.05916, 0.0, 0.00014815, 0.00012198),
    ("female", "older", "FEV1"): (0.4333, -0.00361, -0.000194, 0.00011496, 0.00009283),
    ("female", "older", "FVC"): (-0.3560, 0.01870, -0.000382, 0.00014815, 0.00012198),
}


def age_group(sex: str, age_years: float) -> str:
    """The age group the paper assigns: "younger" or "older"."""
    return "younger" if age_years < CHANGE_POINT_YEARS[sex] else "older"


def predicted_and_lln(
    sex: str, age_years: float, height_cm: float, parameter: str, group: str
) -> tuple[float, float]:
    """Predicted value and lower limit (litres) from the named age group."""
    b0, b1, b2, ht_prd, ht_lln = _TABLE[(sex, group, parameter)]
    base = b0 + b1 * age_years + b2 * age_years**2
    height2 = height_cm**2
    return base + ht_prd * height2, base + ht_lln * height2
