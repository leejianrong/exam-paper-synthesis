"""P3 — multi-part free-form questions: (a), (b)… each with marks, space, answer line, answer."""

from __future__ import annotations

import copy
import re

import pytest
from documents import freeform_block, make_doc, multipart_block, part_node
from exam_engine.document import (
    MAX_PARTS,
    freeform_marks,
    total_marks,
    validate_document,
)
from exam_engine.render import default_space_mm, render_document_html


def _doc(**settings):
    doc = make_doc(
        multipart_block(
            part_node(
                "Find the volume.", marks=2, answer="40 x 25 x 12 = 12 000 cm3", ans_unit="cm^3"
            ),
            part_node("How much more to fill it?", marks=1, answer="18 l", ans_unit="l"),
            stem="A tank is 40 cm by 25 cm by 30 cm.",
        ),
        freeform_block("A one-part question.", marks=2),
    )
    if settings:
        doc["settings"] = settings
    return doc


def _html(doc, mode="student"):
    return render_document_html("Paper", doc, mode=mode)


def test_a_multipart_question_is_valid_and_totals_its_parts():
    doc = _doc()
    assert validate_document(doc) == []
    assert freeform_marks(doc["content"]["content"][0]) == 3
    assert total_marks(doc) == 5
    assert "Total: 5 marks" in _html(doc)


def test_student_paper_has_a_lettered_space_and_labelled_answer_line_per_part():
    html = _html(_doc())
    assert re.findall(r'<span class="part-label">\((\w)\)</span>', html) == ["a", "b"]
    assert re.findall(r'<span class="ans-part">\((\w)\)</span>', html) == ["a", "b"]
    heights = [int(h) for h in re.findall(r'class="answer-space"[^>]*height:(\d+)mm', html)]
    assert heights == [default_space_mm(2), default_space_mm(1), default_space_mm(2)]
    assert html.count("<sup>3</sup>") >= 1  # part (a)'s cm^3 unit on its line


def test_marks_follow_the_paper_setting_per_part():
    default = _html(_doc())
    assert default.count('<span class="marks">[2]</span>') == 2  # (a) and the one-part question
    assert default.count('<span class="marks">[1]</span>') == 1  # (b), on its answer line
    q = _html(_doc(marks_placement="question"))
    lines = re.findall(r'<div class="answer-line">.*?</div>', q)
    assert len(lines) == 3 and not any("marks" in x for x in lines)
    both = _html(_doc(marks_placement="both"))
    assert both.count('<span class="marks">[1]</span>') == 2  # beside (b) and on its line


def test_key_shows_each_parts_answer_and_marks_and_no_answer_lines():
    key = _html(_doc(), "key")
    assert "40 x 25 x 12 = 12 000 cm3" in key and "18 l" in key
    assert '<div class="answer-line"' not in key and '<div class="answer-space"' not in key
    assert key.count('<span class="marks">[2]</span>') >= 1


def test_a_part_without_an_answer_prints_the_placeholder_in_the_key():
    doc = make_doc(multipart_block(part_node("p", marks=1), part_node("q", marks=1, answer="4")))
    key = _html(doc, "key")
    assert key.count("No answer written yet") == 1


@pytest.mark.parametrize(
    "mutate,fragment",
    [
        (lambda b: b["content"].insert(0, b["content"].pop()), "needs a body"),
        (lambda b: b["content"].insert(2, {"type": "paragraph"}), "after the body"),
        (lambda b: b["attrs"].update(marks=3), "belong on the parts"),
        (lambda b: b["content"].extend(part_node() for _ in range(MAX_PARTS)), "parts; the limit"),
    ],
)
def test_structure_rules(mutate, fragment):
    block = multipart_block(part_node(), part_node())
    mutate(block)
    errors = validate_document(make_doc(block))
    assert any(fragment in e for e in errors), errors


def test_a_part_cannot_hold_a_part_or_unknown_attrs():
    block = multipart_block(part_node())
    block["content"][1]["content"].append(part_node())
    assert validate_document(make_doc(block))
    block = multipart_block(part_node())
    block["content"][1]["attrs"]["extra"] = 1
    assert validate_document(make_doc(block))
    block = multipart_block(part_node())
    block["content"][1]["attrs"]["marks"] = 101
    assert validate_document(make_doc(block))


def test_single_part_questions_and_old_documents_are_unchanged():
    doc = make_doc(freeform_block("q", marks=2))
    html = _html(doc)
    assert (
        "multipart" not in html.split("</style>")[-1]
        and "part-label" not in html.split("</style>")[-1]
    )
    legacy = copy.deepcopy(doc)
    legacy["schema_version"] = "1.4.0"
    assert validate_document(legacy) == []


def test_part_answers_count_toward_the_text_limit():
    block = multipart_block(part_node("p", marks=1))
    paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": "x" * 10_000}]}] * 3
    block["content"][1]["attrs"]["answer"] = {"type": "doc", "content": paragraphs}
    assert any("characters of text" in e for e in validate_document(make_doc(block)))
