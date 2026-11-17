"""EXA-142 — the compact answer key: a header block from the cover, an answer grid for each
multiple-choice section and a two-column working table with a right-aligned "Ans:" for the rest,
as real school keys print (REAL-PAPER-COMPARISON.md, "Answer key format")."""

from __future__ import annotations

import copy
import re

from documents import freeform_block, make_doc, multipart_block, part_node
from exam_engine.document import key_options, validate_document
from exam_engine.paper import generate_paper
from exam_engine.render import render_document_html


def compact(doc: dict, **options) -> dict:
    doc = copy.deepcopy(doc)
    doc.setdefault("settings", {})["key_options"] = {"layout": "compact", **options}
    return doc


def body(html: str) -> str:
    return html.split("</style>")[-1]


def grid(html: str) -> dict[int, str]:
    """{question number: what the grid prints under it}, across every grid row."""
    out: dict[int, str] = {}
    for table in re.findall(r'<table class="key-grid"[^>]*>(.*?)</table>', html):
        heads = [int(n) for n in re.findall(r'<th scope="col">Q(\d+)</th>', table)]
        cells = re.findall(r"<td>(.*?)</td>", table)
        out.update(zip(heads, cells, strict=True))
    return out


def rows(html: str) -> list[tuple[str, str]]:
    """The working table's rows as (label, working cell)."""
    return re.findall(r'<tr><th scope="row">([^<]+)</th><td class="key-work">(.*?)</td></tr>', html)


def test_the_layout_is_schema_gated_and_defaults_to_the_full_key():
    doc, _ = generate_paper("p1_booklet_a", "P6", 3)
    assert key_options(doc)["layout"] == "full"
    assert "compact-key" not in body(render_document_html("A", doc, mode="key"))
    assert validate_document(compact(doc)) == []
    bad = compact(doc)
    bad["settings"]["key_options"]["layout"] = "tiny"
    assert validate_document(bad)


def test_booklet_a_prints_a_grid_of_the_correct_option_numbers():
    doc, _ = generate_paper("p1_booklet_a", "P6", 3)
    html = body(render_document_html("A", compact(doc), mode="key"))
    printed = grid(html)
    questions = [n for n in doc["content"]["content"] if n["type"] == "templatedQuestion"]
    assert len(questions) == 15 and sorted(printed) == list(range(1, 16))
    for number, node in enumerate(questions, 1):
        answer = node["attrs"]["question"]["question"]["parts"][0]["answer"]
        assert answer["type"] == "choice"
        assert printed[number] == answer["correct"]
    # ten to a row, as real keys print Q1–Q10 then Q11–Q15; no question text, no working
    assert html.count('<table class="key-grid"') == 2
    assert "key-table" not in html and "solution-steps" not in html
    stem = questions[0]["attrs"]["question"]["question"]["parts"][0]["text"]
    assert stem not in html


def test_booklet_b_table_keeps_the_papers_numbers_and_right_aligns_ans():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    html = body(render_document_html("B", compact(doc), mode="key"))
    labels = [label for label, _ in rows(html)]
    assert labels[0] == "Q16" and labels[-1] == "Q30"
    for _, work in rows(html):
        assert '<p class="key-step">' in work
        assert '<p class="key-ans"><span class="ans-label">Ans:</span>' in work
    assert "Answer:" not in html


def test_the_scheme_prints_only_when_asked():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    with_scheme = body(render_document_html("B", compact(doc), mode="key"))
    without = body(render_document_html("B", compact(doc, show_scheme=False), mode="key"))
    assert 'class="key-scheme"' in with_scheme and 'class="key-mark">A1<' in with_scheme
    assert 'class="key-scheme"' not in without and 'class="key-ans"' in without


def test_multi_part_and_teacher_written_questions_get_a_row_per_part():
    doc = make_doc(
        freeform_block("SINGLE stem", marks=2, answer="42 cm"),
        multipart_block(
            part_node("PART-A text", marks=2, answer="ANSWER-A"),
            part_node("PART-B text", marks=1),
            stem="MULTI stem",
        ),
        freeform_block("LEFT-OUT stem", marks=1, answer="ANSWER-LEFT"),
    )
    doc["content"]["content"][2]["attrs"]["in_key"] = False
    html = body(render_document_html("P", compact(doc), mode="key"))
    got = rows(html)
    assert [label for label, _ in got] == ["Q1", "Q2(a)", "Q2(b)"]
    assert '<span class="ans-label">Ans:</span> 42 cm' in got[0][1]
    assert "ANSWER-A" in got[1][1] and "No answer written yet" in got[2][1]
    for hidden in ("SINGLE stem", "MULTI stem", "PART-A text", "ANSWER-LEFT"):
        assert hidden not in html


def test_the_header_block_comes_from_the_cover_and_full_mode_uses_the_layout():
    doc, _ = generate_paper("p2", "P6", 3)
    cover = doc["content"]["content"][0]
    assert cover["type"] == "coverPage"
    cover["attrs"].update(school="SCHOOL-NAME", level="Primary 6", exam="EXAM-NAME")
    key = body(render_document_html("P2", compact(doc), mode="key"))
    meta = re.search(r'<dl class="key-meta">(.*?)</dl>', key)
    assert meta
    for value in ("<dt>School</dt><dd>SCHOOL-NAME</dd>", "<dt>Exam</dt><dd>EXAM-NAME</dd>"):
        assert value in meta.group(1)
    full = body(render_document_html("P2", compact(doc), mode="full"))
    paper, key_part = full.split('<section class="key-section">')
    assert "compact-key" in key_part and "compact-key" not in paper
    assert rows(key_part) == rows(key)
