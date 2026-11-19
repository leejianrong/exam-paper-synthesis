"""P7 — the cover page and blank pages: validation, print, answer key, and the real PDF pages."""

from __future__ import annotations

import io

import pytest
from documents import freeform_block, make_doc
from exam_engine.document import MAX_BLANK_PAGES, cover_page, validate_document
from exam_engine.render import render_document_html
from pypdf import PdfReader


def cover(**attrs) -> dict:
    base = {
        "school": "Example Primary School",
        "exam": "2026 Preliminary Examination",
        "level": "Primary 6",
        "subject": "Mathematics",
        "paper": "Paper 2",
        "date": "28 August 2026",
        "instructions": "Write your name.\n\nAnswer all questions.",
    }
    return {"type": "coverPage", "attrs": {**base, **attrs}}


def blank(kind="blank", text=None) -> dict:
    return {"type": "blankPage", "attrs": {"kind": kind, "text": text}}


def section(title: str, mode="short") -> dict:
    return {"type": "section", "attrs": {"title": title, "mode": mode}}


def q(text: str, marks: int) -> dict:
    node = freeform_block(text, marks=marks)
    node["attrs"]["space_mm"] = 20  # small, so a page holds several
    return node


def paper(*extra: dict, settings: dict | None = None) -> dict:
    doc = make_doc(
        cover(),
        section("Section A"),
        q("QA1 first", 2),
        q("QA2 second", 2),
        section("Section B", mode="structured"),
        q("QB3 third", 4),
        *extra,
    )
    doc["settings"] = settings or {"time_min": 75}
    return doc


# --- validation -------------------------------------------------------------------------------


def test_a_paper_with_a_cover_and_blank_pages_is_valid():
    doc = paper(blank(), blank("rough"))
    assert validate_document(doc) == []
    assert cover_page(doc) is doc["content"]["content"][0]


def test_the_cover_must_be_the_first_block_and_only_one():
    doc = make_doc(freeform_block("Q", marks=1), cover())
    assert any("cover page must be the paper's first block" in e for e in validate_document(doc))
    two = make_doc(cover(), cover())
    assert any("content/content/1" in e for e in validate_document(two))
    assert cover_page(make_doc(freeform_block("Q"))) is None


def test_cover_and_blank_page_fields_are_schema_gated():
    assert validate_document(make_doc(blank(kind="ruled")))
    assert validate_document(make_doc({"type": "coverPage", "attrs": {"logo": "x"}}))
    assert validate_document(make_doc(cover(school="x" * 121)))


def test_blank_pages_are_capped():
    doc = make_doc(*[blank() for _ in range(MAX_BLANK_PAGES + 1)])
    assert any("blank pages" in e for e in validate_document(doc))


def test_documents_without_the_new_blocks_are_unchanged():
    doc = make_doc(freeform_block("Q1", marks=1))
    assert validate_document(doc) == []
    assert 'class="sheet-header"' in render_document_html("T", doc, mode="student")


# --- print ------------------------------------------------------------------------------------


def _between(html: str, start: str, end: str) -> str:
    part = html[html.index(start) :]
    return part[: part.index(end)]


def test_the_cover_prints_the_paper_details_and_replaces_the_header():
    html = render_document_html("Doc title", paper(), mode="student")
    assert 'class="sheet-header"' not in html
    # the title block: one centred line each, the booklet in brackets on a line of its own
    head = _between(html, '<div class="cover-head">', "</div>")
    assert head == (
        '<div class="cover-head"><p class="cover-school">Example Primary School</p>'
        '<p class="cover-exam">2026 Preliminary Examination</p>'
        '<p class="cover-level">Primary 6</p><p class="cover-subject">Mathematics</p>'
        '<p class="cover-paper">Paper 2</p>'
    )
    for text in (
        '<span class="cover-label">Date:</span><span class="cover-value">28 August 2026</span>',
        '<p class="cover-time">Time: 1 h 15 min</p>',
        "<span>3 questions</span><span>8 marks</span>",
    ):
        assert text in html
    assert "Register No." not in html  # the register number goes in the brackets after the name
    # instructions are one per line, blank lines dropped
    assert "<li>Write your name.</li><li>Answer all questions.</li>" in html


def test_the_title_block_puts_the_booklet_on_its_own_line():
    doc = paper()
    doc["content"]["content"][0]["attrs"]["paper"] = "Paper 1 (Booklet A)"
    html = render_document_html("T", doc, mode="student")
    assert '<p class="cover-paper">Paper 1</p><p class="cover-booklet">(Booklet A)</p>' in html


def test_the_candidate_fields_are_name_with_brackets_class_and_date():
    html = render_document_html("T", paper(), mode="student")
    fields = _between(html, '<div class="cover-fields">', '<p class="cover-time">')
    assert (
        '<span class="cover-label">Name:</span><span class="cover-line"></span>'
        '<span class="cover-reg">(<span></span>)</span>'
    ) in fields
    # the class line starts with the level, as real covers print "Class: Primary 6 ____"
    assert (
        '<span class="cover-label">Class:</span><span class="cover-value">Primary 6</span>'
        '<span class="cover-line short"></span>'
    ) in fields
    no_date = paper()
    del no_date["content"]["content"][0]["attrs"]["date"]
    html = render_document_html("T", no_date, mode="student")
    assert '<span class="cover-label">Date:</span><span class="cover-line"></span>' in html


def test_the_parent_signature_line_is_a_switch():
    assert "Parent&#x27;s signature" not in render_document_html("T", paper(), mode="student")
    doc = paper()
    doc["content"]["content"][0]["attrs"]["parent_signature"] = True
    assert validate_document(doc) == []
    html = render_document_html("T", doc, mode="student")
    assert (
        '<span class="cover-label">Parent\'s signature:</span><span class="cover-line"></span>'
        in html
    )


@pytest.mark.parametrize(
    ("paper_name", "want"),
    [
        ("Paper 1 (Booklet A)", "Total time for Booklets A and B: 1 h"),
        ("Paper 1 (Booklet B)", "Total time for Booklets A and B: 1 h"),
        ("Paper 2", "Time: 1 h 30 min"),
        ("Mid-year test", "Time: 1 h 30 min"),
    ],
)
def test_paper_1_says_its_time_is_shared_by_both_booklets(paper_name, want):
    time_min = 60 if "Paper 1" in paper_name else 90
    doc = paper(settings={"time_min": time_min})
    doc["content"]["content"][0]["attrs"]["paper"] = paper_name
    assert f'<p class="cover-time">{want}</p>' in render_document_html("T", doc, mode="student")


def test_a_capitalised_not_in_the_instructions_is_emphasised():
    doc = paper()
    doc["content"]["content"][0]["attrs"]["instructions"] = (
        "The use of calculators is NOT allowed.\nDo not <b>panic</b>. NOTHING else."
    )
    html = render_document_html("T", doc, mode="student")
    assert (
        '<li>The use of calculators is <strong class="cover-not">NOT</strong> allowed.</li>' in html
    )
    # only the standalone capitalised word; the rest stays escaped plain text
    assert "<li>Do not &lt;b&gt;panic&lt;/b&gt;. NOTHING else.</li>" in html


def _rows(html: str) -> list[tuple[str, int]]:
    import re

    table = _between(html, '<table class="examiner-table">', "</table>")
    return [
        (label, int(maximum))
        for label, maximum in re.findall(
            r'<th scope="row">([^<]*)</th><td class="score">.*?'
            r'<span class="score-max">(\d+)</span></td>',
            table,
        )
    ]


def test_a_paper_outside_the_exam_set_gets_a_row_per_section():
    doc = paper()
    doc["content"]["content"][0]["attrs"]["paper"] = "Mid-year test"
    html = render_document_html("T", doc, mode="student")
    assert _rows(html) == [("Section A", 4), ("Section B", 4), ("Total", 8)]
    # each score cell is split by a diagonal, the maximum in its lower right
    assert '<svg class="score-diag"' in html
    assert '<tr class="total"><th scope="row">Total</th>' in html
    off = paper()  # switched off, on any paper
    off["content"]["content"][0]["attrs"]["examiner_table"] = False
    assert '<table class="examiner-table">' not in render_document_html("T", off, mode="student")


@pytest.mark.parametrize(
    ("paper_name", "want"),
    [
        # this paper's maximum is its own total (8 here); the others are the standard ones
        ("Paper 1 (Booklet A)", [("Paper 1 (Booklet A)", 8)]),
        ("Paper 1 (Booklet B)", [("Booklet A", 20), ("Booklet B", 8), ("Total (Paper 1)", 28)]),
        ("Paper 2", [("Paper 1", 45), ("Paper 2", 8), ("Total", 53)]),
    ],
)
def test_an_exam_set_paper_gets_the_sets_examiner_table(paper_name, want):
    doc = paper()
    doc["content"]["content"][0]["attrs"]["paper"] = paper_name
    assert _rows(render_document_html("T", doc, mode="student")) == want


def test_the_standard_paper_marks_come_from_the_templates():
    from exam_engine.paper import standard_paper_marks

    assert standard_paper_marks() == {"booklet_a": 20, "booklet_b": 25, "paper_2": 55}


@pytest.mark.parametrize(
    ("code", "rows", "time", "signature"),
    [
        ("p1_booklet_a", [], "Total time for Booklets A and B: 1 h", False),
        (
            "p1_booklet_b",
            [("Booklet A", 20), ("Booklet B", 25), ("Total (Paper 1)", 45)],
            "Total time for Booklets A and B: 1 h",
            True,
        ),
        ("p2", [("Paper 1", 45), ("Paper 2", 55), ("Total", 100)], "Time: 1 h 30 min", True),
    ],
)
def test_a_generated_p6_set_prints_real_covers(code, rows, time, signature):
    from exam_engine.paper import generate_paper

    doc, _ = generate_paper(code, "P6", 3)
    assert validate_document(doc) == []
    html = render_document_html("T", doc, mode="student")
    assert (_rows(html) if rows else []) == rows
    assert ('<table class="examiner-table">' in html) == bool(rows)
    assert f'<p class="cover-time">{time}</p>' in html
    assert ("Parent's signature:" in html) == signature
    assert '<p class="cover-level">Primary 6</p><p class="cover-subject">Mathematics</p>' in html
    assert '<strong class="cover-not">NOT</strong>' in html or code == "p2"
    # a blank back of the cover, and the booklet padded to an even page count by the paginator
    assert doc["content"]["content"][1] == {"type": "blankPage", "attrs": {"kind": "blank"}}
    assert '<div class="cover-page" data-even-pages>' in html


def test_an_empty_cover_still_names_the_paper():
    doc = make_doc({"type": "coverPage", "attrs": {}}, freeform_block("Q", marks=3))
    html = render_document_html("Mid-year test", doc, mode="student")
    assert '<p class="cover-paper">Mid-year test</p>' in html
    assert "Time:" not in html  # no time set, none printed


def test_blank_pages_print_their_wording_and_escape_it():
    html = render_document_html(
        "T", paper(blank(), blank("rough"), blank(text="<b>Turn over</b>")), mode="student"
    )
    assert "This page is intentionally left blank." in html
    assert '<div class="blank-page rough"><p class="blank-text">Rough work</p>' in html
    assert "&lt;b&gt;Turn over&lt;/b&gt;" in html


def test_the_answer_key_leaves_out_the_cover_and_blank_pages():
    doc = paper(blank("rough"))
    key = render_document_html("T", doc, mode="key")
    assert 'class="cover-page"' not in key and 'class="blank-page' not in key
    full = render_document_html("T", doc, mode="full")
    key_part = full[full.index('class="key-section"') :]
    assert 'class="cover-page"' not in key_part and 'class="blank-page' not in key_part
    assert full.count('class="cover-page"') == 1


def test_the_new_blocks_add_no_marks_and_take_no_number():
    doc = make_doc(cover(), blank(), freeform_block("QX", marks=1), blank("rough"))
    assert validate_document(doc) == []
    html = render_document_html("T", doc, mode="student")
    assert html.count('class="question') == 1
    assert "<span>1 question</span><span>1 mark</span>" in html


# --- the real PDF -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _pdf(browser, html: str) -> tuple[list[str], list[dict]]:
    page = browser.new_page()
    page.set_content(html, wait_until="load")
    page.wait_for_selector("html[data-paginated='true']", state="attached")
    pgs = page.evaluate(
        """() => Array.from(document.querySelectorAll('.pg')).map((pg) => ({
             text: pg.innerText,
             tally: pg.querySelector('.tally-total')
               ? Number(pg.querySelector('.tally-total').textContent) : null,
           }))"""
    )
    pdf = page.pdf(format="A4", print_background=True)
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages], pgs


@pytest.mark.parametrize("tally", [True, False], ids=["paginated", "plain"])
def test_cover_and_blank_pages_each_get_a_page_of_their_own(browser, tally):
    doc = paper(blank(), q("QB4 fourth", 3), blank("rough"))
    # plain: every section a non-working one, so no tally boxes. Never structured here: that
    # would give QB3 a page of its own (EXA-138), which is not what this test is about.
    for n in doc["content"]["content"]:
        if n["type"] == "section":
            n["attrs"]["mode"] = "short" if tally else "mcq"
    html = render_document_html("T", doc, mode="student")
    text, pgs = _pdf(browser, html)

    assert len(text) == 5, [t[:40] for t in text]
    assert "EXAMPLE PRIMARY SCHOOL" in text[0] and "QA1" not in text[0]
    assert "QA1" in text[1] and "QB3" in text[1]
    assert "intentionally left blank" in text[2] and "QB" not in text[2]
    assert "QB4" in text[3]
    assert "Rough work" in text[4] and "QB4" not in text[4]
    assert len(pgs) == 5  # every paper is paginated, for its footers (EXA-138)
    # cover and blank pages carry no tally box; the question pages carry their marks
    assert [p["tally"] for p in pgs] == ([None, 8, None, 3, None] if tally else [None] * 5)


def test_the_examiner_table_rows_add_up_when_questions_precede_the_sections():
    doc = make_doc(cover(paper="Unit test"), q("Q0 loose", 5), section("Section A"), q("QA1", 2))
    html = render_document_html("T", doc, mode="student")
    assert _rows(html) == [("Other questions", 5), ("Section A", 2), ("Total", 7)]


@pytest.mark.parametrize("keeper", ["section", "heading"])
def test_a_blank_page_after_a_header_is_not_pulled_onto_its_page(browser, keeper):
    from documents import heading

    head = section("Section A") if keeper == "section" else heading("HEADX")
    doc = make_doc(cover(), section("Lead"), q("QL1 lead", 1), head, blank(), q("QA1 first", 2))
    text, pgs = _pdf(browser, render_document_html("T", doc, mode="student"))
    assert len(text) == len(pgs) == 4, [t[:40] for t in text]
    assert "intentionally left blank" in text[2]
    assert "QA1" not in text[2] and ("HEADX" not in text[2]) and ("Section A" not in text[2])
    assert "QA1" in text[3]


def _flat(*extra: dict) -> dict:
    """``paper()`` with every section short-answer: cover, one page of questions, then ``extra``."""
    doc = paper(*extra)
    for n in doc["content"]["content"]:
        if n["type"] == "section":
            n["attrs"]["mode"] = "short"
    return doc


def _count_line(browser, doc: dict) -> tuple[int, str]:
    page = browser.new_page()
    page.set_content(render_document_html("T", doc, mode="student"), wait_until="load")
    page.wait_for_selector("html[data-paginated='true']", state="attached")
    out = page.evaluate(
        """() => [document.querySelectorAll('.pg').length,
                  document.querySelector('.cover-pages').hidden ? '' :
                  document.querySelector('.cover-pages').textContent]"""
    )
    page.close()
    return out[0], out[1]


def test_the_paginator_fills_in_the_page_count_line(browser):
    # cover + a page of questions + a rough-work page (printed) + a page left blank
    doc = _flat(blank("rough"), blank())
    n, line = _count_line(browser, doc)
    assert n == 4
    assert line == "This booklet consists of 3 printed pages and 1 blank page."
    n, line = _count_line(browser, _flat())
    assert (n, line) == (2, "This booklet consists of 2 printed pages.")


def test_an_even_page_cover_pads_the_booklet_with_a_blank_page(browser):
    doc = _flat(blank())  # cover, questions, blank: 3 pages, so one more
    doc["content"]["content"][0]["attrs"]["even_pages"] = True
    assert validate_document(doc) == []
    n, line = _count_line(browser, doc)
    assert n == 4
    assert line == "This booklet consists of 2 printed pages and 2 blank pages."
    text, _ = _pdf(browser, render_document_html("T", doc, mode="student"))
    assert len(text) == 4 and "intentionally left blank" in text[3]
    even = _flat()  # already even: nothing added
    even["content"]["content"][0]["attrs"]["even_pages"] = True
    assert _count_line(browser, even) == (2, "This booklet consists of 2 printed pages.")
