"""EXA-33 (R6.4) — swap a paper's question for one from the owner's bank (engine).

Bank questions here are the fictional stand-in fixtures, re-labelled with the ids and topics a
test needs.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from exam_engine.document import paper_outline, validate_document
from exam_engine.paper import generate_paper
from exam_engine.paper_swap import (
    SwapNotPossible,
    bank_options,
    regenerate_unlocked,
    swap_from_bank,
    swap_question,
)
from exam_engine.pipeline import generate

SOURCED = Path(__file__).parent / "fixtures" / "sourced"


def bank_obj(fixture: str, obj_id: str, topic: str | None = None, reviewed=False) -> dict:
    obj = json.loads((SOURCED / f"{fixture}.json").read_text(encoding="utf-8"))
    obj["id"] = f"sourced:{obj_id}"
    if topic:
        obj["syllabus"]["topic"] = topic
    obj["validation"]["checks"]["human_reviewed"] = reviewed
    return obj


@pytest.fixture(scope="module")
def paper():
    doc, _ = generate_paper("p2", "P6", 5)
    return doc


def _questions(doc):
    return [n for n in doc["content"]["content"] if n["type"].endswith("Question")]


def _short_2(doc):
    """The first 2-mark short-answer question of the paper."""
    return next(
        n for n in _questions(doc) if n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
    )


def _topic(n):
    return n["attrs"]["question"]["syllabus"]["topic"]


def test_options_fit_the_slot_and_put_its_topic_first(paper):
    q = _short_2(paper)
    other = bank_obj("standin_chart_line", "other-topic", reviewed=True)  # 2 marks, Statistics
    same = bank_obj("standin_chart_pie", "same-topic", topic=_topic(q))
    wrong_marks = bank_obj("standin_chart_bar", "three-marks")  # 3 marks
    two_parts = bank_obj("standin_solid_tank", "two-parts")  # 4 marks, (a) and (b)
    choice = bank_obj("standin_cubestack_view", "choice")  # 1-mark multiple choice
    bank = [other, wrong_marks, same, two_parts, choice]
    ids = [o["id"] for o in bank_options(paper, q["attrs"]["block_id"], bank)]
    assert ids == [same["id"], other["id"]]


def test_reviewed_questions_come_before_unreviewed_ones_of_the_same_topic(paper):
    q = _short_2(paper)
    a = bank_obj("standin_chart_line", "a")
    b = bank_obj("standin_chart_pie", "b", reviewed=True)
    ids = [o["id"] for o in bank_options(paper, q["attrs"]["block_id"], [a, b])]
    assert ids == [b["id"], a["id"]]


def test_a_question_already_in_the_paper_is_not_offered(paper):
    q = _short_2(paper)
    obj = bank_obj("standin_chart_line", "used")
    doc, _ = swap_from_bank(paper, q["attrs"]["block_id"], obj)
    other = next(
        n
        for n in _questions(doc)
        if n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
        and n["attrs"]["block_id"] != q["attrs"]["block_id"]
    )
    assert bank_options(doc, other["attrs"]["block_id"], [obj]) == []
    with pytest.raises(SwapNotPossible, match="already in this paper"):
        swap_from_bank(doc, other["attrs"]["block_id"], obj)


def test_a_generated_bank_question_never_repeats_a_blueprint_of_the_paper(paper):
    q, other = _questions(paper)[0], _questions(paper)[1]
    twin = copy.deepcopy(other["attrs"]["question"])
    twin["id"] = "generated:twin"
    assert bank_options(paper, q["attrs"]["block_id"], [twin]) == []


def test_a_question_above_the_papers_level_is_refused():
    doc, _ = generate_paper("p2", "P5", 3)
    q = _short_2(doc)
    obj = bank_obj("standin_chart_line", "p6")  # a P6 question
    assert bank_options(doc, q["attrs"]["block_id"], [obj]) == []
    with pytest.raises(SwapNotPossible, match="P6 question"):
        swap_from_bank(doc, q["attrs"]["block_id"], obj)


def test_swapping_keeps_the_position_and_the_papers_totals(paper):
    q = _short_2(paper)
    q["attrs"]["space_mm"] = 40  # a layout choice the position keeps
    obj = bank_obj("standin_chart_line", "keep", reviewed=True)
    doc, report = swap_from_bank(paper, q["attrs"]["block_id"], obj)
    before = paper["content"]["content"]
    after = doc["content"]["content"]
    idx = next(i for i, n in enumerate(before) if n is q)
    assert [n for i, n in enumerate(after) if i != idx] == [
        n for i, n in enumerate(before) if i != idx
    ]
    new = after[idx]
    assert new["type"] == "templatedQuestion"
    assert new["attrs"]["block_id"] == q["attrs"]["block_id"]
    assert new["attrs"]["space_mm"] == 40
    assert new["attrs"]["slot"] == {"marks": 2, "kind": "short"}
    assert new["attrs"]["question"] == obj  # the bank's snapshot, as inserting it would be
    assert report == {
        "block_id": q["attrs"]["block_id"],
        "mode": "bank",
        "marks": 2,
        "bank_id": obj["id"],
        "topic": obj["syllabus"]["topic"],
        "placeholder": False,
        "locked": False,  # a sourced question is never refilled, so it needs no lock
    }
    assert [s["marks"] for s in paper_outline(doc)] == [s["marks"] for s in paper_outline(paper)]
    assert validate_document(doc) == []
    q["attrs"].pop("space_mm")


def test_a_multi_part_bank_question_fills_a_structured_slot_without_a_stand_in_flag(paper):
    q = next(n for n in _questions(paper) if n["attrs"].get("slot", {}).get("marks") == 4)
    obj = bank_obj("standin_solid_tank", "tank")
    assert [o["id"] for o in bank_options(paper, q["attrs"]["block_id"], [obj])] == [obj["id"]]
    doc, _ = swap_from_bank(paper, q["attrs"]["block_id"], obj)
    new = next(n for n in _questions(doc) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["attrs"]["slot"] == {"marks": 4, "kind": "structured"}


def test_an_empty_placeholder_can_be_filled_from_the_bank(paper):
    q = _short_2(paper)
    doc, _ = swap_question(paper, q["attrs"]["block_id"], "own", 1)
    obj = bank_obj("standin_chart_line", "fill")
    assert bank_options(doc, q["attrs"]["block_id"], [obj]) == [obj]
    out, _ = swap_from_bank(doc, q["attrs"]["block_id"], obj)
    new = next(n for n in _questions(out) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["type"] == "templatedQuestion"
    assert new["attrs"]["slot"] == {"marks": 2, "kind": "short"}


def test_locked_and_bank_questions_are_never_swapped(paper):
    q = _short_2(paper)
    obj = bank_obj("standin_chart_line", "x")
    locked = copy.deepcopy(paper)
    next(n for n in _questions(locked) if n["attrs"]["block_id"] == q["attrs"]["block_id"])[
        "attrs"
    ]["locked"] = True
    with pytest.raises(SwapNotPossible, match="locked"):
        bank_options(locked, q["attrs"]["block_id"], [obj])
    with pytest.raises(SwapNotPossible, match="locked"):
        swap_from_bank(locked, q["attrs"]["block_id"], obj)
    swapped, _ = swap_from_bank(paper, q["attrs"]["block_id"], obj)
    with pytest.raises(SwapNotPossible, match="from your bank"):
        swap_from_bank(swapped, q["attrs"]["block_id"], bank_obj("standin_chart_pie", "y"))


def test_a_question_that_does_not_fit_is_refused_with_a_reason(paper):
    q = _short_2(paper)
    with pytest.raises(SwapNotPossible, match="2-mark single-part"):
        swap_from_bank(paper, q["attrs"]["block_id"], bank_obj("standin_chart_bar", "big"))


def test_a_generated_bank_question_is_locked_so_regenerating_keeps_it(paper):
    q = _short_2(paper)
    obj = generate("rate_medium", 3)  # a 2-mark question of a topic the paper doesn't use
    assert bank_options(paper, q["attrs"]["block_id"], [obj]) == [obj]
    doc, report = swap_from_bank(paper, q["attrs"]["block_id"], obj)
    assert report["locked"] is True
    new = next(n for n in _questions(doc) if n["attrs"]["block_id"] == q["attrs"]["block_id"])
    assert new["attrs"]["locked"] is True
    regenerated, _ = regenerate_unlocked(doc, None, 9)
    kept = next(
        n for n in _questions(regenerated) if n["attrs"]["block_id"] == q["attrs"]["block_id"]
    )
    assert kept["attrs"]["question"]["id"] == obj["id"]
