"""Server-side checks of app.py with Streamlit's AppTest."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from quadrant.charts import LLN_NOTE
from quadrant.registry import EQUATIONS

GUARD_NOTE = "At least one equation must stay selected."

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


def test_pereira_alone_is_classified_by_its_lower_limit():
    from quadrant.fragments import LOWER_LIMIT_NOTE

    at = _run(equations=["pereira_2007"], fev1=2.7)
    assert not at.exception
    text = _markdown(at)
    assert "Pattern consistent with obstructive, by lower limit" in text
    assert ":blue-badge[" in text
    assert "Not classified" not in text
    captions = [str(c.value) for c in at.caption]
    assert LOWER_LIMIT_NOTE in captions
    assert "Not plotted, no z-score: Pereira 2007 (Brazil)" in captions
    assert "nan" not in _page_text(at).lower()


def test_pereira_with_gli_2012_states_the_basis_in_the_summary():
    at = _run(equations=["gli_2012", "pereira_2007"], fev1=2.7)
    assert not at.exception
    text = _markdown(at)
    assert "The equations give the same pattern." in text
    assert "Pereira 2007 (Brazil) is classified from observed values against the published lower limit" in text
    assert "agree on the classification" not in text
    assert "nan" not in _page_text(at).lower()


def test_the_help_text_describes_the_lower_limit_basis():
    at = _run()
    text = _markdown(at)
    assert "observed values against that lower limit" in text
    assert "ECCS 1993" in text


def test_six_equations_render_without_an_exception():
    at = _run(equations=list(EQUATIONS))
    assert not at.exception
    assert len(_matrix_rows(at)) == 6
    assert len(at.warning) == 0
    assert "nan" not in _page_text(at).lower()


def test_an_ethnicity_selector_appears_for_each_selected_equation_with_ethnicities():
    # The example selector is also a selectbox; only ethnicity keys count.
    def ethnicity_keys(at):
        return {s.key for s in at.selectbox if s.key.startswith("ethnicity_")}

    assert ethnicity_keys(_run()) == {"ethnicity_gli_2012", "ethnicity_nhanes3"}
    assert ethnicity_keys(_run(equations=["gli_2022", "kubota_2014"])) == set()


def test_the_comparison_notes_need_both_gli_equations():
    from quadrant.fragments import AGREE_NOTE, AGREE_TEXT, DIFFER_HEADING

    agree = _page_text(_run())
    assert f"{AGREE_TEXT} {AGREE_NOTE}" in agree and DIFFER_HEADING not in agree
    one_gli = _page_text(_run(equations=["gli_2012", "nhanes3"]))
    assert AGREE_TEXT not in one_gli and DIFFER_HEADING not in one_gli


def test_the_comparison_notes_name_the_parameters_on_different_sides():
    from quadrant.fragments import AGREE_TEXT, DIFFER_HEADING

    # Man, 40 years, 170 cm, FVC 4.0 L: at FEV1 2.9 L GLI-2012 puts FEV1
    # below the lower limit and GLI-Global 2022 within it.
    text = _page_text(_run(age_years=40.0, height_cm=170.0, sex="Male", fev1=2.9, fvc=4.0))
    assert DIFFER_HEADING in text and AGREE_TEXT not in text
    assert "FEV1: GLI-2012 z = -1.91 (below LLN)" in text


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


def test_the_guard_note_goes_away_after_an_unrelated_change():
    at = _run(equations=["gli_2012"])
    at.button_group(key="equations_recommended").set_value([])
    at.run()
    assert GUARD_NOTE in [str(c.value) for c in at.caption]
    at.number_input(key="age_years").set_value(45.0)
    at.run()
    assert not at.exception
    assert GUARD_NOTE not in [str(c.value) for c in at.caption]


def test_the_ethnicity_choice_survives_deselecting_the_equation():
    at = _run(ethnicity_gli_2012="African-American")
    assert at.selectbox(key="ethnicity_gli_2012").value == "African-American"
    at.button_group(key="equations_recommended").set_value(["gli_2022"])
    at.run()
    assert "ethnicity_gli_2012" not in {s.key for s in at.selectbox}
    at.button_group(key="equations_recommended").set_value(["gli_2012", "gli_2022"])
    at.run()
    assert not at.exception
    assert at.selectbox(key="ethnicity_gli_2012").value == "African-American"


# Presets and the what-if comparison.

def _cell(at, equation, column="Change in z", tab=0):
    return at.table[tab].value.set_index("Equation").loc[equation, column]


def _z(key, ethnicity=1, **inputs):
    from quadrant.registry import Subject, compute_equation

    values = {"age_years": 40.0, "height_cm": 170.0, "sex_code": 1,
              "fev1": 3.20, "fvc": 4.00} | inputs
    table = compute_equation(key, Subject(**values), ethnicity)
    return dict(zip(table["parameter"], table["z_score"]))


def test_choosing_a_preset_sets_the_inputs():
    from quadrant.presets import PRESETS

    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert at.selectbox(key="preset").value == "custom"
    at.selectbox(key="preset").select("obstructive")
    at.run()
    assert not at.exception
    preset = PRESETS["obstructive"]
    assert at.number_input(key="age_years").value == preset.age_years
    assert at.number_input(key="height_cm").value == preset.height_cm
    assert at.number_input(key="fev1").value == preset.fev1
    assert at.number_input(key="fvc").value == preset.fvc
    assert at.button_group(key="sex").value == "Male"
    assert "Pattern consistent with obstructive" in _markdown(at)
    at.selectbox(key="preset").select("restrictive")
    at.run()
    assert at.button_group(key="sex").value == "Female"


def test_an_edit_after_a_preset_is_kept_on_later_reruns():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.selectbox(key="preset").select("normal_adult")
    at.run()
    at.number_input(key="fev1").set_value(2.10)
    at.run()
    at.run()
    assert not at.exception
    assert at.number_input(key="fev1").value == 2.10
    assert at.selectbox(key="preset").value == "custom"


def test_the_examples_are_called_synthetic():
    captions = " ".join(str(c.value) for c in _run().caption)
    assert "synthetic" in captions
    assert "not patient data" in captions


def test_pinning_adds_a_change_column():
    at = _run()
    assert "Change in z" not in at.table[0].value.columns
    at.button(key="pin_button").click()
    at.run()
    assert not at.exception
    assert _cell(at, "GLI-2012") in ("0.00", "+0.00")
    assert any(
        str(c.value).startswith("Compared with the pinned values: age 40 years, "
                                "height 170 cm, male, FEV1 3.20 L, FVC 4.00 L")
        for c in at.caption
    )
    at.number_input(key="fev1").set_value(2.80)
    at.run()
    expected = _z("gli_2012", fev1=2.80)["FEV1"] - _z("gli_2012")["FEV1"]
    assert _cell(at, "GLI-2012") == f"{expected:+.2f}"
    assert _cell(at, "GLI-2012").startswith("-")


def test_the_pin_survives_a_rerun():
    at = _run()
    at.button(key="pin_button").click()
    at.run()
    at.number_input(key="age_years").set_value(60.0)
    at.run()
    at.run()
    assert not at.exception
    expected = _z("gli_2012", age_years=60.0)["FEV1"] - _z("gli_2012")["FEV1"]
    assert _cell(at, "GLI-2012") == f"{expected:+.2f}"


def test_the_pin_survives_unusable_inputs_and_its_column_returns():
    at = _run()
    at.button(key="pin_button").click()
    at.run()
    assert "Change in z" in at.table[0].value.columns
    # FEV1 above FVC: no equation has a result, so the matrix is not drawn.
    at.number_input(key="fev1").set_value(5.0)
    at.run()
    assert not at.exception
    assert len(at.table) == 0
    assert "pin" in at.session_state
    # Usable inputs again: the change column is back against the same pin.
    at.number_input(key="fev1").set_value(2.80)
    at.run()
    assert not at.exception
    assert "Change in z" in at.table[0].value.columns
    expected = _z("gli_2012", fev1=2.80)["FEV1"] - _z("gli_2012")["FEV1"]
    assert _cell(at, "GLI-2012") == f"{expected:+.2f}"


def test_a_decimal_age_with_all_equations_selected_runs_without_an_exception():
    at = _run(equations=list(EQUATIONS), age_years=19.5)
    assert not at.exception
    assert at.number_input(key="age_years").value == 19.5
    assert _matrix_rows(at)


def test_clearing_the_pin_removes_it():
    at = _run()
    at.button(key="pin_button").click()
    at.run()
    assert "Change in z" in at.table[0].value.columns
    at.button(key="clear_pin").click()
    at.run()
    assert not at.exception
    assert "pin" not in at.session_state
    assert "Change in z" not in at.table[0].value.columns
    assert not any(str(c.value).startswith("Compared with") for c in at.caption)
    assert at.button(key="clear_pin").proto.disabled


def test_the_pin_compares_only_the_equations_in_both():
    at = _run(equations=["gli_2012", "nhanes3"])
    at.button(key="pin_button").click()
    at.run()
    at.button_group(key="equations_recommended").set_value(["gli_2012", "gli_2022"])
    at.run()
    assert not at.exception
    assert _matrix_rows(at) == ["GLI-2012", "GLI-Global 2022", "NHANES III"]
    assert _cell(at, "GLI-2012") in ("0.00", "+0.00")
    # GLI-Global 2022 was not pinned, so it has no change.
    assert _cell(at, "GLI-Global 2022") == "\\-"


def test_a_pinned_nan_shows_a_hyphen():
    at = _run(equations=["gli_2012", "eccs_1993"])
    at.button(key="pin_button").click()
    at.run()
    at.number_input(key="fev1").set_value(2.80)
    at.run()
    assert not at.exception
    assert _cell(at, "ECCS/Quanjer 1993") == "\\-"
    assert "nan" not in _page_text(at).lower()


# The report built by the app.

def _capture_reports(monkeypatch):
    """Record each report the app renders. The app imports the function
    on every run, so the patched one is used."""
    import quadrant.report as report

    reports = []
    original = report.render_report_html

    def record(bundle):
        html = original(bundle)
        reports.append(html)
        return html

    monkeypatch.setattr(report, "render_report_html", record)
    return reports


def test_the_report_keeps_a_rejected_equation_with_its_reason(monkeypatch):
    reports = _capture_reports(monkeypatch)
    _run(equations=["gli_2012", "nhanes3", "kubota_2014"],
         age_years=5.0, height_cm=110.0, fev1=1.2, fvc=1.5)
    html = reports[-1]
    for text in ("GLI-2012", "NHANES III", "Kubota 2014 (JRS)",
                 "between 8 and 80", "between 17 and 95"):
        assert text in html


def test_the_report_has_no_pinned_values(monkeypatch):
    reports = _capture_reports(monkeypatch)
    at = _run()
    at.button(key="pin_button").click()
    at.run()
    at.number_input(key="fev1").set_value(2.80)
    at.run()
    assert not at.exception
    html = reports[-1]
    assert "Change in z" not in html and "pinned" not in html.lower()
    assert "2.80 L" in html and "3.20 L" not in html


def test_the_equation_notes_state_the_age_range_once():
    keys = list(EQUATIONS)
    captions = [str(block.value) for block in _run(equations=keys).caption]
    for key in keys:
        spec = EQUATIONS[key]
        note = f"{spec.citation}. {spec.population.rstrip('.')}."
        assert note in captions
        low, high = spec.age_range
        assert note.count(f"{low:g} to {high:g}") == 1
    assert not any("Age range:" in caption for caption in captions)


def test_no_button_uses_the_primary_type():
    # Streamlit puts white text on a primary button. On the dark-theme
    # brass that is under 4.5:1, so every button is secondary.
    at = _run()
    assert at.get("download_button")
    for block in list(at.button) + list(at.get("download_button")):
        assert block.proto.type != "primary", block.proto.label
