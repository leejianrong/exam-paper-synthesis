"""Solver for ``percentage_easy``: find X% of a money amount
(DIFFICULTY.md — easy Percentage rung: find X% of a number).

Answer type: quantity in ``$`` (a clean positive integer). Constraints are
satisfied *by construction* (ADR-0014): ``percent`` is a multiple of 5 and
``whole`` a multiple of 20, so ``percent * whole`` is always a multiple of 100
and ``percent% of whole`` is an exact integer.
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

_PERCENT_MIN = 1  # ×5 -> 5%
_PERCENT_MAX = 19  # ×5 -> 95%
_WHOLE_UNITS_MIN = 1  # ×20 -> $20
_WHOLE_UNITS_MAX = 100  # ×20 -> $2000


class PercentageEasySolver:
    # ctx keys (params + intermediates) that carry money — scaled by change-to-decimals (V3).
    MONEY_KEYS = {"whole", "answer_value"}

    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        # percent: multiple of 5 in [5, 95]; whole: multiple of 20 in [20, 2000].
        # 5 × 20 = 100, so percent * whole is always divisible by 100 (exact answer).
        percent = 5 * rng.randint(_PERCENT_MIN, _PERCENT_MAX)
        whole = 20 * rng.randint(_WHOLE_UNITS_MIN, _WHOLE_UNITS_MAX)
        return {"name": name, "percent": percent, "whole": whole}

    def solve(self, params: dict) -> dict:
        percent = params["percent"]
        whole = params["whole"]
        answer_value = percent * whole // 100
        return {
            "answer": {"type": "quantity", "value": answer_value, "unit": "$"},
            "intermediates": {
                "answer_value": answer_value,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        percent = params["percent"]
        whole = params["whole"]
        checks: dict[str, bool] = {}
        checks["divides_evenly"] = (percent * whole) % 100 == 0
        answer_value = percent * whole // 100
        checks["answer_verified"] = solution["answer"]["value"] == answer_value
        checks["within_level"] = 0 < percent < 100 and 20 <= whole <= 2000 and answer_value > 0
        return {"ok": all(checks.values()), "checks": checks}


register("percentage_easy", PercentageEasySolver())
