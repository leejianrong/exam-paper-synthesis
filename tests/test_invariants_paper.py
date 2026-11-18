"""P8a — independent seed-sweep invariants for one-click paper generation.

Re-derives every rule of docs/planning/editor/P8-SHAPING.md from the generated *document* (not
from the generator's report or internals): sections hit their targets, no blueprint repeats,
levels respected, every question engine-proven, fixed sections keep the real slot layout,
stand-ins add up, and the same seed gives the same paper.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import cache

import pytest
import yaml
from exam_engine.blueprints.registry import content_dir
from exam_engine.document import paper_outline, validate_document
from exam_engine.paper import (
    LEVELS,
    SET_TOPIC_CAP,
    generate_paper,
    generate_set,
    paper_templates,
    set_fill_order,
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
            "rung": data["cognitive"]["difficulty"],
        }
    return out


META = _blueprint_meta()
SET_SEEDS = range(1, 31)


# The order a set's papers are filled in (EXA-153), written out: biggest slots first.
_FILL_ORDER = ["p2", "p1_booklet_b", "p1_booklet_a"]


def _topics_by_then(papers, code: str) -> Counter[str]:
    """A set's topics when ``code`` was filled: the papers filled before it, plus its own."""
    upto = _FILL_ORDER[: _FILL_ORDER.index(code) + 1]
    return _set_topics([papers[TEMPLATES.index(c)] for c in upto])


@cache
def _sets(level: str) -> dict[int, list[tuple[dict, dict]]]:
    """Exam sets (EXA-153): Booklet A, Booklet B and Paper 2, made as the wizard makes them."""
    return {s: generate_set(TEMPLATES, level, s) for s in SET_SEEDS}


def _set_topics(papers) -> Counter[str]:
    """Questions per topic over a whole set, counted from the documents."""
    return Counter(
        n["attrs"]["question"]["syllabus"]["topic"]
        for doc, _ in papers
        for n in _questions(doc)
        if n["type"] == "templatedQuestion"
    )


MULTIPART = {
    level: [c for c, m in META.items() if m["parts"] > 1 and m["level"] in LEVELS[: i + 1]]
    for i, level in enumerate(LEVELS)
}


# EXA-146: difficulty follows marks. The easiest rung a slot of m marks should take, written out
# from the rule (P8-SHAPING.md "Difficulty follows marks"), not imported from the generator.
_RUNG = {"easy": 0, "medium": 1, "hard": 2}


def _shortfall(code: str, marks: int) -> int:
    need = 0 if marks <= 1 else 1 if marks == 2 else 2
    return max(0, need - _RUNG[META[code]["rung"]])


def _capped(code: str, kind: str, topics: Counter) -> bool:
    """EXA-154: a structured stand-in never gives a topic its third question in a paper, so a
    blueprint of a topic the paper had twice when the stand-in was picked could not be taken."""
    return kind == "structured" and topics[META[code]["topic"]] >= 2


def _topics_at_pick(doc, node) -> Counter[str]:
    """The paper's topics when ``node`` (a structured stand-in) was picked, written out from the
    fill order: every earlier section, then this section's multi-part questions, then its
    stand-ins biggest first (equal marks in print order, since the section is sorted stably)."""
    out: Counter[str] = Counter()
    for _, nodes in _by_section(doc):
        if node not in nodes:
            out.update(_topic(n) for n in nodes if n["type"] == "templatedQuestion")
            continue
        here = nodes.index(node)
        for i, n in enumerate(nodes):
            if n["type"] != "templatedQuestion" or n is node:
                continue
            multipart = META[n["attrs"]["question"]["blueprint_code"]]["parts"] > 1
            bigger = _marks(n) > _marks(node) or (_marks(n) == _marks(node) and i < here)
            if multipart or bigger:
                out[_topic(n)] += 1
        return out
    raise AssertionError("node not in the paper")


def _topic(node) -> str:
    return node["attrs"]["question"]["syllabus"]["topic"]


def _takes(code: str, kind: str, level: str) -> bool:
    """Whether a single-part blueprint could fill a slot of ``kind`` in a ``level`` paper."""
    m = META[code]
    if m["level"] not in LEVELS[: LEVELS.index(level) + 1] or m["parts"] != 1:
        return False
    return kind != "mcq" or m["answer_type"] in _CONVERTIBLE


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
    """Every rule, for a paper on its own and for the same paper made as part of an exam set
    (EXA-153)."""
    template = next(t for t in paper_templates() if t["code"] == code)
    allowed = set(LEVELS[: LEVELS.index(level) + 1])
    alone = ((s, *generate_paper(code, level, s), None) for s in SEEDS)
    in_sets = (
        (s, *papers[TEMPLATES.index(code)], _topics_by_then(papers, code))
        for s, papers in _sets(level).items()
    )
    for seed, doc, report, set_topics in (*alone, *in_sets):
        where = f"{code} {level} seed={seed}{'' if set_topics is None else ' in a set'}"
        # topics the set had filled by the time this paper was made (the papers filled before
        # it, plus its own): only those may excuse a better-rung blueprint left unused
        full = {t for t, n in (set_topics or {}).items() if n >= SET_TOPIC_CAP}

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
                # (today's eight fit in any P6 Section B: 33 marks of 45, 8 of 12 slots)
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

        # difficulty follows marks (EXA-146): a question falls below its slot's rung only when
        # every blueprint that could have filled the slot at that rung is already in the paper
        # (or, in an exam set, its topic is full: EXA-153; or, for a stand-in, the paper had
        # two questions of its topic when the stand-in was picked: EXA-154)
        for sec, nodes in _by_section(doc):
            for n in nodes:
                if n["type"] != "templatedQuestion":
                    continue
                bp, marks = n["attrs"]["question"]["blueprint_code"], _marks(n)
                if META[bp]["parts"] > 1 or _shortfall(bp, marks) == 0:
                    continue
                better = [
                    c
                    for c, m in META.items()
                    if m["marks"] == marks
                    and _takes(c, sec["mode"], level)
                    and _shortfall(c, marks) < _shortfall(bp, marks)
                    and c not in codes
                    and META[c]["topic"] not in full
                    and not _capped(c, sec["mode"], _topics_at_pick(doc, n))
                ]
                assert not better, (where, bp, better)

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


# EXA-153: the most questions one topic may take in a P6 exam set (47 questions). Real P6 sets
# give one topic up to 6 (Fractions at AT and CH, Angles at SN) and the per-topic averages run
# 1.0-4.8 a set (docs/planning/editor/REAL-PAPER-COMPARISON.md, 2b); our P6 blueprints cover 15
# topics, a fair share of 3.1 each, so 4 is a share and one more. Before EXA-153 seven topics
# reached 6 in some set. A P5 set (44 questions, 13 topics: 3.4 each) uses nearly every P5
# blueprint in each paper, so the pool allows no better than 5 (before: 6 in most sets).
_SET_MAX = {"P5": 5, "P6": 4}


def _fit(doc) -> int:
    """Single-part questions at the rung their marks ask for (EXA-146)."""
    return sum(
        _shortfall(n["attrs"]["question"]["blueprint_code"], _marks(n)) == 0
        for n in _questions(doc)
        if n["type"] == "templatedQuestion"
        and META[n["attrs"]["question"]["blueprint_code"]]["parts"] == 1
    )


def _over_cap(counts: Counter[str]) -> int:
    return sum(max(0, n - SET_TOPIC_CAP) for n in counts.values())


@pytest.mark.parametrize("level", LEVELS)
def test_an_exam_set_spreads_its_topics(level):
    """EXA-153: made as a set, the three papers spread their topics over the whole set. No
    topic takes more questions, and fewer questions sit over the cap, than when the same seeds
    make the papers on their own, and no topic passes _SET_MAX. Paper 2 is filled first
    (set_fill_order), so its hard and medium slots keep the rungs they would have alone."""
    assert set_fill_order(TEMPLATES) == _FILL_ORDER
    over_together = over_apart = 0
    for seed, papers in _sets(level).items():
        together = _set_topics(papers)
        apart = _set_topics([generate_paper(code, level, seed) for code in TEMPLATES])
        where = (level, seed, dict(together))
        assert sum(together.values()) == sum(apart.values()), where  # no question lost
        assert max(together.values()) <= max(apart.values()), where
        over_together += _over_cap(together)
        over_apart += _over_cap(apart)
        assert max(together.values()) <= _SET_MAX[level], where
        p2 = TEMPLATES.index("p2")
        assert _fit(papers[p2][0]) >= _fit(generate_paper("p2", level, seed)[0]), where
        # each report counts its own paper's topics, as the wizard adds them up
        assert sum((Counter(r["topics"]) for _, r in papers), Counter()) == together, where
    # the fill is greedy, paper by paper, so one set may sit a question or two further over the
    # cap than its papers made apart (P6 seed 12 once multi-part questions pick first, EXA-154);
    # over the seeds a set has clearly fewer (seeds 1-30: P5 360 against 426, P6 about 0.6x)
    assert over_together <= 0.9 * over_apart, (level, over_together, over_apart)


_CONVERTIBLE = {"integer", "decimal", "quantity", "fraction"}  # a number: multiple choice


@pytest.mark.parametrize("level", LEVELS)
def test_booklet_a_fills_every_slot_and_spreads_topics(level):
    """EXA-145: P5 and P6 Booklet A have no placeholders, and replaying the fill from the
    document shows each question came from the best-fitting rung for its marks (EXA-146), then
    a least-used topic, among the blueprints still free for its slot, so the new one-mark
    topics never crowd out an older one. The 2-mark slots choose first (their rung rule leaves
    the fewest blueprints), then the 1-mark ones, each group in print order."""
    allowed = LEVELS[: LEVELS.index(level) + 1]
    for seed in SEEDS:
        doc, report = generate_paper("p1_booklet_a", level, seed)
        assert report["placeholders"] == unfilled_placeholders(doc) == 0, seed
        used: set[str] = set()
        counts: Counter[str] = Counter()
        paper_topics = set()
        codes = [n["attrs"]["question"]["blueprint_code"] for n in _questions(doc)]
        for code in sorted(codes, key=lambda c: -META[c]["marks"]):  # stable: print order
            marks = META[code]["marks"]
            free = [
                c
                for c, m in META.items()
                if c not in used and m["marks"] == marks and _takes(c, "mcq", level)
            ]
            assert code in free, (seed, code)
            fit = min(_shortfall(c, marks) for c in free)
            assert _shortfall(code, marks) == fit, (seed, code)
            least = min(counts[META[c]["topic"]] for c in free if _shortfall(c, marks) == fit)
            assert counts[META[code]["topic"]] == least, (seed, code, dict(counts))
            used.add(code)
            counts[META[code]["topic"]] += 1
            paper_topics.add(META[code]["topic"])
        # every topic with a one-mark multiple-choice blueprint gets a question (a topic whose
        # 2-mark question was chosen first may give its 1-mark slot to a less-used topic)
        eligible = {
            m["topic"]
            for m in META.values()
            if m["level"] in allowed
            and m["marks"] == 1
            and m["parts"] == 1
            and m["answer_type"] in _CONVERTIBLE
        }
        assert eligible <= paper_topics, (seed, eligible - paper_topics)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("code", TEMPLATES)
def test_difficulty_follows_marks_without_costing_a_question(code, level):
    """EXA-146: in each group of slots of the same marks and kind, either every single-part
    question has the rung its marks ask for (2 marks: medium or harder; 3+: hard) or every
    blueprint that has it is already in the paper. And one topic never takes more than two
    questions of a paper. (No placeholder is added: see test_what_todays_content_fills.)"""
    for seed in SEEDS:
        doc, _ = generate_paper(code, level, seed)
        qs = [
            (n["attrs"]["slot"], n["attrs"]["question"])
            for n in _questions(doc)
            if n["type"] == "templatedQuestion"
        ]
        used = {q["blueprint_code"] for _, q in qs}
        topics = Counter(q["syllabus"]["topic"] for _, q in qs)
        groups: dict[tuple[int, str], list[dict]] = {}
        for n in _questions(doc):
            if (
                n["type"] == "templatedQuestion"
                and META[n["attrs"]["question"]["blueprint_code"]]["parts"] == 1
            ):
                slot = n["attrs"]["slot"]
                groups.setdefault((slot["marks"], slot["kind"]), []).append(n)
        for (marks, kind), nodes in groups.items():
            low = [
                n for n in nodes if _shortfall(n["attrs"]["question"]["blueprint_code"], marks) > 0
            ]
            if not low:
                continue
            fitting = {
                c
                for c, m in META.items()
                if m["marks"] == marks
                and _takes(c, kind, level)
                and _shortfall(c, marks) == 0
                and not all(_capped(c, kind, _topics_at_pick(doc, n)) for n in low)
            }
            assert fitting <= used, (code, level, seed, marks, kind, fitting - used)
        assert max(topics.values()) <= 2, (code, level, seed, topics)


def test_what_todays_content_fills():
    """Regression anchor for the shaping doc's coverage table (changes when content grows)."""

    def fill(code, level):
        _, r = generate_paper(code, level, 1)
        return r["filled"], r["placeholders"]

    assert fill("p1_booklet_a", "P6") == (15, 0)  # 13 one-mark MCQ-able (P8e batch 3)
    assert fill("p1_booklet_a", "P5") == (15, 0)  # 12 one-mark at P5
    assert fill("p1_booklet_b", "P6") == (15, 0)
    assert fill("p1_booklet_b", "P5") == (15, 0)  # 12 two-mark medium at P5 (EXA-154)
    assert fill("p2", "P6") == (17, 0)  # Section B: 8 multi-part + 4 single-part stand-ins
    _, r = generate_paper("p2", "P6", 1)
    assert [(s["multipart"], s["stand_ins"]) for s in r["sections"]] == [(0, 0), (8, 4)]
    assert fill("p2", "P5") == (17, 3)  # Section B: 12 stand-ins, 3 placeholders (13 marks)


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
        topics: dict = {}
        pool = [
            Candidate(f"b{m}_{i}", "T", "P6", m, "constructed")
            for m in range(2, 9)
            for i in range(15)
        ]

    t = time.perf_counter()
    plan = paper._stand_in_plan(_F(), 45, 12)
    assert time.perf_counter() - t < 0.5
    assert sum(plan) == 45 and len(plan) == 12 and min(plan) >= 2
