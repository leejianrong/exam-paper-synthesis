"""Solver for ``geometry_area_easy`` (KAN-230): single-shape area, one step.

Strictly-PSLE area figures (rectangle / square / triangle; base + perpendicular
height labelled — V6b geometry plan). Three structurally-distinct templates:

* ``rectangle`` — area = length × width.
* ``square``    — area = side × side.
* ``triangle`` — a right-angled triangle; area = ½ × base × height (the two
  perpendicular legs are labelled and the right angle is marked).

The answer is an **integer** number of ``cm^2``; the mandatory
``geometry_figure`` aid draws the labelled dimensions, and the consistency check
(``check_geometry_figure_consistency``) cross-verifies every drawn length against
``params["lengths"]``. Exact integer arithmetic (base × height is even by
construction) — the printed key is provably the figure's solution (no LLM).
"""

from __future__ import annotations

import random

from ..registry import register
from .geometry_area_common import AREA_UNIT, _labels, _pt


def _build_rectangle(g: dict) -> dict:
    w, h = g["w"], g["h"]
    ans = w * h
    points = [_pt("A", 0, 0), _pt("B", w, 0), _pt("C", w, h), _pt("D", 0, h)]
    segments = [
        {"from": "A", "to": "B", "label": f"{w} cm"},
        {"from": "B", "to": "C", "label": f"{h} cm"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ]
    angles = [{"at": "A", "from": "B", "to": "D", "right": True}]
    text = (
        f"The figure shows a rectangle measuring {w} cm by {h} cm. "
        f"Find its area. (The figure is not drawn to scale.)"
    )
    steps = [
        "Area of a rectangle = length × width.",
        f"Area = {w} cm × {h} cm = {ans} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "shaded": [{"boundary": ["A", "B", "C", "D"]}],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": w, "B-C": h},
        "answer": ans,
        "text": text,
        "steps": steps,
    }


def _build_square(g: dict) -> dict:
    s = g["s"]
    ans = s * s
    points = [_pt("A", 0, 0), _pt("B", s, 0), _pt("C", s, s), _pt("D", 0, s)]
    segments = [
        {"from": "A", "to": "B", "label": f"{s} cm"},
        {"from": "B", "to": "C", "label": f"{s} cm"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ]
    angles = [{"at": "A", "from": "B", "to": "D", "right": True}]
    text = (
        f"The figure shows a square of side {s} cm. "
        f"Find its area. (The figure is not drawn to scale.)"
    )
    steps = [
        "Area of a square = side × side.",
        f"Area = {s} cm × {s} cm = {ans} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "shaded": [{"boundary": ["A", "B", "C", "D"]}],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": s, "B-C": s},
        "answer": ans,
        "text": text,
        "steps": steps,
    }


def _build_triangle(g: dict) -> dict:
    base, height = g["base"], g["height"]
    ans = base * height // 2
    # Right-angled triangle: legs AB (base) and AC (height) meet at the right angle A.
    points = [_pt("A", 0, height), _pt("B", base, height), _pt("C", 0, 0)]
    segments = [
        {"from": "A", "to": "B", "label": f"{base} cm"},
        {"from": "A", "to": "C", "label": f"{height} cm"},
        {"from": "B", "to": "C"},
    ]
    angles = [{"at": "A", "from": "B", "to": "C", "right": True}]
    text = (
        f"The figure shows a triangle with base {base} cm and perpendicular "
        f"height {height} cm. Find its area. (The figure is not drawn to scale.)"
    )
    steps = [
        "Area of a triangle = ½ × base × height.",
        f"Area = ½ × {base} cm × {height} cm = {ans} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "shaded": [{"boundary": ["A", "B", "C"]}],
        "labels": _labels(["A", "B", "C"]),
        "lengths": {"A-B": base, "A-C": height},
        "answer": ans,
        "text": text,
        "steps": steps,
    }


_BUILDERS = {
    "rectangle": _build_rectangle,
    "square": _build_square,
    "triangle": _build_triangle,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


class GeometryAreaEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_BUILDERS))
        if template == "rectangle":
            w = rng.randint(4, 18)
            h = rng.randint(3, 15)
            givens = {"w": w, "h": h}
        elif template == "square":
            s = rng.randint(3, 15)
            givens = {"s": s}
        else:  # triangle — height even keeps ½·base·height a whole number
            base = rng.randint(5, 18)
            height = rng.randrange(4, 16, 2)
            givens = {"base": base, "height": height}
        built = _BUILDERS[template](givens)
        return {"template": template, "givens": givens, "lengths": built["lengths"]}

    def solve(self, params: dict) -> dict:
        built = _build(params)
        ans = built["answer"]
        return {
            "answer": {"type": "integer", "value": ans, "unit": AREA_UNIT},
            "intermediates": {
                "question_text": built["text"],
                "step1": built["steps"][0],
                "step2": built["steps"][1],
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        ans = built["answer"]
        g = params["givens"]
        template = params["template"]
        checks: dict[str, bool] = {}
        # Independent re-statement of each area formula.
        if template == "rectangle":
            checks["rule"] = ans == g["w"] * g["h"]
        elif template == "square":
            checks["rule"] = ans == g["s"] * g["s"]
        else:
            checks["rule"] = 2 * ans == g["base"] * g["height"]
        checks["answer_verified"] = solution["answer"]["value"] == ans
        checks["unit_area"] = solution["answer"]["unit"] == AREA_UNIT
        checks["positive"] = ans > 0
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        return {
            "type": "geometry_figure",
            "unit": "cm",
            "points": built["points"],
            "segments": built["segments"],
            "angles": built["angles"],
            "shaded": built["shaded"],
            "labels": built["labels"],
        }


register("geometry_area_easy", GeometryAreaEasySolver())
