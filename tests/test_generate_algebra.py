"""Generation suite for the Algebra ladder (P8e): schema-valid, load-gated, tagged at P6,
deterministic, cosmetic names editable, ladder wired, numeric answers (so multiple choice
works), letters typeset in KaTeX, hand-verified goldens."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.ladder import ladder_for, sibling
from exam_engine.mcq import convertible
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, cognitive_level, marks, unit, worked steps)
    "algebra_easy": ("easy", "routine_procedural", 1, "", 2),
    "algebra_medium": ("medium", "complex_familiar", 2, "$", 3),
    "algebra_hard": ("hard", "non_routine_heuristic", 3, "", 3),
}
# the person-name parameter of each rung that has one (easy is a bare expression)
NAMED = {"algebra_medium": "name", "algebra_hard": "names"}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, level, marks, unit, n_steps = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["id"] == f"{code}:{seed}" and obj["blueprint_code"] == code
    assert obj["syllabus"]["level"] == "P6" and obj["syllabus"]["topic"] == "Algebra"
    assert obj["syllabus"]["strand"] == "Number and Algebra"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["cognitive"]["cognitive_level"] == level
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == marks
    assert len(parts[0]["solution_steps"]) == n_steps
    assert parts[0]["diagram"] is None
    answer = parts[0]["answer"]
    assert answer["type"] == "integer" and answer["value"] > 0 and answer["unit"] == unit
    assert convertible(obj)  # numeric, so every rung can become multiple choice
    assert obj["validation"]["status"] == "pass"
    assert obj["provenance"]["llm_used"] is False
    text = parts[0]["text"]
    assert r"\(" in text and text.count(r"\(") == text.count(r"\)")  # letters typeset
    assert " × " not in text and r"\times" not in text  # 5n, never 5 × n
    if code in NAMED:
        names = obj["parameters"][NAMED[code]]
        assert all(n in text for n in (names if isinstance(names, list) else [names]))


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    texts = {generate(code, s)["question"]["parts"][0]["text"] for s in SEEDS}
    assert len(texts) > 1


@pytest.mark.parametrize("code", CASES)
def test_worksheet_hides_the_answer_and_the_key_shows_it(code):
    obj = generate(code, 3)
    sheet = render_worksheet_html("Algebra", [obj])
    key = render_answer_key_html("Algebra", [obj])
    assert "Answer:" not in sheet and "Answer:" in key


@pytest.mark.parametrize("code", NAMED)
def test_rename_is_cosmetic(code):
    obj = generate(code, 4)
    key = NAMED[code]
    old = obj["parameters"][key]
    new: str | list[str] = "Nurul Aini" if isinstance(old, str) else ["Nurul Aini", "Wei Ming"]
    child = edits.apply("set-cosmetic", obj, changes={key: new})
    text = child["question"]["parts"][0]["text"]
    for before, after in zip(
        old if isinstance(old, list) else [old],
        new if isinstance(new, list) else [new],
        strict=True,
    ):
        assert after in text and before not in text
    assert child["question"]["parts"][0]["answer"] == obj["question"]["parts"][0]["answer"]


def test_the_bare_expression_has_no_cosmetic_slots():
    assert not edits.applicable("set-cosmetic", generate("algebra_easy", 1))


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
    rungs = ["algebra_easy", "algebra_medium", "algebra_hard"]
    assert ladder_for("algebra_medium") == rungs
    assert sibling(rungs[0], +1) == rungs[1] and sibling(rungs[2], -1) == rungs[1]
    assert sibling(rungs[0], -1) is None and sibling(rungs[2], +1) is None
    assert {"make-harder", "make-easier"} <= edits.available_ops(generate(rungs[1], 1))
