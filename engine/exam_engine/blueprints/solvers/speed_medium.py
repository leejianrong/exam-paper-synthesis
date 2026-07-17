"""Solver for ``speed_medium``: average speed over two legs (DIFFICULTY.md —
medium Speed rung).

Someone travels ``d1`` km in ``t1`` h, then ``d2`` km in ``t2`` h; find the
average speed for the *whole* journey: ``avg = (d1 + d2) / (t1 + t2)`` — NOT the
mean of the two leg speeds. Answer type: quantity in ``km/h`` (a clean positive
integer).

Exact *by construction* (ADR-0014), with deliberately UNEQUAL legs so the answer
differs from ``(s1 + s2) / 2`` (the classic misconception). Pick ``t1, t2, j``
and a leg-2 speed ``s2``; set ``avg = s2 + j * t1`` and ``s1 = s2 + (t1 + t2) *
j``. Then ``d1 = s1 * t1`` and ``d2 = s2 * t2`` give

    d1 + d2 = (t1 + t2) * (s2 + j * t1) = (t1 + t2) * avg,

so ``avg = (d1 + d2) / (t1 + t2)`` is an integer with no rejection loop, and the
two leg speeds ``s1 != s2`` (since ``j >= 1``). No diagram (ratio-specific check).
"""

from __future__ import annotations

import random

from ..registry import register

# Singapore-appropriate given names (PSLE style, R1.6).
NAME_POOL = [
    "Aisha",
    "Ben",
    "Chloe",
    "Devi",
    "Ethan",
    "Faridah",
    "Gopal",
    "Hui Ling",
    "Ismail",
    "Jia En",
    "Kavya",
    "Lucas",
]

_T_MIN = 1
_T_MAX = 4
_J_MIN = 1  # gap between leg speeds (units of (t1+t2)); >= 1 keeps the legs unequal
_J_MAX = 4
_S2_MIN = 20  # slower leg speed
_S2_MAX = 50


class SpeedMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        # Distinct leg times: with unequal times AND unequal leg speeds the true
        # average (total distance / total time) never coincides with the mean of
        # the two leg speeds — so the classic misconception is always guarded.
        t1, t2 = rng.sample(range(_T_MIN, _T_MAX + 1), 2)
        j = rng.randint(_J_MIN, _J_MAX)
        s2 = rng.randint(_S2_MIN, _S2_MAX)
        s1 = s2 + (t1 + t2) * j  # faster leg; avg = (d1+d2)/(t1+t2) is then integer
        d1 = s1 * t1
        d2 = s2 * t2
        return {"name": name, "d1": d1, "t1": t1, "d2": d2, "t2": t2}

    def solve(self, params: dict) -> dict:
        d1, t1 = params["d1"], params["t1"]
        d2, t2 = params["d2"], params["t2"]
        total_distance = d1 + d2
        total_time = t1 + t2
        avg = total_distance // total_time
        return {
            "answer": {"type": "quantity", "value": avg, "unit": "km/h"},
            "intermediates": {
                "total_distance": total_distance,
                "total_time": total_time,
                "avg": avg,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        d1, t1 = params["d1"], params["t1"]
        d2, t2 = params["d2"], params["t2"]
        inter = solution["intermediates"]
        total_distance = d1 + d2
        total_time = t1 + t2
        checks: dict[str, bool] = {}
        checks["divides_exactly"] = total_distance % total_time == 0
        avg = total_distance // total_time
        checks["totals_verified"] = (
            inter["total_distance"] == total_distance and inter["total_time"] == total_time
        )
        checks["answer_verified"] = inter["avg"] == avg and solution["answer"]["value"] == avg
        checks["unit_kmh"] = solution["answer"]["unit"] == "km/h"
        # Cross-multiplied defining relationship (exact, no float): avg * T == D.
        checks["defining_relationship"] = avg * total_time == total_distance
        checks["positive"] = avg > 0 and d1 > 0 and d2 > 0
        return {"ok": all(checks.values()), "checks": checks}


register("speed_medium", SpeedMediumSolver())
