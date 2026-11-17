"""EXA-136: figure labels never collide with strokes, each other or the canvas edge.

Generated papers showed side lengths printed over a rectangle's edge, a vertex
letter over a right-angle mark or an angle arc, and a height's length over the
height itself. Real papers keep labels clear. ``svg_labels.collisions`` reads the
rendered SVG only (estimated text boxes vs every stroke), so it checks the
drawing independently of how the renderer placed its text.

The sweep covers every blueprint that draws a figure (seeded, so a failure
reproduces) and every hand-built figure kind: the sourced stand-in fixtures
(chart, solid, number line, cube stack, panels, grid figures) and the
hand-written geometry specs of ``test_geometry_figure``.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest
from exam_engine.blueprints.registry import content_dir
from exam_engine.diagram import render_svg
from exam_engine.pipeline import generate
from svg_labels import collisions, parse
from test_geometry_figure import (
    ANGLE_SPEC,
    AREA_SPEC,
    SHADED_ARC_SPEC,
    STEM_SPEC,
    TRACK_SPEC,
)

SEEDS = range(1, 41)
SOURCED = Path(__file__).parent / "fixtures" / "sourced"


def _figures(obj: dict) -> list[tuple[dict, dict | None]]:
    """Every (spec, given) a printed question or its key draws."""
    q = obj["question"]
    stem = obj.get("diagram") or q.get("diagram")
    out = [(stem, None)] if stem else []
    for part in q["parts"]:
        if part.get("diagram"):
            out.append((part["diagram"], None))
        answer = part.get("answer")
        if isinstance(answer, dict) and answer.get("diagram"):
            out.append((answer["diagram"], part.get("diagram") or stem))
    return [(s, g) for s, g in out if s.get("type") != "raster"]


def _drawing_blueprints() -> list[str]:
    codes = sorted(p.stem for p in (content_dir() / "blueprints").glob("*.yaml"))
    return [c for c in codes if _figures(generate(c, 1))]


DRAWING = _drawing_blueprints()


def test_the_sweep_sees_every_figure_family():
    kinds = {s["type"] for c in DRAWING for s, _ in _figures(generate(c, 1))}
    assert {"geometry_figure", "bar_model", "chart", "solid"} <= kinds, kinds
    assert any(c.startswith("geometry_area") for c in DRAWING)


@pytest.mark.parametrize("code", DRAWING)
def test_generated_figure_labels_are_clear(code):
    bad = {}
    for seed in SEEDS:
        for spec, given in _figures(generate(code, seed)):
            problems = collisions(render_svg(spec, given=given))
            if problems:
                bad[seed] = problems
    assert not bad, f"{code}: {len(bad)} seeds, e.g. {next(iter(bad.items()))}"


def _sourced_figures() -> list[tuple[str, dict, dict | None]]:
    out = []
    for path in sorted(SOURCED.glob("*.json")):
        obj = json.loads(path.read_text("utf-8"))
        for i, (spec, given) in enumerate(_figures(obj)):
            out.append((f"{path.stem}#{i}", spec, given))
    return out


HAND_BUILT = [
    *_sourced_figures(),
    *[
        (
            f"cube_stack_{v}",
            {"type": "cube_stack", "heights": [[2, 1, 0], [1, 3, 1]], "view": v},
            None,
        )
        for v in ("iso", "front", "side", "top")
    ],
    ("angle_spec", ANGLE_SPEC, None),
    ("area_spec", AREA_SPEC, None),
    ("shaded_arc_spec", SHADED_ARC_SPEC, None),
    ("track_spec", TRACK_SPEC, None),
    ("stem_spec", STEM_SPEC, None),
    (
        "grid_axes",
        {
            "type": "geometry_figure",
            "unit": "cm",
            "points": [{"id": "A", "x": 1, "y": 1}, {"id": "B", "x": 3, "y": 2}],
            "segments": [{"from": "A", "to": "B"}],
            "labels": [{"at": "A", "text": "A"}, {"at": "B", "text": "B"}],
            "grid": {"cell_size": 1, "cols": 4, "rows": 3, "show_axes": True},
            "polygons": [{"cells": [[0, 2], [1, 2]]}],
        },
        None,
    ),
]


@pytest.mark.parametrize(("name", "spec", "given"), HAND_BUILT, ids=[h[0] for h in HAND_BUILT])
def test_hand_built_figure_labels_are_clear(name, spec, given):
    assert collisions(render_svg(spec, given=given)) == []


# --- side lengths read as the right side ------------------------------------


def _long_lines(svg: str) -> list[tuple[float, float, float, float]]:
    """Every drawn line longer than a tick mark, as (x1, y1, x2, y2)."""
    out = []
    for m in re.finditer(r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', svg):
        x1, y1, x2, y2 = (float(v) for v in m.groups())
        if math.hypot(x2 - x1, y2 - y1) > 15:
            out.append((x1, y1, x2, y2))
    return out


def _dist(line: tuple[float, float, float, float], box) -> float:
    from svg_labels import _seg_box_distance

    return _seg_box_distance(line[:2], line[2:], box)


@pytest.mark.parametrize("code", [c for c in DRAWING if c.startswith("geometry_area")])
def test_a_side_length_sits_beside_its_own_side(code):
    """A side's length is nearest a line running the same way as that side, so it
    cannot be read as another side's length (a narrow triangle's height label
    once landed beside the sloping edge)."""
    for seed in SEEDS:
        for spec, _ in _figures(generate(code, seed)):
            if spec["type"] != "geometry_figure":
                continue
            svg = render_svg(spec)
            boxes = parse(svg).labels
            lines = _long_lines(svg)
            pts = {p["id"]: (p["x"], p["y"]) for p in spec["points"]}
            for seg in spec.get("segments") or []:
                if seg.get("label") is None:
                    continue
                (ax, ay), (bx, by) = pts[seg["from"]], pts[seg["to"]]
                ux, uy = (bx - ax), (by - ay)
                ok = False
                for box in (b for b in boxes if b.text == seg["label"]):
                    near = min(_dist(ln, box) for ln in lines)
                    for ln in lines:
                        if _dist(ln, box) <= near + 0.5:
                            lx, ly = ln[2] - ln[0], ln[3] - ln[1]
                            cross = abs(ux * ly - uy * lx) / (
                                math.hypot(ux, uy) * math.hypot(lx, ly)
                            )
                            ok = ok or cross < 0.02
                assert ok, (code, seed, seg)


# --- the checker itself ------------------------------------------------------

_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60" font-size="13">'


def test_checker_flags_a_label_on_a_line():
    svg = _HEAD + '<line x1="50" y1="0" x2="50" y2="60" stroke="#000" stroke-width="2"/>'
    svg += '<text x="50" y="30" text-anchor="middle">5 cm</text></svg>'
    assert any("touches a line" in p for p in collisions(svg))


def test_checker_flags_a_label_on_an_arc_and_a_right_angle_mark():
    arc = _HEAD + '<path d="M 20 30 A 20 20 0 0 1 60 30" fill="none" stroke="#000"/>'
    assert collisions(arc + '<text x="40" y="14">A</text></svg>')
    mark = _HEAD + '<polyline points="10,40 24,40 24,54" fill="none" stroke="#000"/>'
    assert collisions(mark + '<text x="20" y="46">A</text></svg>')


def test_checker_flags_overlapping_labels_and_the_canvas_edge():
    svg = _HEAD + '<text x="40" y="30">12 cm</text><text x="50" y="32">D</text></svg>'
    assert any("overlap" in p for p in collisions(svg))
    assert any("viewBox" in p for p in collisions(_HEAD + '<text x="90" y="30">8 cm</text></svg>'))


def test_checker_passes_clear_labels_and_reads_turned_text():
    svg = _HEAD + '<line x1="50" y1="0" x2="50" y2="60" stroke="#000" stroke-width="2"/>'
    svg += '<text x="25" y="30" text-anchor="middle">5 cm</text>'
    svg += '<text x="70" y="30" text-anchor="middle" transform="rotate(-90 70 30)">4 cm</text>'
    svg += "</svg>"
    assert collisions(svg) == []
    turned = parse(svg).labels[1]
    assert turned.y1 - turned.y0 > turned.x1 - turned.x0  # runs up the page
