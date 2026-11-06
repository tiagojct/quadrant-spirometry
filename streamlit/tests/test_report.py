"""Report export tests."""

from datetime import datetime, timezone

from quadrant.constants import DISCLAIMER_TEXT
from quadrant.fragments import render_gli_comparison
from quadrant.interpretation import interpret_spirometry
from quadrant.report import prepare_report_bundle, render_report_html
from quadrant.visuals import cross_family_chart_svg
from quadrant.wrappers import compute_gli_2012, compute_gli_global_2022, compute_nhanes3

SUBJECT = {
    "age_years": 40.0, "height_cm": 170.0, "sex_label": "Male",
    "ethnicity_gli_label": "Caucasian", "ethnicity_nhanes3_label": "Caucasian",
    "fev1": 2.7, "fvc": 4.0,
}


def _bundle(results=None):
    results = results or {
        "gli_2012": compute_gli_2012(40, 170, 1, 1, 2.7, 4.0),
        "gli_2022": compute_gli_global_2022(40, 170, 1, 2.7, 4.0),
        "nhanes3": compute_nhanes3(40, 170, 1, 1, 2.7, 4.0),
    }
    interpretations = {k: interpret_spirometry(v) if v is not None else None for k, v in results.items()}
    chart = cross_family_chart_svg(
        {"GLI-2012": results["gli_2012"], "GLI-Global 2022": results["gli_2022"],
         "NHANES III": results["nhanes3"]}
    )
    return prepare_report_bundle(
        SUBJECT, results, interpretations, chart,
        render_gli_comparison(results["gli_2012"], results["gli_2022"]),
        timestamp=datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc),
    )


def test_bundle_has_one_block_per_family():
    bundle = _bundle()
    assert [b["name"] for b in bundle["family_blocks"]] == [
        "GLI-2012", "GLI-Global 2022 (race-neutral)", "NHANES III"]
    for block in bundle["family_blocks"]:
        assert block["badge_html"] and block["table_html"] and block["interpretation_html"]


def test_report_is_a_complete_document_with_the_disclaimer():
    html = render_report_html(_bundle())
    assert html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")
    assert DISCLAIMER_TEXT in html
    assert "2026-11-05 12:00:00 UTC" in html
    for text in ("Subject", "Cross-family z-score comparison", "Per-family results",
                 "Caucasian", "<svg"):
        assert text in html


def test_report_keeps_a_missing_family_without_failing():
    results = {
        "gli_2012": compute_gli_2012(40, 170, 1, 1, 2.7, 4.0),
        "gli_2022": compute_gli_global_2022(40, 170, 1, 2.7, 4.0),
        "nhanes3": None,
    }
    html = render_report_html(_bundle(results))
    assert "No data." in html and "NHANES III" in html


def test_report_escapes_subject_labels():
    bundle = _bundle()
    bundle["subject"] = {**SUBJECT, "sex_label": "<b>x</b>"}
    assert "<b>x</b>" not in render_report_html(bundle)


def test_report_has_one_block_for_each_given_equation():
    from quadrant.wrappers import compute_eccs_1993, compute_kubota_2014

    results = {
        "gli_2012": compute_gli_2012(40, 170, 1, 1, 2.7, 4.0),
        "kubota_2014": compute_kubota_2014(40, 170, 1, 2.7, 4.0),
        "eccs_1993": compute_eccs_1993(40, 170, 1, 2.7, 4.0),
    }
    interpretations = {k: interpret_spirometry(v) for k, v in results.items()}
    bundle = prepare_report_bundle(
        SUBJECT, results, interpretations, "", "",
        timestamp=datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc),
    )
    assert [b["name"] for b in bundle["family_blocks"]] == [
        "GLI-2012", "Kubota 2014 (JRS)", "ECCS/Quanjer 1993"]
    html = render_report_html(bundle)
    assert "Not classified" in html
    assert "nan" not in html.lower()
