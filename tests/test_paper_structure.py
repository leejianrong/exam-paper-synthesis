"""P4 — paper structure: section blocks, derived question ranges and marks, paper time."""

from __future__ import annotations

import re

from documents import freeform_block, gen_block, make_doc, para
from exam_engine.document import MAX_SECTIONS, paper_outline, total_marks, validate_document
from exam_engine.render import render_document_html


def section(title="Section A", *, instructions=None, mode=None, marks_target=None) -> dict:
    return {
        "type": "section",
        "attrs": {
            "title": title,
            "instructions": instructions,
            "mode": mode,
            "marks_target": marks_target,
        },
    }


def _doc(**settings):
    doc = make_doc(
        freeform_block("Before any section.", marks=1),
        section("Booklet A", instructions="Shade your answer.", mode="mcq", marks_target=5),
        freeform_block("Q2", marks=2),
        freeform_block("Q3", marks=3),
        para("a note"),
        section("Booklet B", marks_target=10),
        gen_block("ratio_medium", 1),
        section("Empty section"),
    )
    if settings:
        doc["settings"] = settings
    return doc


def _html(doc, mode="student"):
    return render_document_html("Paper", doc, mode=mode)


def test_sections_are_valid_and_do_not_change_the_paper_total():
    doc = _doc()
    assert validate_document(doc) == []
    assert (
        total_marks(doc)
        == 1 + 2 + 3 + doc["content"]["content"][6]["attrs"]["question"]["question"]["total_marks"]
    )


def test_outline_derives_ranges_and_marks_and_continues_numbers():
    a, b, empty = paper_outline(_doc())
    assert (a["first"], a["last"], a["count"], a["marks"]) == (2, 3, 2, 5)
    assert (a["mode"], a["marks_target"]) == ("mcq", 5)
    assert (b["first"], b["last"], b["count"]) == (4, 4, 1)  # numbering continues
    assert empty["first"] is None and empty["count"] == 0 and empty["marks"] == 0


def test_student_paper_prints_each_section_header_with_range_marks_and_instructions():
    html = _html(_doc())
    titles = re.findall(r'<h2 class="section-title">([^<]*)</h2>', html)
    assert titles == ["Booklet A", "Booklet B", "Empty section"]
    assert "Questions 2–3 · 5 marks · Multiple choice" in html
    assert "Question 4 · " in html  # a single-question section says "Question", not a range
    assert "Shade your answer." in html
    # An empty section prints a title only: no range, no 0 marks.
    assert "Empty section</h2></div>" in html


def test_section_text_is_escaped():
    doc = make_doc(section("<script>alert(1)</script>", instructions="a & b"))
    html = _html(doc)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html and "a &amp; b" in html


def test_answer_key_has_no_section_headers():
    assert '<div class="paper-section">' not in _html(_doc(), "key")


def test_paper_time_prints_in_the_header_only_when_set():
    assert 'class="field-time"' not in _html(_doc())
    assert "Time: 1 h 15 min" in _html(_doc(time_min=75))
    assert "Time: 45 min" in _html(_doc(time_min=45))
    assert "Time: 1 h<" in _html(_doc(time_min=60))


def test_invalid_sections_are_rejected():
    for bad in (
        {"mode": "essay"},
        {"marks_target": -1},
        {"title": "x" * 121},
        {"colour": "red"},
    ):
        doc = make_doc(section())
        doc["content"]["content"][0]["attrs"].update(bad)
        assert validate_document(doc), bad
    doc = make_doc(section())
    doc["settings"] = {"time_min": 0}
    assert validate_document(doc)


def test_section_count_is_limited():
    doc = make_doc(*[section(f"S{i}") for i in range(MAX_SECTIONS + 1)])
    assert any("sections" in e for e in validate_document(doc))
