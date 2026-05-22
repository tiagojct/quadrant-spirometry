# Quadrant: spirometry reference value calculator
# License: AGPL-3.0-or-later
#
# Shared helpers for the test suite. testthat auto-sources every file
# named helper-*.R in tests/testthat/ before running tests.

#' Absolute tolerance used to assert that the wrapper output matches the
#' stored fixture. Set per the validation requirement in CLAUDE.md.
WRAPPER_TOLERANCE <- 0.01

#' Load a reference-case fixture from tests/testthat/fixtures/.
#'
#' @param filename CSV file name, relative to the fixtures directory.
load_fixture <- function(filename) {
  path <- testthat::test_path("fixtures", filename)
  utils::read.csv(path, stringsAsFactors = FALSE)
}

#' Compare a wrapper-produced row against the fixture row for a single
#' (case, parameter) pair. Asserts that predicted, lln, z_score, and
#' percent_predicted agree within \code{WRAPPER_TOLERANCE}.
expect_row_matches_fixture <- function(actual_row, fixture_row, info) {
  for (col in c("predicted", "lln", "z_score", "percent_predicted")) {
    testthat::expect_equal(
      actual_row[[col]], fixture_row[[col]],
      tolerance = WRAPPER_TOLERANCE,
      info = sprintf("%s | column=%s", info, col)
    )
  }
}
