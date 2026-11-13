"""Report export tests."""

import re
from datetime import datetime, timezone
from html import escape

import pytest

from quadrant.constants import DISCLAIMER_TEXT
from quadrant.fragments import NOT_CLASSIFIED_LABEL
from quadrant.interpretation import interpret_spirometry
from quadrant.registry import DEFAULT_KEYS, EQUATIONS, Subject, compute_equation
from quadrant.report import prepare_report_bundle, render_report_html
from quadrant.visuals import cross_family_chart_svg

STAMP = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

INPUTS = {
    "age_years": 40.0, "height_cm": 170.0, "sex_label": "Male",
    "fev1": 2.7, "fvc": 4.0,
    "ethnicities": {"gli_2012": "Caucasian", "nhanes3": "Caucasian"},
}

ETHNICITY_CODE = {"gli_2012": 1, "nhanes3": 1}


def _bundle(keys=DEFAULT_KEYS, inputs=INPUTS):
    """Bundle built the way the app builds it.

    A key whose equation rejects the inputs gets the error message as its
    result.
    """
    subject = Subject(inputs["age_years"], inputs["height_cm"],
                      1 if inputs["sex_label"] == "Male" else 2,
                      inputs["fev1"], inputs["fvc"])
    results, interpretations = {}, {}
    for key in keys:
        try:
            table = compute_equation(key, subject, ETHNICITY_CODE.get(key))
        except ValueError as error:
            results[key] = str(error)
            continue
        results[key] = table
        interpretations[key] = interpret_spirometry(table)
    named = {
        EQUATIONS[k].name: (v if not isinstance(v, str) else None)
        for k, v in results.items()
    }
    chart = cross_family_chart_svg(named)
    return prepare_report_bundle(inputs, list(keys), results, interpretations,
                                 chart, timestamp=STAMP)


def _visible_text(html):
    """Text outside the style block and the tags (the font data is base64)."""
    return re.sub(r"<style>.*?</style>|<[^>]+>", " ", html, flags=re.S)


def _section(html, class_name):
    """Text of the first element with this class, up to its closing tag."""
    match = re.search(rf'<(\w+)[^>]*class="[^"]*\b{class_name}\b[^"]*"[^>]*>(.*?)</\1>',
                      html, re.S)
    assert match, class_name
    return match.group(2)


# The five tests of the brief.

def test_report_lists_every_selected_equation():
    keys = list(EQUATIONS)
    html = render_report_html(_bundle(keys))
    classification = _section(html, "qd-classification")
    notes = _section(html, "qd-notes")
    names = [EQUATIONS[k].name for k in keys]
    for name in names:
        assert name in classification
        assert name in notes
    positions = [classification.index(name) for name in names]
    assert positions == sorted(positions)


def test_report_has_the_disclaimer_and_citations():
    keys = list(EQUATIONS)
    html = render_report_html(_bundle(keys))
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S)
    assert footer and DISCLAIMER_TEXT in footer.group(1)
    for key in keys:
        spec = EQUATIONS[key]
        assert spec.citation in html
        assert spec.population.rstrip(".") in html
        # The population text states the age range, so the notes add no
        # separate age sentence.
        low, high = spec.age_range
        assert f"{low:g} to {high:g}" in spec.population
        if spec.caveat:
            assert spec.caveat in html
    assert "Age range:" not in html


def test_report_embeds_the_font_and_has_no_external_url():
    html = render_report_html(_bundle(list(EQUATIONS)))
    assert html.count("@font-face") == 2
    assert html.count("url(data:font/woff2;base64,") == 2
    assert "font-family: 'Source Sans 3'" in html
    for src in re.findall(r"src:[^;]*;", html):
        assert "http" not in src
    for url in re.findall(r"url\([^)]*\)", html):
        assert "http" not in url
    assert not re.search(r"href\s*=", html)
    assert "<link" not in html
    assert "<a " not in html
    assert "http" not in html


def test_report_marks_unclassified_equations():
    html = render_report_html(_bundle(["gli_2012", "pereira_2007", "eccs_1993"]))
    classification = _section(html, "qd-classification")
    # ECCS 1993 has no lower limit and no z-score. Pereira 2007 has a
    # lower limit, so it is classified by that limit, without a severity.
    assert classification.count(NOT_CLASSIFIED_LABEL) == 1
    pills = dict(re.findall(
        r'<th scope="row">(.*?)</th><td><span class="qd-pill qd-pill-(\w+)"', classification))
    assert pills == {"GLI-2012": "mild", "Pereira 2007 (Brazil)": "ungraded",
                     "ECCS/Quanjer 1993": "none"}
    assert "nan" not in _visible_text(html).lower()


def test_report_states_the_lower_limit_basis_for_pereira():
    from quadrant.fragments import LOWER_LIMIT_NOTE

    bundle = _bundle(["gli_2012", "pereira_2007"])
    pereira = bundle["equations"][1]
    assert pereira["status"] == "classified"
    assert pereira["severity"] is None
    assert pereira["note"] == LOWER_LIMIT_NOTE
    assert pereira["label"] == "Pattern consistent with obstructive, by lower limit"
    assert bundle["equations"][0]["note"] is None
    html = render_report_html(bundle)
    classification = _section(html, "qd-classification")
    assert f'<p class="qd-reason">{escape(LOWER_LIMIT_NOTE)}</p>' in classification
    assert "published lower limit, with no severity grade" in classification
    assert ".qd-pill-ungraded {" in html
    # Pereira has no z-score, so the chart still leaves it out.
    assert bundle["not_plotted"] == "Not plotted, no z-score: Pereira 2007 (Brazil)"
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S).group(1)
    assert "against that lower limit" in footer


def test_report_escapes_labels():
    inputs = {**INPUTS, "sex_label": "Male",
              "ethnicities": {"gli_2012": "<script>alert(1)</script> & co",
                              "nhanes3": "Caucasian"}}
    html = render_report_html(_bundle(inputs=inputs))
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in html


# Further checks.

def test_a_rejected_equation_shows_its_reason():
    inputs = {**INPUTS, "age_years": 5.0, "height_cm": 110.0, "fev1": 1.2, "fvc": 1.5}
    bundle = _bundle(["gli_2012", "nhanes3", "kubota_2014"], inputs)
    html = render_report_html(bundle)
    classification = _section(html, "qd-classification")
    assert "NHANES III" in classification and "Kubota 2014 (JRS)" in classification
    assert "Not available for these inputs" in classification
    assert "between 8 and 80" in classification
    assert "between 17 and 95" in classification
    # The notes still describe the rejected equations.
    assert EQUATIONS["nhanes3"].citation in _section(html, "qd-notes")
    # The matrix has a row only for the equation with a result.
    assert [list(f.index) for f in bundle["matrix"].values()] == [["GLI-2012"]] * 3


def test_a_rejected_message_is_escaped():
    table = compute_equation("gli_2012", Subject(40, 170, 1, 2.7, 4.0), 1)
    bundle = prepare_report_bundle(
        INPUTS, ["gli_2012", "nhanes3"],
        {"gli_2012": table, "nhanes3": "Age <b>x</b> & y"},
        {"gli_2012": interpret_spirometry(table)},
        "", timestamp=STAMP,
    )
    html = render_report_html(bundle)
    assert "<b>x</b>" not in html and "Age &lt;b&gt;x&lt;/b&gt; &amp; y" in html


def test_every_listed_equation_needs_a_result():
    with pytest.raises(ValueError, match="nhanes3"):
        prepare_report_bundle(INPUTS, ["gli_2012", "nhanes3"],
                              {"gli_2012": "x"}, {}, "", timestamp=STAMP)


def test_six_equations_render_with_eccs_and_pereira():
    keys = list(EQUATIONS)
    assert {"eccs_1993", "pereira_2007"} <= set(keys) and len(keys) == 6
    bundle = _bundle(keys)
    html = render_report_html(bundle)
    assert html.startswith("<!DOCTYPE html>") and html.rstrip().endswith("</html>")
    assert html.count("<svg") == 1
    assert [e["status"] for e in bundle["equations"]] == [
        "classified", "classified", "classified", "classified",
        "classified", "unclassified"]
    assert "nan" not in _visible_text(html).lower()


def test_the_report_has_the_inputs_and_the_timestamp():
    html = render_report_html(_bundle(list(EQUATIONS)))
    inputs = _section(html, "qd-inputs")
    for text in ("40 years", "170 cm", "Male", "2.70 L", "4.00 L", "0.68",
                 "Ethnicity (GLI-2012)", "Ethnicity (NHANES III)", "Caucasian"):
        assert text in inputs
    assert "2026-11-05 12:00 UTC" in html


def test_ethnicity_rows_only_for_equations_in_the_report():
    inputs = _section(render_report_html(_bundle(["gli_2022", "kubota_2014"])), "qd-inputs")
    assert "Ethnicity" not in inputs


def test_the_matrix_has_three_tables_and_the_legend():
    html = render_report_html(_bundle(list(EQUATIONS)))
    matrix = html[html.index('class="qd-matrix'):]
    for title in ("FEV1", "FVC", "FEV1/FVC"):
        assert f"<caption>{title}" in matrix
    assert html.count('class="qd-table qd-matrix-table"') == 3
    assert "A hyphen (-) means that the equation publishes no value." in html
    assert ("An asterisk (*) marks a result below the lower limit of normal "
            "(z-score below -1.645, or observed value below the published lower "
            "limit).") in html
    assert "\\*" not in html


def test_the_not_plotted_note_is_under_the_chart():
    bundle = _bundle(["gli_2012", "eccs_1993"])
    assert bundle["not_plotted"] == "Not plotted, no z-score: ECCS/Quanjer 1993"
    html = render_report_html(bundle)
    chart = _section(html, "qd-chart")
    assert "Not plotted, no z-score: ECCS/Quanjer 1993" in chart
    assert "Not plotted" not in render_report_html(_bundle())


def test_the_report_has_print_rules_and_a_light_theme():
    html = render_report_html(_bundle())
    assert "@media print" in html
    assert "size: A4" in html
    assert "break-inside: avoid" in html
    assert "print-color-adjust: exact" in html
    assert "color-scheme: light" in html
    assert "prefers-color-scheme" not in html


def test_the_report_stays_small():
    html = render_report_html(_bundle(list(EQUATIONS)))
    assert len(html.encode("utf-8")) < 400_000


def test_the_report_text_follows_the_wording_rules():
    html = render_report_html(_bundle(list(EQUATIONS)))
    text = _visible_text(html)
    assert "—" not in text and "!" not in text
    assert "diagnos" not in text.lower()


def test_the_disclaimer_is_also_under_the_header():
    html = render_report_html(_bundle(list(EQUATIONS)))
    header = re.search(r"<header[^>]*>(.*?)</header>", html, re.S).group(1)
    assert DISCLAIMER_TEXT in header
    assert html.count(DISCLAIMER_TEXT) == 2


def test_the_footer_disclaimer_has_regular_weight():
    css = re.search(r"<style>(.*?)</style>", render_report_html(_bundle()), re.S).group(1)
    rule = re.search(r"\.qd-foot \.qd-disclaimer \{([^}]*)\}", css).group(1)
    assert "font-weight: 400" in rule and "font-weight: 600" not in rule


def test_the_gli_agreement_text_is_in_the_report():
    from quadrant.fragments import AGREE_NOTE, AGREE_TEXT

    agree = _bundle(inputs={**INPUTS, "fev1": 3.2})
    assert agree["gli_notes"] == []
    html = render_report_html(agree)
    assert AGREE_TEXT in html and AGREE_NOTE in html
    one_gli = render_report_html(_bundle(["gli_2012", "nhanes3"], {**INPUTS, "fev1": 3.2}))
    assert AGREE_TEXT not in one_gli


def test_the_report_names_the_parameters_on_different_sides():
    from quadrant.fragments import AGREE_TEXT, DIFFER_HEADING

    differ = _bundle(inputs={**INPUTS, "fev1": 2.9})
    assert len(differ["gli_notes"]) == 1
    html = render_report_html(differ)
    assert escape(DIFFER_HEADING) in html and AGREE_TEXT not in html
    assert "Classification differs" not in html


def test_the_report_matrix_marks_pereira_values_below_the_lower_limit():
    bundle = _bundle(["gli_2012", "pereira_2007"])
    frames = bundle["matrix"]
    assert frames["FEV1"].loc["Pereira 2007 (Brazil)", "LLN"].endswith(" *")
    assert not frames["FVC"].loc["Pereira 2007 (Brazil)", "LLN"].endswith(" *")
    assert frames["FEV1/FVC"].loc["Pereira 2007 (Brazil)", "LLN"].endswith(" *")
    html = render_report_html(bundle)
    lln = frames["FEV1"].loc["Pereira 2007 (Brazil)", "LLN"]
    assert f"<td>{lln}</td>" in _section(html, "qd-matrix")


def _contrast(a, b):
    def lum(hex_colour):
        rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_ungraded_pill_differs_from_the_unclassified_pill():
    from quadrant.fragments import BADGE_PALETTE
    from quadrant.styles import UNCLASSIFIED_PILL

    bg, fg = BADGE_PALETTE["ungraded"]
    assert bg == "#bfdbfe"
    assert bg != UNCLASSIFIED_PILL[0]
    assert _contrast(bg, fg) >= 4.5
    css = re.search(r"<style>(.*?)</style>", render_report_html(_bundle()), re.S).group(1)
    assert ".qd-pill-ungraded { border: 1px solid #1e3a8a; }" in css
