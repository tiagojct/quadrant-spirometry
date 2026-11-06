"""Server-side checks of app.py with Streamlit's AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from quadrant.charts import LLN_NOTE
from quadrant.registry import EQUATIONS

APP = str(Path(__file__).resolve().parents[1] / "app.py")

GROUPS = ("recommended", "historical", "regional")


def _run(equations=None, **values):
    """Run the app, optionally choose the equations, then set inputs.

    equations is a list of registry keys. Each key goes to the pills of
    its group; a group with no listed key is cleared.
    """
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    if equations is not None:
        for group in GROUPS:
            chosen = [k for k in equations if EQUATIONS[k].group == group]
            at.button_group(key=f"equations_{group}").set_value(chosen)
        at.run()
    for key, value in values.items():
        if key == "sex":
            at.button_group(key="sex").set_value(value)
        elif key.startswith("ethnicity_"):
            at.selectbox(key=key).select(value)
        else:
            at.number_input(key=key).set_value(value)
    return at.run()


def _markdown(at):
    return " ".join(str(block.value) for block in at.markdown)


def _page_text(at):
    parts = [str(block.value) for block in at.markdown]
    parts += [str(block.value) for block in at.caption]
    parts += [str(block.value) for block in at.warning]
    parts += [str(block.value) for block in at.info]
    parts += [block.value.to_string() for block in at.table]
    return " ".join(parts)


def _matrix_rows(at):
    """Equation names in the first matrix table (FEV1)."""
    return list(at.table[0].value["Equation"])


def test_the_default_inputs_render_without_an_exception():
    at = _run()
    assert not at.exception
    text = _markdown(at)
    assert text.count("Pattern consistent with normal") == 3
    assert len(at.warning) == 0
    assert len(at.table) == 3
    assert len(at.get("vega_lite_chart")) == 1


def test_default_selection_is_the_three_current_equations():
    at = _run()
    assert at.button_group(key="equations_recommended").value == ["gli_2012", "gli_2022"]
    assert at.button_group(key="equations_historical").value == ["nhanes3"]
    assert at.button_group(key="equations_regional").value == []
    assert _matrix_rows(at) == ["GLI-2012", "GLI-Global 2022", "NHANES III"]


def test_selecting_kubota_adds_a_row_and_a_caveat():
    at = _run(equations=["gli_2012", "gli_2022", "nhanes3", "kubota_2014"])
    assert not at.exception
    assert _matrix_rows(at) == [
        "GLI-2012", "GLI-Global 2022", "NHANES III", "Kubota 2014 (JRS)"]
    captions = [str(c.value) for c in at.caption]
    assert EQUATIONS["kubota_2014"].caveat in captions
    assert EQUATIONS["nhanes3"].caveat in captions


def test_an_equation_outside_its_range_shows_a_message_and_the_rest_compute():
    at = _run(
        equations=["gli_2012", "nhanes3", "kubota_2014"],
        age_years=5.0, height_cm=110.0, fev1=1.2, fvc=1.5,
    )
    assert not at.exception
    messages = [w.value for w in at.warning]
    assert len(messages) == 2
    assert any("between 8 and 80" in m for m in messages)
    assert any("between 17 and 95" in m for m in messages)
    assert all(w.proto.title == "Not available for these inputs" for w in at.warning)
    assert _matrix_rows(at) == ["GLI-2012"]
    assert _markdown(at).count("Pattern consistent with") == 1


def test_the_last_selected_equation_cannot_be_removed():
    at = _run(equations=["gli_2012"])
    assert _matrix_rows(at) == ["GLI-2012"]
    at.button_group(key="equations_recommended").set_value([])
    at.run()
    assert not at.exception
    assert at.button_group(key="equations_recommended").value == ["gli_2012"]
    assert _matrix_rows(at) == ["GLI-2012"]
    assert "At least one equation must stay selected." in [str(c.value) for c in at.caption]


def test_an_unclassified_equation_shows_the_label_and_no_nan():
    at = _run(equations=["gli_2012", "eccs_1993"])
    assert not at.exception
    assert "Not classified (no z-score for this equation)" in _markdown(at)
    assert "nan" not in _page_text(at).lower()
    assert "ECCS/Quanjer 1993" in _matrix_rows(at)
    # The table cells are Markdown, so the hyphen is escaped (shows as "-").
    fev1 = at.table[0].value.set_index("Equation")
    assert fev1.loc["ECCS/Quanjer 1993", "LLN"] == "\\-"


def test_six_equations_render_without_an_exception():
    at = _run(equations=list(EQUATIONS))
    assert not at.exception
    assert len(_matrix_rows(at)) == 6
    assert len(at.warning) == 0
    assert "nan" not in _page_text(at).lower()


def test_an_ethnicity_selector_appears_for_each_selected_equation_with_ethnicities():
    keys = {s.key for s in _run().selectbox}
    assert keys == {"ethnicity_gli_2012", "ethnicity_nhanes3"}
    keys = {s.key for s in _run(equations=["gli_2022", "kubota_2014"]).selectbox}
    assert keys == set()


def test_the_comparison_notes_need_both_gli_equations():
    from quadrant.fragments import AGREE_TEXT

    assert AGREE_TEXT in _page_text(_run())
    assert AGREE_TEXT not in _page_text(_run(equations=["gli_2012", "nhanes3"]))


def test_the_chart_is_hidden_when_inputs_are_unusable():
    assert len(_run(fev1=5.0, fvc=4.0).get("vega_lite_chart")) == 0


def test_a_family_outside_its_age_range_shows_the_reason_and_the_others_compute():
    at = _run(age_years=5.0, height_cm=110.0, fev1=1.2, fvc=1.5)
    assert not at.exception
    assert len(at.warning) == 1
    assert "between 8 and 80" in at.warning[0].value
    assert at.warning[0].proto.title == "Not available for these inputs"
    assert _matrix_rows(at) == ["GLI-2012", "GLI-Global 2022"]
    assert _markdown(at).count("Pattern consistent with") == 2


def test_fev1_above_fvc_hides_the_results_and_shows_a_warning():
    at = _run(fev1=5.0, fvc=4.0)
    assert not at.exception
    assert len(at.warning) == 1
    assert "FEV1 is larger than FVC" in at.warning[0].value
    assert len(at.table) == 0
    assert "Pattern consistent with" not in _markdown(at)


def test_an_impaired_result_gets_a_severity_and_a_colour():
    at = _run(fev1=1.5, fvc=4.0)
    assert not at.exception
    text = _markdown(at)
    assert "Pattern consistent with obstructive" in text
    assert "-badge[" in text and ":green-badge[" not in text


def test_sex_changes_the_reference_values():
    male = float(_run().table[0].value["Pred."].iloc[1])
    female = float(_run(sex="Female").table[0].value["Pred."].iloc[1])
    assert female < male


def test_the_download_button_is_disabled_when_inputs_are_unusable():
    assert _run(fev1=5.0, fvc=4.0).get("download_button")[0].proto.disabled
    assert not _run().get("download_button")[0].proto.disabled


def test_an_equation_outside_its_range_is_not_called_no_z_score():
    at = _run(age_years=3.0, height_cm=95.0, fev1=0.8, fvc=0.9)
    assert not at.exception
    assert any("between 8 and 80" in w.value for w in at.warning)
    captions = [str(c.value) for c in at.caption]
    assert not any("no z-score" in c for c in captions)
    assert not any(c.startswith("Not plotted") for c in captions)
    assert LLN_NOTE in captions


def test_an_equation_with_no_z_score_is_still_named_under_the_chart():
    at = _run(equations=["gli_2012", "eccs_1993"])
    assert "Not plotted, no z-score: ECCS/Quanjer 1993" in [str(c.value) for c in at.caption]
