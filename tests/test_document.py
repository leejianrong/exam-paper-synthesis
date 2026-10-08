"""W1b — the document model: schema, limits, snapshot verification, rendering (ADR-0021)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from documents import freeform_block, gen_block, heading, make_doc, para, question_block, text
from exam_engine import edits, generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.document import (
    MAX_QUESTION_BLOCKS,
    empty_document,
    question_blocks,
    questions_in_order,
    total_marks,
    validate_document,
    verify_snapshot,
)
from exam_engine.render import _fmt_answer, render_document_html

BLUEPRINT_DIR = Path(__file__).parent.parent / "engine" / "exam_engine" / "content" / "blueprints"
CODES = sorted(p.stem for p in BLUEPRINT_DIR.glob("*.yaml"))
SOURCED = Path(__file__).parent / "fixtures" / "sourced"

# --- schema ------------------------------------------------------------------


def test_empty_and_typical_documents_are_valid():
    assert validate_document(empty_document()) == []
    doc = make_doc(
        heading("Section A", 1),
        para("Answer all questions.", "bold", "italic"),
        {"type": "bulletList", "content": [{"type": "listItem", "content": [para("one")]}]},
        {
            "type": "orderedList",
            "attrs": {"start": 3},
            "content": [{"type": "listItem", "content": [para("x")]}],
        },
        {"type": "paragraph", "content": [text("a"), {"type": "hardBreak"}, text("b")]},
        {"type": "pageBreak"},
        gen_block(),
    )
    assert validate_document(doc) == []


@pytest.mark.parametrize(
    "node",
    [
        {"type": "image", "attrs": {"src": "x.png"}},
        {"type": "table", "content": []},
        {"type": "heading", "attrs": {"level": 4}, "content": [text("h")]},
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "x", "marks": [{"type": "link"}]}],
        },
        {"type": "paragraph", "attrs": {"class": "evil"}},
        {"type": "paragraph", "content": [{"type": "text", "text": ""}]},
    ],
)
def test_unknown_or_malformed_nodes_are_rejected(node):
    assert validate_document(make_doc(node)) != []


def test_non_object_and_missing_fields_rejected():
    assert validate_document("nope") != []
    assert validate_document({"title": "x"}) != []
    bad = make_doc()
    bad["extra"] = 1
    assert validate_document(bad) != []


def test_duplicate_block_ids_rejected():
    obj = generate("ratio_medium", 1)
    doc = make_doc(question_block(obj, "same_id"), question_block(obj, "same_id"))
    errors = validate_document(doc)
    assert any("duplicate block id" in e for e in errors)
    assert any(e.startswith("content/content/1/attrs/block_id") for e in errors)


def test_bad_block_id_rejected():
    block = gen_block()
    block["attrs"]["block_id"] = "has space"
    assert validate_document(make_doc(block)) != []


def test_invalid_embedded_question_is_path_pointed():
    block = gen_block()
    del block["attrs"]["question"]["question"]["total_marks"]
    errors = validate_document(make_doc(para("x"), block))
    assert errors and errors[0].startswith("content/content/1/attrs/question/")


def test_question_count_limit():
    obj = generate("ratio_easy", 1)
    blocks = [question_block(obj, f"blk_{i:04d}") for i in range(MAX_QUESTION_BLOCKS + 1)]
    errors = validate_document(make_doc(*blocks))
    assert any("the limit is 200" in e for e in errors)


def test_size_limit():
    big = para("x" * 20000)
    errors = validate_document(make_doc(*[copy.deepcopy(big) for _ in range(100)]))
    assert any("bytes; the limit is" in e for e in errors)


def test_helpers_order_and_marks():
    a, b = generate("ratio_easy", 1), generate("ratio_hard", 1)
    doc = make_doc(para("intro"), question_block(a), heading("B"), question_block(b))
    assert [q["id"] for q in questions_in_order(doc)] == [a["id"], b["id"]]
    assert len(question_blocks(doc)) == 2
    assert total_marks(doc) == a["question"]["total_marks"] + b["question"]["total_marks"]


# --- verify_snapshot ------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_genuine_generated_snapshots_verify(code):
    for seed in range(1, 11):
        obj = generate(code, seed)
        assert verify_snapshot(obj) == [], (code, seed)
        if "change-to-decimals" in edits.available_ops(obj):
            assert verify_snapshot(edits.apply("change-to-decimals", obj)) == [], (code, seed)
        if edits.applicable("set-cosmetic", obj):
            from exam_engine import cosmetic

            slot = cosmetic.editable_slots(code)[0]
            if slot["role"] == "name":
                names = ["Zara", "Yusof", "Xin Yi"][: slot["count"]]
                changes = {slot["key"]: names if slot["count"] > 1 else names[0]}
                assert verify_snapshot(edits.apply("set-cosmetic", obj, changes=changes)) == []


def test_tampered_answer_is_rejected():
    obj = generate("ratio_medium", 3)
    obj["question"]["parts"][0]["answer"]["value"] += 1
    assert any("does not match" in e for e in verify_snapshot(obj))
    assert any("does not match" in e for e in validate_document(make_doc(question_block(obj))))


def test_tampered_parameters_are_rejected():
    obj = generate("ratio_medium", 3)
    obj["parameters"]["ratio"] = [1, 1, 1]  # answer no longer follows from these
    assert verify_snapshot(obj) != []


def test_unsolvable_or_out_of_schema_parameters_are_rejected():
    obj = generate("ratio_medium", 3)
    obj["parameters"]["total"] = 10**9
    assert verify_snapshot(obj) != []
    obj = generate("ratio_medium", 3)
    del obj["parameters"]["ratio"]
    assert verify_snapshot(obj) != []


def test_fake_generated_claims_are_rejected():
    obj = generate("ratio_medium", 3)
    obj["blueprint_code"] = "no_such_blueprint"
    assert any("unknown blueprint" in e for e in verify_snapshot(obj))
    obj = generate("ratio_medium", 3)
    obj["parameters"] = None
    assert verify_snapshot(obj) != []


def test_tampered_marks_are_rejected():
    obj = generate("ratio_medium", 3)
    obj["question"]["parts"][0]["marks"] += 1
    assert any("marks" in e for e in verify_snapshot(obj))


def test_sourced_objects_are_teacher_vouched_not_verified():
    sourced = json.loads((SOURCED / "psle_2023_ratio.json").read_text(encoding="utf-8"))
    assert verify_snapshot(sourced) == []
    assert validate_document(make_doc(question_block(sourced))) == []


def test_every_blueprint_has_a_solver_for_verification():
    assert all(get_solver(c) for c in CODES)


# --- rendering --------------------------------------------------------------------


def _paper():
    qs = [generate("ratio_easy", 4), generate("percentage_easy", 2), generate("speed_easy", 5)]
    doc = make_doc(
        heading("Section A"),
        para("Answer all questions.", "bold"),
        question_block(qs[0]),
        para("Now try these."),
        question_block(qs[1]),
        {"type": "pageBreak"},
        heading("Section B"),
        question_block(qs[2]),
    )
    return doc, qs


def test_numbering_is_one_counter_across_interleaved_blocks():
    doc, qs = _paper()
    html = render_document_html("P", doc, mode="student")
    body = html.split('<div class="doc-body questions">', 1)[1].split("</main>")[0]
    # The three questions are siblings of the headings/paragraphs inside ONE counter scope.
    assert body.count('<section class="question">') == 3
    assert body.count('<ol class="questions">') == 0
    order = [
        m.start() for m in re.finditer(r"Section A|<section class=\"question\">|Section B", body)
    ]
    assert order == sorted(order)
    assert (
        body.index("Section A") < body.index('<section class="question">') < body.index("Section B")
    )


def test_student_mode_leaks_no_answers():
    doc, qs = _paper()
    html = render_document_html("P", doc, mode="student")
    assert "Answer:" not in html
    assert 'class="solution"' not in html
    assert 'class="marking-scheme"' not in html and 'class="solution-steps"' not in html
    for q in qs:
        for step in q["question"]["parts"][0]["solution_steps"]:
            assert step["text"] not in html
    assert html.count('class="answer-space"') == 3
    assert "Name: ______________" in html and "Total:" in html


def test_key_mode_lists_every_question_with_solutions_in_order():
    doc, qs = _paper()
    html = render_document_html("P", doc, mode="key")
    assert html.count('class="final-answer"') == 3
    assert html.count('class="marking-scheme"') == 3
    assert "Answer Key" in html
    chunks = html.split('<li class="question">')[1:]
    assert len(chunks) == 3
    for chunk, q in zip(chunks, qs, strict=True):
        assert _fmt_answer(q["question"]["parts"][0]["answer"]) in chunk
    assert 'class="answer-space"' not in html


def test_full_mode_is_paper_then_page_break_then_key():
    doc, qs = _paper()
    html = render_document_html("P", doc, mode="full")
    paper, key = html.split('<section class="key-section">')
    assert "Answer:" not in paper and "Answer:" in key
    assert '<h2 class="key-heading">Answer Key</h2>' in key
    assert key.count('class="final-answer"') == 3
    assert 'class="page-break"' in paper


def test_rich_text_is_serialised_and_escaped():
    doc = make_doc(
        heading("A <b>title</b> & more", 1),
        para("bold ", "bold"),
        {
            "type": "paragraph",
            "content": [text("<script>alert(1)</script>", "italic", "underline")],
        },
        {
            "type": "orderedList",
            "attrs": {"start": 3},
            "content": [{"type": "listItem", "content": [para("third")]}],
        },
        {"type": "bulletList", "content": [{"type": "listItem", "content": [para("dot")]}]},
    )
    html = render_document_html("T & <i>", doc, mode="student")
    body = html.split('<div class="doc-body questions">', 1)[1].split("</main>")[0]
    assert '<h2 class="doc-heading">A &lt;b&gt;title&lt;/b&gt; &amp; more</h2>' in body
    assert "<p><strong>bold </strong></p>" in body
    assert "<u><em>&lt;script&gt;alert(1)&lt;/script&gt;</em></u>" in body
    assert '<ol start="3"><li><p>third</p></li></ol>' in body
    assert "<ul><li><p>dot</p></li></ul>" in body
    assert "<title>T &amp; &lt;i&gt;</title>" in html


def test_document_without_questions_renders_student_and_full():
    doc = make_doc(para("Just text."))
    assert "Just text." in render_document_html("T", doc, mode="student")
    assert "Total: 0 marks" in render_document_html("T", doc, mode="full")


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        render_document_html("T", make_doc(), mode="teacher")


# --- free-form questions (W2a, schema 1.1.0) --------------------------------------


def test_freeform_validates_and_old_documents_still_do():
    doc = make_doc(para("intro"), freeform_block("Q?", marks=3, answer="42"), gen_block())
    assert validate_document(doc) == []
    old = make_doc(gen_block())
    old["schema_version"] = "1.0.0"
    assert validate_document(old) == []
    unmarked = make_doc(freeform_block(marks=None))
    assert validate_document(unmarked) == []
    del unmarked["content"]["content"][0]["attrs"]["marks"]
    assert validate_document(unmarked) == []


def _bad_freeform(**change):
    block = freeform_block()
    block["attrs"].update(change.get("attrs", {}))
    if "content" in change:
        block["content"] = change["content"]
    return make_doc(block)


@pytest.mark.parametrize(
    "doc",
    [
        _bad_freeform(attrs={"marks": -1}),
        _bad_freeform(attrs={"marks": 1.5}),
        _bad_freeform(attrs={"marks": 101}),
        _bad_freeform(attrs={"extra": 1}),
        _bad_freeform(attrs={"block_id": "no"}),
        _bad_freeform(content=[]),
        _bad_freeform(content=[heading("no headings")]),
        _bad_freeform(content=[{"type": "templatedQuestion"}]),
        _bad_freeform(content=[{"type": "freeformQuestion", "attrs": {}, "content": []}]),
        _bad_freeform(attrs={"answer": {"type": "doc", "content": [heading("h")]}}),
        _bad_freeform(attrs={"answer": "text"}),
    ],
)
def test_malformed_freeform_rejected(doc):
    assert validate_document(doc) != []


def test_freeform_body_and_answer_text_limits():
    long_body = {"type": "paragraph", "content": [text("x" * 20000), {"type": "hardBreak"}]}
    ok = _bad_freeform(content=[long_body])
    assert validate_document(ok) == []
    two = _bad_freeform(content=[long_body, para("y")])
    assert any("characters of text" in e for e in validate_document(two))
    ans = freeform_block(answer="a")
    ans["attrs"]["answer"]["content"] = [long_body, para("y")]
    assert any("attrs/answer" in e for e in validate_document(make_doc(ans)))


def test_freeform_shares_block_id_space_and_question_limit():
    errors = validate_document(
        make_doc(freeform_block(block_id="same_id"), gen_block()),
    )
    assert errors == []
    dup = make_doc(freeform_block(block_id="same_id"), freeform_block(block_id="same_id"))
    assert any("duplicate block id" in e for e in validate_document(dup))
    many = make_doc(
        *[freeform_block(block_id=f"ff_{i:04d}") for i in range(MAX_QUESTION_BLOCKS + 1)]
    )
    assert any("the limit is 200" in e for e in validate_document(many))
    mixed = make_doc(
        *[freeform_block(block_id=f"ff_{i:04d}") for i in range(MAX_QUESTION_BLOCKS)], gen_block()
    )
    assert any("the limit is 200" in e for e in validate_document(mixed))


def test_total_marks_includes_freeform():
    a = generate("ratio_easy", 1)
    doc = make_doc(
        question_block(a),
        freeform_block(marks=3),
        freeform_block(marks=None),
        freeform_block(marks=2),
    )
    assert total_marks(doc) == a["question"]["total_marks"] + 5


def _question_numbers(html: str) -> int:
    return len(re.findall(r'<(?:li|section) class="question', html))


def test_freeform_render_modes_and_numbering():
    a = generate("ratio_easy", 1)
    doc = make_doc(
        para("Section A"),
        freeform_block("Ann has <b>5</b> & 7 sweets.", marks=3, answer="Answer: 12 sweets"),
        question_block(a),
        freeform_block("Blank answer one", marks=None),
    )
    student = render_document_html("T", doc, mode="student")
    assert _question_numbers(student) == 3
    assert "Answer: 12 sweets" not in student
    assert "No answer written yet" not in student
    assert "[3]" in student and f"Total: {a['question']['total_marks'] + 3} marks" in student
    assert "Ann has &lt;b&gt;5&lt;/b&gt; &amp; 7 sweets." in student
    assert student.count('class="answer-space"') >= 3

    key = render_document_html("T", doc, mode="key")
    assert _question_numbers(key) == 3
    assert "Answer: 12 sweets" in key
    assert key.count("No answer written yet") == 1
    assert "Blank answer one" in key

    full = render_document_html("T", doc, mode="full")
    assert _question_numbers(full) == 6
    assert "Answer: 12 sweets" in full.split('class="key-section"')[1]
    assert "Answer: 12 sweets" not in full.split('class="key-section"')[0]


def test_freeform_only_document_renders_all_modes():
    doc = make_doc(freeform_block("Only one", marks=1, answer="yes"))
    for mode in ("student", "key", "full"):
        assert "Only one" in render_document_html("T", doc, mode=mode)
