"""Generation suite for the P6 Circles ladder (EXA-149): schema-valid, load-gated, tagged,
deterministic, ladder wired (make-harder / make-easier), printed with π and units,
goldens (checked by a person), and the paper generator's rung rule can use every rung."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.paper import candidates, generate_paper, min_rung
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks, solution steps)
    "circles_easy": ("easy", "routine_procedural", 1, 2),
    "circles_medium": ("medium", "complex_familiar", 2, 3),
    "circles_hard": ("hard", "non_routine_heuristic", 3, 3),
}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks, steps = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P6" and obj["syllabus"]["topic"] == "Circles"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert len(parts[0]["solution_steps"]) == steps
    assert parts[0]["diagram"]["type"] == "geometry_figure"
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False
    text = parts[0]["text"]
    assert "Take π = " in text or "Leave your answer in terms of π." in text
    assert "not drawn to scale" not in text  # these figures are drawn to scale


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it_with_its_unit(code):
    for seed in range(1, 12):
        obj = generate(code, seed)
        sheet = render_worksheet_html("Circles", [obj])
        key = render_answer_key_html("Circles", [obj])
        assert "Answer:" not in sheet and "Answer:" in key
        assert "<svg" in sheet  # the figure prints on the student paper
        unit = obj["question"]["parts"][0]["answer"]["unit"]
        assert ("cm²" if unit == "cm^2" else "cm") in key


def test_an_answer_in_terms_of_pi_prints_as_maths():
    obj = next(
        o
        for o in (generate("circles_hard", s) for s in range(1, 60))
        if o["parameters"]["pi"] == "terms"
    )
    s = obj["parameters"]["givens"]["s"]
    key = render_answer_key_html("Circles", [obj])
    assert rf"{s}\pi + {s}" in key and r"\text{cm}" in key


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Golden params -> expected answer (regression anchors; a person checks them)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


def test_ladder_is_wired():
    rungs = ["circles_easy", "circles_medium", "circles_hard"]
    assert ladder_for("circles_medium") == rungs
    assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
    assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
    obj = generate(rungs[1], 1)
    assert {"make-harder", "make-easier"} <= edits.available_ops(obj)
    harder = edits.apply("make-harder", obj)
    easier = edits.apply("make-easier", obj)
    assert harder["blueprint_code"] == rungs[2] and easier["blueprint_code"] == rungs[0]


def test_every_rung_fits_its_slots_under_difficulty_follows_marks():
    """1 mark takes any rung, 2 marks medium or harder, 3 marks hard (EXA-146): each rung's
    marks are exactly what that rule asks for, and a P5 paper never draws a P6 circle."""
    pool = {c.code: c for c in candidates("P6")}
    for code in CASES:
        c = pool[code]
        assert c.topic == "Circles" and c.kind == "constructed"
        assert min_rung(c.marks) in ("easy", c.rung)
    assert pool["circles_easy"].answer_type in ("integer", "decimal")  # Booklet A MCQ
    assert pool["circles_medium"].answer_type in ("integer", "decimal")
    assert not any(c.topic == "Circles" for c in candidates("P5"))


def test_generated_p6_papers_draw_circles():
    found = 0
    for seed in range(1, 11):
        for template in ("p1_booklet_a", "p1_booklet_b", "p2"):
            doc, _ = generate_paper(template, "P6", seed)
            blocks = doc["content"]["content"]
            found += sum(
                1
                for b in blocks
                if b.get("type") == "templatedQuestion"
                and b["attrs"]["question"]["blueprint_code"].startswith("circles_")
            )
    assert found >= 10, found
