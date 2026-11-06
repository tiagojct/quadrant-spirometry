"""Project-wide constants and lookup tables.

No magic numbers in calculation code; everything is named here. Lookup
labels are taken verbatim from the source papers. The values match
R/constants.R in the R app.
"""

# Sex codes used by the app and by the long-form tables. 1 = male,
# 2 = female, as in rspiro. The adapter in wrappers.py maps them to the
# codes pyspiro expects.
SEX_CODES = {"Male": 1, "Female": 2}

# GLI-2012 ethnicity codes (Quanjer et al., ERJ 2012,
# doi:10.1183/09031936.00080312).
GLI_ETHNICITY = {
    "Caucasian": 1,
    "African-American": 2,
    "NE Asian": 3,
    "SE Asian": 4,
    "Other/mixed": 5,
}

# NHANES III ethnicity codes (Hankinson et al., AJRCCM 1999,
# doi:10.1164/ajrccm.159.1.9712108).
NHANES3_ETHNICITY = {
    "Caucasian": 1,
    "African-American": 2,
    "Mexican-American": 3,
}

# Parameters reported by every reference equation wrapper. The order is
# kept in the long-form tables. FEV1FVC is the ratio FEV1/FVC.
SPIROMETRY_PARAMS = ("FEV1", "FVC", "FEV1FVC")

# Age range in years supported by GLI-2012 and GLI-Global 2022.
GLI_AGE_RANGE_YEARS = (3, 95)

# Age range in years of the NHANES III reference population.
NHANES3_AGE_RANGE_YEARS = (8, 80)

# Age range in years of the JRS 2014 equations (Kubota et al., Respir
# Investig 2014, doi:10.1016/j.resinv.2014.03.003).
JRS_AGE_RANGE_YEARS = (17, 95)

# Women: rspiro and pyspiro return NA from 94 years. The limit is
# exclusive: an age of 94 or more is rejected, 93.99 is accepted.
JRS_FEMALE_MAX_AGE_YEARS = 94

# Plausible physiological age range, used when a wrapper passes no
# equation-specific range.
PLAUSIBLE_AGE_RANGE_YEARS = (0, 120)

# Plausible standing height range in centimetres, also used by the UI.
HEIGHT_RANGE_CM = (50, 250)

# Z-score cut-off used as the lower limit of normal in the ATS/ERS 2022
# framework (5th percentile). Every module reads this one value.
LLN_Z = -1.645

# Lower z-score bound of the "mild" severity level. A FEV1 z-score of
# this value or higher is mild.
SEVERITY_MILD_Z_MIN = -2.5

# Lower z-score bound of the "moderate" level. Below it, severity is
# "severe".
SEVERITY_MODERATE_Z_MIN = -4.0

# Standard disclaimer shown in the UI footer and on exported reports.
DISCLAIMER_TEXT = (
    "For research and educational purposes. Not for clinical decision-making."
)
