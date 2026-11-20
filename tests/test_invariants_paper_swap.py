"""P8d — independent seed-sweep invariants for keep / swap / lock on a generated paper.

Every rule of P8a must still hold after any sequence of swaps and after "regenerate unlocked"
(re-derived from the *document* and the blueprint YAML, not from the swapper's internals):
valid and re-solved, sections at their targets, no blueprint twice, levels respected, each
slot's marks unchanged. On top: untouched blocks are byte-for-byte the same, ``like`` keeps the
topic, ``topic`` changes it whenever the content allows (and refuses only when it doesn't),
``own`` gives an empty placeholder with the slot's marks, and locked or teacher-written blocks
survive regeneration exactly.
"""

from __future__ import annotations

import json
import random
from collections import Counter

import pytest
import yaml
from exam_engine.blueprints.registry import content_dir
from exam_engine.document import paper_outline, validate_document
from exam_engine.paper import LEVELS, generate_paper, paper_templates
from exam_engine.paper_swap import (
    SwapNotPossible,
    paper_level,
    regenerate_unlocked,
    swap_question,
)
from exam_engine.pipeline import generate

SEEDS = range(1, 9)
TEMPLATES = [t["code"] for t in paper_templates()]
MODES = ("like", "topic", "own")


def _meta() -> dict[str, dict]:
    out = {}
    for path in (content_dir() / "blueprints").glob("*.yaml"):
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[d["code"]] = {
            "level": d["syllabus"]["level"],
            "topic": d["syllabus"]["topic"],
            "marks": d["marks"],
            "parts": len(d.get("parts") or []) or 1,  # P8c multi-part blueprints
            "rung": d["cognitive"]["difficulty"],
            # every type its answers can have (EXA-155: a list when some are in terms of π)
            "answer_types": set(
                (d.get("answer") or {}).get("types") or [(d.get("answer") or {}).get("type")]
            ),
        }
    return out


META = _meta()


def _blocks(doc):
    return doc["content"]["content"]


def _is_q(n) -> bool:
    return n["type"] in ("templatedQuestion", "freeformQuestion")


def _marks(n) -> int:
    if n["type"] == "templatedQuestion":
        return n["attrs"]["question"]["question"]["total_marks"]
    return n["attrs"]["marks"]


def _code(n):
    return n["attrs"]["question"]["blueprint_code"] if n["type"] == "templatedQuestion" else None


def _dump(n) -> str:
    return json.dumps(n, sort_keys=True)


def _check_rules(doc, level, where):
    """The P8a rules, re-derived from the document."""
    assert validate_document(doc) == [], where  # also re-solves every generated question
    for info in paper_outline(doc):
        assert info["marks"] == info["marks_target"], (where, info)
    codes = [_code(n) for n in _blocks(doc) if _code(n)]
    assert len(codes) == len(set(codes)), (where, Counter(codes))
    # EXA-154: a swap or a regenerate never gives a topic a third question in the paper
    topics = Counter(META[c]["topic"] for c in codes)
    assert max(topics.values(), default=0) <= 2, (where, topics)
    allowed = LEVELS[: LEVELS.index(level) + 1]
    mode = None
    for n in _blocks(doc):
        if n["type"] == "section":
            mode = n["attrs"]["mode"]
        if not _is_q(n):
            continue
        slot = n["attrs"]["slot"]
        assert slot["marks"] == _marks(n) and slot["kind"] == mode, where
        if n["type"] == "freeformQuestion":
            assert slot.get("placeholder") is True, where
        else:
            assert META[_code(n)]["level"] in allowed, where
            assert META[_code(n)]["marks"] == slot["marks"], where
            assert "placeholder" not in slot, where
            parts = n["attrs"]["question"]["question"]["parts"]
            assert len(parts) == META[_code(n)]["parts"], where
            if META[_code(n)]["parts"] > 1:  # P8c: multi-part only in structured, never a stand-in
                assert mode == "structured" and "stand_in" not in slot, where
            elif mode == "structured":
                assert slot.get("stand_in") is True and _marks(n) >= 2, where
            answers = [p["answer"] for p in parts]
            if mode == "mcq":  # P8b: an MCQ slot stays multiple choice, 4 options
                assert len(answers) == 1, where
                assert answers[0]["type"] == "choice", where
                assert len(answers[0]["options"]) == 4, where
            else:
                assert all(a["type"] != "choice" for a in answers), where


_RUNG = {"easy": 0, "medium": 1, "hard": 2}
# a number, or an answer in terms of π (EXA-155): multiple choice
_CONVERTIBLE = {"integer", "decimal", "quantity", "fraction", "expression"}


def _shortfall(code: str, marks: int) -> int:
    """EXA-146, written out from the rule: rungs below what a slot of ``marks`` should take
    (1 mark: any, 2 marks: medium or harder, 3+: hard)."""
    need = 0 if marks <= 1 else 1 if marks == 2 else 2
    return max(0, need - _RUNG[META[code]["rung"]])


def _could_fill(code: str, node, kind: str, level: str) -> bool:
    m = META[code]
    if m["level"] not in LEVELS[: LEVELS.index(level) + 1] or m["marks"] != _marks(node):
        return False
    if m["parts"] > 1:
        return kind == "structured"
    if m["answer_types"] == {"choice"}:  # asks multiple choice itself (EXA-147): mcq slots only
        return kind == "mcq"
    return kind != "mcq" or m["answer_types"] <= _CONVERTIBLE


def _possible_other_topic(doc, idx, level) -> bool:
    """Is there an unused, level-allowed blueprint with the slot's marks from another topic,
    no easier for the slot than the question it would replace (EXA-146)?"""
    node = _blocks(doc)[idx]
    used = {_code(n) for i, n in enumerate(_blocks(doc)) if i != idx and _code(n)}
    allowed = LEVELS[: LEVELS.index(level) + 1]
    topic = META[_code(node)]["topic"] if _code(node) else None
    floor = _shortfall(_code(node), _marks(node)) if _code(node) else 2
    return any(
        code not in used
        and m["level"] in allowed
        and m["marks"] == _marks(node)
        and m["topic"] != topic
        and _shortfall(code, _marks(node)) <= floor
        for code, m in META.items()
    )


def _check_rungs(doc, level, where, only=None):
    """EXA-146: a single-part question below its slot's rung only when no unused blueprint
    that could fill the slot has the rung (``only``: the block indexes to check). A blueprint
    whose topic has two other questions in the paper is excused: the cap (EXA-154)."""
    used = {_code(n) for n in _blocks(doc) if _code(n)}
    topics = Counter(META[c]["topic"] for c in used)
    mode = None
    for i, n in enumerate(_blocks(doc)):
        if n["type"] == "section":
            mode = n["attrs"]["mode"]
        code = _code(n)
        if not code or (only is not None and i not in only):
            continue
        marks = _marks(n)
        if _shortfall(code, marks) == 0:
            continue
        better = [
            c
            for c in META
            if c not in used
            and _could_fill(c, n, mode, level)
            and _shortfall(c, marks) < _shortfall(code, marks)
            and topics[META[c]["topic"]] - (META[c]["topic"] == META[code]["topic"]) < 2
        ]
        assert not better, (where, i, code, better)


def _possible_any(doc, idx, level) -> bool:
    used = {_code(n) for i, n in enumerate(_blocks(doc)) if i != idx and _code(n)}
    allowed = LEVELS[: LEVELS.index(level) + 1]
    marks = _marks(_blocks(doc)[idx])
    return any(
        c not in used and m["level"] in allowed and m["marks"] == marks for c, m in META.items()
    )


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("code", TEMPLATES)
def test_any_sequence_of_swaps_keeps_every_rule(code, level):
    for seed in SEEDS:
        doc, _ = generate_paper(code, level, seed)
        layout = [_marks(n) if _is_q(n) else n["type"] for n in _blocks(doc)]
        rng = random.Random(seed)
        for idx, node in enumerate(list(_blocks(doc))):
            if not _is_q(node):
                continue
            mode = rng.choice(MODES)
            node = _blocks(doc)[idx]
            where = f"{code} {level} seed={seed} #{idx} {mode}"
            kind = node["attrs"]["slot"]["kind"]
            placeholder = node["type"] == "freeformQuestion"
            try:
                new, report = swap_question(doc, node["attrs"]["block_id"], mode, seed * 100 + idx)
            except SwapNotPossible:
                if kind != "mcq":  # P8b decides what fits an MCQ slot
                    if mode == "own":
                        assert placeholder, where
                    elif mode == "topic":
                        assert not _possible_other_topic(doc, idx, level), where
                    else:
                        assert placeholder and not _possible_any(doc, idx, level), where
                continue
            before, after = _blocks(doc), _blocks(new)
            # only the swapped block changed; everything else is byte-for-byte the same
            assert len(before) == len(after), where
            for i, (a, b) in enumerate(zip(before, after, strict=True)):
                if i != idx:
                    assert _dump(a) == _dump(b), where
            out = after[idx]
            assert out["attrs"]["block_id"] == node["attrs"]["block_id"], where
            assert _marks(out) == _marks(node), where  # the slot's marks are kept
            assert report["marks"] == _marks(node), where
            if mode != "own" and not placeholder:  # EXA-146: never an easier rung for the slot
                assert _shortfall(_code(out), _marks(out)) <= _shortfall(
                    _code(node), _marks(node)
                ), where
            if mode != "own" and placeholder:  # a placeholder gets the best rung left
                _check_rungs(new, level, where, only={idx})
            if mode == "own":
                assert out["type"] == "freeformQuestion", where
                assert out["attrs"]["slot"]["placeholder"] is True, where
                assert out["content"] == [{"type": "paragraph"}], where
            else:
                assert out["type"] == "templatedQuestion", where
                if mode == "like" and not placeholder:
                    assert META[_code(out)]["topic"] == META[_code(node)]["topic"], where
                    if _code(out) == _code(node):  # a new seed: visibly another question
                        assert (
                            out["attrs"]["question"]["parameters"]
                            != node["attrs"]["question"]["parameters"]
                        ), where
                if mode == "topic" and not placeholder:
                    assert META[_code(out)]["topic"] != META[_code(node)]["topic"], where
            doc = new
        where = f"{code} {level} seed={seed}"
        _check_rules(doc, level, where)
        assert [_marks(n) if _is_q(n) else n["type"] for n in _blocks(doc)] == layout, where


def _teacher_paper(code, level, seed):
    """A generated paper the teacher has worked on: some questions locked, one placeholder
    started, one generated question replaced by a free-form question they wrote."""
    doc, _ = generate_paper(code, level, seed)
    rng = random.Random(f"teacher{seed}")
    qs = [i for i, n in enumerate(_blocks(doc)) if _is_q(n)]
    for i in rng.sample(qs, k=len(qs) // 3):
        _blocks(doc)[i]["attrs"]["locked"] = True
    written = [i for i in qs if _blocks(doc)[i]["type"] == "freeformQuestion"]
    if written:
        _blocks(doc)[written[0]]["content"] = [
            {"type": "paragraph", "content": [{"type": "text", "text": "My own question."}]}
        ]
    generated = [i for i in qs if _blocks(doc)[i]["type"] == "templatedQuestion"]
    if generated:  # "Write my own", then written: a placeholder with something in it
        n = _blocks(doc)[generated[-1]]
        slot = n["attrs"]["slot"]
        _blocks(doc)[generated[-1]] = {
            "type": "freeformQuestion",
            "attrs": {
                "block_id": n["attrs"]["block_id"],
                "marks": _marks(n),
                "slot": {"marks": slot["marks"], "kind": slot["kind"], "placeholder": True},
            },
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Mine."}]}],
        }
    return doc


def _kept(n) -> bool:
    if not _is_q(n):
        return True
    if n["attrs"].get("locked"):
        return True
    if n["type"] == "templatedQuestion":
        return False
    slot = n["attrs"].get("slot") or {}
    empty = all(not c.get("content") for c in n["content"])
    return not (slot.get("placeholder") and empty)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("code", TEMPLATES)
def test_regenerate_keeps_locked_and_teacher_work_and_every_rule(code, level):
    for seed in SEEDS:
        doc = _teacher_paper(code, level, seed)
        where = f"{code} {level} seed={seed}"
        new, report = regenerate_unlocked(doc, level, seed)
        before, after = _blocks(doc), _blocks(new)
        assert len(before) == len(after), where
        kept = 0
        for a, b in zip(before, after, strict=True):
            if _kept(a):
                assert _dump(a) == _dump(b), where  # untouched, byte for byte
                kept += _is_q(a)
            else:
                assert _marks(a) == _marks(b), where
                assert a["attrs"]["block_id"] == b["attrs"]["block_id"], where
                assert not b["attrs"].get("locked"), where
        assert report["kept"] == kept, where
        _check_rules(new, level, where)
        refilled = {i for i, a in enumerate(before) if not _kept(a)}
        _check_rungs(new, level, where, only=refilled)
        assert json.dumps(regenerate_unlocked(doc, level, seed)[0]) == json.dumps(new), where


def test_regenerate_never_touches_a_hand_written_or_bank_question():
    doc, _ = generate_paper("p2", "P6", 4)
    blocks = _blocks(doc)
    i = next(i for i, n in enumerate(blocks) if n["type"] == "templatedQuestion")
    blocks[i] = {
        "type": "freeformQuestion",
        "attrs": {"block_id": "mine_0001", "marks": _marks(blocks[i])},
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Mine."}]}],
    }
    j = next(i for i, n in enumerate(blocks) if n["type"] == "templatedQuestion")
    blocks[j]["attrs"]["question"]["source_type"] = "sourced"  # stands for a bank question
    new, report = regenerate_unlocked(doc, "P6", 1)
    assert _dump(_blocks(new)[i]) == _dump(blocks[i])
    assert _dump(_blocks(new)[j]) == _dump(blocks[j])
    assert report["kept"] == 2


@pytest.mark.parametrize("level", ["P5", "P6"])
def test_regenerating_a_paper_2_keeps_two_questions_a_topic_at_most(level):
    """EXA-154: with four blueprints a topic, a Paper 2 refilled from scratch could give a topic
    three questions (Section A, then two stand-ins); the cap holds for regenerate as it does
    for the generator."""
    for seed in range(1, 41):
        doc, _ = generate_paper("p2", level, seed)
        new, _ = regenerate_unlocked(doc, level, seed + 1000)
        _check_rules(new, level, f"p2 {level} seed={seed} regenerate")


def test_regenerate_with_everything_unlocked_gives_a_new_paper():
    doc, _ = generate_paper("p2", "P6", 4)
    new, report = regenerate_unlocked(doc, "P6", 99)
    assert report["kept"] == 0 and report["replaced"] == 17  # 5 short, 10 multi-part, 2 stand-ins
    assert json.dumps(new) != json.dumps(doc)
    _check_rules(new, "P6", "p2 regenerate")
    # P8c: like the generator, Section B takes every multi-part blueprint again
    assert sorted(c for c in map(_code, _blocks(new)) if c and META[c]["parts"] > 1) == MULTIPART


# a P6 paper takes P6 multi-part questions only (EXA-117)
MULTIPART = sorted(c for c, m in META.items() if m["parts"] > 1 and m["level"] == "P6")


def _multipart_in(doc) -> list[str]:
    return sorted(c for c in map(_code, _blocks(doc)) if c and META[c]["parts"] > 1)


@pytest.mark.parametrize("seed", range(1, 13))
def test_a_random_walk_on_paper_2_keeps_multipart_in_section_b_and_every_rule(seed):
    """P8c x P8d: swaps of every mode and regenerates, in a seeded random order, on a P6
    Paper 2. Totals stay exact, nothing repeats, multi-part questions stay in Section B (never a
    stand-in), and "like" on a multi-part question keeps it multi-part."""
    doc, _ = generate_paper("p2", "P6", seed)
    assert _multipart_in(doc) == MULTIPART
    rng = random.Random(f"walk{seed}")
    for step in range(30):
        where = f"p2 P6 seed={seed} step={step}"
        if rng.random() < 0.15:
            for n in _blocks(doc):  # lock a few, regenerate the rest
                if _is_q(n) and rng.random() < 0.3:
                    n["attrs"]["locked"] = True
            doc, _ = regenerate_unlocked(doc, "P6", rng.randrange(1000))
            for n in _blocks(doc):
                if _is_q(n):
                    n["attrs"].pop("locked", None)
            _check_rules(doc, "P6", where)
            continue
        qs = [n for n in _blocks(doc) if _is_q(n)]
        node = rng.choice(qs)
        mode = rng.choice(MODES)
        try:
            new, _ = swap_question(doc, node["attrs"]["block_id"], mode, rng.randrange(1000))
        except SwapNotPossible:
            continue
        out = next(
            n for n in _blocks(new) if n["attrs"].get("block_id") == node["attrs"]["block_id"]
        )
        if mode == "like" and _code(node) and META[_code(node)]["parts"] > 1:
            assert META[_code(out)]["parts"] > 1, where  # another multi-part, or a new seed
        doc = new
        _check_rules(doc, "P6", where)


def test_a_freed_structured_slot_is_refilled_with_the_multipart_question_first():
    doc, _ = generate_paper("p2", "P6", 1)
    mp = next(n for n in _blocks(doc) if _code(n) == "speed_structured")
    bid = mp["attrs"]["block_id"]
    own, _ = swap_question(doc, bid, "own", 1)  # "write my own" frees speed_structured
    filled, report = swap_question(own, bid, "like", 2)
    assert report["blueprint"] == "speed_structured"
    out = next(n for n in _blocks(filled) if n["attrs"].get("block_id") == bid)
    assert "stand_in" not in out["attrs"]["slot"]
    _check_rules(filled, "P6", "refill")


def test_multipart_never_goes_into_short_or_mcq_slots():
    for code in TEMPLATES:
        doc, _ = generate_paper(code, "P6", 3)
        for n in _blocks(doc):
            if n["type"] == "templatedQuestion" and n["attrs"]["slot"]["kind"] != "structured":
                for mode in ("like", "topic"):
                    try:
                        new, _ = swap_question(doc, n["attrs"]["block_id"], mode, 7)
                    except SwapNotPossible:
                        continue
                    assert all(
                        META[c]["parts"] == 1
                        for c, m in zip(map(_code, _blocks(new)), _blocks(new), strict=True)
                        if c and m["attrs"]["slot"]["kind"] != "structured"
                    )


# ---------------------------------------------------------------------------
# Edge cases and refusals
# ---------------------------------------------------------------------------


def _first(doc, pred):
    return next(n for n in _blocks(doc) if pred(n))


def test_swaps_are_deterministic_and_leave_the_input_alone():
    doc, _ = generate_paper("p2", "P6", 2)
    snapshot = json.dumps(doc, sort_keys=True)
    bid = _first(doc, lambda n: n["type"] == "templatedQuestion")["attrs"]["block_id"]
    a = swap_question(doc, bid, "topic", 5)
    b = swap_question(doc, bid, "topic", 5)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert json.dumps(doc, sort_keys=True) == snapshot


def test_a_placeholder_is_filled_by_like_and_topic_when_content_allows():
    # P5 Paper 2 is full since its multi-part questions (EXA-117); a placeholder the teacher
    # makes of one in Section B is filled again with the multi-part question it freed ...
    doc, _ = generate_paper("p2", "P5", 1)
    assert not any(n["type"] == "freeformQuestion" for n in _blocks(doc))
    mp = _first(doc, lambda n: bool(_code(n)) and META[_code(n)]["parts"] > 1)
    bid = mp["attrs"]["block_id"]
    doc, _ = swap_question(doc, bid, "own", 1)
    new, report = swap_question(doc, bid, "like", 1)
    assert report["blueprint"] == _code(mp)
    _check_rules(new, "P5", "refilled")
    # ... P5 Booklet B fills its 2-mark slots (EXA-154), and a 2-mark placeholder the
    # teacher makes there is filled again from the blueprints left
    doc, _ = generate_paper("p1_booklet_b", "P5", 1)
    used = _first(doc, lambda n: n["type"] == "templatedQuestion" and _marks(n) == 2)
    doc, _ = swap_question(doc, used["attrs"]["block_id"], "own", 1)
    ph = _first(doc, lambda n: n["type"] == "freeformQuestion" and n["attrs"]["slot"]["marks"] == 2)
    new, _ = swap_question(doc, ph["attrs"]["block_id"], "like", 1)
    filled = _first(new, lambda n: n["attrs"].get("block_id") == ph["attrs"]["block_id"])
    assert filled["type"] == "templatedQuestion" and _marks(filled) == 2
    _check_rules(new, "P5", "filled")

    # P6 Booklet A is full since P8e batch 3 (EXA-145); a 1-mark placeholder the teacher
    # makes is filled again with an unused 1-mark blueprint, still as multiple choice
    doc, _ = generate_paper("p1_booklet_a", "P6", 1)
    used = _first(doc, lambda n: n["type"] == "templatedQuestion" and _marks(n) == 1)
    doc, _ = swap_question(doc, used["attrs"]["block_id"], "own", 1)
    ph = _first(doc, lambda n: n["type"] == "freeformQuestion" and n["attrs"]["slot"]["marks"] == 1)
    new, report = swap_question(doc, ph["attrs"]["block_id"], "like", 1)
    filled = _first(new, lambda n: n["attrs"].get("block_id") == ph["attrs"]["block_id"])
    assert filled["type"] == "templatedQuestion" and _marks(filled) == 1
    assert filled["attrs"]["slot"] == {"marks": 1, "kind": "mcq"}
    assert filled["attrs"]["question"]["question"]["parts"][0]["answer"]["type"] == "choice"
    assert report["placeholder"] is False and report["blueprint"] == _code(filled)
    _check_rules(new, "P6", "filled")


def test_refusals_say_why():
    doc, _ = generate_paper("p1_booklet_b", "P6", 1)
    last = [n for n in doc["content"]["content"] if n["type"] == "templatedQuestion"][-1]
    doc, _ = swap_question(doc, last["attrs"]["block_id"], "own", 1)  # a placeholder
    q = _first(doc, lambda n: n["type"] == "templatedQuestion")
    ph = _first(doc, lambda n: n["type"] == "freeformQuestion")
    with pytest.raises(KeyError):
        swap_question(doc, "nope_1234", "like", 1)
    with pytest.raises(ValueError):
        swap_question(doc, q["attrs"]["block_id"], "sideways", 1)
    with pytest.raises(SwapNotPossible, match="already"):
        swap_question(doc, ph["attrs"]["block_id"], "own", 1)
    q["attrs"]["locked"] = True
    with pytest.raises(SwapNotPossible, match="locked"):
        swap_question(doc, q["attrs"]["block_id"], "like", 1)
    ph["content"] = [{"type": "paragraph", "content": [{"type": "text", "text": "Mine"}]}]
    with pytest.raises(SwapNotPossible, match="started writing"):
        swap_question(doc, ph["attrs"]["block_id"], "like", 1)
    ph["attrs"]["slot"] = None
    del ph["attrs"]["slot"]
    with pytest.raises(SwapNotPossible, match="Only generated"):
        swap_question(doc, ph["attrs"]["block_id"], "like", 1)


def test_a_hand_added_question_is_swapped_by_its_marks_and_stays_slotless():
    doc, _ = generate_paper("p2", "P6", 6)
    q = _first(doc, lambda n: n["type"] == "templatedQuestion")
    del q["attrs"]["slot"]
    new, _ = swap_question(doc, q["attrs"]["block_id"], "topic", 3)
    out = _first(new, lambda n: n["attrs"].get("block_id") == q["attrs"]["block_id"])
    assert "slot" not in out["attrs"] and _marks(out) == _marks(q)
    assert META[_code(out)]["topic"] != META[_code(q)]["topic"]
    assert validate_document(new) == []


def test_position_attributes_survive_a_swap():
    doc, _ = generate_paper("p2", "P6", 6)
    q = _first(doc, lambda n: n["type"] == "templatedQuestion")
    q["attrs"].update(space_mm=40, in_key=False, remark="from last year", ans_unit="cm")
    new, _ = swap_question(doc, q["attrs"]["block_id"], "like", 3)
    out = _first(new, lambda n: n["attrs"].get("block_id") == q["attrs"]["block_id"])
    assert (out["attrs"]["space_mm"], out["attrs"]["in_key"], out["attrs"]["remark"]) == (
        40,
        False,
        "from last year",
    )
    assert "ans_unit" not in out["attrs"]  # the old answer's unit isn't the new one's


def test_the_paper_level_comes_from_the_cover_or_the_questions():
    p5, _ = generate_paper("p2", "P5", 1)
    assert paper_level(p5) == "P5"
    p5["content"]["content"] = p5["content"]["content"][1:]  # no cover: from its questions
    assert paper_level(p5) == "P5"
    assert paper_level({"content": {"type": "doc", "content": []}}) == "P6"
    # a P5 paper never gets a P6 question by swapping
    for n in list(_blocks(p5)):
        if n["type"] == "templatedQuestion":
            try:
                new, _ = swap_question(p5, n["attrs"]["block_id"], "topic", 1)
            except SwapNotPossible:
                continue
            assert all(META[_code(m)]["level"] == "P5" for m in _blocks(new) if _code(m))


@pytest.mark.parametrize("level", LEVELS)
def test_booklet_a_stays_multiple_choice_through_swaps_and_regenerate(level):
    """Every swap mode and "regenerate unlocked" on Booklet A: each MCQ-section question is
    still four-option multiple choice and engine-proven (validate_document re-solves it)."""
    filled = 0
    for seed in SEEDS:
        doc, _ = generate_paper("p1_booklet_a", level, seed)
        for mode in ("like", "topic"):
            for n in list(_blocks(doc)):
                if not _is_q(n):
                    continue
                try:
                    doc, _ = swap_question(doc, n["attrs"]["block_id"], mode, seed)
                except SwapNotPossible:
                    continue
                filled += 1
        _check_rules(doc, level, f"booklet A {level} seed={seed} swaps")
        new, _ = regenerate_unlocked(doc, level, seed)
        _check_rules(new, level, f"booklet A {level} seed={seed} regenerate")
        assert any(n["type"] == "templatedQuestion" for n in _blocks(new))
    assert filled > len(SEEDS)  # swaps really happened (and placeholders were filled)


def test_a_bank_question_is_never_swapped():
    doc, _ = generate_paper("p2", "P6", 4)
    q = _first(doc, lambda n: n["type"] == "templatedQuestion")
    q["attrs"]["question"]["source_type"] = "sourced"  # stands for a bank question
    for mode in ("like", "topic", "own"):
        with pytest.raises(SwapNotPossible, match="bank"):
            swap_question(doc, q["attrs"]["block_id"], mode, 1)


def test_the_cover_level_wins_over_the_requested_one():
    p5, _ = generate_paper("p2", "P5", 2)
    assert paper_level(p5, "P6") == "P5"
    new, _ = regenerate_unlocked(p5, "P6", 3)
    assert all(META[_code(n)]["level"] == "P5" for n in _blocks(new) if _code(n))
    p5["content"]["content"] = p5["content"]["content"][1:]  # no cover: the request decides
    assert paper_level(p5, "P6") == "P6"
    with pytest.raises(ValueError):
        paper_level(p5, "P4")


def _hand_add(doc: dict, code: str, block_id: str) -> None:
    """Add a generated ``code`` question after the paper's last question, as a teacher adding
    one by hand would (no slot)."""
    blocks = doc["content"]["content"]
    last = max(i for i, n in enumerate(blocks) if _is_q(n))
    q = {
        "type": "templatedQuestion",
        "attrs": {"block_id": block_id, "question": generate(code, 1)},
    }
    blocks.insert(last + 1, q)


def _use_up_two_mark_mediums(doc: dict) -> None:
    """Hand-add every P5 single-part 2-mark medium the paper does not use, so a swap can only
    find easy ones (P5 has eleven such blueprints for ten Booklet B slots since EXA-144)."""
    used = {_code(n) for n in _blocks(doc) if _is_q(n)}
    for code, m in sorted(META.items()):
        if (
            code not in used
            and m["level"] == "P5"
            and m["marks"] == 2
            and m["parts"] == 1
            and m["rung"] == "medium"
        ):
            _hand_add(doc, code, f"used-{code}")
    assert validate_document(doc) == []


def test_a_swap_never_trades_a_question_for_an_easier_rung():
    """EXA-146: a P5 Booklet B fills its ten 2-mark slots with medium blueprints (EXA-154,
    147, 148). With every other 2-mark medium taken (here by hand: grid_area, EXA-144, is an
    eleventh), "another topic" on a medium question would only find easy ones, so it is
    refused; "like" on a medium question keeps its rung."""
    doc, _ = generate_paper("p1_booklet_b", "P5", 3)
    two = [n for n in _blocks(doc) if _is_q(n) and _marks(n) == 2]
    medium = [n for n in two if META[_code(n)]["rung"] != "easy"]
    easy = [n for n in two if META[_code(n)]["rung"] == "easy"]
    assert len(medium) == 10 and not easy
    _use_up_two_mark_mediums(doc)
    for n in medium:
        with pytest.raises(SwapNotPossible, match="easier"):
            swap_question(doc, n["attrs"]["block_id"], "topic", 1)
        new, _ = swap_question(doc, n["attrs"]["block_id"], "like", 1)
        out = next(b for b in _blocks(new) if b["attrs"].get("block_id") == n["attrs"]["block_id"])
        assert META[_code(out)]["rung"] != "easy"


def test_another_topic_on_an_easy_two_marker_may_take_any_topic():
    """The other branch: on an easy 2-mark question "another topic" may take any other topic,
    even an easy one, as none is easier. Since EXA-147/148 a P5 Booklet B uses all ten 2-mark
    mediums, so no generated paper leaves an easy 2-marker with another topic free under the
    cap; here the teacher has added one by hand (and every other 2-mark medium, so none is
    left). Every 2-mark blueprint left is easy, so the
    swap succeeds only under the easy rule (the medium rule would refuse it as easier)."""
    doc, _ = generate_paper("p1_booklet_b", "P5", 3)
    _use_up_two_mark_mediums(doc)
    _hand_add(doc, "ratio_easy", "hand-added")
    assert validate_document(doc) == []
    new, report = swap_question(doc, "hand-added", "topic", 1)
    assert report["topic"] != "Ratio"
    out = next(b for b in _blocks(new) if b["attrs"].get("block_id") == "hand-added")
    assert META[_code(out)]["rung"] == "easy"
