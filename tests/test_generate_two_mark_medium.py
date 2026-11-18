"""Generation suite for the 2-mark medium rungs (EXA-154): schema-valid, load-gated, tagged,
deterministic, exact worked steps, wired into their ladders between the 2-mark easy and the
3-mark medium rungs, hand-verified goldens — and the reason they exist: a generated paper's
2-mark slots now find a medium rung in every topic."""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.mcq import _eval
from exam_engine.paper import generate_paper
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (topic, level, the rung below, the rung above, has a figure)
    "ratio_difference": ("Ratio", "P5", "ratio_easy", "ratio_medium", False),
    "percentage_remainder": ("Percentage", "P5", "percentage_easy", "percentage_medium", False),
    "speed_minutes": ("Speed", "P6", "speed_easy", "speed_medium", False),
    "geometry_angle_opposite": (
        "Geometry (Angles)",
        "P5",
        "geometry_angle_easy",
        "geometry_angle_medium",
        True,
    ),
    "geometry_area_perimeter": (
        "Geometry (Area & Perimeter)",
        "P5",
        "geometry_area_easy",
        "geometry_area_medium",
        True,
    ),
}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    topic, level, *_, figure = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == level and obj["syllabus"]["topic"] == topic
    assert obj["cognitive"]["difficulty"] == "medium"
    assert obj["cognitive"]["cognitive_level"] == "complex_familiar"
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == 2
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 2
    assert len(parts[0]["solution_steps"]) == 2
    assert (parts[0]["diagram"] is not None) == figure
    assert parts[0]["answer"]["value"] > 0
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False
    assert "not drawn to scale" not in parts[0]["text"]  # real papers rarely print it


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", ["ratio_difference", "percentage_remainder", "speed_minutes"])
def test_every_step_carries_an_exact_expr_ending_at_the_answer(code, seed):
    part = generate(code, seed)["question"]["parts"][0]
    values = [_eval(s["expr"] or "") for s in part["solution_steps"]]
    assert all(v is not None for v in values)
    assert values[-1] == Fraction(str(part["answer"]["value"]))


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Two marks", [obj])
    key = render_answer_key_html("Two marks", [obj])
    assert "Answer:" not in sheet and "Answer:" in key


@pytest.mark.parametrize("code", ["ratio_difference", "percentage_remainder"])
def test_rename_is_cosmetic(code):
    obj = generate(code, 4)
    key = "names" if code == "ratio_difference" else "name"
    new = ["Nurul Aini", "Wei Ming"] if key == "names" else "Nurul Aini"
    child = edits.apply("set-cosmetic", obj, changes={key: new})
    text = child["question"]["parts"][0]["text"]
    assert "Nurul Aini" in text
    assert child["question"]["parts"][0]["answer"] == obj["question"]["parts"][0]["answer"]


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


@pytest.mark.parametrize("code", CASES)
def test_the_rung_sits_between_the_easy_and_the_three_mark_medium(code):
    *_, below, above, _ = CASES[code]
    assert ladder_for(code) is not None and ladder_for(code).index(code) == 1
    assert sibling(below, +1) == code and sibling(code, +1) == above
    assert sibling(code, -1) == below and sibling(above, -1) == code
    assert load_blueprint(below).marks == 2 and load_blueprint(above).marks == 3
    assert {"make-harder", "make-easier"} <= edits.available_ops(generate(code, 1))
    assert edits.apply("make-harder", generate(below, 1), seed=2)["blueprint_code"] == code


@pytest.mark.parametrize(("level", "medium"), [("P6", 10), ("P5", 9)])
def test_booklet_b_two_mark_slots_take_medium_rungs_across_topics(level, medium):
    """The point of EXA-154: since EXA-146 a 2-mark slot wants a medium rung, and Ratio,
    Percentage, Speed and both Geometry topics had only easy 2-markers. Now a P6 Booklet B
    fills all ten 2-mark slots with medium rungs from at least nine topics (it was 7 medium and
    3 easy);
    a P5 one fills all ten (it left 2 placeholders), 9 of them medium — every P5 2-mark medium
    blueprint there is, cubes_complete (EXA-147) the ninth — from at least 9 topics."""
    for seed in range(1, 41):
        doc, report = generate_paper("p1_booklet_b", level, seed)
        assert report["placeholders"] == 0, (level, seed)
        two = [
            n["attrs"]["question"]
            for n in doc["content"]["content"]
            if n["type"] == "templatedQuestion" and n["attrs"]["slot"]["marks"] == 2
        ]
        assert len(two) == 10
        rungs = Counter(q["cognitive"]["difficulty"] for q in two)
        assert rungs["easy"] == 10 - medium, (level, seed, rungs)
        topics = Counter(q["syllabus"]["topic"] for q in two)
        # P6 Angles has three 2-mark medium blueprints since EXA-150, so on a tie of topic load
        # a seed may give it two of the ten (9 of 40 seeds); no topic takes a third
        assert len(topics) >= min(medium, 9), (level, seed, topics)
        assert max(topics.values()) <= 2, (level, seed, topics)
