"""P6b — the per-page tally boxes land on the page the paginator says, on the real Chromium PDF.

Ground truth is the PDF read back page by page: every question carries a unique marker word, the
paginator reports which `.pg` box it put each question in and what that page's tally says, and
the PDF must have exactly those pages with exactly those questions (and nothing lost).
"""

from __future__ import annotations

import io
import random
import re
from collections import Counter

import pytest
from documents import freeform_block, gen_block, make_doc, multipart_block, part_node
from exam_engine.render import inline_script_hashes, render_document_html
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

TALLY_MAIN = re.compile(r"<main [^>]*data-tally")


def _section(title: str, **attrs) -> dict:
    return {"type": "section", "attrs": {"title": title, "mode": "short", **attrs}}


def _freeform(marker: str, rng: random.Random, space: int | None, lines: int) -> dict:
    body = " ".join(["Ann bought some sweets and shared them equally among her friends."] * lines)
    node = freeform_block(f"{marker} {body}", marks=rng.randint(1, 5))
    if space is not None:
        node["attrs"]["space_mm"] = space
    return node


def make_paper(rng: random.Random, *, oversize: bool = False) -> dict:
    blocks: list[dict] = [_section("Section A")]
    n = rng.randint(8, 14)
    for i in range(1, n + 1):
        marker = f"QM{i:02d}"
        if i == n // 2:
            blocks.append(_section("Section B"))
        kind = rng.choice(["free", "free", "multi", "templated"])
        if kind == "free":
            blocks.append(_freeform(marker, rng, rng.choice([None, 20, 45, 90]), rng.randint(1, 5)))
        elif kind == "multi":
            parts = [
                part_node(f"{marker}{chr(97 + k)} work it out.", marks=rng.randint(1, 3))
                for k in range(rng.randint(2, 3))
            ]
            blocks.append(multipart_block(*parts, stem=f"{marker} A tank is 40 cm by 25 cm."))
        else:
            blocks.append(gen_block("ratio_medium", rng.randint(1, 500)))
    if oversize:
        # 250 mm of working space plus a long stem: taller than the 261 mm page.
        blocks.insert(len(blocks) // 2, _freeform("QM99", rng, 250, 12))
    return make_doc(*blocks)


def _words(pages: list[str]) -> Counter:
    return Counter(w for t in pages for w in t.split())


def _pdf_pages(pdf: bytes) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


_PAGES_JS = """
() => Array.from(document.querySelectorAll('.pg')).map((pg) => ({
  text: pg.innerText,
  tally: pg.querySelector('.tally-total')
    ? Number(pg.querySelector('.tally-total').textContent)
    : null,
  marks: Array.from(pg.querySelectorAll('[data-marks]'))
    .reduce((n, e) => n + Number(e.dataset.marks), 0),
}))
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _paginated(browser, html: str):
    page = browser.new_page()
    page.set_content(html, wait_until="load")
    page.wait_for_selector("html[data-paginated='true']", state="attached")
    return page


@pytest.mark.parametrize("seed", [20261029, 7, 1234])
def test_every_question_and_tally_is_on_the_page_the_paginator_chose(browser, seed):
    doc = make_paper(random.Random(seed))
    html = render_document_html("Spike", doc, mode="student")
    page = _paginated(browser, html)
    pages = page.evaluate(_PAGES_JS)
    pdf = page.pdf(format="A4", print_background=True)
    text = _pdf_pages(pdf)

    assert len(text) == len(pages) >= 2
    for k, pg in enumerate(pages):
        assert pg["tally"] == pg["marks"] > 0  # the box says what the page's questions add up to
        for marker in set(re.findall(r"QM\d\d", pg["text"])):
            assert marker in text[k], f"{marker} predicted on page {k + 1}"
        for other in set(re.findall(r"QM\d\d", " ".join(t for j, t in enumerate(text) if j != k))):
            assert other not in pg["text"] or other in text[k]
    assert not page.evaluate("document.documentElement.hasAttribute('data-pagination-warnings')")

    # nothing lost: the paginated print has every word the plain one has (clipping would drop some)
    plain = browser.new_page()
    plain.set_content(
        html.replace(
            '<main class="sheet worksheet" data-tally', '<main class="sheet worksheet"', 1
        ),
        wait_until="load",
    )
    plain.wait_for_selector("html[data-paginated='true']", state="attached")
    lost = _words(_pdf_pages(plain.pdf(format="A4", print_background=True))) - _words(text)
    assert sum(lost.values()) == 0, lost


def test_a_question_taller_than_the_page_is_clamped_not_clipped(browser):
    html = render_document_html(
        "Spike", make_paper(random.Random(5), oversize=True), mode="student"
    )
    page = _paginated(browser, html)
    assert page.evaluate("document.documentElement.hasAttribute('data-pagination-warnings')")
    text = " ".join(_pdf_pages(page.pdf(format="A4", print_background=True)))
    assert "QM99" in text and text.count("Ans:") >= 1
    # every question that has an Ans: line still prints it (the oversize one is not cut off)
    plain = browser.new_page()
    plain.set_content(
        html.replace(
            '<main class="sheet worksheet" data-tally', '<main class="sheet worksheet"', 1
        ),
        wait_until="load",
    )
    plain.wait_for_selector("html[data-paginated='true']", state="attached")
    base = " ".join(_pdf_pages(plain.pdf(format="A4", print_background=True)))
    assert text.count("Ans:") == base.count("Ans:")


def test_papers_without_a_marking_section_are_left_alone(browser):
    doc = make_doc(
        {"type": "section", "attrs": {"title": "A", "mode": "mcq"}}, freeform_block("QM01 x")
    )
    html = render_document_html("P", doc, mode="student")
    assert not TALLY_MAIN.search(html) and '<template id="tally-template"' not in html
    page = _paginated(browser, html)
    assert page.evaluate("document.querySelectorAll('.pg').length") == 0


def test_the_answer_key_never_gets_tally_boxes():
    html = render_document_html("P", make_paper(random.Random(3)), mode="key")
    assert not TALLY_MAIN.search(html)


def test_the_paginator_is_covered_by_the_csp_hashes():
    assert len(inline_script_hashes()) == 4
