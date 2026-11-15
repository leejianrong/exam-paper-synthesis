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
        "school": "Pandan Primary School",
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


def test_the_cover_prints_the_paper_details_and_replaces_the_header():
    html = render_document_html("Doc title", paper(), mode="student")
    assert 'class="sheet-header"' not in html
    for text in (
        "Pandan Primary School",
        "2026 Preliminary Examination",
        "Primary 6 Mathematics",
        "Paper 2",
        "Date: 28 August 2026",
        "Time: 1 h 15 min",
        "Total: 8 marks",
        "Register No.:",
    ):
        assert text in html
    # instructions are one per line, blank lines dropped
    assert "<li>Write your name.</li><li>Answer all questions.</li>" in html


def test_the_examiner_table_is_derived_from_the_sections():
    html = render_document_html("T", paper(), mode="student")
    table = html[html.index('<table class="examiner-table">') :]
    table = table[: table.index("</table>")]
    assert '<th scope="row">Section A</th><td></td><td>4</td>' in table
    assert '<th scope="row">Section B</th><td></td><td>4</td>' in table
    assert '<tr class="total"><th scope="row">Total</th><td></td><td>8</td>' in table
    off = paper()
    off["content"]["content"][0]["attrs"]["examiner_table"] = False
    assert '<table class="examiner-table">' not in render_document_html("T", off, mode="student")


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
    assert "Total: 1 marks" in html


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
    if not tally:  # every section a non-working one: no marking, so no paginator page boxes
        for n in doc["content"]["content"]:
            if n["type"] == "section":
                n["attrs"]["mode"] = "mcq"
    html = render_document_html("T", doc, mode="student")
    text, pgs = _pdf(browser, html)

    assert len(text) == 5, [t[:40] for t in text]
    assert "PANDAN PRIMARY SCHOOL" in text[0] and "QA1" not in text[0]
    assert "QA1" in text[1] and "QB3" in text[1]
    assert "intentionally left blank" in text[2] and "QB" not in text[2]
    assert "QB4" in text[3]
    assert "Rough work" in text[4] and "QB4" not in text[4]
    if tally:
        assert len(pgs) == 5
        # cover and blank pages carry no tally box; the question pages carry their marks
        assert [p["tally"] for p in pgs] == [None, 8, None, 3, None]
    else:
        assert pgs == []


def test_the_examiner_table_rows_add_up_when_questions_precede_the_sections():
    doc = make_doc(cover(), q("Q0 loose", 5), section("Section A"), q("QA1", 2))
    html = render_document_html("T", doc, mode="student")
    assert '<th scope="row">Other questions</th><td></td><td>5</td>' in html
    assert '<th scope="row">Section A</th><td></td><td>2</td>' in html
    assert '<tr class="total"><th scope="row">Total</th><td></td><td>7</td>' in html


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
