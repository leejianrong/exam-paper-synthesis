"""Generation suite for the Whole Numbers ladder (P8e): schema-valid, load-gated, tagged at
P5, deterministic, cosmetic name/item editable, ladder wired, hand-verified goldens, and a
fair multiple-choice copy (the answer never sits in the middle of evenly spaced options)."""

from __future__ import annotations

import json
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.mcq import _eval, to_mcq
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks, steps)
    "whole_numbers_easy": ("easy", "routine_procedural", 1, 3),
    "whole_numbers_medium": ("medium", "complex_familiar", 2, 4),
    "whole_numbers_hard": ("hard", "non_routine_heuristic", 3, 4),
}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks, steps = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P5" and obj["syllabus"]["topic"] == "Whole Numbers"
    assert obj["syllabus"]["strand"] == "Number and Algebra"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert len(parts[0]["solution_steps"]) == steps
    assert parts[0]["diagram"] is None
    answer = parts[0]["answer"]
    assert answer["type"] == "integer" and 0 < answer["value"] <= 999 and answer["unit"] == ""
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False


@pytest.mark.parametrize("seed", range(1, 41))
@pytest.mark.parametrize("code", CASES)
def test_every_step_expr_evaluates_to_a_whole_number_ending_in_the_answer(code, seed):
    part = generate(code, seed)["question"]["parts"][0]
    values = [_eval(s["expr"]) for s in part["solution_steps"]]
    assert all(v is not None and v > 0 and v.denominator == 1 for v in values), values
    assert values[-1] == part["answer"]["value"]
    # each step's printed result is the value its expr evaluates to
    for step, v in zip(part["solution_steps"], values, strict=True):
        assert str(int(v)) in step["text"]


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Whole Numbers", [obj])
    key = render_answer_key_html("Whole Numbers", [obj])
    assert "Answer:" not in sheet and "Answer:" in key


def test_easy_prints_times_and_divide_signs():
    texts = [generate("whole_numbers_easy", s)["question"]["parts"][0]["text"] for s in SEEDS]
    assert all(t.startswith("Find the value of ") for t in texts)
    assert all("*" not in t and "/" not in t for t in texts)
    assert any("×" in t for t in texts) and any("÷" in t for t in texts)


def test_hard_rename_and_item_swap_are_cosmetic():
    obj = generate("whole_numbers_hard", 4)
    old_name, old_item = obj["parameters"]["name"], obj["parameters"]["item"]
    new_item = next(i for i in get_solver("whole_numbers_hard").ITEM_POOL if i != old_item)
    child = edits.apply("set-cosmetic", obj, changes={"name": "Nurul Aini", "item": new_item})
    part = child["question"]["parts"][0]
    assert "Nurul Aini" in part["text"] and old_name not in part["text"]
    assert new_item in part["text"] and old_item not in part["text"]
    assert part["answer"] == obj["question"]["parts"][0]["answer"]


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


@pytest.mark.parametrize("code", CASES)
def test_multiple_choice_does_not_give_the_answer_away(code):
    """No two wrong options sit evenly either side of the answer (e.g. 38, 39, 40)."""
    for seed in range(1, 201):
        obj = generate(code, seed)
        mcq = to_mcq(obj, seed)["question"]["parts"][0]["answer"]
        ans = Fraction(obj["question"]["parts"][0]["answer"]["value"])
        values = [Fraction(o["text"].lstrip("$")) for o in mcq["options"]]
        wrong = [v for v in values if v != ans]
        assert len(wrong) == 3, (code, seed, values)
        assert not any(x + y == 2 * ans for x, y in combinations(wrong, 2)), (code, seed, values)


def test_ladder_is_wired():
    rungs = ["whole_numbers_easy", "whole_numbers_medium", "whole_numbers_hard"]
    assert ladder_for("whole_numbers_medium") == rungs
    assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
    assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
    assert {"make-harder", "make-easier"} <= edits.available_ops(generate(rungs[1], 1))
