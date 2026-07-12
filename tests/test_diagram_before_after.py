"""A5 — before-after bar-model diagram: consistency check (honest spec passes,
each corruption rejected), spec → SVG render smoke, and determinism (R3.3, R3.4)."""

from __future__ import annotations

import copy

from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import (
    check_bar_model_before_after_consistency,
    check_consistency,
    render_svg,
)

PARAMS = {
    "names": ["Aisha", "Ben"],
    "ratio_before": [2, 3],
    "ratio_after": [1, 2],
    "spent": 20,
}


def _built(params: dict = PARAMS) -> tuple[dict, dict]:
    """Return (solution, diagram) for a params set via the real solver."""
    solver = get_solver("ratio_hard")
    solution = solver.solve(params)
    diagram = solver.diagram(params, solution)
    return solution, diagram


# --- consistency check (R3.3) ----------------------------------------------


def test_consistency_passes_for_built_spec():
    solution, diagram = _built()
    checks = check_consistency(diagram, PARAMS, solution)
    assert all(checks.values()), checks


def test_consistency_rejects_corrupted_units():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["stages"][0]["bars"][0]["units"] += 1  # A's before-units no longer match
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["before_bars"] is False
    assert not all(checks.values())


def test_consistency_rejects_broken_invariant():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["stages"][1]["bars"][1]["units"] += 1  # after.B != before.B → invariant broken
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["invariant"] is False
    assert not all(checks.values())


def test_consistency_rejects_corrupted_annotation():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["annotations"][0]["label"] = "1 unit = $999"
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["unit_annotation"] is False
    assert not all(checks.values())


# --- SVG render (R3.4) ------------------------------------------------------


def test_svg_render_smoke():
    _, diagram = _built()
    svg = render_svg(diagram)

    assert svg
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "viewBox" in svg
    for name in PARAMS["names"]:
        assert name in svg
    assert "Before" in svg
    assert "After" in svg
    # v=20, spent=20, B=$120 (see golden fixture 1)
    assert "1 unit = $20" in svg
    assert "Aisha spent = $20" in svg
    assert "Ben = $120" in svg
    assert "<path" in svg  # the invariant brace is a path


def test_svg_is_deterministic():
    _, diagram = _built()
    assert render_svg(diagram) == render_svg(diagram)
