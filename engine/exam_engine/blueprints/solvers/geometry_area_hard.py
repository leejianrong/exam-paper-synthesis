"""Solver for ``geometry_area_hard`` (KAN-230): shaded area / composite figures.

Strictly-PSLE composite figures (V6b geometry plan). Structurally-distinct
templates:

* ``square_minus_quarter`` — a square with a quarter circle (radius = side,
  centred on a corner) removed; shaded area = square − quarter circle. π
  auto-select (G4): ``22/7`` when the side is a multiple of 7 (whole answer),
  else ``3.14`` (2-dp decimal).
* ``rectangle_with_semicircle_ends`` (KAN-233) — a running track / stadium: a
  rectangle with a semicircle on each end; perimeter = ``2 × L + 2 × π × r`` (the
  two ends form one full circle). π auto-select on the radius (G4).
* ``triangle_with_semicircle`` (KAN-233) — a triangle joined to a semicircle on
  its base (the base is the diameter); total area = ``½ × b × H + ½ × π × r²``
  with ``r = b ÷ 2``. π auto-select on the radius (G4).

(The single-step ``inverse_rectangle`` template — area ÷ length → width — was
rebalanced down to the MEDIUM rung in KAN-312: one inverse division reads as
medium, not a hard non-routine composite.)

Answers are ``cm^2`` for the shaded area, ``cm`` for the perimeter; the mandatory
``geometry_figure`` aid carries the labelled dimensions, cross-verified by
``check_geometry_figure_consistency``. Exact rational arithmetic — the printed
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
    # Shaded region = square minus the quarter disc at corner A: trace B→C→D along
    # the square edges, then close D→B along the quarter-circle arc (centre A). The
    # arc-closed boundary makes the polygon-minus-circle region fill visually.
    shaded = [
        {
            "boundary": ["B", "C", "D"],
            "arcs": [{"from": "D", "to": "B", "center": "A", "radius": s, "large": 0, "sweep": 0}],
        }
    ]
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
        "shaded": shaded,
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": s, "A-D": s},
        "radii": {"A": s},
        "answer": answer,
        "text": text,
        "steps": steps,
    }


def _build_rectangle_with_semicircle_ends(g: dict) -> dict:
    L, r = g["L"], g["r"]
    pi_str = pi_str_for(r)
    exact = 2 * L + pi_value(pi_str) * 2 * r
    answer = format_measure(exact, LEN_UNIT)
    # Stadium: rectangle x∈[0,L], y∈[0,2r]; a semicircle (radius r) at each end.
    points = [
        _pt("TL", 0, 0),
        _pt("TR", L, 0),
        _pt("BR", L, 2 * r),
        _pt("BL", 0, 2 * r),
        _pt("OL", 0, r),
        _pt("OR", L, r),
    ]
    segments = [
        {"from": "TL", "to": "TR", "label": f"{L} cm"},
        {"from": "BL", "to": "BR"},
        {"from": "OL", "to": "TL", "label": f"{r} cm"},
    ]
    arcs = [
        {"center": "OL", "radius": r, "start_deg": 90, "end_deg": 270, "label": None},
        {"center": "OR", "radius": r, "start_deg": -90, "end_deg": 90, "label": None},
    ]
    shaded = [
        {
            "boundary": ["TL", "TR", "BR", "BL"],
            "arcs": [
                {"from": "TR", "to": "BR", "center": "OR", "radius": r, "large": 0, "sweep": 1},
                {"from": "BL", "to": "TL", "center": "OL", "radius": r, "large": 0, "sweep": 1},
            ],
        }
    ]
    text = (
        "The figure (not drawn to scale) shows a running track made of a rectangle "
        f"with a semicircle at each end. Each straight side is {L} cm long and each "
        f"semicircular end has radius {r} cm. Take π = {pi_str}. Find the perimeter "
        "of the track."
    )
    steps = [
        f"Take π = {pi_str}. The two semicircular ends form one full circle, so the "
        f"curved part = 2 × π × {r} cm.",
        f"The two straight sides total 2 × {L} cm = {2 * L} cm.",
        f"Perimeter = 2 × {L} + 2 × {pi_str} × {r} = {answer['value']} cm.",
    ]
    return {
        "points": points,
        "segments": segments,
        "arcs": arcs,
        "angles": [],
        "shaded": shaded,
        "labels": _labels(["TL", "TR", "BR", "BL"]),
        "lengths": {"TL-TR": L, "OL-TL": r},
        "radii": {"OL": r, "OR": r},
        "answer": answer,
        "text": text,
        "steps": steps,
    }


def _build_triangle_with_semicircle(g: dict) -> dict:
    b, H = g["b"], g["H"]  # b = diameter of the semicircle (even), H = triangle height
    r = b // 2
    pi_str = pi_str_for(r)
    tri_exact = Fraction(b * H, 2)  # = r × H, a whole number since b is even
    semi_exact = pi_value(pi_str) * r * r / 2
    total_exact = tri_exact + semi_exact
    tri = format_measure(tri_exact, AREA_UNIT)
    semi = format_measure(semi_exact, AREA_UNIT)
    answer = format_measure(total_exact, AREA_UNIT)
    # Diameter A(0,0)–B(b,0); centre O(r,0); semicircle bulges DOWN; apex T above.
    points = [_pt("A", 0, 0), _pt("B", b, 0), _pt("T", r, -H), _pt("O", r, 0)]
    segments = [
        {"from": "A", "to": "T"},
        {"from": "B", "to": "T"},
        {"from": "A", "to": "B", "label": f"{b} cm"},
        {"from": "T", "to": "O", "label": f"{H} cm"},
    ]
    angles = [{"at": "O", "from": "T", "to": "A", "right": True}]
    arcs = [{"center": "O", "radius": r, "start_deg": 0, "end_deg": 180, "label": None}]
    shaded = [
        {
            "boundary": ["A", "T", "B"],
            "arcs": [{"from": "B", "to": "A", "center": "O", "radius": r, "large": 0, "sweep": 1}],
        }
    ]
    text = (
        "The figure (not drawn to scale) shows a triangle joined to a semicircle. "
        f"AB is the diameter of the semicircle, AB = {b} cm, and the triangle has "
        f"perpendicular height {H} cm. Take π = {pi_str}. Find the total area of the "
        "figure."
    )
    steps = [
        f"Take π = {pi_str}. Area of the triangle = ½ × {b} cm × {H} cm = {tri['value']} cm².",
        f"Radius = {b} ÷ 2 = {r} cm. Area of the semicircle = ½ × π × {r} × {r} = "
        f"{semi['value']} cm².",
        f"Total area = {tri['value']} cm² + {semi['value']} cm² = {answer['value']} cm².",
    ]
    return {
        "points": points,
        "segments": segments,
        "arcs": arcs,
        "angles": angles,
        "shaded": shaded,
        "labels": _labels(["A", "B", "T"]),
        "lengths": {"A-B": b, "T-O": H},
        "radii": {"O": r},
        "answer": answer,
        "text": text,
        "steps": steps,
    }


_BUILDERS = {
    "square_minus_quarter": _build_square_minus_quarter,
    "rectangle_with_semicircle_ends": _build_rectangle_with_semicircle_ends,
    "triangle_with_semicircle": _build_triangle_with_semicircle,
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
        elif template == "rectangle_with_semicircle_ends":
            # r a multiple of 7 -> 22/7 path (whole answer); else the 3.14 path.
            r = 7 * rng.randint(1, 2) if rng.random() < 0.5 else rng.choice([4, 5, 6, 8, 9, 10])
            givens = {"L": rng.randint(10, 25), "r": r}
        else:  # triangle_with_semicircle
            # diameter a multiple of 14 -> radius a multiple of 7 -> 22/7 path; else 3.14.
            b = 14 * rng.randint(1, 2) if rng.random() < 0.5 else rng.choice([6, 8, 10, 12, 16])
            givens = {"b": b, "H": rng.randint(5, 14)}
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
        elif template == "rectangle_with_semicircle_ends":
            L, r = g["L"], g["r"]
            perim_exact = 2 * L + pi_value(pi_str_for(r)) * 2 * r
            expected = format_measure(perim_exact, LEN_UNIT)
            checks["perimeter_pos"] = perim_exact > 0
        else:  # triangle_with_semicircle
            b, H = g["b"], g["H"]
            r = b // 2
            total_exact = Fraction(b * H, 2) + pi_value(pi_str_for(r)) * r * r / 2
            expected = format_measure(total_exact, AREA_UNIT)
            checks["even_diameter"] = b % 2 == 0
            checks["area_pos"] = total_exact > 0
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
