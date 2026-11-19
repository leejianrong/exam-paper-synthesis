"""EXA-168: one answer key for a whole exam set (Booklet A, Booklet B, Paper 2).

The invariant: the set key holds every in-key question of every paper exactly once, in order,
under that paper's booklet heading, and each paper's part of it is that paper's own key (same
answers, same style and options) with only the cover lines and the paper's name replaced by the
set's title block and the booklet heading. Which papers form a set, and in what order, is
``document.exam_set_order``.
"""

from __future__ import annotations

import copy
import io
import re

import pytest
from exam_engine.document import (
    exam_set_order,
    in_key,
    number_from,
    numbered_blocks,
    paper_part,
    with_key_style,
)
from exam_engine.errors import ExamSetError
from exam_engine.paper import generate_set
from exam_engine.render import SET_HEADINGS, render_document_html, render_set_key_html

TEMPLATES = ["p1_booklet_a", "p1_booklet_b", "p2"]
SEEDS = range(8)
_LABEL = re.compile(r'<th scope="(?:row|col)">Q(\d+)</th>')
_LI_NUMBER = re.compile(r'<li style="counter-reset: q (\d+)" class="question')


def _set(level: str, seed: int) -> list[dict]:
    return [doc for doc, _ in generate_set(TEMPLATES, level, seed)]


def _main(html: str) -> str:
    return html[html.index("<main ") : html.index("</main>")]


def _sections(html: str) -> list[tuple[str, str]]:
    """The set key's papers as (data-part, inner HTML), in print order."""
    return re.findall(
        r'<section class="set-paper" data-part="([^"]*)">(.*?)</section>(?=<section class="set-|$)',
        _main(html).removesuffix("\n"),
        flags=re.DOTALL,
    )


def _own_key_as_in_set(doc: dict) -> str:
    """The paper's own school key, with its cover lines dropped and its name replaced by the
    booklet heading: what the set key must print for it."""
    own = _main(render_document_html(doc["title"], doc, mode="key"))
    start = own.index('<div class="compact-key">')
    compact = own[start : own.rindex("</div>") + len("</div>")]
    compact = re.sub(r'<dl class="key-meta">.*?</dl>', "", compact, count=1)
    return re.sub(
        r'<h2 class="key-paper">[^<]*</h2>',
        f'<h2 class="key-paper">{SET_HEADINGS[paper_part(doc)]}</h2>',
        compact,
        count=1,
    )


def _in_key_numbers(doc: dict) -> list[int]:
    return [n for n, b in enumerate(numbered_blocks(doc), number_from(doc)) if in_key(b)]


@pytest.mark.parametrize("level", ["P5", "P6"])
@pytest.mark.parametrize("seed", SEEDS)
def test_the_set_key_is_each_papers_own_key_once_in_order(level, seed):
    docs = _set(level, seed)
    html = render_set_key_html("Set", [(d["title"], d) for d in docs])
    sections = _sections(html)
    assert [p for p, _ in sections] == ["booklet_a", "booklet_b", "paper_2"]
    for doc, (part, inner) in zip(docs, sections, strict=True):
        # under its booklet heading, and nothing else of the paper's own header
        heads = re.findall(r'<h2 class="key-paper">([^<]*)</h2>', inner)
        assert heads == [SET_HEADINGS[part]]
        assert "key-meta" not in inner
        # every in-key question once, in order, numbered as the paper numbers it
        assert [int(n) for n in _LABEL.findall(inner)] == _in_key_numbers(doc)
        # the same answers, style and options as the paper's own key
        assert inner == _own_key_as_in_set(doc)
    first = _in_key_numbers(docs[1])[0]
    assert first == 16  # Booklet B carries on from Booklet A


def test_one_title_block_from_the_covers():
    docs = _set("P6", 1)
    docs[0]["content"]["content"][0]["attrs"].update(school="Pandan Primary", exam="")
    docs[2]["content"]["content"][0]["attrs"].update(exam="Preliminary Examination")
    html = _main(render_set_key_html("Set", [(d["title"], d) for d in docs]))
    assert html.count('<dl class="key-meta">') == 1
    meta = re.search(r'<dl class="key-meta">(.*?)</dl>', html).group(1)
    pairs = re.findall(r"<dt>(\w+)</dt><dd>([^<]*)</dd>", meta)
    assert pairs == [
        ("School", "Pandan Primary"),
        ("Level", "Primary 6"),
        ("Subject", "Mathematics"),
        ("Exam", "Preliminary Examination"),
    ]
    assert html.index("key-meta") < html.index('class="set-paper"')


def test_without_cover_lines_the_set_is_headed_by_its_title():
    docs = _set("P6", 2)
    for d in docs:
        d["content"]["content"][0]["attrs"].update(level="", subject="")
    html = _main(render_set_key_html("Term 3 set", [(d["title"], d) for d in docs]))
    assert '<h1 class="sheet-title">Term 3 set</h1>' in html
    assert "key-meta" not in html


def test_each_paper_keeps_its_own_style_and_left_out_questions():
    docs = _set("P6", 3)
    worked = with_key_style(copy.deepcopy(docs[2]), "worked")  # Paper 2 as worked solutions
    left_out = copy.deepcopy(docs[1])
    blocks = numbered_blocks(left_out)
    blocks[2]["attrs"]["in_key"] = False  # Q18 left out of Booklet B's key
    papers = [docs[0], left_out, worked]
    html = render_set_key_html("Set", [(d["title"], d) for d in papers])
    (_, a), (_, b), (_, p2) = _sections(html)
    assert "compact-key" in a and "compact-key" in b
    assert 18 not in [int(n) for n in _LABEL.findall(b)]
    assert [int(n) for n in _LABEL.findall(b)] == _in_key_numbers(left_out)
    # worked solutions: the full layout, numbered from 1 and never continuing Booklet B's count
    assert "compact-key" not in p2 and '<ol class="questions">' in p2
    assert [int(n) + 1 for n in _LI_NUMBER.findall(p2)] == _in_key_numbers(worked)
    assert '<h2 class="key-paper">Paper 2</h2>' in p2
    total = sum(b["attrs"]["question"]["question"]["total_marks"] for b in numbered_blocks(worked))
    assert f"Total: {total} marks" in p2


def test_the_set_key_flows_with_paper_2_on_a_new_page():
    html = render_set_key_html("Set", [(d["title"], d) for d in _set("P6", 4)])
    assert 'class="sheet answer-key set-key"' in html  # the key's numbered @page
    assert "data-paginate" not in _main(html)
    assert '.set-paper[data-part="paper_2"] { break-before: page;' in html


@pytest.mark.parametrize(
    "parts, order",
    [
        (["booklet_a", "booklet_b", "paper_2"], [0, 1, 2]),
        (["paper_2", None, "booklet_a", "booklet_b"], [2, 3, 0]),
    ],
)
def test_the_set_is_found_by_part_and_put_in_exam_order(parts, order):
    assert exam_set_order(parts) == order


def test_an_incomplete_set_is_refused_with_what_is_missing():
    with pytest.raises(ExamSetError) as e:
        exam_set_order(["booklet_a", None])
    assert e.value.code == "incomplete_set"
    assert e.value.parts == ["booklet_b", "paper_2"]
    assert e.value.message == (
        "This folder has no Booklet B or Paper 2. "
        "A set's answer key needs Booklet A, Booklet B and Paper 2."
    )


def test_two_of_a_part_is_ambiguous():
    with pytest.raises(ExamSetError) as e:
        exam_set_order(["booklet_a", "booklet_a", "booklet_b"])
    assert e.value.code == "ambiguous_set"  # reported before what is missing
    assert e.value.parts == ["booklet_a"]
    assert "more than one Booklet A." in e.value.message


def test_the_printed_set_key_numbers_its_pages_through_the_set():
    """Read back from Chromium's PDF: one page count for the whole set, Paper 2 starting a page."""
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader

    html = render_set_key_html("Set", [(d["title"], d) for d in _set("P6", 11)])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.wait_for_selector("html[data-paginated='true']", state="attached")
        pdf = page.pdf(format="A4", print_background=True)
        browser.close()
    pages = [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(pdf)).pages]
    assert len(pages) >= 3
    lines = [text.strip().splitlines() for text in pages]
    # Chromium's page-number margin box comes first in the extracted text
    assert [page[0].strip() for page in lines] == [str(n) for n in range(1, len(pages) + 1)]
    starts = [k for k, page in enumerate(lines) if page[1].strip() == "Paper 2"]
    assert len(starts) == 1 and starts[0] > 0
    assert "Paper 1 Booklet B" in "".join(pages[: starts[0]])
