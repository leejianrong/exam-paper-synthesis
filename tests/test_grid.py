"""EXA-144 — the ``grid`` diagram (schema 1.13.0): consistency gate and renderer."""

from __future__ import annotations

import copy

import pytest
from exam_engine import canonical, palette
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.grid import check_grid_consistency, is_simple
from exam_engine.pipeline import generate
from exam_engine.schema import validate_diagram
from svg_labels import collisions

SPEC = {
    "type": "grid",
    "cols": 8,
    "rows": 6,
    "cells": [{"col": 1, "row": 1}, {"col": 2, "row": 1, "shaded": False, "label": "A"}],
    "polygons": [{"vertices": [[3, 1], [6, 1], [6, 3], [4, 4]], "shaded": True}],
    "segments": [{"from": [0, 5], "to": [8, 5], "dashed": True}],
    "points": [{"x": 1, "y": 4, "label": "P"}, {"x": 7, "y": 4, "label": "Q"}],
    "compass": True,
}


def test_a_full_spec_is_schema_valid_and_consistent():
    assert validate_diagram(SPEC) == []
    assert all(check_grid_consistency(SPEC).values())
    assert all(check_consistency(SPEC, {}, {}).values())


@pytest.mark.parametrize(
    ("change", "failing"),
    [
        (lambda s: s.update(cols=0), "size_in_range"),
        (lambda s: s.update(rows=13), "size_in_range"),
        (lambda s: s["cells"].append({"col": 8, "row": 0}), "cells_inside"),
        (lambda s: s["cells"].append({"col": 1, "row": 1}), "cells_unique"),
        (lambda s: s["polygons"][0]["vertices"].append([9, 1]), "polygons_inside"),
        (
            lambda s: s["polygons"].append({"vertices": [[0, 0], [2, 2], [2, 0], [0, 2]]}),
            "polygons_simple",
        ),
        (lambda s: s["polygons"].append({"vertices": [[0, 0], [1, 0], [2, 0]]}), "polygons_simple"),
        (lambda s: s["segments"].append({"from": [0, 0], "to": [0, 7]}), "segments_inside"),
        (lambda s: s["segments"].append({"from": [2, 2], "to": [2, 2]}), "segments_not_points"),
        (lambda s: s["points"].append({"x": 9, "y": 0, "label": "R"}), "points_inside"),
        (lambda s: s["points"].append({"x": 1, "y": 4, "label": "R"}), "points_distinct"),
        (lambda s: s["points"].append({"x": 0, "y": 0, "label": "A"}), "labels_unique"),
    ],
)
def test_each_invariant_catches_its_fault(change, failing):
    s = copy.deepcopy(SPEC)
    change(s)
    assert check_grid_consistency(s)[failing] is False


def test_junk_never_raises():
    for junk in [
        {},
        {"cols": "x"},
        {"cols": [8], "rows": {}},
        {"cols": 3, "rows": 3, "polygons": [{"vertices": "no"}]},
        {"cols": 3, "rows": 3, "cells": [{"col": [1], "row": 0, "label": ["A"]}]},
        {"cols": 3, "rows": 3, "points": [{"x": 0, "y": 0, "label": ["A"]}]},
    ]:
        out = check_grid_consistency(junk)
        assert isinstance(out, dict) and all(isinstance(v, bool) for v in out.values())
    assert not check_grid_consistency({"cols": [8], "rows": 6})["size_in_range"]


def test_simple_polygons():
    assert is_simple([(0, 0), (2, 0), (2, 2), (0, 2)])
    assert not is_simple([(0, 0), (2, 0), (0, 2), (2, 2)])  # a bow tie
    assert not is_simple([(0, 0), (2, 0), (1, 0), (1, 1)])  # a side folds back on itself
    assert not is_simple([(0, 0), (1, 0), (0, 0), (0, 1)])  # a repeated corner


def test_the_load_gate_rejects_an_inconsistent_grid():
    obj = copy.deepcopy(generate("grid_lines", 1))
    obj["question"]["parts"][0]["diagram"]["points"][0]["x"] = 40
    with pytest.raises(canonical.CanonicalValidationError, match="grid inconsistent"):
        canonical.load(obj)


def test_render_is_deterministic_grey_and_labels_are_clear():
    svg = render_svg(SPEC)
    assert svg == render_svg(copy.deepcopy(SPEC))
    assert svg.startswith("<svg") and 'stroke-dasharray="6 4"' in svg
    for letter in ("A", "P", "Q", "N", "E", "S", "W"):
        assert f">{letter}</text>" in svg
    assert palette.SHADE in svg and palette.GRID in svg
    assert collisions(svg) == []


def test_dot_grid_draws_dots_not_lines():
    spec = {**copy.deepcopy(SPEC), "style": "dots"}
    svg = render_svg(spec)
    assert palette.GRID not in svg  # no grid lines
    assert svg.count("<circle") >= (spec["cols"] + 1) * (spec["rows"] + 1)
    assert collisions(svg) == []


def test_a_point_letter_never_sits_on_a_grid_line():
    """Letters go inside a square next to the point, for every point on a crowded grid."""
    spec = {
        "type": "grid",
        "cols": 4,
        "rows": 3,
        "points": [
            {"x": x, "y": y, "label": chr(65 + 3 * x + y)} for x in range(0, 5, 2) for y in (0, 2)
        ],
        "segments": [{"from": [0, 0], "to": [4, 2]}],
    }
    assert all(check_grid_consistency(spec).values())
    assert collisions(render_svg(spec)) == []
