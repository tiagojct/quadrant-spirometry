"""Server-side checks of app.py with Streamlit's AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _run(**values):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    for key, value in values.items():
        if key in ("sex", "ethnicity_gli", "ethnicity_nhanes3"):
            at.selectbox(key=key).select(value)
        else:
            at.number_input(key=key).set_value(value)
    return at.run()


def _html(at):
    return " ".join(str(block.value) for block in at.get("html"))


def test_the_default_inputs_render_without_an_exception():
    at = _run()
    assert not at.exception
    text = _html(at)
    assert "Pattern consistent with" in text
    assert "Not available for these inputs" not in text


def test_a_family_outside_its_age_range_shows_the_reason_and_the_others_compute():
    at = _run(age_years=5.0, height_cm=110.0, fev1=1.2, fvc=1.5)
    assert not at.exception
    text = _html(at)
    assert "between 8 and 80" in text
    assert text.count("Pattern consistent with") == 2


def test_fev1_above_fvc_hides_the_results_and_shows_a_notice():
    at = _run(fev1=5.0, fvc=4.0)
    assert not at.exception
    text = _html(at)
    assert "FEV1 is larger than FVC" in text
    assert "Pattern consistent with" not in text


def test_the_download_button_is_disabled_when_inputs_are_unusable():
    assert _run(fev1=5.0, fvc=4.0).get("download_button")[0].proto.disabled
    assert not _run().get("download_button")[0].proto.disabled
