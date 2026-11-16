"""EXA-139 — section headers, per-section marks placement and the Ans: line, as real papers print.

Real P6 papers print no "Section A" label: a sentence from the question range and marks
("Questions 1 to 10 carry 1 mark each."), the instructions, "(20 marks)" at the right, a rule.
MCQ and short-answer sections print no per-question [n]; structured ones print [n] after the
Ans: line and say so in the header.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from documents import freeform_block, make_doc, multipart_block, part_node
from exam_engine.document import paper_outline, section_placement, validate_document
from exam_engine.paper import generate_paper
from exam_engine.render import render_document_html


def section(title="Section A", *, mode=None, instructions=None, **attrs) -> dict:
    return {
        "type": "section",
        "attrs": {
            "title": title,
            "instructions": instructions,
            "mode": mode,
            "marks_target": None,
            **attrs,
        },
    }


def _student(doc) -> str:
    return render_document_html("Paper", doc, mode="student")


def _headers(html: str) -> list[str]:
    # a marking section's header keeps clear of the strip, a structured one starts a page (EXA-138)
    return re.findall(r'<div [^>]*class="paper-section[^"]*">.*?</div>', html)


def _intro_text(header: str) -> str:
    return re.sub(r"<[^>]+>", "", header)


def _body(html: str) -> str:
    return html.split('<div class="doc-body questions"', 1)[1]


# --- header sentences --------------------------------------------------------------------


def test_booklet_a_header_states_each_run_of_marks_then_the_total():
    doc, _ = generate_paper("p1_booklet_a", "P6", 1)
    (header,) = _headers(_student(doc))
    assert _intro_text(header).startswith(
        "Questions 1 to 10 carry 1 mark each. Questions 11 to 15 carry 2 marks each. For each"
    )
    assert header.endswith('<span class="section-total">(20 marks)</span></p></div>')
    # how to record the answer, as every real Booklet A says it (EXA-141)
    assert _intro_text(header).endswith(
        "Make your choice (1, 2, 3 or 4) and shade your answer on the Optical Answer Sheet."
        "(20 marks)"
    )
    assert "<b>1</b> to <b>10</b>" in header  # the numbers are bold, as printed
    # no "Booklet A" label, no grey meta line
    assert "section-title" not in header and "section-meta" not in header


def test_booklet_b_is_two_sections_numbered_on_from_16():
    doc, _ = generate_paper("p1_booklet_b", "P6", 2)
    one, two = (_intro_text(h) for h in _headers(_student(doc)))
    assert one.startswith("Questions 16 to 20 carry 1 mark each. ") and one.endswith("(5 marks)")
    assert two.startswith("Questions 21 to 30 carry 2 marks each. ") and two.endswith("(20 marks)")


def test_paper_2_structured_section_points_at_the_brackets():
    doc, _ = generate_paper("p2", "P6", 3)
    short, structured = (_intro_text(h) for h in _headers(_student(doc)))
    assert short.startswith("Questions 1 to 5 carry 2 marks each.") and short.endswith("(10 marks)")
    assert structured.startswith(
        "The number of marks available is shown in brackets [ ] at the end of each question or "
        "part question."
    )
    assert structured.endswith("(45 marks)")


def test_sentence_wording_for_one_and_two_questions():
    doc = make_doc(
        section(mode="short"),
        freeform_block(marks=1),
        section("Section B", mode="short"),
        freeform_block(marks=2),
        freeform_block(marks=2),
    )
    one, two = (_intro_text(h) for h in _headers(_student(doc)))
    assert one == "Question 1 carries 1 mark.(1 mark)"
    assert two == "Questions 2 and 3 carry 2 marks each.(4 marks)"


def test_a_section_printing_its_own_uniform_marks_still_states_them():
    doc = make_doc(section(mode=None), freeform_block(marks=2), freeform_block(marks=2))
    (header,) = _headers(_student(doc))
    assert _intro_text(header).startswith("Questions 1 and 2 carry 2 marks each.")


def test_a_teachers_own_title_prints_but_generic_labels_do_not():
    for generic in ("Section A", "booklet b", " Part 2 ", ""):
        assert '<h2 class="section-title"' not in _student(make_doc(section(generic)))
    for own in ("Fractions revision", "Part One"):
        html = _student(make_doc(section(own)))
        assert f'<h2 class="section-title">{own}</h2>' in html


# --- marks placement per section ---------------------------------------------------------


def test_placement_derives_from_the_mode_and_an_authored_choice_wins():
    assert section_placement({"mode": "mcq"}, "answer") == "none"
    assert section_placement({"mode": "short"}, "both") == "none"
    assert section_placement({"mode": "structured"}, "answer") == "answer"
    assert section_placement({"mode": "structured"}, "both") == "both"  # the paper's choice
    assert section_placement({"mode": None}, "question") == "question"
    assert section_placement({"mode": "short", "marks_placement": "both"}, "answer") == "both"
    assert section_placement({"mode": "structured", "marks_placement": "none"}, "x") == "none"


def _paper():
    return make_doc(
        freeform_block("Loose question", marks=3),  # before any section: the paper's setting
        section(mode="short"),
        freeform_block("Short one", marks=2),
        section("Section B", mode="structured"),
        multipart_block(part_node("Part a", marks=1), part_node("Part b", marks=2)),
    )


def test_short_sections_print_no_marks_and_structured_ones_print_them_after_ans():
    doc = _paper()
    assert validate_document(doc) == []
    assert [s["marks_placement"] for s in paper_outline(doc)] == ["none", "answer"]
    qs = re.findall(r'<section [^>]*class="question.*?</section>', _body(_student(doc)), re.S)
    loose, short, structured = qs
    assert "[3]" in loose  # old behaviour outside sections
    assert "[2]" not in short and "Ans:" in short
    lines = re.findall(r'<div class="answer-line">.*?</div>', structured)
    assert [("[1]" in x, "[2]" in x) for x in lines] == [(True, False), (False, True)]
    assert 'class="part-label">(a)</span><div class="part-text"><p>Part a</p></div></div>' in (
        structured
    )


def test_an_authored_section_placement_overrides_the_default():
    doc = _paper()
    doc["content"]["content"][1]["attrs"]["marks_placement"] = "question"
    doc["content"]["content"][3]["attrs"]["marks_placement"] = "none"
    assert validate_document(doc) == []
    _, short, structured = re.findall(
        r'<section [^>]*class="question.*?</section>', _body(_student(doc)), re.S
    )
    assert '<span class="marks">[2]</span></div><div class="answer-space"' in short
    assert "[1]" not in structured and "[2]" not in structured
    # the header no longer points at brackets that are not printed
    assert _intro_text(_headers(_student(doc))[1]).startswith("Question 3 carries 3 marks.")


def test_the_answer_key_always_shows_marks():
    key = render_document_html("Paper", _paper(), mode="key")
    assert "[2]" in key and "[1]" in key


def test_mcq_questions_print_no_marks_on_the_student_paper():
    doc, _ = generate_paper("p1_booklet_a", "P6", 4)
    assert '<span class="marks">' not in _body(_student(doc)).split("</div></div>", 1)[1]


@pytest.mark.parametrize("value", ["none", "question", "answer", "both", None])
def test_schema_accepts_the_section_placements(value):
    doc = make_doc(section(marks_placement=value))
    assert validate_document(doc) == []


def test_schema_rejects_an_unknown_section_placement():
    assert validate_document(make_doc(section(marks_placement="margin")))


# --- the Ans: line -----------------------------------------------------------------------


def test_ans_line_markup_puts_dollar_before_unit_after_and_parts_lettered():
    money = freeform_block("Cost?", marks=2)
    money["attrs"]["ans_unit"] = "$"
    area = freeform_block("Area?", marks=2)
    area["attrs"]["ans_unit"] = "cm^2"
    parts = multipart_block(part_node("a", marks=1), part_node("b", marks=1))
    html = _student(make_doc(money, area, parts))
    lines = re.findall(r'<div class="answer-line">.*?</div>', html)
    assert lines[0] == (
        '<div class="answer-line"><span class="ans-label">Ans:</span>'
        '<span class="ans-pre">$</span><span class="ans-blank"></span>'
        '<span class="marks">[2]</span></div>'
    )
    assert '<span class="ans-blank"></span><span class="ans-unit">cm<sup>2</sup></span>' in lines[1]
    assert '<span class="ans-label">Ans:</span><span class="ans-part">(a)</span>' in lines[2]


def test_ans_line_is_short_and_right_aligned_in_print():
    css = (
        Path(__file__).resolve().parents[1] / "engine" / "exam_engine" / "assets" / "print.css"
    ).read_text()
    rule = re.search(r"\.answer-line \{[^}]*\}", css).group(0)
    assert "justify-content: flex-end" in rule
    assert "flex: 0 1 55mm" in re.search(r"\.answer-line \.ans-blank \{[^}]*\}", css).group(0)
