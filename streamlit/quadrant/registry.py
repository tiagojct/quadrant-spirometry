"""Registry of reference equations.

Each entry describes one equation (name, citation, population, valid age
range, ethnicity codes) and holds an adapter that calls the existing
wrapper. Pure functions, no Streamlit state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .constants import (
    GLI_AGE_RANGE_YEARS,
    GLI_ETHNICITY,
    JRS_AGE_RANGE_YEARS,
    NHANES3_AGE_RANGE_YEARS,
    NHANES3_ETHNICITY,
)
from .wrappers import (
    compute_gli_2012,
    compute_gli_global_2022,
    compute_kubota_2014,
    compute_nhanes3,
)


@dataclass(frozen=True)
class Subject:
    """One person's inputs. Sex: 1 male, 2 female. FEV1 and FVC in litres."""

    age_years: float
    height_cm: float
    sex_code: int
    fev1: float
    fvc: float


@dataclass(frozen=True)
class EquationSpec:
    """Description of one reference equation and how to compute it.

    group is "recommended", "historical" or "regional". compute takes the
    subject and an ethnicity code (None when the equation has none) and
    returns the long-form table.
    """

    key: str
    name: str
    citation: str
    population: str
    age_range: tuple[float, float]
    ethnicities: dict[str, int] | None
    has_lower_limit: bool
    group: str
    caveat: str | None
    compute: Callable[[Subject, int | None], pd.DataFrame]


def _gli_2012(subject: Subject, ethnicity_code: int | None) -> pd.DataFrame:
    return compute_gli_2012(
        subject.age_years,
        subject.height_cm,
        subject.sex_code,
        ethnicity_code,
        subject.fev1,
        subject.fvc,
    )


def _gli_2022(subject: Subject, ethnicity_code: int | None) -> pd.DataFrame:
    return compute_gli_global_2022(
        subject.age_years,
        subject.height_cm,
        subject.sex_code,
        subject.fev1,
        subject.fvc,
    )


def _nhanes3(subject: Subject, ethnicity_code: int | None) -> pd.DataFrame:
    return compute_nhanes3(
        subject.age_years,
        subject.height_cm,
        subject.sex_code,
        ethnicity_code,
        subject.fev1,
        subject.fvc,
    )


def _kubota_2014(subject: Subject, ethnicity_code: int | None) -> pd.DataFrame:
    return compute_kubota_2014(
        subject.age_years,
        subject.height_cm,
        subject.sex_code,
        subject.fev1,
        subject.fvc,
    )


_SPECS = (
    EquationSpec(
        key="gli_2012",
        name="GLI-2012",
        citation="Quanjer et al., ERJ 2012",
        population=(
            "Multi-ethnic sample of healthy never-smokers from many "
            "countries, ages 3 to 95 years."
        ),
        age_range=GLI_AGE_RANGE_YEARS,
        ethnicities=GLI_ETHNICITY,
        has_lower_limit=True,
        group="recommended",
        caveat=None,
        compute=_gli_2012,
    ),
    EquationSpec(
        key="gli_2022",
        name="GLI-Global 2022",
        citation="Bowerman et al., AJRCCM 2023",
        population=(
            "Race-neutral equation built from healthy never-smokers of "
            "several ethnic groups, ages 3 to 95 years."
        ),
        age_range=GLI_AGE_RANGE_YEARS,
        ethnicities=None,
        has_lower_limit=True,
        group="recommended",
        caveat=None,
        compute=_gli_2022,
    ),
    EquationSpec(
        key="nhanes3",
        name="NHANES III",
        citation="Hankinson et al., AJRCCM 1999",
        population=(
            "US population sample of healthy never-smokers, ages 8 to 80 "
            "years."
        ),
        age_range=NHANES3_AGE_RANGE_YEARS,
        ethnicities=NHANES3_ETHNICITY,
        has_lower_limit=True,
        group="historical",
        caveat="A pre-GLI US reference, kept for comparison.",
        compute=_nhanes3,
    ),
    EquationSpec(
        key="kubota_2014",
        name="Kubota 2014 (JRS)",
        citation="Kubota et al., Respir Investig 2014",
        population="Japanese adults, 17 to 95 years (women below 94 years)",
        age_range=JRS_AGE_RANGE_YEARS,
        ethnicities=None,
        has_lower_limit=True,
        group="regional",
        caveat="Japanese reference population. Use for comparison, not as the default.",
        compute=_kubota_2014,
    ),
)

# Display order. Later tasks add regional and other sets here.
EQUATIONS: dict[str, EquationSpec] = {spec.key: spec for spec in _SPECS}

# Equations selected when the operator has not chosen any. Regional and
# historical sets stay out of this tuple.
DEFAULT_KEYS = ("gli_2012", "gli_2022", "nhanes3")


def compute_equation(
    key: str, subject: Subject, ethnicity_code: int | None = None
) -> pd.DataFrame:
    """Long-form reference table for one equation and one subject."""
    if key not in EQUATIONS:
        raise ValueError(f"Unknown equation: {key}.")
    return EQUATIONS[key].compute(subject, ethnicity_code)
