# Generate tests/testthat/fixtures/nhanes3_age_split_cases.csv from rspiro.
# Run from the repo root: Rscript streamlit/tests/r/make_nhanes3_age_split_fixtures.R
# The cases sit around the age at which NHANES III changes from the
# equations for younger subjects to the equations for older subjects.
# rspiro: gender 1 = male, 2 = female; ethnicity 1 = Caucasian,
# 2 = African-American, 3 = Mexican-American; height in metres; ratio as
# fraction. rspiro changes equations at age 20 for both sexes.
library(rspiro)

if (!file.exists("tests/testthat/fixtures")) {
  stop("Run this script from the repo root: Rscript streamlit/tests/r/make_nhanes3_age_split_fixtures.R")
}
message("rspiro version: ", as.character(packageVersion("rspiro")))

ages <- c(8, 17, 17.5, 18, 19, 19.5, 20)
ethnicity_names <- c("caucasian", "africanamerican", "mexicanamerican")

cases <- expand.grid(
  age_years = ages, sex_code = c(1, 2), ethnicity_code = 1:3,
  KEEP.OUT.ATTRS = FALSE
)
# Heights inside the pyspiro range of both age groups for every sex and
# ethnicity: 128 cm at 8 years, 172 cm for men and 165 cm for women otherwise.
cases$height_cm <- ifelse(cases$age_years == 8, 128,
                          ifelse(cases$sex_code == 1, 172, 165))
cases$fev1_input <- ifelse(cases$age_years == 8, 1.5,
                           ifelse(cases$sex_code == 1, 4.0, 3.0))
cases$fvc_input <- ifelse(cases$age_years == 8, 1.8,
                          ifelse(cases$sex_code == 1, 4.8, 3.5))
cases$case_id <- sprintf(
  "%s_%s_%s_%s",
  ifelse(cases$sex_code == 1, "male", "female"),
  format(cases$age_years, trim = TRUE),
  cases$height_cm,
  ethnicity_names[cases$ethnicity_code]
)

rows <- list()
for (i in seq_len(nrow(cases))) {
  cs <- cases[i, ]
  h <- cs$height_cm / 100
  ratio <- cs$fev1_input / cs$fvc_input
  for (p in c("FEV1", "FVC", "FEV1FVC")) {
    obs <- switch(p, FEV1 = cs$fev1_input, FVC = cs$fvc_input, FEV1FVC = ratio)
    args <- list(age = cs$age_years, height = h, gender = cs$sex_code,
                 ethnicity = cs$ethnicity_code)
    args[[p]] <- obs
    rows[[length(rows) + 1]] <- data.frame(
      case_id = cs$case_id, age_years = cs$age_years, height_cm = cs$height_cm,
      sex_code = cs$sex_code, ethnicity_code = cs$ethnicity_code,
      fev1_input = cs$fev1_input, fvc_input = cs$fvc_input,
      parameter = p, observed = obs,
      predicted = pred_NHANES3(cs$age_years, h, cs$sex_code, cs$ethnicity_code, p),
      lln = LLN_NHANES3(cs$age_years, h, cs$sex_code, cs$ethnicity_code, p),
      z_score = do.call(zscore_NHANES3, args),
      percent_predicted = do.call(pctpred_NHANES3, args),
      stringsAsFactors = FALSE
    )
  }
}
out <- do.call(rbind, rows)
stopifnot(!anyNA(out))
write.csv(out, "tests/testthat/fixtures/nhanes3_age_split_cases.csv", row.names = FALSE)
