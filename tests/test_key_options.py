"""P5 — answer-key options: hide question text, omit the M/A breakdown, leave questions out."""

from __future__ import annotations

import re

from documents import freeform_block, gen_block, make_doc, multipart_block, part_node
from exam_engine.document import in_key, key_options, validate_document
from exam_engine.render import render_document_html


def _doc(**settings):
    doc = make_doc(
        freeform_block("FREEFORM-ONE stem", marks=2, answer="ANSWER-ONE"),
        gen_block("ratio_medium", 1),
        multipart_block(
            part_node("PART-A text", marks=2, answer="ANSWER-A"),
            part_node("PART-B text", marks=1, answer="ANSWER-B"),
            stem="MULTI stem",
        ),
    )
    if settings:
        doc["settings"] = settings
    return doc


def _key(doc, mode="key"):
    return render_document_html("Paper", doc, mode=mode)


def _numbers(html):
    return [int(n) + 1 for n in re.findall(r'<li style="counter-reset: q (\d+)"', html)]


def test_defaults_are_the_pre_p5_key():
    assert key_options(_doc()) == {"show_question": True, "show_scheme": True}
    html = _key(_doc())
    assert "FREEFORM-ONE stem" in html and "PART-A text" in html
    assert 'class="marking-scheme"' in html
    assert "key-only" not in html.split("</style>")[-1]


def test_hide_question_leaves_number_marks_steps_and_answer_only():
    doc = _doc(key_options={"show_question": False})
    assert validate_document(doc) == []
    html = _key(doc).split("</style>")[-1]
    for hidden in ("FREEFORM-ONE stem", "PART-A text", "PART-B text", "MULTI stem"):
        assert hidden not in html
    for shown in ("ANSWER-ONE", "ANSWER-A", "ANSWER-B", 'class="solution-steps"'):
        assert shown in html
    assert '<span class="part-label">(a)</span><span class="marks">[2]</span>' in html
    assert _numbers(html) == []  # nothing left out: the key just counts 1, 2, 3


def test_omit_scheme_drops_the_marking_breakdown_only():
    html = _key(_doc(key_options={"show_scheme": False})).split("</style>")[-1]
    assert 'class="marking-scheme"' not in html
    assert 'class="solution-steps"' in html and "FREEFORM-ONE stem" in html


def test_excluded_questions_leave_the_key_but_keep_paper_numbers():
    doc = _doc()
    doc["content"]["content"][0]["attrs"]["in_key"] = False
    assert validate_document(doc) == []
    assert in_key(doc["content"]["content"][0]) is False
    key = _key(doc).split("</style>")[-1]
    assert "ANSWER-ONE" not in key and "ANSWER-A" in key
    assert _numbers(key) == [2, 3]  # not renumbered 1, 2
    # the student paper still has every question
    student = _key(doc, "student")
    assert "FREEFORM-ONE stem" in student


def test_full_mode_applies_the_options_to_its_key_section_only():
    doc = _doc(key_options={"show_question": False})
    html = _key(doc, "full").split("</style>")[-1]
    paper, key = html.split('<section class="key-section">')
    assert "FREEFORM-ONE stem" in paper and "PART-A text" in paper
    assert "FREEFORM-ONE stem" not in key


def test_invalid_options_are_rejected():
    for bad in ({"key_options": {"show_question": "no"}}, {"key_options": {"colour": True}}):
        doc = _doc(**bad)
        assert validate_document(doc), bad
    doc = _doc()
    doc["content"]["content"][0]["attrs"]["in_key"] = "no"
    assert validate_document(doc)
