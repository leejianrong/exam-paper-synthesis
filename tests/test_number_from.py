"""EXA-134 — ``settings.number_from``: Paper 1 Booklet B carries on from Booklet A (Q16 on)."""

from __future__ import annotations

import re

from documents import freeform_block, gen_block, make_doc
from exam_engine.document import number_from, paper_outline, validate_document, with_key_style
from exam_engine.paper import generate_paper, template_document
from exam_engine.paper_swap import regenerate_unlocked, swap_question
from exam_engine.render import render_document_html


def section(title: str) -> dict:
    return {
        "type": "section",
        "attrs": {"title": title, "instructions": None, "mode": "short", "marks_target": None},
    }


def _doc(start: int | None = 16) -> dict:
    doc = make_doc(
        section("Booklet B"),
        freeform_block("Q one", marks=2),
        gen_block("ratio_medium", 1),
        freeform_block("Q three", marks=1),
    )
    if start is not None:
        doc["settings"] = {"number_from": start}
    return doc


def _key_numbers(html: str) -> list[int]:
    return [int(n) + 1 for n in re.findall(r'<li style="counter-reset: q (\d+)"', html)]


def test_the_setting_is_valid_and_old_documents_number_from_one():
    assert validate_document(_doc()) == []
    assert number_from(_doc()) == 16
    assert number_from(_doc(None)) == 1
    assert number_from({**_doc(None), "settings": {"number_from": None}}) == 1


def test_number_from_must_be_a_positive_integer():
    for bad in (0, -3, 1.5, "16"):
        doc = _doc()
        doc["settings"]["number_from"] = bad
        assert validate_document(doc), bad


def test_outline_ranges_start_at_number_from():
    (sec,) = paper_outline(_doc())
    assert (sec["first"], sec["last"], sec["count"]) == (16, 18, 3)
    (sec,) = paper_outline(_doc(None))
    assert (sec["first"], sec["last"]) == (1, 3)


def test_student_paper_starts_the_counter_and_prints_the_range():
    html = render_document_html("B", _doc(), mode="student")
    assert '<div class="doc-body questions" style="counter-reset: q 15">' in html
    assert "Question <b>16</b> carries 2 marks." in html  # the header sentence (EXA-139)
    # an old document is untouched
    plain = render_document_html("B", _doc(None), mode="student")
    assert '<div class="doc-body questions">' in plain
    assert "Question <b>1</b> carries 2 marks." in plain


def test_answer_key_keeps_the_papers_numbers():
    for mode in ("key", "full"):
        assert _key_numbers(render_document_html("B", _doc(), mode=mode)) == [16, 17, 18]
    doc = _doc()
    doc["content"]["content"][2]["attrs"]["in_key"] = False
    assert _key_numbers(render_document_html("B", doc, mode="key")) == [16, 18]
    # numbering from 1 with nothing left out still lets the key count up by itself
    assert _key_numbers(render_document_html("B", _doc(None), mode="key")) == []


def test_booklet_b_template_and_generated_paper_start_at_16():
    assert template_document("p1_booklet_b")["settings"]["number_from"] == 16
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    assert doc["settings"]["number_from"] == 16
    assert paper_outline(doc)[0]["first"] == 16
    html = render_document_html("B", doc, mode="key")
    assert '<th scope="row">Q16</th>' in html  # the school key labels rows with the paper's numbers
    worked = render_document_html("B", with_key_style(doc, "worked"), mode="key")
    assert _key_numbers(worked)[0] == 16
    for code in ("p1_booklet_a", "p2"):
        assert "number_from" not in template_document(code)["settings"]
        assert "number_from" not in generate_paper(code, "P6", 3)[0]["settings"]


def test_swap_and_regenerate_keep_the_setting():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    block = next(n for n in doc["content"]["content"] if n["type"] == "templatedQuestion")
    swapped, _ = swap_question(doc, block["attrs"]["block_id"], "like", 7)
    regenerated, _ = regenerate_unlocked(doc, "P6", 9)
    assert swapped["settings"]["number_from"] == regenerated["settings"]["number_from"] == 16
