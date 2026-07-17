"""Solver for ``geometry_angle_medium`` (KAN-229): two-step / property recall.

Strictly-PSLE unknown-angle figures (polygon-only, no circles, no additional
construction — V6b geometry plan). Two structurally-distinct templates:

* ``isosceles`` — an isosceles triangle (equal sides ticked). Two modes:
  ``isosceles_apex`` gives the apex angle and asks for a base angle; ``
  isosceles_base`` gives a base angle and asks for the apex. Property recall
  (equal sides -> equal base angles) then angle sum.
* ``exterior``  — a triangle with one side extended past a vertex. Angle on a
  straight line to get the interior angle, then triangle angle sum.

Answer: integer ``degrees``; mandatory ``geometry_figure`` aid, verified by the
consistency check. Exact integer arithmetic throughout (apex is sampled even so
base angles stay whole) — the key is provably the figure's solution.
"""

from __future__ import annotations

import random

from ..registry import register

_UNIT = "degrees"


def _pt(pid: str, x: float, y: float) -> dict:
    return {"id": pid, "x": float(x), "y": float(y)}


def _labels(point_ids: list[str]) -> list[dict]:
    return [{"at": pid, "text": pid} for pid in point_ids]


def _isosceles_points_segments() -> tuple[list[dict], list[dict]]:
    points: list[dict] = [_pt("A", 4, 0), _pt("B", 0, 7), _pt("C", 8, 7)]
    segments: list[dict] = [
        {"from": "A", "to": "B", "ticks": 1},
        {"from": "A", "to": "C", "ticks": 1},
        {"from": "B", "to": "C"},
    ]
    return points, segments


def _build_isosceles_apex(g: dict) -> dict:
    apex = g["apex"]
    ans = (180 - apex) // 2
    points, segments = _isosceles_points_segments()
    angles = [
        {"at": "A", "from": "B", "to": "C", "value_deg": apex, "unknown": False},
        {"at": "B", "from": "A", "to": "C", "value_deg": ans, "unknown": True},
    ]
    given_map = {"B-A-C": apex}
    text = (
        f"In the figure, triangle ABC is isosceles with AB = AC. "
        f"∠BAC = {apex}°. "
        f"Find ∠ABC. (The figure is not drawn to scale.)"
    )
    steps = [
        "AB = AC, so the base angles are equal: ∠ABC = ∠ACB.",
        f"∠ABC = (180° − {apex}°) ÷ 2 = {ans}°.",
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


def _build_isosceles_base(g: dict) -> dict:
    base = g["base"]
    ans = 180 - 2 * base
    points, segments = _isosceles_points_segments()
    angles = [
        {"at": "B", "from": "A", "to": "C", "value_deg": base, "unknown": False},
        {"at": "A", "from": "B", "to": "C", "value_deg": ans, "unknown": True},
    ]
    given_map = {"A-B-C": base}
    text = (
        f"In the figure, triangle ABC is isosceles with AB = AC. "
        f"∠ABC = {base}°. "
        f"Find ∠BAC. (The figure is not drawn to scale.)"
    )
    steps = [
        f"AB = AC, so ∠ACB = ∠ABC = {base}°.",
        f"∠BAC = 180° − {base}° − {base}° = {ans}°.",
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


def _build_exterior(g: dict) -> dict:
    b, ext = g["b"], g["ext"]
    interior_c = 180 - ext
    ans = ext - b
    points = [_pt("B", 0, 6), _pt("C", 7, 6), _pt("D", 11, 6), _pt("A", 2, 0)]
    segments = [
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
        {"from": "A", "to": "B"},
        {"from": "A", "to": "C"},
    ]
    angles = [
        {"at": "B", "from": "A", "to": "C", "value_deg": b, "unknown": False},
        {"at": "C", "from": "A", "to": "D", "value_deg": ext, "unknown": False},
        {"at": "A", "from": "B", "to": "C", "value_deg": ans, "unknown": True},
    ]
    given_map = {"A-B-C": b, "A-C-D": ext}
    text = (
        f"In the figure, BCD is a straight line. "
        f"∠ABC = {b}° and ∠ACD = {ext}°. "
        f"Find ∠BAC. (The figure is not drawn to scale.)"
    )
    steps = [
        f"BCD is a straight line, so ∠ACB = 180° − {ext}° = {interior_c}°.",
        f"∠BAC = 180° − {b}° − {interior_c}° = {ans}°.",
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
    "isosceles_apex": _build_isosceles_apex,
    "isosceles_base": _build_isosceles_base,
    "exterior": _build_exterior,
}


def _build(params: dict) -> dict:
    return _BUILDERS[params["template"]](params["givens"])


class GeometryAngleMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        family = rng.choice(["isosceles", "exterior"])
        if family == "isosceles":
            if rng.random() < 0.5:
                template = "isosceles_apex"
                apex = rng.randrange(30, 141, 2)  # even -> whole base angles
                givens = {"apex": apex}
            else:
                template = "isosceles_base"
                base = rng.randint(25, 75)
                givens = {"base": base}
        else:
            template = "exterior"
            while True:
                b = rng.randint(30, 60)
                ext = rng.randint(80, 150)
                if 25 <= ext - b <= 130 and 180 - ext >= 20:
                    break
            givens = {"b": b, "ext": ext}
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
        if template == "isosceles_apex":
            # base angles equal + angle sum: apex + 2*base = 180.
            checks["rule"] = g["apex"] + 2 * ans == 180
        elif template == "isosceles_base":
            checks["rule"] = 2 * g["base"] + ans == 180
        else:  # exterior: interior C = 180 - ext, triangle sum -> ans = ext - b.
            checks["rule"] = g["b"] + (180 - g["ext"]) + ans == 180
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


register("geometry_angle_medium", GeometryAngleMediumSolver())
