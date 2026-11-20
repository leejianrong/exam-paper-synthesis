"""EXA-90 — shared stems: a block of text and figures the next few questions all refer to.

The questions stay ordinary numbered blocks; the stem only prints a derived lead line
("Use the information below to answer Questions 12 and 13.") and its own content above them.
"""

from __future__ import annotations

import copy
import re

import pytest
from documents import (
    freeform_block,
    gen_block,
    image_node,
    make_doc,
    math_node,
    multipart_block,
    para,
    part_node,
    stem_block,
)
from exam_engine.document import (
    flag_wording,
    paper_outline,
    stem_groups,
    stem_sentence,
    total_marks,
    validate_document,
)
from exam_engine.render import render_document_html


def _section(title: str = "Section B", **attrs) -> dict:
    return {"type": "section", "attrs": {"title": title, **attrs}}


def _paper() -> dict:
    return make_doc(
        freeform_block("QA first", marks=1),
        stem_block(
            "STEMTEXT The table shows the cost of postage.",
            {"type": "paragraph", "content": [math_node(r"\frac{1}{2}")]},
            count=2,
        ),
        freeform_block("QB second", marks=2, answer="ANSB"),
        gen_block("ratio_medium", 3),
        freeform_block("QD fourth", marks=3),
    )


# --- numbering and validation ------------------------------------------------------------


@pytest.mark.parametrize(
    ("numbers", "want"),
    [
        ([], ""),
        ([4], "Use the information below to answer Question 4."),
        ([12, 13], "Use the information below to answer Questions 12 and 13."),
        ([3, 4, 5], "Use the information below to answer Questions 3 to 5."),
    ],
)
def test_the_lead_line_is_derived_from_the_numbers(numbers, want):
    assert stem_sentence(numbers) == want


def test_a_stem_covers_the_next_count_questions_and_numbering_continues():
    doc = _paper()
    assert validate_document(doc) == []
    assert stem_groups(doc) == {1: [2, 3]}
    doc["settings"] = {"number_from": 16}
    assert stem_groups(doc) == {1: [17, 18]}


def test_rich_text_between_questions_stays_in_the_group():
    doc = make_doc(stem_block(count=2), freeform_block("a"), para("note"), freeform_block("b"))
    assert stem_groups(doc) == {0: [1, 2]}


def test_a_section_or_another_stem_ends_a_group_early():
    doc = make_doc(
        stem_block(count=3),
        freeform_block("a"),
        _section(),
        freeform_block("b"),
        stem_block(count=5),
        freeform_block("c"),
    )
    assert validate_document(doc) == []
    assert stem_groups(doc) == {0: [1], 4: [3]}
    # a stem with nothing after it yet saves (the editor autosaves while it is being written)
    lone = make_doc(freeform_block("a"), stem_block(count=2))
    assert validate_document(lone) == [] and stem_groups(lone) == {1: []}


def test_marks_sections_and_totals_ignore_the_stem():
    with_stem = make_doc(_section(marks_target=6), *_paper()["content"]["content"])
    plain = copy.deepcopy(with_stem)
    plain["content"]["content"] = [
        b for b in plain["content"]["content"] if b["type"] != "groupStem"
    ]
    assert paper_outline(with_stem) == paper_outline(plain)
    assert total_marks(with_stem) == total_marks(plain)
    assert paper_outline(with_stem)[0]["first"] == 1 and paper_outline(with_stem)[0]["last"] == 4


@pytest.mark.parametrize(
    "bad",
    [
        {"count": 0},
        {"count": 21},
        {"count": "2"},
    ],
)
def test_the_schema_bounds_the_count(bad):
    doc = _paper()
    doc["content"]["content"][1]["attrs"].update(bad)
    assert any("count" in e for e in validate_document(doc))


def test_a_stem_needs_content_and_only_text_blocks():
    doc = _paper()
    doc["content"]["content"][1]["content"] = []
    assert validate_document(doc)
    doc["content"]["content"][1]["content"] = [freeform_block("nested")]
    assert validate_document(doc)


def test_a_stem_block_id_is_unique_across_blocks():
    doc = make_doc(stem_block(block_id="same1"), freeform_block("a", block_id="same1"))
    assert any("duplicate block id" in e for e in validate_document(doc))


def test_generated_questions_in_a_group_still_verify_and_keep_their_badge():
    doc = _paper()
    assert validate_document(doc) == []
    q = flag_wording(doc)["content"]["content"][3]["attrs"]["question"]
    assert q["validation"]["status"] == "pass"
    forged = copy.deepcopy(doc)
    forged["content"]["content"][3]["attrs"]["question"]["question"]["parts"][0]["answer"][
        "value"
    ] = 99999
    assert any("does not match" in e for e in validate_document(forged))


def test_an_older_document_without_stems_is_unaffected():
    doc = make_doc(freeform_block("a"), freeform_block("b"))
    doc["schema_version"] = "1.16.0"
    assert validate_document(doc) == [] and stem_groups(doc) == {}


# --- printing ----------------------------------------------------------------------------


def test_the_student_paper_prints_the_lead_line_and_stem_before_its_questions():
    html = render_document_html("P", _paper(), mode="student")
    lead = "Use the information below to answer Questions 2 and 3."
    assert lead in html
    assert (
        html.index("QA first") < html.index(lead) < html.index("STEMTEXT") < html.index("QB second")
    )
    stem = re.search(r'<div class="group-stem">.*?</div></div>', html).group()
    assert 'class="question' not in stem  # not numbered
    assert r"\frac{1}{2}" in stem  # equations print, typeset by KaTeX


def test_a_stem_image_prints():
    doc = make_doc(stem_block(image_node("asset_0042"), count=1), freeform_block("a"))
    html = render_document_html(
        "P", doc, mode="student", assets=lambda a: ("image/png", b"\x89PNG") if a else None
    )
    assert 'class="doc-image"' in html


def test_in_a_structured_section_the_stem_starts_the_page_not_its_question():
    doc = make_doc(
        _section(mode="structured"),
        freeform_block("QQAQ"),
        stem_block("QQSTEM", count=2),
        multipart_block(part_node("p1"), part_node("p2"), stem="QQBQ"),
        freeform_block("QQCQ"),
    )
    html = render_document_html("P", doc, mode="student")
    body = html[html.index('class="doc-body') :]
    assert 'class="group-stem own-page"' in body
    # the stem starts the page; its first question follows it there, the next one starts its own
    assert "own-page" not in body[body.index("QQSTEM") : body.index("QQBQ")]
    assert body.count("own-page") == 3  # the stem, QQCQ, and the section header


def test_the_full_key_prints_the_stem_above_the_first_question_it_keeps():
    doc = _paper()
    doc["settings"] = {"key_options": {"layout": "full", "show_question": True}}
    doc["content"]["content"][2]["attrs"]["in_key"] = False  # Q2 is left out of the key
    key = render_document_html("P", doc, mode="key")
    lead = "Use the information below to answer Questions 2 and 3."
    assert key.count(lead) == 1 and "QB second" not in key
    assert key.index(lead) < key.index("STEMTEXT")


def test_the_key_leaves_the_stem_out_when_it_hides_the_question_text():
    doc = _paper()
    doc["settings"] = {"key_options": {"layout": "full", "show_question": False}}
    assert "STEMTEXT" not in render_document_html("P", doc, mode="key")
    doc["settings"] = {"key_options": {"layout": "compact"}}
    key = render_document_html("P", doc, mode="key")
    assert "STEMTEXT" not in key and "ANSB" in key


def test_full_mode_prints_the_stem_once_in_the_paper_and_once_in_the_key():
    doc = _paper()
    doc["settings"] = {"key_options": {"layout": "full"}}
    assert render_document_html("P", doc, mode="full").count("STEMTEXT") == 2


# --- pagination: the stem stays on the page of its first question ------------------------


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


_WHERE_JS = """
() => {
  const pgs = Array.from(document.querySelectorAll('.pg'))
  const at = (sel) => pgs.findIndex((pg) => pg.querySelector(sel))
  const has = (word) => pgs.findIndex((pg) => pg.innerText.includes(word))
  return { stem: at('.group-stem'), first: has('QFIRST'), filler: has('QFILL2') }
}
"""


def test_the_stem_and_its_first_question_share_a_page(browser):
    moved = 0
    for space in range(40, 200, 10):
        doc = make_doc(
            _section(mode="short"),
            freeform_block("QFILL1 work it out.", marks=2),
            freeform_block("QFILL2 work it out.", marks=2),
            stem_block(*[f"STEMLINE {k} The table shows the cost of postage." for k in range(6)]),
            freeform_block("QFIRST the first.", marks=2),
            freeform_block("QSECOND the second.", marks=2),
        )
        doc["content"]["content"][1]["attrs"]["space_mm"] = 100
        doc["content"]["content"][2]["attrs"]["space_mm"] = space
        page = browser.new_page()
        page.set_content(render_document_html("P", doc, mode="student"), wait_until="load")
        page.wait_for_selector("html[data-paginated='true']", state="attached")
        where = page.evaluate(_WHERE_JS)
        page.close()
        assert where["stem"] == where["first"], (space, where)
        moved += where["stem"] > where["filler"]
    # some layouts had to carry the stem over to the next page with its question
    assert 0 < moved < len(range(40, 200, 10))
