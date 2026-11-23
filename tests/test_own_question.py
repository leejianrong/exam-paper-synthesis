"""EXA-90 — a teacher's own question saved to the bank and inserted back (engine)."""

from __future__ import annotations

import copy

import pytest
from documents import (
    freeform_block,
    image_node,
    make_doc,
    math_node,
    multipart_block,
    part_node,
    text,
)
from exam_engine import canonical, own_question
from exam_engine.canonical import CanonicalValidationError
from exam_engine.document import validate_document
from exam_engine.paper import generate_paper
from exam_engine.paper_swap import SwapNotPossible, bank_options, swap_from_bank
from exam_engine.render import render_document_html

PNG = ("image/png", b"\x89PNG-not-really")


def resolve(asset_id: str):
    return PNG if asset_id == "asset_0001" else None


def rich_multipart() -> dict:
    """Parts, an image, inline maths, Ans: units and written answers, all at once."""
    stem = {
        "type": "paragraph",
        "content": [text("Sample Primary's tank is "), math_node(r"\frac{3}{4}"), text(" full.")],
    }
    block = multipart_block(
        part_node("How many litres are in it?", marks=2, answer="45", ans_unit="ℓ", space_mm=40),
        part_node("How much more water fills it?", marks=1, answer="15 ℓ"),
        block_id="ffm_own1",
    )
    block["content"] = [stem, image_node(), *block["content"][1:]]
    block["attrs"]["remark"] = "From the term 2 review."
    return block


def single() -> dict:
    block = freeform_block("Round 4 567 to the nearest hundred.", marks=1, answer="4 600")
    block["attrs"].update({"ans_unit": "", "space_mm": 20, "slot": {"marks": 1, "kind": "short"}})
    return block


def save(block: dict, **kw) -> dict:
    return own_question.to_canonical(
        block, **{"topic": "Whole Numbers", "level": "P5", "difficulty": "easy", **kw}
    )


def printed(*blocks: dict) -> dict[str, str]:
    doc = make_doc(*blocks)
    assert validate_document(doc) == []
    return {
        m: render_document_html("Paper", doc, mode=m, assets=resolve)
        for m in ("student", "key", "full")
    }


@pytest.mark.parametrize("make", [rich_multipart, single])
def test_saved_then_inserted_prints_the_same_paper(make):
    block = make()
    obj = save(block)
    assert obj["freeform"]["content"] == block["content"]
    back = own_question.to_block(obj, block["attrs"]["block_id"])
    if "slot" in block["attrs"]:  # its place in the paper is not part of the question
        back["attrs"]["slot"] = block["attrs"]["slot"]
    assert printed(back) == printed(block)
    assert back["attrs"]["bank_id"] == obj["id"] and "bank_id" not in printed(back)["full"]


def test_insert_into_another_paper_under_a_new_id():
    obj = save(rich_multipart())
    other = freeform_block("Already here.", block_id="ff_other")
    a = own_question.to_block(obj, "ff_new1")
    b = own_question.to_block(obj, "ff_new2")
    doc = make_doc(other, a, b)
    assert validate_document(doc) == []
    html = render_document_html("Paper", doc, mode="key", assets=resolve)
    assert html.count("data:image/png;base64") == 2 and html.count("45") >= 2


def test_canonical_summary_and_metadata():
    obj = save(rich_multipart(), topic="Volume", level="P6", difficulty="hard")
    assert obj["source_type"] == "sourced" and obj["provenance"]["created_by"] == "teacher"
    assert obj["validation"] == {"status": "unverified", "checks": {"human_reviewed": False}}
    assert obj["syllabus"]["topic"] == "Volume" and obj["syllabus"]["strand"]
    assert obj["syllabus"]["level"] == "P6" and obj["cognitive"]["difficulty"] == "hard"
    q = obj["question"]
    assert q["stem"] == r"Sample Primary's tank is \(\frac{3}{4}\) full. [picture]"
    assert [p["label"] for p in q["parts"]] == ["a", "b"] and q["total_marks"] == 3
    assert q["parts"][0]["answer"] == {"type": "text", "text": "45"}
    assert obj["id"] == "own-ffm_own1"
    assert obj["freeform"]["attrs"]["remark"] == "From the term 2 review."


def test_paper_only_attributes_are_left_behind_and_marks_can_be_set():
    block = single()
    block["attrs"].update({"locked": True, "in_key": False})
    obj = save(block, marks=2)
    attrs = obj["freeform"]["attrs"]
    assert not {"slot", "locked", "in_key"} & set(attrs)
    assert attrs["marks"] == 2 and obj["question"]["total_marks"] == 2
    assert block["attrs"]["marks"] == 1  # the paper's block is untouched


def test_saving_again_finds_the_same_id_and_only_reuses_own_ids():
    obj = save(single())
    again = own_question.to_block(obj, "ff_elsewhere")
    assert save(again)["id"] == obj["id"]
    forged = single()
    forged["attrs"]["bank_id"] = "sourced:psle-2023-q4"
    assert save(forged)["id"] == "own-" + forged["attrs"]["block_id"]


@pytest.mark.parametrize(
    ("change", "kw", "why"),
    [
        (lambda b: b.update(content=[{"type": "paragraph"}]), {}, "Write the question"),
        (lambda b: b["attrs"].update(marks=None), {}, "marks"),
        (lambda b: None, {"topic": "Cookery"}, "Unknown topic"),
        (lambda b: None, {"level": "P4"}, "level"),
        (lambda b: b.update(type="templatedQuestion"), {}, "question you wrote"),
    ],
)
def test_not_savable(change, kw, why):
    block = single()
    change(block)
    with pytest.raises(own_question.NotSavable, match=why):
        save(block, **kw)


def test_load_gate_holds_the_block_and_the_summary_together():
    good = save(rich_multipart())
    canonical.load(copy.deepcopy(good))

    def broken(edit) -> list[str]:
        obj = copy.deepcopy(good)
        edit(obj)
        with pytest.raises(CanonicalValidationError) as e:
            canonical.load(obj)
        return e.value.errors

    assert broken(lambda o: o.update(freeform=None))
    assert broken(lambda o: o.update(source_type="generated"))
    assert broken(lambda o: o["provenance"].update(created_by="ingested"))
    assert any(
        e.startswith("question") for e in broken(lambda o: o["question"].update(total_marks=9))
    )
    assert any(
        e.startswith("question")
        for e in broken(lambda o: o["question"].update(parts=o["question"]["parts"][:1]))
    )
    bad_math = lambda o: o["freeform"]["content"][0]["content"].__setitem__(  # noqa: E731
        1, math_node(r"x \) y")
    )
    assert any(e.startswith("freeform") for e in broken(bad_math))
    assert any(e.startswith("freeform") for e in broken(lambda o: o["freeform"].pop("attrs")))


def test_topics_are_the_blueprints_own():
    names = [t["topic"] for t in own_question.topics()]
    assert names == sorted(names) and {"Ratio", "Fractions", "Whole Numbers"} <= set(names)
    assert all(t["strand"] for t in own_question.topics())


def _short_2(doc):
    return next(
        n
        for n in doc["content"]["content"]
        if n["type"].endswith("Question")
        and n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
    )


def test_swap_from_the_bank_puts_the_teachers_block_back():
    doc, _ = generate_paper("p2", "P6", 5)
    target = _short_2(doc)
    block = freeform_block("Find 15% of $80.", marks=2, answer="$12", block_id="ff_mine")
    obj = save(block, topic="Percentage", level="P6")
    assert obj in bank_options(doc, target["attrs"]["block_id"], [obj])

    out, report = swap_from_bank(doc, target["attrs"]["block_id"], obj)
    assert validate_document(out) == []
    placed = next(
        n
        for n in out["content"]["content"]
        if n["attrs"].get("block_id") == target["attrs"]["block_id"]
    )
    assert placed["type"] == "freeformQuestion" and placed["content"] == block["content"]
    assert placed["attrs"]["bank_id"] == obj["id"] and placed["attrs"]["slot"]["marks"] == 2
    assert report["bank_id"] == obj["id"] and report["locked"] is False

    # the same bank question can't go into the paper twice
    other = next(
        n
        for n in out["content"]["content"]
        if n["type"] == "templatedQuestion"
        and n["attrs"].get("slot") == {"marks": 2, "kind": "short"}
    )
    with pytest.raises(SwapNotPossible, match="already in this paper"):
        swap_from_bank(out, other["attrs"]["block_id"], obj)


def test_three_mark_own_question_does_not_fit_a_two_mark_place():
    doc, _ = generate_paper("p2", "P6", 5)
    obj = save(freeform_block("Long one.", marks=3, block_id="ff_three"))
    assert bank_options(doc, _short_2(doc)["attrs"]["block_id"], [obj]) == []


def _errors(obj: dict) -> list[str]:
    with pytest.raises(CanonicalValidationError) as e:
        canonical.load(obj)
    return e.value.errors


def test_an_empty_or_bare_block_is_refused():
    good = save(single())
    assert _errors({**good, "freeform": {}})
    assert _errors({**good, "freeform": {"type": "freeformQuestion", "attrs": {}}})


def test_the_summary_must_be_the_blocks_own():
    """A crafted object can't list one question in the bank and insert another."""
    good = save(rich_multipart())
    lying = copy.deepcopy(good)
    lying["question"]["parts"][0]["text"] = "A harmless question."
    assert any(e.startswith("question:") for e in _errors(lying))
    lying = copy.deepcopy(good)
    lying["question"]["parts"][0]["answer"]["text"] = "99"
    assert _errors(lying)


@pytest.mark.parametrize("key", ["slot", "locked", "in_key", "bank_id"])
def test_paper_attributes_are_refused_in_the_bank(key):
    obj = save(single())
    obj["freeform"]["attrs"][key] = {
        "slot": {"marks": 1, "kind": "short"},
        "locked": True,
        "in_key": False,
        "bank_id": "own-x",
    }[key]
    assert any(key in e for e in _errors(obj))


def test_own_ids_belong_to_teachers_questions_only():
    teacher = save(single())
    assert _errors({**teacher, "id": "sourced:psle-1"})
    imported = copy.deepcopy(teacher)
    imported.pop("freeform")
    imported["provenance"]["created_by"] = "ingested"
    assert any(e.startswith("id:") for e in _errors(imported))


def test_gate_errors_are_short():
    obj = save(rich_multipart())
    obj["freeform"]["content"][2]["content"] = [{"type": "nope"}]
    errors = _errors(obj)
    assert errors and all(len(e) < 200 for e in errors) and errors[0].startswith("freeform")


def test_swap_into_a_placeholder_keeps_its_space_and_remark_where_the_question_has_none():
    doc, _ = generate_paper("p2", "P6", 5)
    target = _short_2(doc)
    target["attrs"].update({"space_mm": 55, "remark": "Keep this place.", "in_key": False})
    plain = save(
        freeform_block("Find 15% of $80.", marks=2, block_id="ff_plain"), topic="Percentage"
    )
    out, _ = swap_from_bank(doc, target["attrs"]["block_id"], plain)
    placed = next(
        n
        for n in out["content"]["content"]
        if n["attrs"].get("block_id") == target["attrs"]["block_id"]
    )
    assert placed["attrs"]["space_mm"] == 55 and placed["attrs"]["remark"] == "Keep this place."
    assert placed["attrs"]["in_key"] is False

    spaced = freeform_block("Find 20% of $80.", marks=2, block_id="ff_spaced")
    spaced["attrs"].update({"space_mm": 30, "remark": "Mine."})
    out, _ = swap_from_bank(doc, target["attrs"]["block_id"], save(spaced, topic="Percentage"))
    placed = next(
        n
        for n in out["content"]["content"]
        if n["attrs"].get("block_id") == target["attrs"]["block_id"]
    )
    assert placed["attrs"]["space_mm"] == 30 and placed["attrs"]["remark"] == "Mine."
