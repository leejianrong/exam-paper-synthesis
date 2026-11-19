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
from documents import gen_block, make_doc
from exam_engine.document import (
    check_exam_set_covers,
    exam_set_order,
    in_key,
    number_from,
    numbered_blocks,
    paper_part,
    paper_part_source,
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
    # its own <ol class="questions"> resets the CSS counter, so Paper 2 counts 1, 2, 3, ...
    assert _LI_NUMBER.findall(p2) == [] and p2.count('<ol class="questions">') == 1
    assert _in_key_numbers(worked) == list(range(1, len(_in_key_numbers(worked)) + 1))
    assert '<h2 class="key-paper">Paper 2</h2>' in p2
    total = sum(b["attrs"]["question"]["question"]["total_marks"] for b in numbered_blocks(worked))
    assert f"Total: {total} marks" in p2


def _own_worked_key_as_in_set(doc: dict) -> str:
    """The paper's own worked-solutions key, its title bar replaced by the booklet heading and
    the total: what the set key must print for it, byte for byte."""
    own = _main(render_document_html(doc["title"], doc, mode="key"))
    body = own[own.index("</header>") + len("</header>\n") :].removesuffix("\n")
    total = re.search(r"Total: (\d+) marks", own).group(1)
    return (
        f'<h2 class="key-paper">{SET_HEADINGS[paper_part(doc)]}</h2>'
        f'<p class="key-total">Total: {total} marks</p>{body}'
    )


OPTIONS = [
    {"show_scheme": True, "show_marks": True, "one_mark_working": True},
    {"show_scheme": False, "show_marks": True, "one_mark_working": False},
]


@pytest.mark.parametrize("seed", [3, 6])
@pytest.mark.parametrize("options", OPTIONS)
def test_worked_and_optioned_keys_are_byte_for_byte_each_papers_own(seed, options):
    """Worked solutions (with and without M/A lines and the question) and school keys with
    non-default options, mixed in one set: each part is exactly the paper's own key."""
    a, b, p2 = (copy.deepcopy(d) for d in _set("P6", seed))
    a["settings"]["key_options"].update(options)  # school key, options changed
    b = with_key_style(b, "worked")
    b["settings"]["key_options"].update(show_scheme=options["show_scheme"], show_question=False)
    numbered_blocks(b)[1]["attrs"]["in_key"] = False  # Q17 left out: explicit numbers
    p2 = with_key_style(p2, "worked")
    html = render_set_key_html("Set", [(d["title"], d) for d in (a, b, p2)])
    (_, ka), (_, kb), (_, kp2) = _sections(html)
    assert ka == _own_key_as_in_set(a)
    assert kb == _own_worked_key_as_in_set(b)
    assert kp2 == _own_worked_key_as_in_set(p2)
    assert "counter-reset: q 17" in kb and 'counter-reset: q 16"' not in kb


def test_the_set_key_flows_with_paper_2_on_a_new_page():
    html = render_set_key_html("Set", [(d["title"], d) for d in _set("P6", 4)])
    assert 'class="sheet answer-key set-key"' in html  # the key's numbered @page
    assert "data-paginate" not in _main(html)
    assert '.set-paper[data-part="paper_2"] { break-before: page;' in html


def _cover(part, title=""):
    return (part, "cover", title or part)


@pytest.mark.parametrize(
    "papers, order",
    [
        ([_cover("booklet_a"), _cover("booklet_b"), _cover("paper_2")], [0, 1, 2]),
        (
            [_cover("paper_2"), (None, None, "Drill"), _cover("booklet_a"), _cover("booklet_b")],
            [2, 3, 0],
        ),
        # a title alone is enough when nothing better names the part
        ([_cover("booklet_a"), ("booklet_b", "title", "Booklet B"), _cover("paper_2")], [0, 1, 2]),
    ],
)
def test_the_set_is_found_by_part_and_put_in_exam_order(papers, order):
    assert exam_set_order(papers) == order


def test_a_cover_beats_a_title_that_only_looks_like_the_part():
    """A worksheet titled "Booklet A practice" doesn't stand in the way of the set's Booklet A."""
    papers = [
        ("booklet_a", "title", "Booklet A practice"),
        _cover("booklet_b"),
        _cover("booklet_a", "P6 Prelim A"),
        _cover("paper_2"),
    ]
    assert exam_set_order(papers) == [2, 1, 3]


def test_where_the_part_was_read():
    worksheet = make_doc(gen_block(), title="Booklet A practice")
    assert paper_part_source(worksheet) == ("booklet_a", "title")
    booklet_a = _set("P6", 1)[0]
    booklet_a["title"] = "Prelim, first booklet"  # renamed: the cover still says
    assert paper_part_source(booklet_a) == ("booklet_a", "cover")
    assert paper_part_source(make_doc(gen_block(), title="Fractions")) == (None, None)


def test_an_incomplete_set_is_refused_with_what_is_missing():
    with pytest.raises(ExamSetError) as e:
        exam_set_order([_cover("booklet_a"), (None, None, "Drill")])
    assert e.value.code == "incomplete_set"
    assert e.value.parts == ["booklet_b", "paper_2"]
    assert e.value.message == (
        "This folder has no Booklet B or Paper 2. "
        "A set's answer key needs Booklet A, Booklet B and Paper 2."
    )


@pytest.mark.parametrize("source", ["cover", "title"])
def test_two_equally_good_candidates_are_ambiguous_and_named(source):
    papers = [
        ("booklet_a", source, "Booklet A practice"),
        ("booklet_a", source, "P6 Booklet A"),
        _cover("booklet_b"),
    ]
    with pytest.raises(ExamSetError) as e:
        exam_set_order(papers)
    assert e.value.code == "ambiguous_set"  # reported before what is missing
    assert e.value.parts == ["booklet_a"]
    assert e.value.message == (
        "\u201cBooklet A practice\u201d and \u201cP6 Booklet A\u201d both look like Booklet A. "
        "Keep one Booklet A in the folder to make the set's answer key."
    )


def _covers(docs, **per_part):
    for doc, attrs in zip(docs, (per_part.get(k, {}) for k in ("a", "b", "p2")), strict=True):
        doc["content"]["content"][0]["attrs"].update(attrs)
    return docs


def test_papers_sharing_a_title_are_counted_not_listed_twice():
    papers = [_cover("booklet_a", "P6 Paper 1 Booklet A")] * 3 + [_cover("booklet_b")]
    with pytest.raises(ExamSetError) as e:
        exam_set_order(papers)
    assert e.value.message == (
        "Three papers titled \u201cP6 Paper 1 Booklet A\u201d all look like Booklet A. "
        "Keep one Booklet A in the folder to make the set's answer key."
    )


@pytest.mark.parametrize("level", ["P6", "p6", "Pri 6", "Pr. 6", "PRIMARY 6", " Primary  6 "])
def test_the_same_level_written_another_way_doesnt_clash(level):
    docs = _covers(_set("P6", 2), a={"level": level}, b={"level": "Primary 6"})
    check_exam_set_covers(docs)  # no error
    clash = _covers(_set("P6", 2), a={"level": level}, b={"level": "P5"})
    with pytest.raises(ExamSetError, match=r"but Booklet B is P5\."):
        check_exam_set_covers(clash)


def test_a_mixed_level_is_refused_naming_the_clash():
    docs = _covers(
        _set("P6", 2), a={"level": "Primary 5"}, b={"level": "Primary 6"}, p2={"level": "Primary 6"}
    )
    with pytest.raises(ExamSetError) as e:
        check_exam_set_covers(docs)
    assert e.value.code == "mixed_set"
    assert e.value.parts == ["booklet_a", "booklet_b"]
    assert e.value.message == (
        "Booklet A is Primary 5 but Booklet B is Primary 6. "
        "Make the covers match to print one answer key for the set."
    )


def test_a_mixed_school_is_refused_naming_the_clash():
    docs = _covers(_set("P6", 2), a={"school": "Example Primary"}, p2={"school": "Sample Primary"})
    with pytest.raises(ExamSetError) as e:
        check_exam_set_covers(docs)
    assert e.value.code == "mixed_set"
    assert e.value.parts == ["booklet_a", "paper_2"]
    assert e.value.message.startswith(
        "Booklet A is from Example Primary but Paper 2 is from Sample Primary."
    )


def test_empty_fields_case_and_spacing_dont_clash():
    docs = _covers(
        _set("P6", 2),
        a={"school": "Pandan Primary", "exam": ""},
        b={"school": "  pandan   PRIMARY "},
        p2={"exam": "Prelim"},
    )
    check_exam_set_covers(docs)  # no error


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
