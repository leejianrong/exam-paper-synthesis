"""geometry_angle_hard (KAN-229): P6 composite unknown-angle figures (a triangle
sharing an edge with a special quadrilateral). Schema-valid, tagged
hard/non-routine, 3 marks, MANDATORY geometry figure (no toggle), integer
degrees answer, deterministic, seeds vary, hand-verified golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import check_geometry_figure_consistency, render_svg
from exam_engine.edits import available_ops
from exam_engine.schema import validate_object

CODE = "geometry_angle_hard"
GOLDEN = Path(__file__).parent / "golden" / f"{CODE}.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate(CODE, seed)

    assert validate_object(obj) == []
    assert obj["id"] == f"{CODE}:{seed}"
    assert obj["blueprint_code"] == CODE
    assert obj["cognitive"]["difficulty"] == "hard"
    assert obj["cognitive"]["cognitive_level"] == "non_routine_heuristic"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 3
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 3

    answer = parts[0]["answer"]
    assert answer["type"] == "integer"
    assert answer["unit"] == "degrees"
    assert isinstance(answer["value"], int) and 0 < answer["value"] < 180

    fig = parts[0]["diagram"]
    assert fig is not None and fig["type"] == "geometry_figure"
    checks = check_geometry_figure_consistency(fig, obj["parameters"], {"answer": answer})
    assert all(checks.values()), checks
    assert render_svg(fig).startswith("<svg")

    assert obj["validation"]["status"] == "pass"


def test_no_diagram_toggle_offered():
    obj = generate(CODE, 1)
    ops = available_ops(obj)
    assert "toggle-diagram" not in ops
    # Top rung: make-harder is unavailable, make-easier is.
    assert "make-harder" not in ops
    assert "make-easier" in ops


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate(CODE, seed) == generate(CODE, seed)


def test_golden_fixtures():
    """Correctness anchor: hand-verified params -> expected answer (ADR-0003)."""
    solver = get_solver(CODE)
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        report = solver.validate(rec["params"], solution)
        assert report["ok"] is True
