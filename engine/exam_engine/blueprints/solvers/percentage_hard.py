"""Solver for ``percentage_hard``: reverse percentage — recover the original
amount from the amount *after* a % change (DIFFICULTY.md — hard Percentage rung:
work-backwards + hidden structure).

The trap is that the given amount is not 100% of the original but ``factor`` % of
it, where ``factor = 100 ± percent``. The original is ``new_value × 100 ÷ factor``.

Answer type: quantity in ``$`` (a clean positive integer). Everything is exact
*by construction* (ADR-0014): an integer ``original`` (multiple of 20) and
``percent`` (multiple of 5) are sampled, then ``new_value`` is derived as
``original × factor ÷ 100`` — a multiple of 100 over 100 — so the reverse
division reproduces ``original`` exactly.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..base import spread_sides
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
_PERCENT_MAX = 16  # ×5 -> 80%  (keeps a decrease factor >= 20%, i.e. strictly positive)
_ORIGINAL_UNITS_MIN = 1  # ×20 -> $20
_ORIGINAL_UNITS_MAX = 75  # ×20 -> $1500


class PercentageHardSolver:
    ITEM_POOL = ITEM_POOL

    # ctx keys (params + intermediates) that carry money — scaled by change-to-decimals (V3).
    MONEY_KEYS = {"new_value", "original"}

    def sample(self, schema: dict, rng: random.Random) -> dict:
        context = rng.choice(ITEM_POOL)
        percent = 5 * rng.randint(_PERCENT_MIN, _PERCENT_MAX)
        original = 20 * rng.randint(_ORIGINAL_UNITS_MIN, _ORIGINAL_UNITS_MAX)
        direction = rng.choice(["increase", "decrease"])
        factor = 100 + percent if direction == "increase" else 100 - percent
        # original (×20) × factor (×5) is a multiple of 100 -> new_value is exact.
        new_value = original * factor // 100
        return {
            "context": context,
            "percent": percent,
            "direction": direction,
            "new_value": new_value,
        }

    def number_problem(self, params: dict) -> str | None:
        """Why a teacher's numbers don't give a whole original price (EXA-89), else ``None``."""
        percent, new_value = params["percent"], params["new_value"]
        factor = 100 + percent if params["direction"] == "increase" else 100 - percent
        if new_value * 100 % factor:
            return (
                f"The price before would not be a whole number of dollars: ${new_value} "
                f"must be {factor}% of a whole number of dollars."
            )
        return None

    def solve(self, params: dict) -> dict:
        percent = params["percent"]
        direction = params["direction"]
        new_value = params["new_value"]
        if direction == "increase":
            factor, op = 100 + percent, "+"
        else:
            factor, op = 100 - percent, "-"
        original = new_value * 100 // factor
        return {
            "answer": {"type": "quantity", "value": original, "unit": "$"},
            "intermediates": {
                "factor": factor,
                "original": original,
                "op": op,
                "op_text": op.replace("-", "−"),
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), in $, best first."""
        p, new = params["percent"], params["new_value"]
        up = params["direction"] == "increase"
        of_new = Fraction(p * new, 100)
        original = solution["answer"]["value"]
        factor = 100 + p if up else 100 - p
        return [
            (
                new - of_new if up else new + of_new,
                f"{'took' if up else 'added'} {p}% of the new price {'off' if up else 'back'}",
            ),
            (Fraction(new * factor, 100), f"found {factor}% of the new price"),
            (abs(original - new), "the change in price, not the original price"),
            (
                Fraction(new * 100, 100 - p if up else 100 + p),
                f"used {200 - factor}%, not {factor}%",
            ),
            (new, "the new price"),
            (Fraction(new * 100, p), f"took the new price as {p}% of the original"),
            (
                Fraction(new * (200 - factor), factor),
                f"found 1% as ${new} ÷ {factor}, then multiplied by {200 - factor}",
            ),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        percent = params["percent"]
        direction = params["direction"]
        new_value = params["new_value"]
        inter = solution["intermediates"]
        factor = inter["factor"]
        original = inter["original"]
        checks: dict[str, bool] = {}
        expected_factor = 100 + percent if direction == "increase" else 100 - percent
        checks["factor_correct"] = factor == expected_factor and factor > 0
        checks["divides_evenly"] = (new_value * 100) % factor == 0
        checks["answer_verified"] = solution["answer"]["value"] == original
        # Round-trip: applying the change to the recovered original returns new_value.
        checks["round_trip"] = original * factor // 100 == new_value
        checks["within_level"] = new_value > 0 and original > 0 and 0 < percent < 100
        return {"ok": all(checks.values()), "checks": checks}


register("percentage_hard", PercentageHardSolver())
