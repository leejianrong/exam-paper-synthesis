"""P8a — independent seed-sweep invariants for one-click paper generation.

Re-derives every rule of docs/planning/editor/P8-SHAPING.md from the generated *document* (not
from the generator's report or internals): sections hit their targets, no blueprint repeats,
levels respected, every question engine-proven, fixed sections keep the real slot layout,
stand-ins add up, and the same seed gives the same paper.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest
import yaml
from exam_engine.blueprints.registry import content_dir
from exam_engine.document import paper_outline, validate_document
from exam_engine.paper import (
    LEVELS,
    generate_paper,
    paper_templates,
    template_document,
    unfilled_placeholders,
)

SEEDS = range(1, 41)
TEMPLATES = [t["code"] for t in paper_templates()]


def _blueprint_meta() -> dict[str, dict]:
    """Level and marks straight from the YAML (independent of the generator's pool)."""
    out = {}
    for path in (content_dir() / "blueprints").glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        out[data["code"]] = {
            "level": data["syllabus"]["level"],
            "marks": data["marks"],
            "parts": len(data.get("parts") or []) or 1,  # P8c multi-part blueprints
            "topic": data["syllabus"]["topic"],
            "answer_type": (data.get("answer") or {}).get("type"),
        }
    return out


META = _blueprint_meta()
MULTIPART = {
    level: [c for c, m in META.items() if m["parts"] > 1 and m["level"] in LEVELS[: i + 1]]
    for i, level in enumerate(LEVELS)
}


def _questions(doc):
    return [n for n in doc["content"]["content"] if n["type"].endswith("Question")]


def _marks(node) -> int:
    if node["type"] == "templatedQuestion":
        return node["attrs"]["question"]["question"]["total_marks"]
    return node["attrs"]["marks"]


def _by_section(doc):
    out, cur = [], None
    for n in doc["content"]["content"]:
        if n["type"] == "section":
            cur = (n["attrs"], [])
            out.append(cur)
        elif n["type"].endswith("Question"):
            assert cur is not None, "every generated question sits in a section"
            cur[1].append(n)
    return out


def test_templates_are_consistent():
    for t in paper_templates():
        for s in t["sections"]:
            assert sum(x["marks"] * x["count"] for x in s["slots"]) == s["marks_target"], (
                t["code"],
                s["title"],
            )
        assert validate_document(template_document(t["code"])) == []


@pytest.mark.parametrize("code", TEMPLATES)
def test_a_starter_paper_has_the_generated_papers_cover_without_a_level(code):
    """An empty template starts with the same cover a generated paper gets; the level is left
    for the teacher (an empty template has none), so swaps fall back to the request's level."""
    starter = template_document(code)["content"]["content"]
    generated = generate_paper(code, "P6", 1)[0]["content"]["content"]
    assert starter[0]["type"] == generated[0]["type"] == "coverPage"
    assert "level" not in starter[0]["attrs"]
    assert {**starter[0]["attrs"], "level": "Primary 6"} == generated[0]["attrs"]
    # then the blank back of the cover (EXA-140) and the sections
    assert starter[1] == generated[1] == {"type": "blankPage", "attrs": {"kind": "blank"}}
    assert [n["type"] for n in starter[2:]] == ["section"] * (len(starter) - 2)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("code", TEMPLATES)
def test_generated_papers_keep_every_rule(code, level):
    template = next(t for t in paper_templates() if t["code"] == code)
    allowed = set(LEVELS[: LEVELS.index(level) + 1])
    for seed in SEEDS:
        doc, report = generate_paper(code, level, seed)
        where = f"{code} {level} seed={seed}"

        # valid, and validate_document re-solves every generated question (engine-proven)
        assert validate_document(doc) == [], where
        assert doc["content"]["content"][0]["type"] == "coverPage", where

        # each section's marks equal its target (placeholders count), and its [n] print as on
        # real papers: in the header for MCQ and short answer, after the Ans: line in structured
        for info in paper_outline(doc):
            assert info["marks"] == info["marks_target"], (where, info)
            want = "answer" if info["mode"] == "structured" else "none"
            assert info["marks_placement"] == want, (where, info["title"])

        codes = [
            n["attrs"]["question"]["blueprint_code"]
            for n in _questions(doc)
            if n["type"] == "templatedQuestion"
        ]
        assert len(codes) == len(set(codes)), (where, Counter(codes))  # no repeats
        for c in codes:
            assert META[c]["level"] in allowed, (where, c)

        for (sec, nodes), tsec in zip(_by_section(doc), template["sections"], strict=True):
            for n in nodes:
                slot = n["attrs"]["slot"]
                assert slot["marks"] == _marks(n), where
                assert slot["kind"] == sec["mode"], where
                if n["type"] == "freeformQuestion":
                    assert slot.get("placeholder") is True, where
                else:
                    blueprint = n["attrs"]["question"]["blueprint_code"]
                    assert META[blueprint]["marks"] == slot["marks"], where
            if sec["mode"] == "structured":
                # P8c: real multi-part questions (no stand-in flag, every part present), then
                # single-part stand-ins of 2+ marks; placeholders 3-5 marks unless tiny
                multipart = []
                for n in nodes:
                    if n["type"] == "templatedQuestion":
                        blueprint = n["attrs"]["question"]["blueprint_code"]
                        parts = n["attrs"]["question"]["question"]["parts"]
                        assert len(parts) == META[blueprint]["parts"], where
                        if META[blueprint]["parts"] > 1:
                            assert "stand_in" not in n["attrs"]["slot"], where
                            multipart.append(blueprint)
                        else:
                            assert n["attrs"]["slot"]["stand_in"] is True, where
                            assert _marks(n) >= 2, where
                assert [_marks(n) for n in nodes] == sorted(_marks(n) for n in nodes), where
                # every multi-part blueprint the level allows is used before any stand-in
                # (today's three fit in any Section B: 14 marks of 45, 3 of ~12 slots)
                assert sorted(multipart) == sorted(MULTIPART[level]), where
                rep = next(s for s in report["sections"] if s["title"] == sec["title"])
                assert rep["multipart"] == len(multipart), where
                assert rep["stand_ins"] == rep["filled"] - len(multipart), where
            else:
                # multi-part blueprints never go in short-answer or MCQ sections
                for n in nodes:
                    if n["type"] == "templatedQuestion":
                        assert META[n["attrs"]["question"]["blueprint_code"]]["parts"] == 1
                # fixed sections keep the real paper's slot layout, in order
                want = [x["marks"] for x in tsec["slots"] for _ in range(x["count"])]
                assert [_marks(n) for n in nodes] == want, where
                if sec["mode"] == "mcq":  # P8b: multiple choice, or a placeholder
                    for n in nodes:
                        if n["type"] == "templatedQuestion":
                            ans = n["attrs"]["question"]["question"]["parts"][0]["answer"]
                            assert ans["type"] == "choice" and len(ans["options"]) == 4, where
                else:
                    for n in nodes:
                        if n["type"] == "templatedQuestion":
                            ans = n["attrs"]["question"]["question"]["parts"][0]["answer"]
                            assert ans["type"] != "choice", where

        # the report agrees with the document
        placeholders = [n for n in _questions(doc) if n["attrs"].get("slot", {}).get("placeholder")]
        assert report["placeholders"] == len(placeholders) == unfilled_placeholders(doc)
        assert report["placeholder_marks"] == sum(_marks(n) for n in placeholders)
        assert report["filled"] == len(codes)


@pytest.mark.parametrize("level", LEVELS)
def test_booklet_b_numbering_carries_on_from_booklet_a(level):
    """EXA-134: Paper 1 is one numbering across both booklets; Paper 2 starts again at 1."""
    for seed in SEEDS[:5]:
        a = generate_paper("p1_booklet_a", level, seed)[0]
        b = generate_paper("p1_booklet_b", level, seed)[0]
        p2 = generate_paper("p2", level, seed)[0]
        (sec_a,) = paper_outline(a)
        sec_b1, sec_b2 = paper_outline(b)  # 1-mark then 2-mark questions, as real papers (EXA-139)
        assert sec_a["first"] == 1 and sec_b1["first"] == sec_a["last"] + 1, (level, seed)
        assert (sec_b1["first"], sec_b1["last"], sec_b1["marks"]) == (16, 20, 5), (level, seed)
        assert (sec_b2["first"], sec_b2["last"], sec_b2["marks"]) == (21, 30, 20), (level, seed)
        assert paper_outline(p2)[0]["first"] == 1
        assert template_document("p1_booklet_b")["settings"] == b["settings"]


@pytest.mark.parametrize("code", TEMPLATES)
def test_the_same_seed_gives_the_same_paper_and_another_seed_another(code):
    a, _ = generate_paper(code, "P6", 11)
    b, _ = generate_paper(code, "P6", 11)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    others = {json.dumps(generate_paper(code, "P6", s)[0], sort_keys=True) for s in range(12, 17)}
    assert json.dumps(a, sort_keys=True) not in others


def test_topics_are_spread_when_choice_allows():
    # Paper 2 Section A takes five 2-mark questions; seven 2-mark P6 blueprints cover seven
    # topics, so the five must come from five different topics.
    for seed in SEEDS:
        doc, _ = generate_paper("p2", "P6", seed)
        sec_a = _by_section(doc)[0][1]
        topics = [n["attrs"]["question"]["syllabus"]["topic"] for n in sec_a]
        assert len(set(topics)) == len(topics) == 5, topics


_CONVERTIBLE = {"integer", "decimal", "quantity", "fraction"}  # a number: multiple choice


@pytest.mark.parametrize("level", LEVELS)
def test_booklet_a_fills_every_slot_and_spreads_topics(level):
    """EXA-145: P5 and P6 Booklet A have no placeholders, and replaying the fill from the
    document shows each question came from a least-used topic among the blueprints still
    free for its slot, so the new one-mark topics never crowd out an older one."""
    allowed = LEVELS[: LEVELS.index(level) + 1]
    for seed in SEEDS:
        doc, report = generate_paper("p1_booklet_a", level, seed)
        assert report["placeholders"] == unfilled_placeholders(doc) == 0, seed
        used: set[str] = set()
        counts: Counter[str] = Counter()
        one_mark_topics = set()
        for n in _questions(doc):  # a fixed section fills its slots in print order
            code = n["attrs"]["question"]["blueprint_code"]
            marks = META[code]["marks"]
            free = [
                c
                for c, m in META.items()
                if c not in used
                and m["level"] in allowed
                and m["marks"] == marks
                and m["parts"] == 1
                and m["answer_type"] in _CONVERTIBLE
            ]
            assert code in free, (seed, code)
            least = min(counts[META[c]["topic"]] for c in free)
            assert counts[META[code]["topic"]] == least, (seed, code, dict(counts))
            used.add(code)
            counts[META[code]["topic"]] += 1
            if marks == 1:
                one_mark_topics.add(META[code]["topic"])
        # every topic with a one-mark multiple-choice blueprint gets a one-mark question
        eligible = {
            m["topic"]
            for m in META.values()
            if m["level"] in allowed
            and m["marks"] == 1
            and m["parts"] == 1
            and m["answer_type"] in _CONVERTIBLE
        }
        assert one_mark_topics == eligible, (seed, eligible - one_mark_topics)


def test_what_todays_content_fills():
    """Regression anchor for the shaping doc's coverage table (changes when content grows)."""

    def fill(code, level):
        _, r = generate_paper(code, level, 1)
        return r["filled"], r["placeholders"]

    assert fill("p1_booklet_a", "P6") == (15, 0)  # 13 one-mark MCQ-able (P8e batch 3)
    assert fill("p1_booklet_a", "P5") == (15, 0)  # 12 one-mark at P5
    assert fill("p1_booklet_b", "P6") == (15, 0)
    assert fill("p1_booklet_b", "P5") == (13, 2)
    assert fill("p2", "P6") == (17, 0)  # Section B: 3 multi-part + 9 single-part stand-ins
    assert fill("p2", "P5") == (16, 3)  # Section B: 11 stand-ins, 3 placeholders (15 marks)


def test_unknown_template_and_level_are_refused():
    from exam_engine.paper import UnknownPaperTemplate

    with pytest.raises(UnknownPaperTemplate):
        generate_paper("p3", "P6", 1)
    with pytest.raises(ValueError):
        generate_paper("p2", "P4", 1)


def test_a_placeholder_counts_as_written_once_anything_is_in_it():
    from exam_engine.paper_swap import swap_question

    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
    # make three placeholders the teacher could write (content may fill every slot)
    for q in [n for n in _questions(doc) if n["type"] == "templatedQuestion"][:3]:
        doc, _ = swap_question(doc, q["attrs"]["block_id"], "own", 1)
    before = unfilled_placeholders(doc)
    phs = [n for n in _questions(doc) if n["attrs"].get("slot", {}).get("placeholder")]
    phs[0]["content"] = [
        {"type": "paragraph"},
        {
            "type": "freeformPart",
            "attrs": {"marks": phs[0]["attrs"]["marks"]},
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Find x."}]}],
        },
    ]
    phs[1]["content"] = [
        {"type": "paragraph", "content": [{"type": "math", "attrs": {"latex": "x"}}]}
    ]
    phs[2]["content"] = [{"type": "paragraph", "content": [{"type": "text", "text": "   "}]}]
    assert unfilled_placeholders(doc) == before - 2


def test_the_stand_in_plan_stays_fast_and_exact_as_content_grows():
    import time

    from exam_engine import paper
    from exam_engine.paper import Candidate

    class _F:
        used: set = set()
        pool = [
            Candidate(f"b{m}_{i}", "T", "P6", m, "constructed")
            for m in range(2, 9)
            for i in range(15)
        ]

    t = time.perf_counter()
    plan = paper._stand_in_plan(_F(), 45, 12)
    assert time.perf_counter() - t < 0.5
    assert sum(plan) == 45 and len(plan) == 12 and min(plan) >= 2
