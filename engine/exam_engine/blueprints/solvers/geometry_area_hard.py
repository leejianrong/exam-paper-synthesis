"""Solver for ``geometry_area_hard`` (KAN-230): shaded area / inverse length.

Strictly-PSLE composite figures (V6b geometry plan). Two structurally-distinct
templates:

* ``square_minus_quarter`` — a square with a quarter circle (radius = side,
  centred on a corner) removed; shaded area = square − quarter circle. π
  auto-select (G4): ``22/7`` when the side is a multiple of 7 (whole answer),
  else ``3.14`` (2-dp decimal).
* ``inverse_rectangle``    — the inverse direction: a rectangle's area and length
  are given, find the (unknown) width by ``width = area ÷ length``.

Answers are ``cm^2`` for the shaded area, ``cm`` for the recovered length; the
mandatory ``geometry_figure`` aid carries the labelled dimensions, cross-verified
by ``check_geometry_figure_consistency``. Exact rational arithmetic — the printed
key is provably the figure's solution (no LLM).
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register
from .geometry_area_common import (
    AREA_UNIT,
    LEN_UNIT,
    _labels,
    _pt,
    format_measure,
    pi_str_for,
    pi_value,
)


def _build_square_minus_quarter(g: dict) -> dict:
    s = g["s"]
    pi_str = pi_str_for(s)
    square_area = s * s
    quarter_exact = pi_value(pi_str) * s * s / 4
    quarter = format_measure(quarter_exact, AREA_UNIT)
    shaded_exact = square_area - quarter_exact
    answer = format_measure(shaded_exact, AREA_UNIT)
    # Square ABCD (side s); quarter circle centred at A, radius s, arc B -> D.
    points = [_pt("A", 0, 0), _pt("B", s, 0), _pt("C", s, s), _pt("D", 0, s)]
    segments = [
        {"from": "A", "to": "B", "label": f"{s} cm"},
        {"from": "A", "to": "D", "label": f"{s} cm"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
    ]
    arcs = [{"center": "A", "radius": s, "start_deg": 0, "end_deg": 90, "label": None}]
    text = (
        f"The figure (not drawn to scale) shows a square of side {s} cm. A quarter "
        f"circle of radius {s} cm is drawn inside it, with its centre at one corner. "
        f"Take π = {pi_str}. Find the area of the shaded region (the part of the "
        f"square outside the quarter circle)."
    )
    steps = [
        f"Take π = {pi_str}. Area of the square = {s} cm × {s} cm = {square_area} cm².",
        f"Area of the quarter circle = π × {s} × {s} ÷ 4 = {quarter['value']} cm².",
        f"Shaded area = {square_area} cm² − {quarter['value']} cm² = {answer['value']} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "arcs": arcs,
        "angles": [],
        "shaded": [],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": s, "A-D": s},
        "radii": {"A": s},
        "answer": answer,
        "text": text,
        "steps": steps,
    }


def _build_inverse_rectangle(g: dict) -> dict:
    length, width = g["length"], g["width"]
    area = length * width
    answer = {"type": "integer", "value": width, "unit": LEN_UNIT}
    points = [_pt("A", 0, 0), _pt("B", length, 0), _pt("C", length, width), _pt("D", 0, width)]
    segments = [
        {"from": "A", "to": "B", "label": f"{length} cm"},
        {"from": "B", "to": "C", "label": "? cm"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ]
    angles = [{"at": "A", "from": "B", "to": "D", "right": True}]
    text = (
        f"A rectangle has an area of {area} cm² and a length of {length} cm. "
        f"Find its width. (The figure is not drawn to scale.)"
    )
    steps = [
        "Area of a rectangle = length × width.",
        f"Width = Area ÷ length = {area} cm² ÷ {length} cm",
        f"Width = {width} cm.",
    ]
    return {
        "points": points,
        "segments": segments,
        "arcs": [],
        "angles": angles,
        "shaded": [{"boundary": ["A", "B", "C", "D"]}],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": length},
        "radii": {},
        "answer": answer,
        "text": text,
        "steps": steps,
    }


_BUILDERS = {
    "square_minus_quarter": _build_square_minus_quarter,
    "inverse_rectangle": _build_inverse_rectangle,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


class GeometryAreaHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_BUILDERS))
        if template == "square_minus_quarter":
            if rng.random() < 0.5:
                s = 14 * rng.randint(1, 2)  # 14 / 28 -> multiple of 7 -> 22/7, whole
            else:
                s = rng.choice([8, 10, 12, 16, 18, 20])  # even, not mult of 7 -> 3.14
            givens = {"s": s}
        else:  # inverse_rectangle
            givens = {"length": rng.randint(4, 15), "width": rng.randint(3, 14)}
        built = _BUILDERS[template](givens)
        out = {"template": template, "givens": givens, "lengths": built["lengths"]}
        if built["radii"]:
            out["radii"] = built["radii"]
        return out

    def solve(self, params: dict) -> dict:
        built = _build(params)
        return {
            "answer": built["answer"],
            "intermediates": {
                "question_text": built["text"],
                "step1": built["steps"][0],
                "step2": built["steps"][1],
                "step3": built["steps"][2],
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        g = params["givens"]
        template = params["template"]
        checks: dict[str, bool] = {}
        if template == "square_minus_quarter":
            s = g["s"]
            shaded_exact = s * s - pi_value(pi_str_for(s)) * s * s / 4
            expected = format_measure(shaded_exact, AREA_UNIT)
            checks["shaded_nonneg"] = shaded_exact > 0
        else:  # inverse_rectangle: width recovered from area ÷ length is exact.
            area = g["length"] * g["width"]
            expected = {"type": "integer", "value": area // g["length"], "unit": LEN_UNIT}
            checks["inverse_exact"] = area % g["length"] == 0 and area // g["length"] == g["width"]
        checks["answer_verified"] = solution["answer"] == expected == built["answer"]
        checks["positive"] = Fraction(str(solution["answer"]["value"])) > 0
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        return {
            "type": "geometry_figure",
            "unit": "cm",
            "points": built["points"],
            "segments": built["segments"],
            "arcs": built["arcs"],
            "angles": built["angles"],
            "shaded": built["shaded"],
            "labels": built["labels"],
        }


register("geometry_area_hard", GeometryAreaHardSolver())
