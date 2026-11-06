"""Tests for the comparison matrix."""

import pandas as pd

from quadrant.matrix import matrix_frames

NAN = float("nan")


def _table(predicted, lln, z, percent):
    return pd.DataFrame(
        {
            "parameter": ["FEV1", "FVC", "FEV1FVC"],
            "observed": [3.0, 4.0, 0.75],
            "predicted": predicted,
            "lln": lln,
            "z_score": z,
            "percent_predicted": percent,
        }
    )


TABLES = {
    "GLI-2012": _table([3.912, 4.876, 0.8049], [3.101, 3.902, 0.7012],
                       [-1.701, -1.2, 0.333], [76.68, 82.03, 93.2]),
    "GLI-Global 2022": _table([3.8, 4.7, 0.81], [3.0, 3.8, 0.7],
                              [-1.5, -1.0, -1.645], [78.9, 85.1, 92.6]),
    "ECCS/Quanjer 1993": _table([3.85, 4.75, 0.79], [NAN, NAN, NAN],
                                [NAN, NAN, NAN], [77.92, 84.21, 94.94]),
}


def test_matrix_has_one_row_for_each_equation():
    frames = matrix_frames(TABLES)
    assert list(frames) == ["FEV1", "FVC", "FEV1/FVC"]
    for frame in frames.values():
        assert frame.index.name == "Equation"
        assert list(frame.index) == ["GLI-2012", "GLI-Global 2022", "ECCS/Quanjer 1993"]
        assert list(frame.columns) == ["Pred.", "LLN", "Z-score", "% pred"]
    fev1 = frames["FEV1"]
    assert list(fev1.loc["GLI-2012"]) == ["3.91", "3.10", "-1.70 *", "76.7"]
    assert list(frames["FEV1/FVC"].loc["GLI-2012"]) == ["0.80", "0.70", "0.33", "93.2"]


def test_matrix_marks_values_below_the_lln():
    frames = matrix_frames(TABLES)
    assert frames["FEV1"].loc["GLI-2012", "Z-score"] == "-1.70 *"
    assert frames["FEV1"].loc["GLI-Global 2022", "Z-score"] == "-1.50"
    # -1.645 is the limit itself and is not below it.
    assert frames["FEV1/FVC"].loc["GLI-Global 2022", "Z-score"] == "-1.65"
    assert frames["FVC"].loc["GLI-2012", "Z-score"] == "-1.20"


def test_matrix_shows_a_dash_for_missing_limits():
    frames = matrix_frames(TABLES)
    for frame in frames.values():
        row = frame.loc["ECCS/Quanjer 1993"]
        assert row["LLN"] == "-"
        assert row["Z-score"] == "-"
        assert "nan" not in frame.to_string().lower()
    assert list(frames["FVC"].loc["ECCS/Quanjer 1993"]) == ["4.75", "-", "-", "84.2"]


def test_markdown_cells_escape_the_dash_and_the_asterisk():
    # st.table reads every cell as Markdown: a lone "-" becomes a list bullet.
    from quadrant.matrix import markdown_cells

    shown = markdown_cells(matrix_frames(TABLES)["FEV1"])
    assert shown.loc["ECCS/Quanjer 1993", "LLN"] == "\\-"
    assert shown.loc["GLI-2012", "Z-score"] == "-1.70 \\*"
    assert shown.loc["GLI-2012", "Pred."] == "3.91"
    assert shown.index.name == "Equation"


# Ported from the tests of the removed results_for_display helper.
def test_matrix_rounds_values_and_keeps_the_limit_itself_unmarked():
    table = _table([3.5, 4.5, 0.8], [2.8, 3.6, 0.7], [-2.0, 0.0, -1.645], [85.0, 90.0, 94.0])
    frames = matrix_frames({"A": table})
    assert frames["FEV1"].loc["A", "Z-score"] == "-2.00 *"
    assert frames["FVC"].loc["A", "Z-score"] == "0.00"
    assert frames["FEV1/FVC"].loc["A", "Z-score"] == "-1.65"
    assert [frames[p].loc["A", "% pred"] for p in frames] == ["85.0", "90.0", "94.0"]


def test_a_missing_z_score_never_gets_the_below_lln_asterisk():
    table = _table([3.5, 4.4, 0.8], [NAN, 3.5, NAN], [NAN, -2.0, NAN], [85.7, 90.9, 93.8])
    frames = matrix_frames({"A": table})
    assert [frames[p].loc["A", "Z-score"] for p in frames] == ["-", "-2.00 *", "-"]
    assert [frames[p].loc["A", "LLN"] for p in frames] == ["-", "3.50", "-"]


def test_matrix_rows_for_the_real_eccs_and_pereira_tables():
    from quadrant.wrappers import compute_eccs_1993, compute_pereira_2007

    eccs = compute_eccs_1993(40, 170, 1, 3.0, 4.0)
    pereira = compute_pereira_2007(40, 170, 1, 3.0, 4.0)
    frames = matrix_frames({"ECCS": eccs, "Pereira": pereira})
    for code, title in (("FEV1", "FEV1"), ("FVC", "FVC"), ("FEV1FVC", "FEV1/FVC")):
        frame = frames[title]
        assert "nan" not in frame.to_string().lower()
        assert frame.loc["ECCS", "LLN"] == "-" and frame.loc["ECCS", "Z-score"] == "-"
        assert frame.loc["Pereira", "Z-score"] == "-"
        row = pereira.loc[pereira["parameter"] == code].iloc[0]
        mark = " *" if row["observed"] < row["lln"] else ""
        assert frame.loc["Pereira", "LLN"] == f"{row['lln']:.2f}{mark}"
    # FEV1 3.0 L is below the Pereira lower limit (3.19 L) for this man.
    assert frames["FEV1"].loc["Pereira", "LLN"].endswith(" *")


# An equation with a published lower limit and no z-score (Pereira 2007):
# the LLN cell ends with " *" when the observed value is strictly below it.

def test_lln_cell_is_marked_when_observed_is_below_a_published_limit():
    # observed 3.0, 4.0, 0.75; limits 3.1 (above), 4.0 (equal), 0.70 (below observed)
    table = _table([3.5, 4.5, 0.8], [3.1, 4.0, 0.70], [NAN, NAN, NAN], [85.7, 88.9, 93.8])
    frames = matrix_frames({"P": table})
    assert frames["FEV1"].loc["P", "LLN"] == "3.10 *"
    # Exactly equal to the limit is not below it.
    assert frames["FVC"].loc["P", "LLN"] == "4.00"
    assert frames["FEV1/FVC"].loc["P", "LLN"] == "0.70"
    for frame in frames.values():
        assert frame.loc["P", "Z-score"] == "-"


def test_lln_cell_is_not_marked_for_equations_with_z_scores():
    # GLI-2012 FEV1: observed 3.0 is below the lln 3.101, but the mark
    # goes on the z-score cell only.
    frames = matrix_frames(TABLES)
    assert frames["FEV1"].loc["GLI-2012", "LLN"] == "3.10"
    assert frames["FEV1"].loc["GLI-2012", "Z-score"] == "-1.70 *"


def test_the_lln_mark_uses_the_rule_of_the_classifier():
    from quadrant.interpretation import interpret_spirometry, is_below
    from quadrant.wrappers import compute_pereira_2007

    table = compute_pereira_2007(40, 170, 1, 2.7, 4.0)
    frames = matrix_frames({"Pereira": table})
    for row in table.itertuples(index=False):
        title = {"FEV1": "FEV1", "FVC": "FVC", "FEV1FVC": "FEV1/FVC"}[row.parameter]
        marked = frames[title].loc["Pereira", "LLN"].endswith(" *")
        assert marked == is_below(row.observed, row.lln)
    # FEV1 and FEV1/FVC below, FVC not: the obstructive pattern.
    assert [frames[t].loc["Pereira", "LLN"].endswith(" *") for t in frames] == [
        True, False, True]
    assert interpret_spirometry(table)["pattern"] == "obstructive"


def test_a_real_pereira_value_equal_to_its_limit_gets_no_mark():
    from quadrant.wrappers import compute_pereira_2007

    fvc_lln = float(compute_pereira_2007(40, 170, 1, 3.5, 4.5)
                    .set_index("parameter").loc["FVC", "lln"])
    frames = matrix_frames({"Pereira": compute_pereira_2007(40, 170, 1, 3.3, fvc_lln)})
    assert frames["FVC"].loc["Pereira", "LLN"] == f"{fvc_lln:.2f}"


def test_the_legend_covers_both_kinds_of_mark():
    from quadrant.matrix import MATRIX_LEGEND

    assert MATRIX_LEGEND == (
        "A hyphen (-) means that the equation publishes no value. An asterisk "
        "(\\*) marks a result below the lower limit of normal (z-score below "
        "-1.645, or observed value below the published lower limit)."
    )


def test_a_pereira_value_equal_to_the_printed_limit_gets_no_mark():
    from quadrant.wrappers import compute_pereira_2007

    # The lower limit is 3.2800000000000002 in floating point.
    frames = matrix_frames({"Pereira": compute_pereira_2007(27, 163, 1, 3.28, 4.0)})
    assert frames["FEV1"].loc["Pereira", "LLN"] == "3.28"
