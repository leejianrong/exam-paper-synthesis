"""The school key (EXA-142, the default for new papers since EXA-159): a header block from the
cover, an answer grid for each multiple-choice section, and ruled tables for the rest: 1-mark
answers two to a row, the other questions one to a row with short working and a right-aligned
"Ans:". No question text, no marks and no M1/A1 unless asked, never an MCQ's distractor reasons.
The key flows on from page to page and a row never splits (REAL-PAPER-COMPARISON.md, "Answer key
format"; docs/planning/editor/UI-REDESIGN.md, section 3)."""

from __future__ import annotations

import copy
import io
import re

import pytest
from documents import freeform_block, make_doc, multipart_block, para, part_node
from exam_engine.blueprints.registry import load_blueprint
from exam_engine.document import (
    empty_document,
    key_options,
    new_key_options,
    validate_document,
    with_key_style,
)
from exam_engine.paper import generate_paper, template_document
from exam_engine.render import render_document_html
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


def compact(doc: dict, **options) -> dict:
    doc = copy.deepcopy(doc)
    doc.setdefault("settings", {})["key_options"] = {"layout": "compact", **options}
    return doc


def school(doc: dict, **options) -> dict:
    """``doc`` with a new paper's school key, plus ``options``."""
    return compact(doc, **{**new_key_options("school"), **options})


def body(html: str) -> str:
    """The printed page: ``<main>`` and what is in it (no styles, no scripts)."""
    return html[html.index("<main ") : html.index("</main>")]


def key(doc: dict, mode: str = "key") -> str:
    return body(render_document_html("Paper", doc, mode=mode))


def grid(html: str) -> dict[int, str]:
    """{question number: what the grid prints under it}, across every grid row."""
    out: dict[int, str] = {}
    for table in re.findall(r'<table class="key-grid"[^>]*>(.*?)</table>', html):
        heads = [int(n) for n in re.findall(r'<th scope="col">Q(\d+)</th>', table)]
        cells = re.findall(r"<td>(.*?)</td>", table)[: len(heads)]
        out.update(zip(heads, cells, strict=True))
    return out


def rows(html: str) -> list[tuple[str, str]]:
    """The one-question-a-row tables' rows as (label, working cell)."""
    return re.findall(r'<tr><th scope="row">([^<]+)</th><td class="key-work">(.*?)</td></tr>', html)


def pairs(html: str) -> list[tuple[str, str]]:
    """The 1-mark answers printed two to a row, as (label, answer)."""
    return re.findall(r'<th scope="row">([^<]+)</th><td class="key-short">(.*?)</td>', html)


def questions(doc: dict) -> list[dict]:
    return [n for n in doc["content"]["content"] if n["type"] == "templatedQuestion"]


# --- defaults --------------------------------------------------------------------------------


def test_new_papers_start_with_the_school_key():
    want = {
        "layout": "compact",
        "show_scheme": False,
        "show_marks": False,
        "one_mark_working": False,
    }
    assert new_key_options() == want
    made = [
        generate_paper("p1_booklet_a", "P6", 3)[0],
        template_document("p2"),
        empty_document("New"),
    ]
    for doc in made:
        assert doc["settings"]["key_options"] == want
        assert validate_document(doc) == []
        assert "compact-key" in key(doc)
    worked = with_key_style(made[0], "worked")
    assert key_options(worked)["layout"] == "full" and key_options(worked)["show_scheme"]
    assert worked["settings"]["time_min"] == made[0]["settings"]["time_min"]  # others kept
    with pytest.raises(ValueError):
        new_key_options("tiny")


def test_saved_papers_keep_the_key_they_had():
    # no key options at all: the worked solutions with M/A lines, as before EXA-142
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    del doc["settings"]["key_options"]
    assert key_options(doc) == {
        "show_question": True,
        "show_scheme": True,
        "layout": "full",
        "show_marks": False,
        "one_mark_working": True,
    }
    html = key(doc)
    assert "compact-key" not in html and 'class="marking-scheme"' in html
    # a compact key saved before EXA-159 keeps the working of its 1-mark questions
    old = key(compact(doc))
    assert pairs(old) == [] and [label for label, _ in rows(old)][:2] == ["Q16", "Q17"]
    assert 'class="key-scheme"' in old  # and its M/A lines, as it had them


def test_the_schema_gates_the_options():
    doc, _ = generate_paper("p1_booklet_a", "P6", 3)
    for bad in ({"layout": "tiny"}, {"show_marks": "yes"}, {"one_mark_working": 1}, {"x": True}):
        broken = compact(doc, **bad)
        assert validate_document(broken), bad


# --- Booklet A: the grid ---------------------------------------------------------------------


def test_booklet_a_prints_a_grid_of_the_correct_option_numbers():
    doc, _ = generate_paper("p1_booklet_a", "P6", 3)
    html = key(doc)
    printed = grid(html)
    qs = questions(doc)
    assert len(qs) == 15 and sorted(printed) == list(range(1, 16))
    for number, node in enumerate(qs, 1):
        answer = node["attrs"]["question"]["question"]["parts"][0]["answer"]
        assert answer["type"] == "choice"
        assert printed[number] == answer["correct"]
    # ten to a row, Q1–Q10 then Q11–Q15 with the row completed by empty cells
    tables = re.findall(r'<table class="key-grid">(.*?)</table>', html)
    assert len(tables) == 2
    assert tables[1].count("<th></th>") == 5 and tables[1].count("<td></td>") == 5
    assert "key-table" not in html and "solution-steps" not in html
    assert "Wrong options" not in html and "key-scheme" not in html
    stem = qs[0]["attrs"]["question"]["question"]["parts"][0]["text"]
    assert stem not in html


# --- Booklet B and Paper 2: the tables --------------------------------------------------------


def test_booklet_b_one_mark_answers_pair_up_and_two_mark_questions_show_working():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    html = key(doc)
    short = pairs(html)
    assert [label for label, _ in short] == ["Q16", "Q17", "Q18", "Q19", "Q20"]
    assert html.count('<table class="key-table key-pairs">') == 1
    assert html.count("<tr>", html.index("key-pairs"), html.index("</table>")) == 3  # 2+2+1
    for _, answer in short:
        assert answer and "key-step" not in answer and "Ans:" not in answer
    worked = rows(html)
    assert [label for label, _ in worked] == [f"Q{n}" for n in range(21, 31)]
    for _, work in worked:
        steps = work.count('<p class="key-step">')
        assert 1 <= steps <= 4
        assert re.search(r'<p class="key-ans"><span class="ans-label">Ans:</span> [^<]', work)
    # no marks, no M1/A1, never the question again, no "Answer:" of the worked layout
    for absent in ("key-scheme", "key-marks", "A1", "M1", "Answer:", "[2]"):
        assert absent not in html, absent
    for node in questions(doc):
        assert node["attrs"]["question"]["question"]["parts"][0]["text"] not in html


def test_the_options_bring_back_the_scheme_marks_and_one_mark_working():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    scheme = key(school(doc, show_scheme=True))
    assert 'class="key-scheme"' in scheme and 'class="key-mark">A1<' in scheme
    marks = key(school(doc, show_marks=True))
    assert re.search(r'<td class="key-short">[^<]+ <span class="key-marks">\[1\]</span>', marks)
    assert all('<span class="key-marks">[2]</span>' in work for _, work in rows(marks))
    assert "Total: 25 marks" in marks
    working = key(school(doc, one_mark_working=True))
    assert pairs(working) == []
    assert [label for label, _ in rows(working)][0] == "Q16"
    assert '<p class="key-step">' in rows(working)[0][1]


def test_distractor_reasons_never_print_in_the_school_key():
    booklet_a, _ = generate_paper("p1_booklet_a", "P6", 3)
    # a converted multiple-choice question (its wrong options carry reasons), outside an MCQ section
    mcq = next(
        q
        for q in questions(booklet_a)
        if load_blueprint(q["attrs"]["question"]["blueprint_code"]).answer_types != ("choice",)
    )
    doc = make_doc(copy.deepcopy(mcq))
    full = key(with_key_style(doc, "worked"))
    assert "Wrong options" in full  # worked solutions keep them for the teacher
    html = key(school(doc, show_scheme=True))
    assert 'class="key-mark">A1<' in html and "Wrong options" not in html


def test_structured_questions_keep_one_row_with_each_part_on_its_own_line():
    doc, _ = generate_paper("p2", "P6", 3)
    multi = [
        (n, q)
        for n, q in enumerate(questions(doc), 1)
        if len(q["attrs"]["question"]["question"]["parts"]) > 1
    ]
    assert multi
    labels = dict(rows(key(doc)))
    for number, node in multi:
        work = labels[f"Q{number}"]
        for part in node["attrs"]["question"]["question"]["parts"]:
            assert (
                f'<span class="ans-label">Ans:</span> <span class="ans-part">({part["label"]})'
                in (work)
            )
    assert not any("(" in label for label in labels)  # no "Q9(a)" rows


def test_teacher_written_questions():
    doc = make_doc(
        freeform_block("SINGLE stem", marks=2, answer="42 cm"),
        multipart_block(
            part_node("PART-A text", marks=2, answer="ANSWER-A"),
            part_node("PART-B text", marks=1),
            stem="MULTI stem",
        ),
        freeform_block("LEFT-OUT stem", marks=1, answer="ANSWER-LEFT"),
        freeform_block("ONE stem", marks=1, answer="ONE-ANSWER"),
        freeform_block("EMPTY stem", marks=1),
    )
    doc["content"]["content"][2]["attrs"]["in_key"] = False
    html = key(school(doc))
    got = rows(html)
    assert [label for label, _ in got] == ["Q1", "Q2"]
    assert '<span class="ans-label">Ans:</span> 42 cm' in got[0][1]
    assert '<span class="ans-part">(a)</span> ANSWER-A' in got[1][1]
    assert "(b) No answer written yet" in got[1][1]
    assert [label for label, _ in pairs(html)] == ["Q4", "Q5"]  # Q3 left out; numbers kept
    assert "ONE-ANSWER" in pairs(html)[0][1] and "No answer written yet" in pairs(html)[1][1]
    for hidden in ("SINGLE stem", "MULTI stem", "PART-A text", "ANSWER-LEFT", "ONE stem"):
        assert hidden not in html


# --- the header -------------------------------------------------------------------------------


def test_the_header_block_comes_from_the_cover_and_replaces_the_title():
    doc, _ = generate_paper("p2", "P6", 3)
    cover = doc["content"]["content"][0]
    assert cover["type"] == "coverPage"
    cover["attrs"].update(school="SCHOOL-NAME", exam="EXAM-NAME")
    html = key(doc)
    meta = re.search(r'<dl class="key-meta">(.*?)</dl>', html)
    assert meta
    assert re.findall(r"<dt>(\w+)</dt>", meta.group(1)) == ["School", "Level", "Subject", "Exam"]
    assert "<dt>School</dt><dd>SCHOOL-NAME</dd>" in meta.group(1)
    assert f'<h2 class="key-paper">{cover["attrs"]["paper"]}</h2>' in html
    assert "sheet-header" not in html and "Answer Key" not in html and "Total:" not in html
    assert "Section A" not in html  # the templates' generic section titles do not print
    # a cover field left empty leaves its line out
    cover["attrs"]["school"] = ""
    del cover["attrs"]["level"]
    meta = re.search(r'<dl class="key-meta">(.*?)</dl>', key(doc))
    assert meta and re.findall(r"<dt>(\w+)</dt>", meta.group(1)) == ["Subject", "Exam"]
    # without a cover the paper's title names it
    plain = make_doc(freeform_block("Q", marks=2, answer="A"), title="My quiz")
    assert '<h2 class="key-paper">My quiz</h2>' in body(
        render_document_html("My quiz", school(plain), mode="key")
    )
    assert "key-meta" not in key(school(plain))


def test_full_mode_uses_the_layout():
    doc, _ = generate_paper("p2", "P6", 3)
    full = key(doc, mode="full")
    paper, key_part = full.split('<section class="key-section">')
    assert "compact-key" in key_part and "compact-key" not in paper
    assert rows(key_part) == rows(key(doc))


# --- continuous flow --------------------------------------------------------------------------


def test_the_key_is_not_paginated_question_by_question():
    doc, _ = generate_paper("p2", "P6", 3)
    html = render_document_html("P2", doc, mode="key")
    assert "data-paginate" not in body(html)
    for page_breaker in ("own-page", 'class="page-break"', "page-foot"):
        assert page_breaker not in body(html)
    assert ".key-table tr { break-inside: avoid; }" in html


def _pdf_pages(html: str) -> list[str]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.wait_for_selector("html[data-paginated='true']", state="attached")
        pdf = page.pdf(format="A4", print_background=True)
        browser.close()
    return [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(pdf)).pages]


def test_the_printed_key_flows_on_and_no_row_splits():
    """Read back from Chromium's PDF: pages are filled with several questions each, and every
    question's first and last line of working land on the same page."""
    blocks = []
    for n in range(1, 31):
        answer = [para(f"R{n:02d}TOP working line.")]
        answer += [
            para(f"Then the next step of the working for this question, line {k}.")
            for k in range(6)
        ]
        answer.append(para(f"R{n:02d}END so the answer is {n}."))
        node = freeform_block(f"Question {n}", marks=3)
        node["attrs"]["answer"] = {"type": "doc", "content": answer}
        blocks.append(node)
    pages = _pdf_pages(render_document_html("Long", school(make_doc(*blocks)), mode="key"))
    assert len(pages) >= 3
    for n in range(1, 31):
        on = [k for k, text in enumerate(pages) if f"R{n:02d}TOP" in text or f"R{n:02d}END" in text]
        assert len(set(on)) == 1, f"Q{n} split across pages {on}"
    for text in pages[:-1]:
        assert len(re.findall(r"R\d\dTOP", text)) >= 3  # continuous: no page per question


def test_a_drawn_part_without_steps_is_still_labelled():
    """Review of #237: a construction part with no solution steps names its part (and, with
    marks on, its marks) on an "Ans:" line above the drawing."""
    import json
    from pathlib import Path

    obj = json.loads(
        (Path(__file__).parent / "fixtures/sourced/psle_2023_construction.json").read_text()
    )
    part = obj["question"]["parts"][0]
    drawn = {**copy.deepcopy(part), "label": "b", "solution_steps": []}
    obj["question"]["parts"] = [part, drawn]
    from documents import question_block

    html = key(school(make_doc(question_block(obj)), show_marks=True))
    assert '<span class="ans-part">(b)</span>' in html
    assert html.count('class="key-marks"') >= 2
