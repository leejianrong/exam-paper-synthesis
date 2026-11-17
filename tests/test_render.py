"""V5 — pure HTML renderers (KAN-146).

Structure/content assertions against real generated objects. No browser; the
renderers are pure functions, so these are fast and deterministic.
"""

from __future__ import annotations

import copy
import re

import pytest
from exam_engine import generate
from exam_engine.render import _fmt_answer, render_answer_key_html, render_worksheet_html

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


def test_ratios_and_money_are_plain_text_not_katex():
    # One typeface (EXA-94): only real maths (fractions, authored \\(…\\)) goes through KaTeX.
    html = render_worksheet_html(TITLE, ALL)
    body = html.split("<body>")[1].split("<script>")[0]
    assert r"\(" not in body
    assert "$" in body and " : " in body


def test_authored_math_and_fraction_answers_still_use_katex():
    obj = generate("ratio_easy", 1)
    obj["question"]["parts"][0]["text"] = r"Find \(\frac{1}{2}\) of 8."
    assert r"\(\frac{1}{2}\)" in render_worksheet_html(TITLE, [obj])
    assert _fmt_answer({"type": "fraction", "numerator": 3, "denominator": 4}) == r"\(\frac{3}{4}\)"


# --- diagrams ---------------------------------------------------------------


def test_a_worked_bar_model_prints_in_the_key_never_on_the_worksheet():
    """EXA-132: a bar model is the worked solution ("1 unit = $36", even the answer), so the
    student's worksheet never shows it; the answer key does, verbatim from render_svg."""
    from exam_engine import diagram

    spec = EASY["question"]["parts"][0]["diagram"]
    assert diagram.is_worked_model(spec)
    svg = diagram.render_svg(spec)
    assert svg not in render_worksheet_html(TITLE, [EASY])
    assert svg in render_answer_key_html(TITLE, [EASY])


def test_question_figures_still_print_on_the_worksheet():
    from exam_engine import diagram

    obj = generate("geometry_angle_easy", 3)
    spec = obj["question"]["parts"][0].get("diagram") or obj["question"].get("diagram")
    assert spec and not diagram.is_worked_model(spec)
    assert diagram.render_svg(spec) in render_worksheet_html(TITLE, [obj])


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
    assert f"Answer: ${answer['value']}" in html


def test_answer_key_renders_decimal_money_at_2dp():
    # A change-to-decimals object carries a decimal $ answer; the answer key must
    # print it at exactly 2 dp (KAN-309), not the value's bare 1-dp form.
    from exam_engine import edits

    obj = edits.apply("change-to-decimals", generate("ratio_medium", 11))
    ans = obj["question"]["parts"][0]["answer"]
    assert ans["type"] == "decimal" and ans["unit"] == "$"

    html = render_answer_key_html(TITLE, [obj])
    assert f"Answer: ${ans['value']:.2f}" in html
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


# --- E2 (KAN-663): MCQ options, stem-level diagram, optional marks -----------


def _mcq_object() -> dict:
    obj = copy.deepcopy(EASY)
    obj["question"]["parts"][0]["answer"] = {
        "type": "choice",
        "options": [
            {"label": "1", "text": "Twelve"},
            {"label": "2", "text": "Twenty"},
        ],
        "correct": "2",
    }
    return obj


def test_worksheet_never_reveals_mcq_correct_option():
    html = render_worksheet_html(TITLE, [_mcq_object()])
    assert "option option-correct" not in html  # (the class name itself is in the inlined CSS)
    assert "Answer:" not in html
    assert '<span class="option-label">(1)</span>' in html
    assert '<span class="option-label">(2)</span>' in html


def test_answer_key_marks_correct_option():
    html = render_answer_key_html(TITLE, [_mcq_object()])
    match = re.search(r'<li class="([^"]*)"><span class="option-label">\(2\)</span>', html)
    assert match is not None
    assert "option-correct" in match.group(1)
    match_wrong = re.search(r'<li class="([^"]*)"><span class="option-label">\(1\)</span>', html)
    assert match_wrong is not None
    assert "option-correct" not in match_wrong.group(1)
    assert "Answer: (2) Twenty" in html


def test_text_options_print_in_one_column_and_picture_options_in_a_grid(monkeypatch):
    """EXA-141: every real Booklet A lists text options (1)-(4) down one column, even short
    numbers; only picture options sit in a 2 x 2 grid."""
    from exam_engine import render

    css = render._PRINT_CSS
    rule = re.search(r"\.options \{[^}]*\}", css)
    assert rule is not None and "grid-template-columns: minmax(0, 1fr);" in rule.group(0)
    assert re.search(r"\.options-grid \{[^}]*repeat\(2,", css)

    for texts in (["Twelve", "Twenty", "Thirty", "Forty"], ["1", "2", "3", "4"]):
        obj = _mcq_object()
        obj["question"]["parts"][0]["answer"]["options"] = [
            {"label": str(i), "text": t} for i, t in enumerate(texts, 1)
        ]
        for html in (
            render_worksheet_html(TITLE, [obj]),
            render_answer_key_html(TITLE, [obj]),
        ):
            assert '<ol class="options">' in html
            assert '<ol class="options options-grid">' not in html

    monkeypatch.setattr(render.diagram, "render_svg", lambda spec: "<svg></svg>")
    pictures = {
        "type": "choice",
        "correct": "1",
        "options": [{"label": str(i), "diagram": {"type": "bar_model"}} for i in range(1, 5)],
    }
    html = "".join(render._render_options(pictures, reveal_correct=False))
    assert html.startswith('<ol class="options options-grid">')


def test_stem_diagram_renders_once_before_parts():
    obj = copy.deepcopy(EASY)
    obj["question"]["parts"][0]["diagram"] = None  # isolate the stem-level figure
    part_b = copy.deepcopy(obj["question"]["parts"][0])
    part_b["label"] = "b"
    obj["question"]["parts"].append(part_b)
    obj["question"]["diagram"] = {
        "type": "shaded_fraction",
        "shape": "rectangle",
        "total_parts": 4,
        "shaded_parts": 1,
    }

    html = render_worksheet_html(TITLE, [obj])
    assert html.count('<figure class="diagram">') == 1
    assert html.index('<figure class="diagram">') < html.index('<div class="part">')


def test_part_without_marks_omits_bracket_worksheet_and_key():
    obj = copy.deepcopy(EASY)
    part = obj["question"]["parts"][0]
    del part["marks"]
    del part["marking_scheme"]

    ws = render_worksheet_html(TITLE, [obj])
    ak = render_answer_key_html(TITLE, [obj])
    assert '<span class="marks">' not in ws
    assert '<span class="marks">' not in ak
    assert '<div class="answer-space"' in ws


# --- E3 (KAN-663): table + construction render units ------------------------


def _obj_with_table() -> dict:
    obj = copy.deepcopy(generate("ratio_medium", 42))
    part = obj["question"]["parts"][0]
    part["answer"] = {"type": "integer", "value": 7351, "unit": ""}
    obj["question"]["table"] = {
        "headers": ["Item", "Value"],
        "rows": [["Given", "12"], ["Missing", {"answer_for": part["label"]}]],
    }
    return obj


def test_worksheet_table_blank_cell_hides_answer():
    html = render_worksheet_html("T", [_obj_with_table()])
    table = html.split('<table class="content-table">')[1].split("</table>")[0]
    assert "7351" not in table
    assert 'class="table-blank"' in table


def test_answer_key_table_fills_blank_cell():
    html = render_answer_key_html("T", [_obj_with_table()])
    table = html.split('<table class="content-table">')[1].split("</table>")[0]
    assert "7351" in table
    assert "table-blank" not in table


def test_construction_answer_key_renders_figure_not_text():
    obj = generate("ratio_medium", 42)
    fig = {
        "type": "geometry_figure",
        "unit": "cm",
        "points": [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 2, "y": 0}],
        "segments": [{"from": "A", "to": "B"}],
    }
    obj["question"]["parts"][0]["answer"] = {"type": "construction", "diagram": fig}
    html = render_answer_key_html("C", [obj])
    assert 'class="diagram answer-diagram"' in html
    assert 'class="final-answer"' not in html


# --- W1d: question fragments ---------------------------------------------------


def test_fragment_numbering_and_modes():
    from exam_engine.render import fragment_css, render_question_fragment

    obj = generate("ratio_medium", 3)
    plain = render_question_fragment(obj)
    assert plain.startswith('<div class="frag unnumbered">') and "counter-reset" not in plain
    numbered = render_question_fragment(obj, mode="key", number=7)
    assert 'style="counter-reset: q 6"' in numbered and 'class="final-answer"' in numbered
    assert 'class="final-answer"' not in plain and 'class="answer-space"' in plain
    with pytest.raises(ValueError):
        render_question_fragment(obj, mode="full")
    css = fragment_css()
    assert ":host {" in css and ":root {" not in css and ".frag.unnumbered .question::before" in css
    # An unnumbered fragment must not advance the page's question counter (the editor draws
    # its own numbers; counters cross the shadow boundary).
    assert "counter-increment: none" in css


def test_print_sheet_is_plain_white():
    html = render_worksheet_html("T", [generate("ratio_medium", 1)])
    assert "--paper-2: #ffffff" in html and "linear-gradient" not in html.split("</style>")[1]


def test_a_bank_question_keeps_its_bar_model_on_the_paper():
    """A sourced (bank) question prints its figures as the real paper did: there a bar model
    may be the question itself ("The model shows…"), so only generated ones are key-only."""
    import copy

    from exam_engine import diagram

    obj = copy.deepcopy(EASY)
    obj["source_type"] = "sourced"
    svg = diagram.render_svg(obj["question"]["parts"][0]["diagram"])
    assert svg in render_worksheet_html(TITLE, [obj])
    assert not diagram.hides_worked_model(obj, obj["question"]["parts"][0]["diagram"])


def test_a_worked_model_inside_panels_counts():
    from exam_engine import diagram

    bar = EASY["question"]["parts"][0]["diagram"]
    panels = {"type": "panels", "panels": [{"title": "Before", "figure": bar}]}
    assert diagram.is_worked_model(panels)
    assert not diagram.is_worked_model({"type": "panels", "panels": []})
