"""EXA-138 — page furniture on the printed paper, checked on the real Chromium layout and PDF.

Every question page gets a footer (page number counting the cover as page 1, "(Go on to the next
page)" on all but the last page, the tally box on the footer line), the last question is followed
by the end marker for its booklet, a page that ends early has its last working space stretched
down to the footer, a marking page has one continuous strip, and a structured section gives each
question a page of its own.
"""

from __future__ import annotations

import io
import re

import pytest
from documents import freeform_block, make_doc
from exam_engine.paper import generate_paper
from exam_engine.render import render_document_html
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

MM = 96 / 25.4
GO_ON = "(Go on to the next page)"


def _cover(paper: str, **attrs) -> dict:
    return {"type": "coverPage", "attrs": {"paper": paper, **attrs}}


def _section(mode: str) -> dict:
    return {"type": "section", "attrs": {"title": "Section", "mode": mode}}


def _q(text: str, marks: int = 2, space: int = 30) -> dict:
    node = freeform_block(text, marks=marks)
    node["attrs"]["space_mm"] = space
    return node


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


_LAYOUT_JS = """
() => Array.from(document.querySelectorAll('.pg')).map((pg) => {
  const box = pg.getBoundingClientRect()
  const foot = pg.querySelector('.page-foot')
  const flow = Array.from(pg.children).filter(
    (c) => !c.classList.contains('page-foot') && !c.classList.contains('margin-strip'))
  const last = flow[flow.length - 1]
  const strips = Array.from(pg.querySelectorAll('.margin-strip'))
  const tally = foot && foot.querySelector('.tally')
  const go = foot && foot.querySelector('.foot-go')
  const lines = last ? last.querySelectorAll('.answer-line') : []
  const firstQ = pg.querySelector('.question')
  return {
    kind: pg.querySelector('.cover-page') ? 'cover'
      : pg.querySelector('.blank-page') ? 'blank' : 'q',
    number: foot ? foot.querySelector('.foot-num').textContent : null,
    tag: foot ? foot.querySelector('.foot-tag').textContent : null,
    go: !!go,
    end: pg.querySelector('.end-marker') ? pg.querySelector('.end-marker').textContent : null,
    pgTop: box.top,
    footTop: foot ? foot.getBoundingClientRect().top : null,
    lastBottom: last
      ? last.getBoundingClientRect().bottom + parseFloat(getComputedStyle(last).marginBottom)
      : null,
    lastBoxBottom: last ? last.getBoundingClientRect().bottom : null,
    lastHasSpace:!!(last && last.querySelector('.answer-space')),
    filled: pg.querySelectorAll('.answer-space[data-filled]').length,
    lastAnsBottom: lines.length ? lines[lines.length - 1].getBoundingClientRect().bottom : null,
    marked: pg.querySelectorAll('.question.marked').length,
    strips: strips.map((s) => [s.getBoundingClientRect().top, s.getBoundingClientRect().bottom]),
    captions: Array.from(pg.querySelectorAll('.question.marked')).map(
      (q) => getComputedStyle(q, '::after').content),
    tally: tally
      ? { w: tally.getBoundingClientRect().width, left: tally.getBoundingClientRect().left,
          total: Number(tally.textContent) }
      : null,
    goRight: go ? go.getBoundingClientRect().right : null,
    ownPageFirst: firstQ ? firstQ.classList.contains('own-page') : null,
    structuredHead: !!pg.querySelector('.paper-section.own-page'),
    questions: pg.querySelectorAll('.question:not(.cont)').length,
  }
})
"""


def _render(browser, doc: dict, mode: str = "student"):
    page = browser.new_page()
    page.set_content(render_document_html("T", doc, mode=mode), wait_until="load")
    page.wait_for_selector("html[data-paginated='true']", state="attached")
    pages = page.evaluate(_LAYOUT_JS)
    pdf = page.pdf(format="A4", print_background=True)
    text = [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]
    warnings = page.evaluate("document.documentElement.getAttribute('data-pagination-warnings')")
    page.close()
    return pages, text, warnings


@pytest.fixture(scope="module")
def booklet_b(browser):
    doc, _ = generate_paper("p1_booklet_b", "P6", 7)
    doc["content"]["content"][0]["attrs"]["school"] = "Example Primary"
    return _render(browser, doc)


@pytest.fixture(scope="module")
def paper_2(browser):
    doc, _ = generate_paper("p2", "P6", 7)
    return doc, _render(browser, doc)


def test_every_question_page_has_its_printed_page_number(booklet_b):
    pages, text, warnings = booklet_b
    assert warnings is None and len(text) == len(pages) >= 4
    assert pages[0]["kind"] == "cover" and pages[0]["number"] is None  # the cover: no footer
    # the template's blank back of the cover (EXA-140): no footer, but it counts
    assert pages[1]["kind"] == "blank" and pages[1]["number"] is None
    assert len(pages) % 2 == 0  # padded to an even page count; a pad page is blank too
    for k, p in enumerate(pages[2:], start=3):
        if p["kind"] == "blank":
            assert k == len(pages) and p["number"] is None
            continue
        assert p["kind"] == "q" and p["number"] == str(k)  # the cover counts as page 1
        assert re.search(rf"(?m)\b{k}\b", text[k - 1])


def test_go_on_is_on_every_page_but_the_last_and_the_end_marker_closes_the_booklet(booklet_b):
    pages, text, _ = booklet_b
    questions = [k for k, p in enumerate(pages) if p["kind"] == "q"]
    for k in questions[:-1]:
        assert pages[k]["go"] and GO_ON in text[k] and pages[k]["end"] is None
    last = questions[-1]
    assert not pages[last]["go"] and GO_ON not in text[last]
    assert pages[last]["end"] == "End of Booklet B" and "End of Booklet B" in text[last]
    assert sum(t.count(GO_ON) for t in text) == len(questions) - 1


def test_the_footer_tag_names_the_school_and_paper_only_when_the_cover_does(booklet_b, browser):
    pages, _, _ = booklet_b
    assert {p["tag"] for p in pages if p["kind"] == "q"} == {"Example Primary · Paper 1 (Booklet B)"}
    plain, _, _ = _render(browser, make_doc(_cover("Paper 2"), _q("Q1 x")))
    assert plain[1]["tag"] == ""


@pytest.mark.parametrize(
    "cover, end",
    [
        (_cover("Paper 1 (Booklet A)"), "End of Booklet A"),
        (_cover("Paper 1 (Booklet B)"), "End of Booklet B"),
        (_cover("Paper 2"), "End of Paper"),
        (None, "End of Paper"),
    ],
)
def test_the_end_marker_follows_the_last_question_only(cover, end):
    blocks = [_q("Q1 first"), _q("Q2 last"), {"type": "blankPage", "attrs": {"kind": "blank"}}]
    doc = make_doc(*([cover] if cover else []), *blocks)
    html = render_document_html("T", doc, mode="student")
    body = html.split("</style>")[-1]
    assert body.count('class="end-marker"') == 1
    assert re.search(rf'Q2 last.*<p class="end-marker">{end}</p>.*blank-page', body, re.S)
    assert 'class="end-marker"' not in render_document_html("T", doc, mode="key")


def test_a_page_that_ends_early_has_its_working_space_stretched_to_the_footer(booklet_b):
    pages, _, _ = booklet_b
    questions = [p for p in pages if p["kind"] == "q"]
    stretched = [p for p in questions[:-1] if p["lastHasSpace"]]
    assert stretched, "some page must end on a question with working space"
    assert any(p["filled"] for p in stretched)  # (a page that is already full needs none)
    for p in stretched:
        if not p["filled"]:
            # a page that is already full: only its last question's bottom margin may reach
            # past the footer line (the paginator packs boxes, not their trailing margins)
            assert p["footTop"] - p["lastBoxBottom"] >= 0, p
            continue
        gap = p["footTop"] - p["lastBottom"]
        assert 0 <= gap <= 3 * MM, gap / MM  # down to the footer, not into it
        # the Ans: line moved down with the space: it sits at the foot of the page
        assert p["footTop"] - p["lastAnsBottom"] < 15 * MM
    # the last page keeps its natural height: the end marker follows the last answer
    assert questions[-1]["filled"] == 0


def test_one_marking_strip_per_page_from_the_top_to_the_footer(booklet_b):
    pages, text, _ = booklet_b
    for k, p in enumerate(pages):
        if not p["marked"]:
            assert p["strips"] == []
            continue
        assert len(p["strips"]) == 1
        top, bottom = p["strips"][0]
        assert abs(top - p["pgTop"]) < 1 and abs(bottom - p["footTop"]) < 1
        assert set(p["captions"]) == {"none"}  # no rule or caption per question any more
        assert text[k].count("Do not write in") == 1


def test_the_tally_box_is_small_and_sits_on_the_footer_beside_go_on(booklet_b):
    pages, _, _ = booklet_b
    tallied = [p for p in pages if p["tally"]]
    assert len(tallied) == len([p for p in pages if p["kind"] == "q"])
    for p in tallied:
        assert abs(p["tally"]["w"] - 12 * MM) < 1
        assert p["goRight"] is None or p["tally"]["left"] >= p["goRight"]  # no collision


def test_structured_questions_each_start_a_page(paper_2):
    doc, (pages, text, warnings) = paper_2
    assert warnings is None and len(text) == len(pages)
    sections = [s["attrs"]["mode"] for s in doc["content"]["content"] if s["type"] == "section"]
    assert sections[-1] == "structured"
    # the structured section starts a page with its first question, then one question a page
    head = next(k for k, p in enumerate(pages) if p["structuredHead"])
    assert head > 1 and pages[head]["questions"] == 1
    later = [p for p in pages[head + 1 :] if p["kind"] == "q"]
    assert later and all(p["questions"] <= 1 and p["ownPageFirst"] for p in later)


def test_the_answer_key_has_page_numbers_but_no_paper_furniture(browser):
    doc, _ = generate_paper("p2", "P6", 7)
    page = browser.new_page()
    page.set_content(render_document_html("T", doc, mode="key"), wait_until="load")
    page.wait_for_selector("html[data-paginated='true']", state="attached")
    assert page.evaluate("document.querySelectorAll('.pg, .page-foot, .end-marker').length") == 0
    text = [
        p.extract_text() or ""
        for p in PdfReader(io.BytesIO(page.pdf(format="A4", print_background=True))).pages
    ]
    assert len(text) >= 2
    for k, t in enumerate(text, start=1):
        assert str(k) in {line.strip() for line in t.splitlines()}  # Chromium's page number
        assert GO_ON not in t
