"""Solver for ``percentage_medium``: percentage increase / decrease of a money
amount (DIFFICULTY.md — medium Percentage rung).

Answer type: quantity in ``$`` (a clean positive integer). Constraints are
satisfied *by construction* (ADR-0014): ``percent`` is a multiple of 5 and
``original`` a multiple of 20, so the change (``percent% of original``) is an
exact integer; ``percent < 100`` keeps a decrease strictly positive.
"""

from __future__ import annotations

import random

from ..registry import register

# Everyday priced items (R1.6). Context only — no arithmetic hangs off the word.
ITEM_POOL = [
    "bicycle",
    "watch",
    "backpack",
    "printer",
    "guitar",
    "kettle",
    "camera",
    "desk",
    "fan",
    "helmet",
]

_PERCENT_MIN = 1  # ×5 -> 5%
_PERCENT_MAX = 18  # ×5 -> 90%
_ORIGINAL_UNITS_MIN = 1  # ×20 -> $20
_ORIGINAL_UNITS_MAX = 100  # ×20 -> $2000


class PercentageMediumSolver:
    # ctx keys (params + intermediates) that carry money — scaled by change-to-decimals (V3).
    MONEY_KEYS = {"original", "change_amount", "new_value"}

    def sample(self, schema: dict, rng: random.Random) -> dict:
        context = rng.choice(ITEM_POOL)
        percent = 5 * rng.randint(_PERCENT_MIN, _PERCENT_MAX)
        original = 20 * rng.randint(_ORIGINAL_UNITS_MIN, _ORIGINAL_UNITS_MAX)
        direction = rng.choice(["increase", "decrease"])
        return {
            "context": context,
            "original": original,
            "percent": percent,
            "direction": direction,
        }

    def solve(self, params: dict) -> dict:
        original = params["original"]
        percent = params["percent"]
        direction = params["direction"]
        change_amount = percent * original // 100
        if direction == "increase":
            verb, op = "increased", "+"
            new_value = original + change_amount
        else:
            verb, op = "decreased", "-"
            new_value = original - change_amount
        return {
            "answer": {"type": "quantity", "value": new_value, "unit": "$"},
            "intermediates": {
                "change_amount": change_amount,
                "new_value": new_value,
                "verb": verb,
                "op": op,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        original = params["original"]
        percent = params["percent"]
        direction = params["direction"]
        inter = solution["intermediates"]
        change_amount = inter["change_amount"]
        new_value = inter["new_value"]
        checks: dict[str, bool] = {}
        checks["divides_evenly"] = (percent * original) % 100 == 0
        checks["change_verified"] = change_amount == percent * original // 100
        expected = original + change_amount if direction == "increase" else original - change_amount
        checks["answer_verified"] = (
            solution["answer"]["value"] == new_value and new_value == expected
        )
        checks["within_level"] = 0 < percent < 100 and 20 <= original <= 2000 and new_value > 0
        return {"ok": all(checks.values()), "checks": checks}


register("percentage_medium", PercentageMediumSolver())
