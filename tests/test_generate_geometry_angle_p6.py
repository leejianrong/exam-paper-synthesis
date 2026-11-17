"""The deeper P6 angle blueprints (EXA-150): folded paper, a quadrilateral with an isosceles
or equilateral triangle, reflex angles at a point, and the two-part Paper 2 question.

Schema-valid, load-gated, tagged P6 with the marks the paper generator's rung rule wants,
on no difficulty ladder, a mandatory figure, the hand-verified goldens, and (single-part
ones) a multiple-choice copy whose wrong options are mostly the solver's named mistakes.
The two-part blueprint's framework tests live in ``test_multipart_blueprints.py``; the
correctness authority is ``test_invariants_geometry_angle_p6.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot
from exam_engine.ladder import ladder_for
from exam_engine.paper import min_rung
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (difficulty, marks)
    "geometry_angle_folded": ("medium", 2),
    "geometry_angle_composite": ("hard", 3),
    "geometry_angle_reflex": ("medium", 2),
    "geometry_angle_structured": ("hard", 4),
}
SINGLE = [c for c in CASES if c != "geometry_angle_structured"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    difficulty, marks = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["syllabus"]["level"] == "P6"
    assert obj["syllabus"]["topic"] == "Geometry (Angles)"
    assert obj["cognitive"]["difficulty"] == difficulty
    assert obj["question"]["total_marks"] == marks
    fig = obj["question"]["parts"][0]["diagram"]
    assert fig is not None and fig["type"] == "geometry_figure"
    assert obj["validation"]["status"] == "pass"
    assert verify_snapshot(obj) == []


@pytest.mark.parametrize("code", CASES)
def test_the_rung_suits_the_marks(code):
    """paper.py's rule (EXA-146): 2 marks take medium or harder, 3 or more take hard."""
    difficulty, marks = CASES[code]
    order = ["easy", "medium", "hard"]
    assert order.index(difficulty) >= order.index(min_rung(marks))


@pytest.mark.parametrize("code", CASES)
def test_on_no_ladder_and_deterministic(code):
    assert ladder_for(code) is None
    obj = generate(code, 5)
    assert obj == generate(code, 5)
    assert edits.available_ops(obj) == {"regenerate"}  # the figure is not optional


@pytest.mark.parametrize("code", SINGLE)
def test_golden_fixtures(code):
    """Hand-verified params -> expected answer (regression anchors, ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]


def test_the_goldens_cover_every_template():
    for code in CASES:
        lines = (GOLDEN / f"{code}.jsonl").read_text().splitlines()
        templates = {json.loads(ln)["params"]["template"] for ln in lines if ln.strip()}
        enum = load_blueprint(code).parameter_schema["properties"]["template"]["enum"]
        assert templates == set(enum), code


def test_a_reflex_answer_gets_a_reflex_mark():
    for seed in range(1, 41):
        obj = generate("geometry_angle_reflex", seed)
        part = obj["question"]["parts"][0]
        (mark,) = [m for m in part["diagram"]["angles"] if m["unknown"]]
        assert mark["value_deg"] == part["answer"]["value"]
        assert ("reflex angle" in part["text"].split("Find")[-1]) == (mark["value_deg"] > 180)


# ------------------------------------------------------------------ multiple choice


@pytest.mark.parametrize("code", SINGLE)
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = 0
    for seed in range(1, 101):
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked and all(why.strip() for _, why in hooked), seed
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], seed
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        assert len(wrong) == 3
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 85, (code, from_hook)


def _given(text: str) -> list[int]:
    return [int(v) for v in re.findall(r"(?:=|is) (\d+)°", text)]


@pytest.mark.parametrize("code", SINGLE)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    """The minor angle of a reflex answer, the half-way step of a fold, the base angle of
    the isosceles triangle: worked from the numbers in the text, never the solver."""
    for seed in range(1, 61):
        obj = generate(code, seed)
        text = obj["question"]["parts"][0]["text"]
        g = _given(text)
        if code == "geometry_angle_folded":
            expected = g[0] // 2  # ∠EFB' instead of ∠B'FC
        elif code == "geometry_angle_reflex" and "is a straight line" in text:
            expected = 180 - g[0] - g[1]  # ∠BOD, not the reflex angle
        elif code == "geometry_angle_reflex" and "cross" in text:
            expected = 180 - g[0]
        elif code == "geometry_angle_reflex":
            expected = 360 - g[0] - g[1]  # forgot to halve
        elif "rhombus" in text:
            expected = g[0] + 60  # ∠ADE, not ∠DAE
        elif "parallelogram" in text:
            expected = 180 - g[0]  # ∠DAB, not ∠EAB
        else:
            expected = (180 - g[0]) // 2  # ∠BDC, not ∠DBC
        assert expected in [v for v, _ in mcq.common_wrong_answers(obj)], (code, seed, text)
