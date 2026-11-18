"""Solver for ``geometry_area_perimeter`` (EXA-154): go from a rectangle's (or square's)
perimeter to its area, or from its area to its perimeter. The 2-mark medium rung between
``geometry_area_easy`` (one area formula) and ``geometry_area_medium`` (composite figures,
3 marks): the missing side has to be found first.

* ``area_from_perimeter`` — perimeter P and length L given: width = P ÷ 2 − L, area = L × W.
* ``perimeter_from_area`` — area and length L given: width = area ÷ L, perimeter = 2 × (L + W).
* ``square_area``         — a square's perimeter P given: side = P ÷ 4, area = side × side.

The figure labels only the given length (the missing side is not labelled), marks the right
angle and, for the square, ticks the four equal sides; ``check_geometry_figure_consistency``
cross-checks the label against ``params["lengths"]``. Exact integer arithmetic throughout.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register
from .geometry_area_common import AREA_UNIT, LEN_UNIT, _labels, _pt

TEMPLATES = ("area_from_perimeter", "perimeter_from_area", "square_area")


def _build(params: dict) -> dict:
    g, template = params["givens"], params["template"]
    if template == "square_area":
        side = g["side"]
        per = 4 * side
        points = [_pt("A", 0, 0), _pt("B", side, 0), _pt("C", side, side), _pt("D", 0, side)]
        segments = [{"from": a, "to": b, "ticks": 1} for a, b in ("AB", "BC", "CD", "DA")]
        text = f"ABCD is a square. Its perimeter is {per} cm. Find the area of the square."
        steps = [
            f"Length of one side = {per} cm ÷ 4 = {side} cm.",
            f"Area = {side} cm × {side} cm = {side * side} cm².",
        ]
        answer = {"type": "integer", "value": side * side, "unit": AREA_UNIT}
        lengths: dict[str, int] = {}
    else:
        L, W = g["length"], g["width"]
        points = [_pt("A", 0, 0), _pt("B", L, 0), _pt("C", L, W), _pt("D", 0, W)]
        segments = [
            {"from": "A", "to": "B", "label": f"{L} cm"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "D"},
            {"from": "D", "to": "A"},
        ]
        lengths = {"A-B": L}
        if template == "area_from_perimeter":
            per = 2 * (L + W)
            text = (
                f"ABCD is a rectangle. Its perimeter is {per} cm and AB = {L} cm. "
                f"Find the area of the rectangle."
            )
            steps = [
                f"BC = {per} cm ÷ 2 − {L} cm = {W} cm.",
                f"Area = {L} cm × {W} cm = {L * W} cm².",
            ]
            answer = {"type": "integer", "value": L * W, "unit": AREA_UNIT}
        else:
            area = L * W
            text = (
                f"ABCD is a rectangle. Its area is {area} cm² and AB = {L} cm. "
                f"Find the perimeter of the rectangle."
            )
            steps = [
                f"BC = {area} cm² ÷ {L} cm = {W} cm.",
                f"Perimeter = 2 × ({L} cm + {W} cm) = {2 * (L + W)} cm.",
            ]
            answer = {"type": "integer", "value": 2 * (L + W), "unit": LEN_UNIT}
    return {
        "points": points,
        "segments": segments,
        "angles": [{"at": "A", "from": "B", "to": "D", "right": True}],
        "shaded": [{"boundary": ["A", "B", "C", "D"]}],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": lengths,
        "answer": answer,
        "text": text,
        "steps": steps,
    }


class GeometryAreaPerimeterSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(TEMPLATES)
        if template == "square_area":
            givens = {"side": rng.randint(4, 15)}
        else:
            length = rng.randint(8, 20)
            givens = {"length": length, "width": rng.randint(3, length - 2)}
        params = {"template": template, "givens": givens}
        params["lengths"] = _build(params)["lengths"]
        return params

    def solve(self, params: dict) -> dict:
        built = _build(params)
        return {
            "answer": built["answer"],
            "intermediates": {
                "question_text": built["text"],
                "step1": built["steps"][0],
                "step2": built["steps"][1],
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers in the answer's own unit (cm² or cm), best first (EXA-122)."""
        g, template = params["givens"], params["template"]
        if template == "square_area":
            s = g["side"]
            return [
                (4 * s, "the perimeter, not the area"),
                (s, "the length of one side only"),
                (2 * s * 2 * s, "took half the perimeter as the side"),
                (2 * s, "doubled the side instead of squaring it"),
            ]
        L, W = g["length"], g["width"]
        if template == "area_from_perimeter":
            per = 2 * (L + W)
            return [
                (L * (per - 2 * L), "forgot to halve: took BC as the perimeter − 2 × AB"),
                (L * (per - L), "took BC as the perimeter − AB"),
                (W, "the length of BC only"),
                (Fraction(per * L, 2), "took half the perimeter as BC"),
            ]
        return [
            (L + W, "half the perimeter (AB + BC only)"),
            (2 * L + W, "left out one side"),
            (L * W - L, "took away AB from the area"),
            (W, "the length of BC only"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        g, template = params["givens"], params["template"]
        checks: dict[str, bool] = {}
        if template == "square_area":
            checks["shape_ok"] = g["side"] > 0
            expected = g["side"] ** 2
        else:
            checks["shape_ok"] = 0 < g["width"] < g["length"]
            if template == "area_from_perimeter":
                expected = g["length"] * g["width"]
            else:
                expected = 2 * (g["length"] + g["width"])
        checks["answer_verified"] = solution["answer"]["value"] == expected
        checks["lengths_contract"] = params.get("lengths", {}) == _build(params)["lengths"]
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        return {
            "type": "geometry_figure",
            "unit": "cm",
            "points": built["points"],
            "segments": built["segments"],
            "arcs": [],
            "angles": built["angles"],
            "shaded": built["shaded"],
            "labels": built["labels"],
        }


register("geometry_area_perimeter", GeometryAreaPerimeterSolver())
