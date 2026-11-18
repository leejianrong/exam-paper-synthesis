"""The ``net`` diagram (schema 1.13.0, EXA-147) and the cube_stack "Front" arrow."""

from __future__ import annotations

import copy
import re
from itertools import product

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.cube_stack import readable, visible_cubes
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.net import check_net_consistency, fold, normalise, opposite
from exam_engine.schema import validate_diagram
from svg_labels import collisions

CROSS = [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (3, 1)]


def _spec(cells=CROSS, shaded=None) -> dict:
    return {
        "type": "net",
        "faces": [
            {"row": r, "col": c, "label": "ABCDEF"[i]} | ({"shaded": True} if i == shaded else {})
            for i, (r, c) in enumerate(cells)
        ],
    }


def test_a_net_validates_and_passes_the_gate():
    spec = _spec()
    assert validate_diagram(spec) == []
    assert all(check_net_consistency(spec).values())
    assert all(check_consistency(spec, {}, {}).values())
    canonical.load_diagram(spec)


@pytest.mark.parametrize(
    ("change", "fails"),
    [
        (lambda s: s["faces"][1].update(row=0, col=1), "cells_distinct"),
        (lambda s: s["faces"][5].update(row=5, col=5), "squares_joined"),
        (lambda s: s["faces"][1].update(label="A"), "labels_unique"),
    ],
)
def test_the_gate_refuses_a_broken_net(change, fails):
    spec = copy.deepcopy(_spec())
    change(spec)
    assert check_net_consistency(spec)[fails] is False
    with pytest.raises(CanonicalValidationError, match=fails):
        canonical.load_diagram(spec)


def test_the_schema_wants_six_squares():
    spec = _spec()
    spec["faces"].pop()
    assert validate_diagram(spec) != []


def _free(cells) -> tuple:
    """A shape up to turning and flipping."""
    forms = []
    for flip, turns in product((False, True), range(4)):
        pts = [(r, -c) if flip else (r, c) for r, c in cells]
        for _ in range(turns):
            pts = [(c, -r) for r, c in pts]
        forms.append(tuple(normalise(pts)))
    return min(forms)


def test_fold_finds_the_eleven_nets_of_a_cube():
    """All 35 hexominoes, grown square by square: exactly 11 fold into a cube."""
    shapes = {((0, 0),)}
    for _ in range(5):
        shapes = {
            tuple(normalise([*s, (r + dr, c + dc)]))
            for s in shapes
            for r, c in s
            for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))
            if (r + dr, c + dc) not in s
        }
    free = {_free(s) for s in shapes}
    assert len(free) == 35
    assert sum(fold(list(s)) is not None for s in free) == 11


def test_opposite_faces_of_the_cross():
    assert opposite(CROSS, (0, 1)) == (2, 1)
    assert opposite(CROSS, (1, 0)) == (1, 2)
    assert opposite(CROSS, (1, 1)) == (3, 1)
    assert opposite([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 0)], (0, 0)) is None


def test_render_labels_shading_and_clear_text():
    svg = render_svg(_spec(shaded=2))
    assert svg.count("<rect") == 6
    assert re.findall(r">([A-F])</text>", svg) == list("ABCDEF")
    assert svg.count('fill="#d0d0d0"') == 1  # palette.SHADE, the one shaded face
    assert collisions(svg) == []


def test_front_arrow_only_on_the_iso_picture():
    spec = {"type": "cube_stack", "heights": [[2, 1], [1, 1]], "show_front": True}
    assert validate_diagram(spec) == []
    svg = render_svg(spec)
    assert ">Front</text>" in svg and collisions(svg) == []
    assert ">Front</text>" not in render_svg({**spec, "show_front": False})
    with pytest.raises(CanonicalValidationError, match="front_arrow_on_iso"):
        canonical.load_diagram({**spec, "view": "front"})


def test_readable_and_visible_cubes():
    assert readable([[2, 2], [1, 1]]) and visible_cubes([[2, 2], [1, 1]]) == 5  # 1 hidden
    # a stack one row nearer and one column to the right, a cube taller, hides the top
    assert not readable([[1, 1], [1, 2]])
