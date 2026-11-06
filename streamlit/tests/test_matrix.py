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
        lln = pereira.loc[pereira["parameter"] == code, "lln"].iloc[0]
        assert frame.loc["Pereira", "LLN"] == f"{lln:.2f}"
