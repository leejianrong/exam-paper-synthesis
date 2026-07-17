"""geometry_angle_easy (KAN-229): one rule, one step unknown-angle figures.
Schema-valid, tagged easy/routine, 2 marks, MANDATORY geometry figure (no
toggle), integer degrees answer, deterministic, seeds vary, hand-verified
golden fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import check_geometry_figure_consistency, render_svg
from exam_engine.edits import available_ops
from exam_engine.schema import validate_object

CODE = "geometry_angle_easy"
GOLDEN = Path(__file__).parent / "golden" / f"{CODE}.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate(CODE, seed)

    assert validate_object(obj) == []
    assert obj["id"] == f"{CODE}:{seed}"
    assert obj["blueprint_code"] == CODE
    assert obj["cognitive"]["difficulty"] == "easy"
    assert obj["cognitive"]["cognitive_level"] == "routine_procedural"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 2
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 2

    answer = parts[0]["answer"]
    assert answer["type"] == "integer"
    assert answer["unit"] == "degrees"
    assert isinstance(answer["value"], int) and 0 < answer["value"] < 180

    # Mandatory figure: present, consistent, renders.
    fig = parts[0]["diagram"]
    assert fig is not None and fig["type"] == "geometry_figure"
    checks = check_geometry_figure_consistency(fig, obj["parameters"], {"answer": answer})
    assert all(checks.values()), checks
    assert render_svg(fig).startswith("<svg")

    assert obj["validation"]["status"] == "pass"


def test_no_diagram_toggle_offered():
    # Mandatory-figure family: toggle-diagram must NOT be available (aid-gating).
    obj = generate(CODE, 1)
    assert "toggle-diagram" not in available_ops(obj)


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
