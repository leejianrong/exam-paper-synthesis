"""Solver for ``speed_easy``: distance = speed x time, direct (DIFFICULTY.md —
easy Speed rung).

Given a constant ``speed`` (km/h) held for a whole number of hours ``time``,
find the ``distance`` travelled. Answer type: quantity in ``km`` (a clean
positive integer).

Everything is exact *by construction* (ADR-0014): both ``speed`` and ``time``
are sampled as integers, so ``distance = speed * time`` is a whole number without
any rejection loop. No diagram (the bar-model check is ratio-specific).
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
_SPEED_MAX = 120
_TIME_MIN = 1
_TIME_MAX = 12


class SpeedEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        speed = rng.randint(_SPEED_MIN, _SPEED_MAX)
        time = rng.randint(_TIME_MIN, _TIME_MAX)
        return {"name": name, "speed": speed, "time": time}

    def solve(self, params: dict) -> dict:
        speed = params["speed"]
        time = params["time"]
        distance = speed * time
        return {
            "answer": {"type": "quantity", "value": distance, "unit": "km"},
            "intermediates": {"distance": distance},
        }

    def validate(self, params: dict, solution: dict) -> dict:
        speed = params["speed"]
        time = params["time"]
        inter = solution["intermediates"]
        distance = speed * time
        checks: dict[str, bool] = {}
        checks["answer_verified"] = (
            inter["distance"] == distance and solution["answer"]["value"] == distance
        )
        checks["unit_km"] = solution["answer"]["unit"] == "km"
        checks["within_level"] = (
            _SPEED_MIN <= speed <= _SPEED_MAX and _TIME_MIN <= time <= _TIME_MAX
        )
        checks["positive"] = distance > 0
        return {"ok": all(checks.values()), "checks": checks}


register("speed_easy", SpeedEasySolver())
