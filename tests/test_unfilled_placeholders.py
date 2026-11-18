"""EXA-137 — an unwritten generator placeholder: which printed numbers, and how it prints."""

from __future__ import annotations

import re

from documents import freeform_block, gen_block, make_doc
from exam_engine.document import unfilled_placeholder_numbers, validate_document
from exam_engine.paper import generate_paper, unfilled_placeholders
from exam_engine.render import render_document_html


def section(mode: str, marks_target: int | None = None) -> dict:
    return {
        "type": "section",
        "attrs": {"title": mode, "instructions": None, "mode": mode, "marks_target": marks_target},
    }


def empty_teacher_block(marks: int = 2) -> dict:
    node = freeform_block(marks=marks)
    node["content"] = [{"type": "paragraph"}]
    return node


def placeholder(marks: int, kind: str, text: str = "") -> dict:
    node = freeform_block(text, marks=marks) if text else empty_teacher_block(marks)
    node["attrs"]["slot"] = {"marks": marks, "kind": kind, "placeholder": True}
    return node


def _doc() -> dict:
    return make_doc(
        section("mcq"),
        gen_block("ratio_medium", 1),  # 1
        placeholder(1, "mcq"),  # 2: empty, in an MCQ section
        placeholder(1, "mcq", "Written by the teacher."),  # 3: written
        section("short"),
        empty_teacher_block(),  # 4: an empty teacher block is not a placeholder
        placeholder(2, "short"),  # 5: empty, in a short-answer section
    )


def test_numbers_are_the_printed_question_numbers_of_unwritten_placeholders():
    doc = _doc()
    assert validate_document(doc) == []
    assert unfilled_placeholder_numbers(doc) == [2, 5]
    assert unfilled_placeholders(doc) == 2


def test_the_generator_report_and_the_numbers_agree():
    doc, report = generate_paper("p2", "P5", 1)  # too few 3-5 mark blueprints at P5
    assert unfilled_placeholder_numbers(doc) == [21, 22]
    assert report["placeholders"] == 2


def _questions(html: str) -> list[str]:
    body = html.split('<div class="doc-body questions">', 1)[1]
    return re.findall(r'<section [^>]*class="question[^"]*"[^>]*>.*?</section>', body, flags=re.S)


def test_an_empty_mcq_placeholder_prints_a_numbered_gap_without_an_ans_line():
    html = render_document_html("P", _doc(), mode="student")
    qs = _questions(html)
    assert len(qs) == 5
    gap = qs[1]
    assert 'class="question freeform unwritten"' in gap
    # its marks are in the MCQ header, as for every MCQ question (EXA-139)
    assert "[1]" not in gap and "answer-space" in gap
    assert "answer-line" not in gap and "Ans:" not in gap
    # a written placeholder, and an empty one outside an MCQ section, print as before
    assert "unwritten" not in qs[2] and "unwritten" not in qs[4]
    assert "answer-line" in qs[4]


def test_the_key_still_says_no_answer_written_yet():
    html = render_document_html("P", _doc(), mode="key")
    assert "unwritten" not in html
    assert html.count("No answer written yet") >= 2


def test_numbers_count_from_the_papers_first_question_number():
    """Booklet B numbers on from 16 (EXA-134): the refusal names the printed numbers."""
    doc = _doc()
    doc["settings"] = {**(doc.get("settings") or {}), "number_from": 16}
    assert validate_document(doc) == []
    assert unfilled_placeholder_numbers(doc) == [17, 20]
