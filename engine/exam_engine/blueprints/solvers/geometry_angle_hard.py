"""Solver for ``geometry_angle_hard`` (KAN-229): P6 composite figures.

A triangle sharing an edge with a special quadrilateral; a multi-step chain that
combines two shape properties (strictly PSLE, no additional construction — V6b
geometry plan). Two structurally-distinct templates:

* ``parallelogram`` — parallelogram ABCD with side AB extended to E and triangle
  BCE. AD ∥ BC with transversal ABE gives ∠CBE = ∠DAB (corresponding angles);
  then triangle-BCE angle sum gives ∠BCE.
* ``rhombus`` — rhombus ABCD with diagonal AC. Equal sides make triangle ABC
  isosceles (AB = BC), so the base angles equal (180 − ∠ABC) ÷ 2.

Answer: integer ``degrees``; mandatory ``geometry_figure`` aid, verified by the
consistency check. Exact integer arithmetic (rhombus apex sampled even) — the
printed key is provably the figure's solution.
"""

from __future__ import annotations

import random

from ..registry import register

_UNIT = "degrees"


def _pt(pid: str, x: float, y: float) -> dict:
    return {"id": pid, "x": float(x), "y": float(y)}


def _labels(point_ids: list[str]) -> list[dict]:
    return [{"at": pid, "text": pid} for pid in point_ids]


def _build_parallelogram(g: dict) -> dict:
    a, e = g["a"], g["e"]
    ans = 180 - a - e
    # ABCD parallelogram (AD ∥ BC, AB ∥ DC); AB extended past B to E; triangle BCE.
    points = [
        _pt("A", 0, 0),
        _pt("B", 4, 0),
        _pt("C", 5, 5),
        _pt("D", 1, 5),
        _pt("E", 7, 0),
    ]
    segments = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
        {"from": "B", "to": "E"},
        {"from": "C", "to": "E"},
    ]
    angles = [
        {"at": "A", "from": "D", "to": "B", "value_deg": a, "unknown": False},
        {"at": "E", "from": "B", "to": "C", "value_deg": e, "unknown": False},
        {"at": "C", "from": "B", "to": "E", "value_deg": ans, "unknown": True},
    ]
    given_map = {"D-A-B": a, "B-E-C": e}
    text = (
        f"In the figure, ABCD is a parallelogram and ABE is a straight line. "
        f"∠DAB = {a}° and ∠BEC = {e}°. "
        f"Find ∠BCE. (The figure is not drawn to scale.)"
    )
    steps = [
        f"AD ∥ BC and ABE is a straight line, so ∠CBE = ∠DAB = {a}° (corresponding angles).",
        f"In triangle BCE, ∠BCE = 180° − {a}° − {e}° = {ans}°.",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "labels": _labels(["A", "B", "C", "D", "E"]),
        "given_map": given_map,
        "answer": ans,
        "text": text,
        "steps": steps,
    }


def _build_rhombus(g: dict) -> dict:
    b = g["b"]
    ans = (180 - b) // 2
    # Rhombus ABCD drawn as a diamond; diagonal AC; triangle ABC (top half).
    points = [_pt("A", 0, 4), _pt("B", 4, 0), _pt("C", 8, 4), _pt("D", 4, 8)]
    segments = [
        {"from": "A", "to": "B", "ticks": 1},
        {"from": "B", "to": "C", "ticks": 1},
        {"from": "C", "to": "D", "ticks": 1},
        {"from": "D", "to": "A", "ticks": 1},
        {"from": "A", "to": "C"},
    ]
    angles = [
        {"at": "B", "from": "A", "to": "C", "value_deg": b, "unknown": False},
        {"at": "A", "from": "B", "to": "C", "value_deg": ans, "unknown": True},
    ]
    given_map = {"A-B-C": b}
    text = (
        f"In the figure, ABCD is a rhombus and AC is a diagonal. "
        f"∠ABC = {b}°. "
        f"Find ∠BAC. (The figure is not drawn to scale.)"
    )
    steps = [
        "ABCD is a rhombus, so AB = BC and triangle ABC is isosceles.",
        f"∠BAC = (180° − {b}°) ÷ 2 = {ans}°.",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "labels": _labels(["A", "B", "C", "D"]),
        "given_map": given_map,
        "answer": ans,
        "text": text,
        "steps": steps,
    }


_BUILDERS = {
    "parallelogram": _build_parallelogram,
    "rhombus": _build_rhombus,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


class GeometryAngleHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_BUILDERS))
        if template == "parallelogram":
            while True:
                a = rng.randint(55, 110)
                e = rng.randint(30, 70)
                if 180 - a - e >= 20:
                    break
            givens = {"a": a, "e": e}
        else:  # rhombus
            b = rng.randrange(40, 141, 2)  # even -> whole base angle
            givens = {"b": b}
        built = _BUILDERS[template](givens)
        return {"template": template, "givens": givens, "angles": built["given_map"]}

    def solve(self, params: dict) -> dict:
        built = _build(params)
        ans = built["answer"]
        return {
            "answer": {"type": "integer", "value": ans, "unit": _UNIT},
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
        if template == "parallelogram":
            # ∠CBE = ∠DAB = a (corresponding), then triangle BCE sum: a + e + ans = 180.
            checks["rule"] = g["a"] + g["e"] + ans == 180
        else:  # rhombus: isosceles triangle ABC, apex b -> base angles.
            checks["rule"] = g["b"] + 2 * ans == 180
        checks["answer_verified"] = solution["answer"]["value"] == ans
        checks["unit_degrees"] = solution["answer"]["unit"] == _UNIT
        checks["in_range"] = 0 < ans < 180
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        built = _build(params)
        return {
            "type": "geometry_figure",
            "unit": _UNIT,
            "points": built["points"],
            "segments": built["segments"],
            "angles": built["angles"],
            "labels": built["labels"],
        }


register("geometry_angle_hard", GeometryAngleHardSolver())
