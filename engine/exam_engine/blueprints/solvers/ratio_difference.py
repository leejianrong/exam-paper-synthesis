"""Solver for ``ratio_difference`` (EXA-154): a 2-term ratio and the difference between the
two amounts are given; find the total. The 2-mark medium rung between ``ratio_easy`` (share
a given total) and ``ratio_medium`` (a 3-term share): the pupil has to see that the
difference is the gap in units, not the total.

    "The ratio of A's stickers to B's stickers is 7 : 4. A has 27 more stickers than B.
     How many stickers do they have altogether?"   3 units = 27, 1 unit = 9, 11 units = 99.

The names and the item noun are cosmetic (W1a): they appear only in the YAML templates.
Exact by construction (ADR-0014): the difference is sampled as ``|a - b| × unit``, so the
unit and every amount are whole numbers. The ratio is in its simplest form, with unequal
terms, as printed ratios are on PSLE papers.
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from ..registry import register
from .ratio_easy import NAME_POOL

# Countable things two children collect (W1a item pool: a plural noun, no article).
ITEM_POOL = ["stickers", "marbles", "stamps", "beads", "cards", "seashells"]

_TERM_MAX = 9
_UNIT_MIN, _UNIT_MAX = 3, 40


class RatioDifferenceSolver:
    ITEM_POOL = ITEM_POOL

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            a, b = rng.randint(1, _TERM_MAX), rng.randint(1, _TERM_MAX)
            if a != b and gcd(a, b) == 1:
                break
        unit = rng.randint(_UNIT_MIN, _UNIT_MAX)
        return {
            "names": rng.sample(NAME_POOL, 2),
            "item": rng.choice(ITEM_POOL),
            "ratio": [a, b],
            "difference": abs(a - b) * unit,
        }

    def solve(self, params: dict) -> dict:
        a, b = params["ratio"]
        diff_units = abs(a - b)
        unit = params["difference"] // diff_units
        units_total = a + b
        total = units_total * unit
        big, small, d = max(a, b), min(a, b), params["difference"]
        if diff_units == 1:
            step1 = f"The difference is {big} − {small} = 1 unit, so 1 unit = {d}."
        else:
            step1 = (
                f"The difference is {big} − {small} = {diff_units} units, "
                f"so 1 unit = {d} ÷ {diff_units} = {unit}."
            )
        return {
            "answer": {"type": "integer", "value": total, "unit": ""},
            "intermediates": {
                "more_fewer": "more" if a > b else "fewer",
                "step1": step1,
                "diff_units": diff_units,
                "unit_value": unit,
                "units_total": units_total,
                "total": total,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), best first."""
        a, b = params["ratio"]
        d = params["difference"]
        unit = Fraction(d, abs(a - b))
        return [
            (max(a, b) * unit, "the larger amount only, not the total"),
            (min(a, b) * unit, "the smaller amount only, not the total"),
            (max(a, b) * unit + d, "added the difference to the larger amount"),
            ((a + b) * d, f"took the difference ({d}) as 1 unit"),
            (unit, "found 1 unit only"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        a, b = params["ratio"]
        d = params["difference"]
        checks: dict[str, bool] = {}
        checks["unequal_simplest"] = a != b and gcd(a, b) == 1
        checks["divides_evenly"] = d % abs(a - b) == 0
        unit = d // abs(a - b)
        first, second = a * unit, b * unit
        checks["difference_kept"] = abs(first - second) == d
        checks["answer_verified"] = solution["answer"]["value"] == first + second
        checks["within_level"] = 0 < first + second <= 1000
        return {"ok": all(checks.values()), "checks": checks}


register("ratio_difference", RatioDifferenceSolver())
