"""Generation suite for the Decimals ladder (P8e): schema-valid, load-gated, tagged at P5,
deterministic, cosmetic names/items editable, ladder wired, sensible multiple choice,
hand-verified goldens."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks, steps)
    "decimals_easy": ("easy", "routine_procedural", 1, 1),
    "decimals_medium": ("medium", "complex_familiar", 2, 2),
    "decimals_hard": ("hard", "complex_familiar", 3, 4),
}
MONEY = re.compile(r"^\$\d+\.\d\d$")


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks, steps = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P5" and obj["syllabus"]["topic"] == "Decimals"
    assert obj["syllabus"]["strand"] == "Number and Algebra"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert len(parts[0]["solution_steps"]) == steps
    assert all(s["expr"] for s in parts[0]["solution_steps"])
    assert parts[0]["diagram"] is None
    answer = parts[0]["answer"]
    assert answer["type"] in ("integer", "decimal") and answer["value"] > 0
    if code == "decimals_easy":
        assert answer["unit"] == "" and (answer["type"] == "integer") == (
            answer["value"] == int(answer["value"])
        )
    else:
        assert answer["type"] == "decimal" and answer["dp"] == 2 and answer["unit"] == "$"
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False
    if code == "decimals_hard":
        assert obj["parameters"]["name"] in parts[0]["text"]


@pytest.mark.parametrize("code", CASES)
def test_steps_evaluate_to_their_results(code):
    """Each step's ``expr`` is that step's value, and the last one is the answer (MCQ uses
    the intermediate values as distractors)."""
    for seed in SEEDS:
        part = generate(code, seed)["question"]["parts"][0]
        for step in part["solution_steps"]:
            value = mcq._eval(step["expr"])
            assert value is not None, step
            shown = step["text"].rstrip(".").rsplit("= ", 1)[1].lstrip("$")
            assert value == Fraction(shown), step
        assert value == mcq._value(part["answer"])


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Decimals", [obj])
    key = render_answer_key_html("Decimals", [obj])
    assert "Answer:" not in sheet and "Answer:" in key
    if code != "decimals_easy":  # money always prints at 2 dp
        assert re.search(r"\$\d+\.\d\d", mcq.answer_text(obj["question"]["parts"][0]["answer"]))


def test_rename_is_cosmetic():
    obj = generate("decimals_hard", 4)
    old = obj["parameters"]["name"]
    child = edits.apply("set-cosmetic", obj, changes={"name": "Nurul Aini"})
    text = child["question"]["parts"][0]["text"]
    assert "Nurul Aini" in text and old not in text
    assert child["question"]["parts"][0]["answer"] == obj["question"]["parts"][0]["answer"]


def test_item_swap_is_cosmetic():
    obj = generate("decimals_medium", 4)
    new = next(i for i in get_solver("decimals_medium").ITEM_POOL if i != obj["parameters"]["item"])
    child = edits.apply("set-cosmetic", obj, changes={"item": new})
    assert child["question"]["parts"][0]["text"].count(new) == 2
    assert child["question"]["parts"][0]["answer"] == obj["question"]["parts"][0]["answer"]


@pytest.mark.parametrize("code", CASES)
def test_no_representation_ops(code):
    """Already decimal: no change-to-decimals, no diagram toggles — only the resample ops."""
    for seed in SEEDS:
        ops = edits.available_ops(generate(code, seed))
        assert ops <= {"regenerate", "make-harder", "make-easier"}


@pytest.mark.parametrize("code", CASES)
def test_multiple_choice_keeps_the_answers_format(code):
    for seed in range(1, 41):
        obj = generate(code, seed)
        options = [
            o["text"] for o in mcq.to_mcq(obj, seed)["question"]["parts"][0]["answer"]["options"]
        ]
        if code == "decimals_easy":
            assert all(re.fullmatch(r"\d+(\.\d{1,2})?", t) for t in options), options
        else:
            assert all(MONEY.fullmatch(t) for t in options), options


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


def test_ladder_is_wired():
    rungs = ["decimals_easy", "decimals_medium", "decimals_hard"]
    assert ladder_for("decimals_medium") == rungs
    assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
    assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
    assert {"make-harder", "make-easier"} <= edits.available_ops(generate(rungs[1], 1))
