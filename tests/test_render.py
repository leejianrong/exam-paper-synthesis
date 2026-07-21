"""V5 — pure HTML renderers (KAN-146).

Structure/content assertions against real generated objects. No browser; the
renderers are pure functions, so these are fast and deterministic.
"""

from __future__ import annotations

import re

import pytest
from exam_engine import generate
from exam_engine.render import render_answer_key_html, render_worksheet_html

# One object per rung of the Ratio ladder; easy/medium carry a ``bar_model``
# diagram, hard carries a ``bar_model_before_after``.
EASY = generate("ratio_easy", 0)
MEDIUM = generate("ratio_medium", 0)
HARD = generate("ratio_hard", 0)
ALL = [EASY, MEDIUM, HARD]

TITLE = "Ratio Practice"


# --- document shell ---------------------------------------------------------


def _assert_no_external_fetches(html: str) -> None:
    """No CDN / network resource references (xmlns namespace URIs are not fetches)."""
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "@import" not in html
    for cdn in ("cdn.jsdelivr", "unpkg.com", "cdnjs", "fonts.googleapis", "fonts.gstatic"):
        assert cdn not in html
    # Fonts are inlined as data: URIs (no dangling font file refs).
    assert "data:font/woff2;base64," in html
    assert "url(fonts/" not in html


def test_worksheet_is_a_full_selfcontained_doc():
    html = render_worksheet_html(TITLE, ALL)
    assert html.startswith("<!doctype html>")
    assert '<main class="sheet worksheet">' in html
    # KaTeX is inlined, not linked.
    assert "renderMathInElement" in html
    assert ".katex" in html  # a KaTeX CSS rule is present
    _assert_no_external_fetches(html)


def test_answer_key_is_a_full_selfcontained_doc():
    html = render_answer_key_html(TITLE, ALL)
    assert html.startswith("<!doctype html>")
    assert '<main class="sheet answer-key">' in html
    _assert_no_external_fetches(html)


def test_title_appears_in_sheet_title():
    ws = render_worksheet_html(TITLE, ALL)
    assert f'<h1 class="sheet-title">{TITLE}</h1>' in ws
    ak = render_answer_key_html(TITLE, ALL)
    assert f'<h1 class="sheet-title">{TITLE} — Answer Key</h1>' in ak


def test_title_is_html_escaped():
    html = render_worksheet_html("A & B <sheet>", [EASY])
    assert "A &amp; B &lt;sheet&gt;" in html


# --- questions / parts / marks ---------------------------------------------


@pytest.mark.parametrize("render", [render_worksheet_html, render_answer_key_html])
def test_one_question_block_per_input(render):
    html = render(TITLE, ALL)
    assert html.count('<li class="question">') == len(ALL)
    assert '<ol class="questions">' in html


@pytest.mark.parametrize("render", [render_worksheet_html, render_answer_key_html])
def test_marks_present_and_bracketed(render):
    html = render(TITLE, ALL)
    for obj in ALL:
        marks = obj["question"]["parts"][0]["marks"]
        assert f'<span class="marks">[{marks}]</span>' in html


def test_total_marks_is_sum_on_both_sheets():
    total = sum(o["question"]["total_marks"] for o in ALL)
    assert f"Total: {total} marks" in render_worksheet_html(TITLE, ALL)
    assert f"Total: {total} marks" in render_answer_key_html(TITLE, ALL)


def test_math_is_katex_delimited():
    # Ratio + currency atoms in the question text are wrapped for KaTeX.
    html = render_worksheet_html(TITLE, ALL)
    assert r"\(" in html
    assert r"\(\$" in html  # currency written with an escaped dollar


# --- diagrams ---------------------------------------------------------------


def test_diagram_svg_embedded_when_present():
    from exam_engine import diagram

    html = render_worksheet_html(TITLE, [EASY])
    assert '<figure class="diagram">' in html
    # The SVG is reused verbatim from diagram.render_svg (not re-rendered).
    svg = diagram.render_svg(EASY["question"]["parts"][0]["diagram"])
    assert svg in html


def test_diagram_omitted_when_absent():
    obj = generate("ratio_easy", 0)
    obj["question"]["parts"][0]["diagram"] = None
    html = render_worksheet_html(TITLE, [obj])
    assert '<figure class="diagram">' not in html


# --- worksheet vs answer-key surface ----------------------------------------


def test_worksheet_has_answer_space_and_no_solutions():
    html = render_worksheet_html(TITLE, ALL)
    assert '<div class="answer-space"' in html
    assert 'aria-hidden="true"' in html
    # No answer-key markup (class names also live in the CSS, so match elements).
    assert '<ul class="marking-scheme">' not in html
    assert '<p class="final-answer">' not in html
    assert '<ol class="solution-steps">' not in html


def test_answer_key_has_solutions_and_no_answer_space():
    html = render_answer_key_html(TITLE, ALL)
    assert '<ol class="solution-steps">' in html
    assert '<li class="step">' in html
    assert '<p class="final-answer">' in html
    assert '<ul class="marking-scheme">' in html
    assert '<div class="answer-space"' not in html


def test_answer_key_shows_typed_final_answer():
    html = render_answer_key_html(TITLE, [EASY])
    answer = EASY["question"]["parts"][0]["answer"]
    # quantity in dollars → escaped-dollar KaTeX atom.
    assert rf"Answer: \(\${answer['value']}\)" in html


def test_answer_key_renders_decimal_money_at_2dp():
    # A change-to-decimals object carries a decimal $ answer; the answer key must
    # print it at exactly 2 dp (KAN-309), not the value's bare 1-dp form.
    from exam_engine import edits

    obj = edits.apply("change-to-decimals", generate("ratio_medium", 11))
    ans = obj["question"]["parts"][0]["answer"]
    assert ans["type"] == "decimal" and ans["unit"] == "$"

    html = render_answer_key_html(TITLE, [obj])
    assert rf"Answer: \(\${ans['value']:.2f}\)" in html
    # No 1-dp money slips through the rendered questions body (the KaTeX JS/CSS in
    # the document shell is excluded — it is not question content).
    body = html[html.index('<ol class="questions">') : html.index("</main>")]
    assert not re.search(r"\$\d+\.\d(?!\d)", body)


def test_answer_key_has_all_mark_types():
    # HARD has M and A rows; assert the styled type spans are emitted.
    html = render_answer_key_html(TITLE, ALL)
    assert re.search(r'<span class="mark-type mark-M">M\d+</span>', html)
    assert re.search(r'<span class="mark-type mark-A">A\d+</span>', html)


def test_mark_descriptions_rendered():
    html = render_answer_key_html(TITLE, [EASY])
    for mark in EASY["question"]["parts"][0]["marking_scheme"]:
        assert f'<span class="mark-desc">{mark["description"]}</span>' in html


# --- determinism ------------------------------------------------------------


def test_worksheet_is_deterministic():
    a = render_worksheet_html(TITLE, ALL)
    b = render_worksheet_html(TITLE, ALL)
    assert a == b


def test_answer_key_is_deterministic():
    a = render_answer_key_html(TITLE, ALL)
    b = render_answer_key_html(TITLE, ALL)
    assert a == b


def test_question_order_follows_input():
    # First question's text must appear before the second's in the output.
    html = render_worksheet_html(TITLE, [HARD, EASY])
    assert html.index(HARD["question"]["parts"][0]["text"][:20]) < html.index(
        EASY["question"]["parts"][0]["text"][:20]
    )
