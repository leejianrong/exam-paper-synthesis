"""Solver for ``geometry_angle_opposite`` (EXA-154): two straight lines AB and CD cross at O,
and a ray OE lies inside ∠AOD. Two steps, two angle facts. The 2-mark medium rung between
``geometry_angle_easy`` (one rule) and ``geometry_angle_medium`` (isosceles / exterior
angle, 3 marks).

* ``opposite_part`` — ∠BOC and ∠DOE are given; find ∠AOE. ∠AOD = ∠BOC (vertically
  opposite angles), then ∠AOE = ∠AOD − ∠DOE.
* ``opposite_sum``  — ∠AOE and ∠EOD are given; find ∠BOC. ∠AOD = ∠AOE + ∠EOD, then
  ∠BOC = ∠AOD (vertically opposite angles).
* ``line_part``     — ∠BOD and ∠AOE are given; find ∠EOD. ∠AOD = 180° − ∠BOD (AOB is a
  straight line), then ∠EOD = ∠AOD − ∠AOE.

The figure is fixed (not drawn to scale) and carries the given angles and the marked unknown;
``check_geometry_figure_consistency`` cross-checks every drawn value. Exact integer
arithmetic: integer angles in, integer angle out.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register

_UNIT = "degrees"
POINTS = {"O": (5, 4), "A": (0, 5), "B": (10, 3), "C": (3, 0), "D": (7, 8), "E": (1, 9)}


def _pt(pid: str) -> dict:
    x, y = POINTS[pid]
    return {"id": pid, "x": float(x), "y": float(y)}


def _mark(name: str, value: int, unknown: bool = False) -> dict:
    """An angle mark from its three-letter name: ``"BOC"`` -> at O, from B to C."""
    return {"at": name[1], "from": name[0], "to": name[2], "value_deg": value, "unknown": unknown}


def _build(params: dict) -> dict:
    g, template = params["givens"], params["template"]
    if template == "opposite_part":
        r, q = g["r"], g["q"]
        ans = r - q
        given = {"BOC": r, "DOE": q}
        ask = "AOE"
        steps = [
            f"∠AOD = ∠BOC = {r}° (vertically opposite angles).",
            f"∠AOE = {r}° − {q}° = {ans}°.",
        ]
    elif template == "opposite_sum":
        p, q = g["p"], g["q"]
        ans = p + q
        given = {"AOE": p, "EOD": q}
        ask = "BOC"
        steps = [
            f"∠AOD = {p}° + {q}° = {ans}°.",
            f"∠BOC = ∠AOD = {ans}° (vertically opposite angles).",
        ]
    else:  # line_part
        p, q = g["p"], g["q"]
        aod = 180 - p
        ans = aod - q
        given = {"BOD": p, "AOE": q}
        ask = "EOD"
        steps = [
            f"AOB is a straight line, so ∠AOD = 180° − {p}° = {aod}°.",
            f"∠EOD = {aod}° − {q}° = {ans}°.",
        ]
    (n1, v1), (n2, v2) = given.items()
    text = (
        f"In the figure, AB and CD are straight lines that meet at O. "
        f"∠{n1} = {v1}° and ∠{n2} = {v2}°. Find ∠{ask}."
    )
    angles = [_mark(n, v) for n, v in given.items()] + [_mark(ask, ans, unknown=True)]
    return {
        "text": text,
        "steps": steps,
        "answer": ans,
        "angles": angles,
        "given_map": {f"{n[0]}-{n[1]}-{n[2]}": v for n, v in given.items()},
    }


class GeometryAngleOppositeSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(["opposite_part", "opposite_sum", "line_part"])
        if template == "opposite_part":
            r = rng.randint(80, 140)
            givens = {"r": r, "q": rng.randint(20, r - 25)}
        elif template == "opposite_sum":
            total = rng.randint(80, 140)
            p = rng.randint(25, total - 25)
            givens = {"p": p, "q": total - p}
        else:
            p = rng.randint(40, 100)
            givens = {"p": p, "q": rng.randint(20, 180 - p - 25)}
        params = {"template": template, "givens": givens}
        params["angles"] = _build(params)["given_map"]
        return params

    def solve(self, params: dict) -> dict:
        built = _build(params)
        return {
            "answer": {"type": "integer", "value": built["answer"], "unit": _UNIT},
            "intermediates": {
                "question_text": built["text"],
                "step1": built["steps"][0],
                "step2": built["steps"][1],
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong angles (degrees), best first (EXA-122)."""
        g, template = params["givens"], params["template"]
        if template == "opposite_part":
            r, q = g["r"], g["q"]
            return [
                (180 - r - q, "took ∠AOD as 180° − ∠BOC"),
                (r, "stopped at ∠AOD"),
                (r + q, "added the two given angles"),
                (180 - r, "the angle next to ∠BOC on the line"),
            ]
        if template == "opposite_sum":
            p, q = g["p"], g["q"]
            return [
                (180 - p - q, "took ∠BOC as 180° − ∠AOD"),
                (abs(p - q), "subtracted the two given angles"),
                (p, "took ∠BOC equal to ∠AOE"),
                (q, "took ∠BOC equal to ∠EOD"),
            ]
        p, q = g["p"], g["q"]
        return [
            (p - q, "took ∠AOD equal to ∠BOD"),
            (180 - p, "stopped at ∠AOD"),
            (180 - q, "subtracted only ∠AOE from 180°"),
            (p + q, "added the two given angles"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        g, template = params["givens"], params["template"]
        ans = solution["answer"]["value"]
        checks: dict[str, bool] = {}
        if template == "opposite_part":  # ∠AOE + ∠DOE = ∠AOD = ∠BOC
            checks["rule"] = ans + g["q"] == g["r"]
        elif template == "opposite_sum":  # ∠BOC = ∠AOD = ∠AOE + ∠EOD
            checks["rule"] = ans == g["p"] + g["q"]
        else:  # ∠BOD + ∠AOE + ∠EOD = 180° on the straight line AOB
            checks["rule"] = g["p"] + g["q"] + ans == 180
        checks["answer_verified"] = ans == _build(params)["answer"]
        checks["unit_degrees"] = solution["answer"]["unit"] == _UNIT
        checks["in_range"] = 15 <= ans < 180 and all(0 < v < 180 for v in g.values())
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return {
            "type": "geometry_figure",
            "unit": _UNIT,
            "points": [_pt(p) for p in POINTS],
            "segments": [
                {"from": "A", "to": "O"},
                {"from": "O", "to": "B"},
                {"from": "C", "to": "O"},
                {"from": "O", "to": "D"},
                {"from": "O", "to": "E"},
            ],
            "angles": _build(params)["angles"],
            "labels": [{"at": p, "text": p} for p in POINTS],
        }


register("geometry_angle_opposite", GeometryAngleOppositeSolver())
