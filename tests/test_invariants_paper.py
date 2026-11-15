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
        out[data["code"]] = {"level": data["syllabus"]["level"], "marks": data["marks"]}
    return out


META = _blueprint_meta()


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

        # each section's marks equal its target (placeholders count)
        for info in paper_outline(doc):
            assert info["marks"] == info["marks_target"], (where, info)

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
                # stand-ins: 2+ marks, single-part; placeholders 3-5 marks unless tiny
                for n in nodes:
                    if n["type"] == "templatedQuestion":
                        assert n["attrs"]["slot"]["stand_in"] is True, where
                        assert _marks(n) >= 2, where
                        assert len(n["attrs"]["question"]["question"]["parts"]) == 1, where
            else:
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


def test_what_todays_content_fills():
    """Regression anchor for the shaping doc's coverage table (changes when content grows)."""

    def fill(code, level):
        _, r = generate_paper(code, level, 1)
        return r["filled"], r["placeholders"]

    assert fill("p1_booklet_a", "P6") == (9, 6)  # 4 one-mark + 5 two-mark convertible
    assert fill("p1_booklet_a", "P5") == (9, 6)
    assert fill("p1_booklet_b", "P6") == (12, 3)
    assert fill("p1_booklet_b", "P5") == (9, 6)
    assert fill("p2", "P6") == (19, 0)
    assert fill("p2", "P5") == (10, 6)


def test_unknown_template_and_level_are_refused():
    from exam_engine.paper import UnknownPaperTemplate

    with pytest.raises(UnknownPaperTemplate):
        generate_paper("p3", "P6", 1)
    with pytest.raises(ValueError):
        generate_paper("p2", "P4", 1)


def test_a_placeholder_counts_as_written_once_anything_is_in_it():
    doc, _ = generate_paper("p1_booklet_b", "P6", 3)
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
