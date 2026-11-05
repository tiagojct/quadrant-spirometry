"""Server-side checks of app.py with Streamlit's AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _run(**values):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    for key, value in values.items():
        if key == "sex":
            at.get("button_group")[0].set_value(value)
        elif key in ("ethnicity_gli", "ethnicity_nhanes3"):
            at.selectbox(key=key).select(value)
        else:
            at.number_input(key=key).set_value(value)
    return at.run()


def _markdown(at):
    return " ".join(str(block.value) for block in at.markdown)


def test_the_default_inputs_render_without_an_exception():
    at = _run()
    assert not at.exception
    text = _markdown(at)
    assert text.count("Pattern consistent with normal") == 3
    assert len(at.warning) == 0
    assert len(at.table) == 3
    assert len(at.get("vega_lite_chart")) == 1


def test_the_chart_is_hidden_when_inputs_are_unusable():
    assert len(_run(fev1=5.0, fvc=4.0).get("vega_lite_chart")) == 0


def test_a_family_outside_its_age_range_shows_the_reason_and_the_others_compute():
    at = _run(age_years=5.0, height_cm=110.0, fev1=1.2, fvc=1.5)
    assert not at.exception
    assert len(at.warning) == 1
    assert "between 8 and 80" in at.warning[0].value
    assert at.warning[0].proto.title == "Not available for these inputs"
    assert len(at.table) == 2
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
    male = float(_run().table[1].value["Pred."].iloc[0])
    female = float(_run(sex="Female").table[1].value["Pred."].iloc[0])
    assert female < male


def test_the_download_button_is_disabled_when_inputs_are_unusable():
    assert _run(fev1=5.0, fvc=4.0).get("download_button")[0].proto.disabled
    assert not _run().get("download_button")[0].proto.disabled
