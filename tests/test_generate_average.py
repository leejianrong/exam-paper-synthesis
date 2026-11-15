"""Generation suite for the Average ladder (P8e, EXA-117): schema-valid, load-gated,
tagged at P5, deterministic, cosmetic names editable, ladder wired, hand-verified goldens."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks)
    "average_easy": ("easy", "routine_procedural", 1),
    "average_medium": ("medium", "complex_familiar", 2),
    "average_hard": ("hard", "non_routine_heuristic", 3),
}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P5" and obj["syllabus"]["topic"] == "Average"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert len(parts[0]["solution_steps"]) == max(marks, 2)
    assert parts[0]["diagram"] is None
    assert parts[0]["answer"]["type"] == "integer" and parts[0]["answer"]["value"] > 0
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False
    assert obj["parameters"]["name"] in parts[0]["text"]


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Average", [obj])
    key = render_answer_key_html("Average", [obj])
    assert "Answer:" not in sheet and "Answer:" in key


@pytest.mark.parametrize("code", CASES)
def test_rename_is_cosmetic(code):
    obj = generate(code, 4)
    old = obj["parameters"]["name"]
    child = edits.apply("set-cosmetic", obj, changes={"name": "Nurul Aini"})
    text = child["question"]["parts"][0]["text"]
    assert "Nurul Aini" in text and old not in text
    assert child["question"]["parts"][0]["answer"] == obj["question"]["parts"][0]["answer"]


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert lines
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


def test_ladder_is_wired():
    rungs = ["average_easy", "average_medium", "average_hard"]
    assert ladder_for("average_medium") == rungs
    assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
    assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
    assert {"make-harder", "make-easier"} <= edits.available_ops(generate(rungs[1], 1))
