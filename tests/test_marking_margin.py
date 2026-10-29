"""P6a — marking margin per section, per-question marks for the paginator, the tally box."""

from __future__ import annotations

import re

from documents import freeform_block, gen_block, make_doc, multipart_block, part_node
from exam_engine.document import paper_outline, section_marking, validate_document
from exam_engine.render import render_document_html, render_tally_box


def section(title, **attrs) -> dict:
    return {"type": "section", "attrs": {"title": title, **attrs}}


def _doc():
    return make_doc(
        section("Booklet A", mode="mcq"),
        freeform_block("MCQ-ISH", marks=1),
        section("Booklet B", mode="short"),
        freeform_block("SHORT-ONE", marks=2),
        gen_block("ratio_medium", 1),
        section("Section B", mode="structured", marking=False),
        multipart_block(part_node("PA", marks=2), part_node("PB", marks=3), stem="STEM"),
        section("Free", marking=True),
        freeform_block("FREE-ONE", marks=4),
    )


def _items(html):
    """(data-marks or None, marked?) for each numbered question in the student paper, in order."""
    body = html.split("</style>")[-1].split("<script>")[0]
    out = []
    for tag in re.findall(r'<section [^>]*class="question[^>]*>', body):
        m = re.search(r'data-marks="(\d+)"', tag)
        out.append((int(m.group(1)) if m else None, "question marked" in tag))
    return out


def test_default_marking_follows_the_section_mode():
    assert section_marking({"mode": "short"}) and section_marking({"mode": "structured"})
    assert not section_marking({"mode": "mcq"}) and not section_marking({})
    assert section_marking({"mode": "mcq", "marking": True})
    assert not section_marking({"mode": "short", "marking": False})
    assert [s["marking"] for s in paper_outline(_doc())] == [False, True, False, True]


def test_only_questions_in_marking_sections_get_the_margin():
    html = render_document_html("P", _doc(), mode="student")
    # MCQ-ish: off; Booklet B (short): on x2; Section B (explicitly off): off; Free (explicit): on
    assert [marked for _, marked in _items(html)] == [False, True, True, False, True]


def test_marked_questions_carry_their_marks_for_the_paginator():
    marks = [m for m, _ in _items(render_document_html("P", _doc(), mode="student"))]
    generated = gen_block("ratio_medium", 1)["attrs"]["question"]["question"]["total_marks"]
    assert marks == [None, 2, generated, None, 4]  # other questions are untouched


def test_the_answer_key_has_no_margin_and_the_paper_stays_numbered():
    doc = _doc()
    key = render_document_html("P", doc, mode="key").split("</style>")[-1].split("<script>")[0]
    assert " marked" not in key and "data-marks" not in key
    full = render_document_html("P", doc, mode="full").split("</style>")[-1].split("<script>")[0]
    paper, _ = full.split('<section class="key-section">')
    assert paper.count(" marked") == 3


def test_tally_box_markup_and_validity():
    box = render_tally_box(7)
    assert 'class="tally"' in box and '<span class="tally-total">7</span>' in box
    assert "out of 7" in box
    doc = _doc()
    assert validate_document(doc) == []
    doc["content"]["content"][0]["attrs"]["marking"] = "yes"
    assert validate_document(doc)
