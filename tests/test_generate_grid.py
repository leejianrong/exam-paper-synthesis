"""Generation suite for the square-grid blueprints (EXA-144).

Schema-valid, load-gated, tagged, deterministic, on no ladder, goldens (a person checks them,
see the PR); the area blueprint converts to multiple choice through its distractors hook with
the answer anywhere among the options; the three that ask multiple choice themselves go into a
paper's MCQ slots as they are, only there, and stay engine-proven (a tampered option or figure
is caught).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot
from exam_engine.ladder import ladder_for
from exam_engine.paper import _fits, as_slot_question, candidates, generate_paper
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (marks, rung, answer type)
    "grid_area": (2, "medium", "quantity"),
    "grid_lines": (1, "easy", "choice"),
    "grid_compass": (1, "easy", "choice"),
    "grid_symmetry": (1, "easy", "choice"),
}
CHOICE = ["grid_lines", "grid_compass", "grid_symmetry"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    marks, rung, atype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["syllabus"]["level"] == "P5" and obj["syllabus"]["topic"] == "Square Grids"
    assert obj["syllabus"]["strand"] == "Geometry"
    assert obj["cognitive"]["difficulty"] == rung
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert parts[0]["answer"]["type"] == atype and parts[0]["diagram"]["type"] == "grid"
    assert obj["validation"]["status"] == "pass"
    assert verify_snapshot(obj) == []


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    figures = {json.dumps(generate(code, s)["question"]["parts"][0]["diagram"]) for s in SEEDS}
    assert len(figures) == len(SEEDS)


@pytest.mark.parametrize("code", CASES)
def test_on_no_ladder(code):
    assert ladder_for(code) is None
    ops = edits.available_ops(generate(code, 3))
    assert ops == (set() if code in CHOICE else {"regenerate"})


@pytest.mark.parametrize("code", CASES)
def test_worksheet_shows_the_figure_and_hides_the_answer(code):
    obj = generate(code, 3)
    paper = render_worksheet_html("P", [obj])
    assert "<svg" in paper and "Answer:" not in paper
    assert "Answer:" in render_answer_key_html("P", [obj])


@pytest.mark.parametrize("code", CHOICE)
def test_letter_options_in_letter_order_and_the_answer_anywhere(code):
    places = []
    for seed in range(1, 121):
        answer = generate(code, seed)["question"]["parts"][0]["answer"]
        texts = [o["text"] for o in answer["options"]]
        assert texts == sorted(texts) and len(set(texts)) == 4
        assert [o["label"] for o in answer["options"]] == ["1", "2", "3", "4"]
        places.append(int(answer["correct"]))
    share = {p: places.count(p) / len(places) for p in (1, 2, 3, 4)}
    assert all(0.12 <= v <= 0.4 for v in share.values()), share


def test_area_mcq_copies_use_the_hook_and_stay_proven():
    from_hook = 0
    for seed in range(1, 61):
        obj = generate("grid_area", seed)
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == []
        answer = m["question"]["parts"][0]["answer"]
        hooked = {
            mcq.answer_text(mcq._with_value(obj["question"]["parts"][0]["answer"], v))
            for v, _ in mcq.common_wrong_answers(obj)
        }
        wrong = [o["text"] for o in answer["options"] if o["label"] != answer["correct"]]
        from_hook += sum(t in hooked for t in wrong)
    assert from_hook >= 0.7 * 60 * 3


def test_area_answers_place_among_the_options_gives_nothing_away():
    """Options print in ascending order, so the hook offers slips on both sides of the
    answer: over many seeds it is in every place and not mostly at either end."""
    places = [
        int(mcq.to_mcq(generate("grid_area", s), s)["question"]["parts"][0]["answer"]["correct"])
        for s in range(1, 201)
    ]
    share = {p: places.count(p) / len(places) for p in (1, 2, 3, 4)}
    assert all(v >= 0.05 for v in share.values()), share
    assert share[1] <= 0.4 and share[4] <= 0.4 and max(share.values()) <= 0.5, share


def test_area_hook_has_slips_on_both_sides():
    solver = get_solver("grid_area")
    for seed in range(1, 41):
        obj = generate("grid_area", seed)
        value = obj["question"]["parts"][0]["answer"]["value"]
        slips = solver.distractors(obj["parameters"], {})
        assert any(v < value for v, _ in slips) and any(v > value for v, _ in slips), seed
        named = {why: v for v, why in slips}
        assert named["counted only the whole squares"] < value
        assert named["counted each half square as a whole one"] > value


@pytest.mark.parametrize("code", CHOICE)
def test_a_tampered_choice_is_caught(code):
    obj = generate(code, 9)
    bad = copy.deepcopy(obj)
    answer = bad["question"]["parts"][0]["answer"]
    answer["correct"] = next(
        o["label"] for o in answer["options"] if o["label"] != answer["correct"]
    )
    assert verify_snapshot(bad) != []


@pytest.mark.parametrize("code", CASES)
def test_a_tampered_figure_is_caught(code):
    """The drawn grid is the question: moving what is on it must not keep the proof."""
    obj = generate(code, 9)
    bad = copy.deepcopy(obj)
    figure = bad["question"]["parts"][0]["diagram"]
    if figure.get("points"):
        figure["points"][0]["x"] += 1 if figure["points"][0]["x"] < figure["cols"] else -1
    elif figure.get("polygons"):
        figure["polygons"][0]["vertices"].reverse()
    else:
        figure["cells"][0]["row"] += 1
    assert verify_snapshot(obj) == []
    assert verify_snapshot(bad) == [
        "the figure does not match the engine's figure for these parameters"
    ]


@pytest.mark.parametrize("code", CHOICE)
def test_choice_blueprints_fill_mcq_slots_only_and_unchanged(code):
    c = next(c for c in candidates("P5") if c.code == code)
    assert _fits(c, "mcq") and not _fits(c, "short") and not _fits(c, "structured")
    obj = generate(code, 4)
    assert as_slot_question(obj, "mcq", 1) is obj


def test_area_fits_two_mark_written_slots():
    c = next(c for c in candidates("P5") if c.code == "grid_area")
    assert _fits(c, "short") and _fits(c, "structured") and _fits(c, "mcq")


def test_a_booklet_a_takes_the_choice_ones_as_they_are():
    seen = set()
    for seed in range(1, 31):
        doc, _ = generate_paper("p1_booklet_a", "P5", seed)
        for node in doc["content"]["content"]:
            q = (node.get("attrs") or {}).get("question")
            if q and q["blueprint_code"] in CHOICE:
                seen.add(q["blueprint_code"])
                assert q["question"]["parts"][0]["answer"]["type"] == "choice"
                assert verify_snapshot(q) == []
    assert seen == set(CHOICE)


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Seed-picked params -> expected answer, checked by a person (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]
