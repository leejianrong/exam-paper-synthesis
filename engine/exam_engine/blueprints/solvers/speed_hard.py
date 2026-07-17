"""Solver for ``speed_hard``: two objects meeting — combined speed closes the gap
(DIFFICULTY.md — hard Speed rung: Hidden structure + Heuristic demand).

Two people start ``gap`` km apart and move towards each other at ``s1`` and
``s2`` km/h. They close the gap at their *combined* speed, so they meet after
``t_meet = gap / (s1 + s2)`` h. Answer type: quantity in ``h`` (a clean positive
integer).

Exact *by construction* (ADR-0014): sample the two speeds and an integer
``t_meet``, then set ``gap = (s1 + s2) * t_meet``. The reverse division therefore
reproduces ``t_meet`` exactly with no rejection loop. No diagram (ratio-specific
check).
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

_SPEED_MIN = 10
_SPEED_MAX = 90
_T_MIN = 1
_T_MAX = 6


class SpeedHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        name1, name2 = rng.sample(NAME_POOL, 2)
        s1 = rng.randint(_SPEED_MIN, _SPEED_MAX)
        s2 = rng.randint(_SPEED_MIN, _SPEED_MAX)
        t_meet = rng.randint(_T_MIN, _T_MAX)
        gap = (s1 + s2) * t_meet  # exact: gap / (s1+s2) recovers t_meet
        return {"name1": name1, "name2": name2, "s1": s1, "s2": s2, "gap": gap}

    def solve(self, params: dict) -> dict:
        s1, s2 = params["s1"], params["s2"]
        gap = params["gap"]
        combined_speed = s1 + s2
        t_meet = gap // combined_speed
        return {
            "answer": {"type": "quantity", "value": t_meet, "unit": "h"},
            "intermediates": {"combined_speed": combined_speed, "t_meet": t_meet},
        }

    def validate(self, params: dict, solution: dict) -> dict:
        s1, s2 = params["s1"], params["s2"]
        gap = params["gap"]
        inter = solution["intermediates"]
        combined_speed = s1 + s2
        checks: dict[str, bool] = {}
        checks["divides_exactly"] = gap % combined_speed == 0
        t_meet = gap // combined_speed
        checks["combined_verified"] = inter["combined_speed"] == combined_speed
        checks["answer_verified"] = (
            inter["t_meet"] == t_meet and solution["answer"]["value"] == t_meet
        )
        checks["unit_h"] = solution["answer"]["unit"] == "h"
        # Defining relationship (exact): combined speed x meeting time recovers gap.
        checks["defining_relationship"] = combined_speed * t_meet == gap
        checks["positive"] = t_meet > 0 and gap > 0
        return {"ok": all(checks.values()), "checks": checks}


register("speed_hard", SpeedHardSolver())
