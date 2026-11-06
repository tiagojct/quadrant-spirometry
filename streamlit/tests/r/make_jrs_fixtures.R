# Generate tests/testthat/fixtures/jrs_reference_cases.csv from rspiro.
# Run from the repo root: Rscript streamlit/tests/r/make_jrs_fixtures.R
# rspiro: gender 1 = male, 2 = female; height in metres; ratio as fraction.
# rspiro returns NA for females above age 93, so the oldest female case is 90.
library(rspiro)

cases <- data.frame(
  case_id = c(
    "c1_male_30_175", "c2_female_17_160", "c3_male_17_180",
    "c4_female_18_150", "c5_male_18_190", "c6_female_30_165",
    "c7_male_50_170", "c8_female_50_155", "c9_male_80_172",
    "c10_female_80_158", "c11_male_95_165", "c12_female_90_150",
    "c13_male_50_185", "c14_female_30_175", "c15_male_80_150"
  ),
  age_years = c(30, 17, 17, 18, 18, 30, 50, 50, 80, 80, 95, 90, 50, 30, 80),
  height_cm = c(175, 160, 180, 150, 190, 165, 170, 155, 172, 158, 165, 150, 185, 175, 150),
  sex_code  = c(1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1),
  fev1_input = c(4.0, 2.8, 4.5, 2.0, 5.2, 3.2, 2.2, 2.3, 1.9, 1.2, 1.2, 0.7, 3.9, 2.0, 1.0),
  fvc_input  = c(5.0, 3.4, 5.4, 2.6, 6.2, 3.9, 3.6, 2.9, 3.0, 1.9, 2.0, 1.2, 5.1, 3.6, 2.0)
)

rows <- list()
for (i in seq_len(nrow(cases))) {
  cs <- cases[i, ]
  h <- cs$height_cm / 100
  ratio <- cs$fev1_input / cs$fvc_input
  for (p in c("FEV1", "FVC", "FEV1FVC")) {
    obs <- switch(p, FEV1 = cs$fev1_input, FVC = cs$fvc_input, FEV1FVC = ratio)
    args <- list(age = cs$age_years, height = h, gender = cs$sex_code)
    args[[p]] <- obs
    rows[[length(rows) + 1]] <- data.frame(
      case_id = cs$case_id, age_years = cs$age_years, height_cm = cs$height_cm,
      sex_code = cs$sex_code, fev1_input = cs$fev1_input, fvc_input = cs$fvc_input,
      parameter = p, observed = obs,
      predicted = pred_JRS(cs$age_years, h, cs$sex_code, p),
      lln = LLN_JRS(cs$age_years, h, cs$sex_code, p),
      z_score = do.call(zscore_JRS, args),
      percent_predicted = do.call(pctpred_JRS, args),
      stringsAsFactors = FALSE
    )
  }
}
out <- do.call(rbind, rows)
write.csv(out, "tests/testthat/fixtures/jrs_reference_cases.csv", row.names = FALSE)
