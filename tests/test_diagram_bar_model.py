"""A5 — bar-model diagram: consistency check (valid passes, corrupt rejected),
spec → SVG render smoke, and determinism (R2.6, R3.3, R3.4)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from exam_engine import generate
from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import (
    check_bar_model_consistency,
    check_consistency,
    render_svg,
)
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden" / "ratio_medium.jsonl"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]


def _built(params: dict) -> tuple[dict, dict]:
    """Return (solution, diagram) for a params set via the real solver."""
    solver = get_solver("ratio_medium")
    solution = solver.solve(params)
    diagram = solver.diagram(params, solution)
    return solution, diagram


def _golden_params() -> list[dict]:
    lines = [ln for ln in GOLDEN.read_text().splitlines() if ln.strip()]
    return [json.loads(ln)["params"] for ln in lines]


def test_svg_content_stays_within_canvas():
    """Every drawn x-coordinate must fit inside the declared width — the 'Total'
    bracket spans sum(units), which is wider than the longest bar, so the canvas
    must grow to fit it (regression: bracket was clipping off the right edge)."""
    for params in _golden_params() + [
        {"names": ["A", "B", "C"], "ratio": [1, 2, 9], "total": 108},  # lopsided
    ]:
        solution, diagram = _built(params)
        svg = render_svg(diagram)
        width = int(re.search(r'width="(\d+)"', svg).group(1))
        xs = [int(v) for v in re.findall(r'x[12]?="(\d+)"', svg)]
        assert xs, "expected x coordinates in the svg"
        assert max(xs) <= width, f"coordinate {max(xs)} exceeds canvas width {width}"


# --- spec shape & schema validity ------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_generated_object_carries_valid_bar_model(seed: int):
    obj = generate("ratio_medium", seed)
    assert validate_object(obj) == []  # schema-valid WITH a diagram present
    diagram = obj["question"]["parts"][0]["diagram"]
    assert diagram is not None
    assert diagram["type"] == "bar_model"

    ratio = obj["parameters"]["ratio"]
    names = obj["parameters"]["names"]
    assert [b["units"] for b in diagram["bars"]] == ratio
    assert [b["label"] for b in diagram["bars"]] == names
    assert obj["validation"]["checks"]["diagram_consistent"] is True


# --- consistency check (R3.3) ----------------------------------------------


def test_consistency_passes_for_built_spec():
    params = _golden_params()[0]
    solution, diagram = _built(params)
    checks = check_consistency(diagram, params, solution)
    assert all(checks.values()), checks


def test_consistency_rejects_corrupted_units():
    params = _golden_params()[0]
    solution, diagram = _built(params)
    bad = copy.deepcopy(diagram)
    bad["bars"][0]["units"] += 1  # no longer equals ratio[0]
    checks = check_bar_model_consistency(bad, params, solution)
    assert checks["bar_units"] is False
    assert not all(checks.values())


def test_consistency_rejects_corrupted_label():
    params = _golden_params()[0]
    solution, diagram = _built(params)
    bad = copy.deepcopy(diagram)
    bad["bars"][1]["label"] = "Nobody"
    checks = check_bar_model_consistency(bad, params, solution)
    assert checks["bar_labels"] is False


def test_consistency_rejects_corrupted_annotation():
    params = _golden_params()[0]
    solution, diagram = _built(params)
    bad = copy.deepcopy(diagram)
    bad["annotations"][1]["label"] = "Total = $999999"
    checks = check_bar_model_consistency(bad, params, solution)
    assert checks["total_annotation"] is False


def test_consistency_rejects_missing_bar():
    params = _golden_params()[0]
    solution, diagram = _built(params)
    bad = copy.deepcopy(diagram)
    del bad["bars"][0]
    checks = check_bar_model_consistency(bad, params, solution)
    assert checks["bar_count"] is False


# --- SVG render (R3.4) ------------------------------------------------------


def test_svg_render_smoke():
    params = {"names": ["Aisha", "Ben", "Chloe"], "ratio": [2, 3, 5], "total": 200}
    solution, diagram = _built(params)
    svg = render_svg(diagram)

    assert svg
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "viewBox" in svg
    for name in params["names"]:
        assert name in svg
    # annotation values present (1 unit = $20, Total = $200)
    assert "1 unit = $20" in svg
    assert "Total = $200" in svg
    # one divider line per interior unit boundary across the three bars
    assert svg.count("<rect") == len(params["ratio"])


def test_svg_escapes_text():
    spec = {
        "type": "bar_model",
        "bars": [{"label": "A & <B>", "units": 1}],
        "annotations": [],
    }
    svg = render_svg(spec)
    assert "A &amp; &lt;B&gt;" in svg
    assert "<B>" not in svg


def test_render_svg_rejects_unknown_type():
    with pytest.raises(ValueError):
        render_svg({"type": "composite_geometry"})


# --- determinism ------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_svg_is_deterministic(seed: int):
    a = generate("ratio_medium", seed)
    b = generate("ratio_medium", seed)
    svg_a = render_svg(a["question"]["parts"][0]["diagram"])
    svg_b = render_svg(b["question"]["parts"][0]["diagram"])
    assert svg_a == svg_b


# --- golden coverage for the diagram ---------------------------------------


def test_golden_diagram_bars_match_params():
    for params in _golden_params():
        _, diagram = _built(params)
        assert [b["units"] for b in diagram["bars"]] == params["ratio"]
        assert [b["label"] for b in diagram["bars"]] == params["names"]
