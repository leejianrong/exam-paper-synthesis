"""Solver for ``geometry_area_medium`` (KAN-230): composite polygon / circle part.

Strictly-PSLE area/perimeter figures (V6b geometry plan). Structurally-distinct
templates:

* ``L_shape``             — an L-shaped polygon (a rectangle with a rectangular
  corner removed); area = big rectangle − removed corner.
* ``semicircle_area``     — area of a semicircle, ``π × r × r ÷ 2``.
* ``semicircle_perimeter``— perimeter of a semicircle, ``π × r + 2 × r``.

The two semicircle templates auto-select π (G4): ``22/7`` when the radius is a
multiple of 7 (whole answer), else ``3.14`` (2-dp decimal). Answers are ``cm^2``
for area, ``cm`` for perimeter; the mandatory ``geometry_figure`` aid carries the
labelled dimensions/radius, cross-verified by ``check_geometry_figure_consistency``
against ``params["lengths"]`` / ``params["radii"]``. Exact rational arithmetic —
the printed key is provably the figure's solution (no LLM).
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


def _ans_text(answer: dict) -> str:
    return str(answer["value"])


def _build_l_shape(g: dict) -> dict:
    big_w, big_h, notch_w, notch_h = g["W"], g["H"], g["w"], g["h"]
    ans = big_w * big_h - notch_w * notch_h
    # Big rectangle [0,W]x[0,H] with the top-right notch [W-w,W]x[H-h,H] removed.
    points = [
        _pt("A", 0, 0),
        _pt("B", big_w, 0),
        _pt("C", big_w, big_h - notch_h),
        _pt("D", big_w - notch_w, big_h - notch_h),
        _pt("E", big_w - notch_w, big_h),
        _pt("F", 0, big_h),
    ]
    segments = [
        {"from": "A", "to": "B", "label": f"{big_w} cm"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D", "label": f"{notch_w} cm"},
        {"from": "D", "to": "E", "label": f"{notch_h} cm"},
        {"from": "E", "to": "F"},
        {"from": "F", "to": "A", "label": f"{big_h} cm"},
    ]
    text = (
        "The figure (not drawn to scale) shows an L-shaped figure made from "
        "rectangles. Find the area of the figure."
    )
    steps = [
        f"Area of the whole rectangle = {big_w} cm × {big_h} cm = {big_w * big_h} cm².",
        f"Area of the removed corner = {notch_w} cm × {notch_h} cm = {notch_w * notch_h} cm².",
        f"Area of the L-shape = {big_w * big_h} cm² − {notch_w * notch_h} cm² = {ans} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": [],
        "arcs": [],
        "shaded": [{"boundary": ["A", "B", "C", "D", "E", "F"]}],
        "labels": _labels(["A", "B", "C", "D", "E", "F"]),
        "lengths": {"A-B": big_w, "A-F": big_h, "C-D": notch_w, "D-E": notch_h},
        "radii": {},
        "answer": {"type": "integer", "value": ans, "unit": AREA_UNIT},
        "text": text,
        "steps": steps,
    }


def _semicircle_figure(r: int) -> dict:
    points = [_pt("O", r, r), _pt("P", 0, r), _pt("Q", 2 * r, r), _pt("T", r, 0)]
    segments = [
        {"from": "P", "to": "Q"},
        {"from": "O", "to": "T", "label": f"{r} cm"},
    ]
    arcs = [{"center": "O", "radius": r, "start_deg": 180, "end_deg": 360, "label": None}]
    return {
        "points": points,
        "segments": segments,
        "arcs": arcs,
        "labels": _labels(["P", "Q", "T"]),
        "lengths": {"O-T": r},
        "radii": {"O": r},
    }


def _build_semicircle_area(g: dict) -> dict:
    r = g["r"]
    pi_str = pi_str_for(r)
    exact = pi_value(pi_str) * r * r / 2
    answer = format_measure(exact, AREA_UNIT)
    fig = _semicircle_figure(r)
    text = (
        f"The figure (not drawn to scale) shows a semicircle of radius {r} cm. "
        f"Take π = {pi_str}. Find its area."
    )
    steps = [
        f"Take π = {pi_str}. Area of a semicircle = π × r × r ÷ 2.",
        f"Area = {pi_str} × {r} × {r} ÷ 2",
        f"Area = {_ans_text(answer)} cm².",
    ]
    return {**fig, "angles": [], "shaded": [], "answer": answer, "text": text, "steps": steps}


def _build_semicircle_perimeter(g: dict) -> dict:
    r = g["r"]
    pi_str = pi_str_for(r)
    exact = pi_value(pi_str) * r + 2 * r
    answer = format_measure(exact, LEN_UNIT)
    fig = _semicircle_figure(r)
    text = (
        f"The figure (not drawn to scale) shows a semicircle of radius {r} cm. "
        f"Take π = {pi_str}. Find its perimeter."
    )
    steps = [
        f"Take π = {pi_str}. Perimeter of a semicircle = π × r + 2 × r (curved edge + diameter).",
        f"Perimeter = {pi_str} × {r} + 2 × {r}",
        f"Perimeter = {_ans_text(answer)} cm.",
    ]
    return {**fig, "angles": [], "shaded": [], "answer": answer, "text": text, "steps": steps}


_BUILDERS = {
    "L_shape": _build_l_shape,
    "semicircle_area": _build_semicircle_area,
    "semicircle_perimeter": _build_semicircle_perimeter,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


def _sample_radius(rng: random.Random) -> int:
    # Half the time a multiple of 7 (22/7 path, whole answer); else the 3.14 path.
    if rng.random() < 0.5:
        return 7 * rng.randint(1, 2)
    return rng.choice([4, 5, 6, 8, 9, 10, 11, 12, 13])


class GeometryAreaMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_BUILDERS))
        if template == "L_shape":
            big_w = rng.randint(12, 20)
            big_h = rng.randint(9, 14)
            notch_w = rng.randint(3, big_w - 5)
            notch_h = rng.randint(3, big_h - 4)
            givens = {"W": big_w, "H": big_h, "w": notch_w, "h": notch_h}
        else:  # semicircle_area / semicircle_perimeter
            givens = {"r": _sample_radius(rng)}
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
        # Independent recomputation of the measure via exact rational arithmetic.
        if template == "L_shape":
            expected = {
                "type": "integer",
                "value": g["W"] * g["H"] - g["w"] * g["h"],
                "unit": AREA_UNIT,
            }
            checks["geometry_ok"] = 0 < g["w"] < g["W"] and 0 < g["h"] < g["H"]
        elif template == "semicircle_area":
            expected = format_measure(pi_value(pi_str_for(g["r"])) * g["r"] * g["r"] / 2, AREA_UNIT)
            checks["geometry_ok"] = g["r"] > 0
        else:  # semicircle_perimeter
            expected = format_measure(pi_value(pi_str_for(g["r"])) * g["r"] + 2 * g["r"], LEN_UNIT)
            checks["geometry_ok"] = g["r"] > 0
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


register("geometry_area_medium", GeometryAreaMediumSolver())
