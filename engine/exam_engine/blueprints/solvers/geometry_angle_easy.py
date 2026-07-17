"""Solver for ``geometry_angle_easy`` (KAN-229): one rule, one step.

Strictly-PSLE unknown-angle figures (polygon-only, no circles, no additional
construction of lines — V6b geometry plan). Three structurally-distinct
templates, one rule each:

* ``straight_line``  — angles on a straight line add up to 180 deg.
* ``at_point``       — angles at a point add up to 360 deg.
* ``triangle_sum``   — the interior angles of a triangle add up to 180 deg.

The answer is an **integer** number of ``degrees``; the mandatory
``geometry_figure`` aid draws the given angles and the marked unknown, and the
consistency check (``check_geometry_figure_consistency``) cross-verifies every
drawn value against ``params``/``solution`` (see its docstring for the contract).

Everything is exact integer arithmetic — integer angles in, integer angle out —
so the printed key is provably the solution to the printed figure (no LLM).
"""

from __future__ import annotations

import random

from ..registry import register

_UNIT = "degrees"


def _pt(pid: str, x: float, y: float) -> dict:
    return {"id": pid, "x": float(x), "y": float(y)}


def _labels(point_ids: list[str]) -> list[dict]:
    return [{"at": pid, "text": pid} for pid in point_ids]


# --- template builders: pure functions of the sampled givens ----------------
# Each returns the full figure + the given-angle contract map + the solved
# unknown + the rendered question/solution text, so solve(), diagram() and
# validate() all share one source of truth.


def _build_straight_line(g: dict) -> dict:
    p, q = g["p"], g["q"]
    ans = 180 - p - q
    points = [_pt("A", 0, 4), _pt("O", 5, 4), _pt("B", 10, 4), _pt("P", 2, 0), _pt("Q", 8, 0)]
    segments = [
        {"from": "A", "to": "O"},
        {"from": "O", "to": "B"},
        {"from": "O", "to": "P"},
        {"from": "O", "to": "Q"},
    ]
    angles = [
        {"at": "O", "from": "A", "to": "P", "value_deg": p, "unknown": False},
        {"at": "O", "from": "P", "to": "Q", "value_deg": q, "unknown": False},
        {"at": "O", "from": "Q", "to": "B", "value_deg": ans, "unknown": True},
    ]
    given_map = {"A-O-P": p, "P-O-Q": q}
    text = (
        f"In the figure, AOB is a straight line. "
        f"∠AOP = {p}° and ∠POQ = {q}°. "
        f"Find ∠QOB. (The figure is not drawn to scale.)"
    )
    steps = [
        "Angles on a straight line add up to 180°.",
        f"∠QOB = 180° − {p}° − {q}° = {ans}°.",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "labels": _labels(["A", "O", "B", "P", "Q"]),
        "given_map": given_map,
        "answer": ans,
        "text": text,
        "steps": steps,
    }


def _build_at_point(g: dict) -> dict:
    a, c = g["a"], g["c"]
    ans = 360 - a - c
    points = [_pt("O", 5, 5), _pt("A", 5, 0), _pt("B", 9, 8), _pt("C", 1, 8)]
    segments = [
        {"from": "O", "to": "A"},
        {"from": "O", "to": "B"},
        {"from": "O", "to": "C"},
    ]
    angles = [
        {"at": "O", "from": "A", "to": "B", "value_deg": a, "unknown": False},
        {"at": "O", "from": "C", "to": "A", "value_deg": c, "unknown": False},
        {"at": "O", "from": "B", "to": "C", "value_deg": ans, "unknown": True},
    ]
    given_map = {"A-O-B": a, "C-O-A": c}
    text = (
        f"In the figure, the rays OA, OB and OC meet at the point O. "
        f"∠AOB = {a}° and ∠COA = {c}°. "
        f"Find ∠BOC. (The figure is not drawn to scale.)"
    )
    steps = [
        "Angles at a point add up to 360°.",
        f"∠BOC = 360° − {a}° − {c}° = {ans}°.",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "labels": _labels(["O", "A", "B", "C"]),
        "given_map": given_map,
        "answer": ans,
        "text": text,
        "steps": steps,
    }


def _build_triangle_sum(g: dict) -> dict:
    a, b = g["a"], g["b"]
    ans = 180 - a - b
    points = [_pt("A", 0, 6), _pt("B", 8, 6), _pt("C", 4, 0)]
    segments = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "A"},
    ]
    angles = [
        {"at": "A", "from": "B", "to": "C", "value_deg": a, "unknown": False},
        {"at": "B", "from": "A", "to": "C", "value_deg": b, "unknown": False},
        {"at": "C", "from": "A", "to": "B", "value_deg": ans, "unknown": True},
    ]
    given_map = {"B-A-C": a, "A-B-C": b}
    text = (
        f"In triangle ABC, ∠BAC = {a}° and ∠ABC = {b}°. "
        f"Find ∠ACB. (The figure is not drawn to scale.)"
    )
    steps = [
        "The interior angles of a triangle add up to 180°.",
        f"∠ACB = 180° − {a}° − {b}° = {ans}°.",
    ]
    return {
        "points": points,
        "segments": segments,
        "angles": angles,
        "labels": _labels(["A", "B", "C"]),
        "given_map": given_map,
        "answer": ans,
        "text": text,
        "steps": steps,
    }


_BUILDERS = {
    "straight_line": _build_straight_line,
    "at_point": _build_at_point,
    "triangle_sum": _build_triangle_sum,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


class GeometryAngleEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_BUILDERS))
        if template == "straight_line":
            while True:
                p = rng.randint(30, 80)
                q = rng.randint(30, 80)
                if 180 - p - q >= 20:
                    break
            givens = {"p": p, "q": q}
        elif template == "at_point":
            while True:
                a = rng.randint(110, 150)
                c = rng.randint(110, 150)
                if 40 <= 360 - a - c <= 150:
                    break
            givens = {"a": a, "c": c}
        else:  # triangle_sum
            while True:
                a = rng.randint(35, 80)
                b = rng.randint(35, 80)
                if 180 - a - b >= 20:
                    break
            givens = {"a": a, "b": b}
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
        # Independent re-statement of the defining rule per template.
        if template == "straight_line":
            checks["rule"] = g["p"] + g["q"] + ans == 180
        elif template == "at_point":
            checks["rule"] = g["a"] + g["c"] + ans == 360
        else:
            checks["rule"] = g["a"] + g["b"] + ans == 180
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


register("geometry_angle_easy", GeometryAngleEasySolver())
