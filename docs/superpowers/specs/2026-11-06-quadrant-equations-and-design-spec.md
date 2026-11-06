# Quadrant Streamlit: more equations and a stronger design (spec)

Date: 2026-11-06. Branch: streamlit-port. Scope: the Python app in `streamlit/` only. The R app is not changed.

## Requests from the maintainer

1. Add more reference equations. Chosen: ECCS/Quanjer 1993, Pereira 2007 (Brazil), Kubota 2014 (Japan, JRS), and the Asian sets Jian 2017, Jo 2018 and Choi 2005.
2. Improve the design. Chosen focus: an equation selector with a comparison matrix, a stronger visual identity, a report and print output that match the new look, and faster input (presets, checks, a what-if comparison).
3. Verification standard: add an equation only when its coefficients match the published paper, with tests from worked examples. Where rspiro also has the equation, cross-check against it as well. State which sets have only one source.
4. Typeface: Source Sans 3 (SIL Open Font License), self-hosted, from the official Adobe Fonts GitHub release. No external font request at run time.
5. Quality bar: "incredible" and "no mistakes".

## Findings from the pyspiro survey

- Kubota 2014: LMS equations, age 17 to 95. rspiro has the same set (`pred_JRS`, `LLN_JRS`, `zscore_JRS`), so a full independent cross-check is possible.
- ECCS 1993: pyspiro publishes no lower limit, so `lln` and `zscore` are NA. Predicted value and percent of predicted only, unless the paper's residual standard deviations are verified from a source.
- Choi 2005: no lower limit, and weight is required for FVC and FEV6. It gives no z-score and so no classification. Recommendation: do not add it. The maintainer may overrule.
- Pereira 2007: regression equations for White Brazilian adults, age 20 to 86. Weight is optional for men.
- Jian 2017 (age 4 to 80) and Jo 2018 (age 19 to 90): LMS equations with large spline tables from supplementary material. No second implementation exists. They are added only if a verification source is found.
- Units differ: Jian 2017, ECCS 1993 and NHANES III hold FEV1/FVC as a percentage. The app always shows a fraction.
- pyspiro codes sex as 1 for male and 0 for female. The app uses 1 and 2.

## Requirements

- Every family returns the same long-form table. `z_score` may be NaN only for an equation that publishes no z-score or no lower limit (ECCS 1993 and Pereira 2007). `lln` may be NaN only when the equation publishes no lower limit.
- An equation without a lower limit shows "not classified". It never shows "normal".
- Note, 2026-11-06 (decision of the maintainer): an equation that publishes a lower limit but no z-score (Pereira 2007) is classified from the observed values against the published lower limit, with the same strict rule as for z-scores. Its severity is not graded, and the page and the report state the basis. An equation with neither a lower limit nor a z-score (ECCS 1993) stays "not classified".
- Each equation states its population and age range. A regional or historical set carries a short caveat.
- The app keeps no patient data. Session state holds only the current inputs and the pinned what-if values for the session.
- Text rules of the project apply: no emojis, no em dashes, no exclamation marks, no bold emphasis in UI text, descriptive wording only, the disclaimer on every export.
