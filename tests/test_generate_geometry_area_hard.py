"""geometry_area_hard (KAN-230): shaded area (square − quarter circle) / inverse
length. Schema-valid, tagged hard/non-routine, 4 marks, MANDATORY geometry figure
(no toggle), integer OR 2-dp decimal answer (π auto-select), deterministic,
hand-verified golden fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import check_geometry_figure_consistency, render_svg
from exam_engine.edits import available_ops
from exam_engine.schema import validate_object

CODE = "geometry_area_hard"
GOLDEN = Path(__file__).parent / "golden" / f"{CODE}.jsonl"
SEEDS = [1, 2, 3, 4, 7, 42, 100, 999, 123456]


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_schema_valid_and_tagged(seed: int):
    obj = generate(CODE, seed)

    assert validate_object(obj) == []
    assert obj["id"] == f"{CODE}:{seed}"
    assert obj["cognitive"]["difficulty"] == "hard"

    parts = obj["question"]["parts"]
    assert len(parts) == 1
    assert obj["question"]["total_marks"] == 4
    assert sum(m["mark"] for m in parts[0]["marking_scheme"]) == 4

    answer = parts[0]["answer"]
    assert answer["type"] in {"integer", "decimal"}
    assert answer["unit"] in {"cm^2", "cm"}
    assert float(answer["value"]) > 0
    if answer["type"] == "decimal":
        assert answer["dp"] == 2

    fig = parts[0]["diagram"]
    assert fig is not None and fig["type"] == "geometry_figure"
    checks = check_geometry_figure_consistency(fig, obj["parameters"], {"answer": answer})
    assert all(checks.values()), checks
    assert render_svg(fig).startswith("<svg")

    assert obj["validation"]["status"] == "pass"


def test_both_pi_paths_reachable():
    kinds = set()
    for seed in range(1, 120):
        obj = generate(CODE, seed)
        if obj["parameters"]["template"] == "square_minus_quarter":
            kinds.add(obj["question"]["parts"][0]["answer"]["type"])
    assert kinds == {"integer", "decimal"}, kinds


def test_no_diagram_toggle_offered():
    obj = generate(CODE, 1)
    assert "toggle-diagram" not in available_ops(obj)


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_is_deterministic(seed: int):
    assert generate(CODE, seed) == generate(CODE, seed)


def test_golden_fixtures():
    solver = get_solver(CODE)
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    assert lines, "golden fixture file is empty"
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
