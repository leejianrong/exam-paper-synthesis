"""Solver for ``fractions_medium``: fraction of a remainder — a two-step
question (DIFFICULTY.md — medium Fractions rung).

Someone spends ``n1/d1`` of a sum, then ``n2/d2`` of the *remainder*; find the
second amount. Answer type: quantity in ``$`` (a clean positive integer).

Everything is exact *by construction* (ADR-0014): ``whole = d1 * d2 * k``, so the
remainder ``whole × (d1 − n1) / d1 = d2 · k · (d1 − n1)`` is a whole number, and
``n2 / d2`` of that remainder ``= k · (d1 − n1) · n2`` is a whole number too. No
diagram: ``check_bar_model_consistency`` is hardcoded to ratio param keys, so this
rung carries no figure (as the Percentage ladder did).
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

_FRAC_MIN = 2  # smallest denominator
_FRAC_MAX = 6  # largest denominator
_K_MIN = 2
_K_MAX = 15


class FractionsMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        d1 = rng.randint(_FRAC_MIN, _FRAC_MAX)
        n1 = rng.randint(1, d1 - 1)
        d2 = rng.randint(_FRAC_MIN, _FRAC_MAX)
        n2 = rng.randint(1, d2 - 1)
        k = rng.randint(_K_MIN, _K_MAX)
        whole = d1 * d2 * k  # divisible by d1; remainder then divisible by d2
        return {"name": name, "whole": whole, "n1": n1, "d1": d1, "n2": n2, "d2": d2}

    def solve(self, params: dict) -> dict:
        whole = params["whole"]
        n1, d1 = params["n1"], params["d1"]
        n2, d2 = params["n2"], params["d2"]
        kept1_num = d1 - n1
        remainder = kept1_num * whole // d1
        answer_value = n2 * remainder // d2
        return {
            "answer": {"type": "quantity", "value": answer_value, "unit": "$"},
            "intermediates": {
                "kept1_num": kept1_num,
                "remainder": remainder,
                "answer_value": answer_value,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        whole = params["whole"]
        n1, d1 = params["n1"], params["d1"]
        n2, d2 = params["n2"], params["d2"]
        inter = solution["intermediates"]
        checks: dict[str, bool] = {}
        checks["remainder_divides"] = (d1 - n1) * whole % d1 == 0
        remainder = (d1 - n1) * whole // d1
        checks["food_divides"] = n2 * remainder % d2 == 0
        answer_value = n2 * remainder // d2
        checks["remainder_verified"] = inter["remainder"] == remainder
        checks["answer_verified"] = (
            inter["answer_value"] == answer_value and solution["answer"]["value"] == answer_value
        )
        checks["proper_fractions"] = 0 < n1 < d1 and 0 < n2 < d2
        checks["within_level"] = whole > 0 and 0 < answer_value < whole
        return {"ok": all(checks.values()), "checks": checks}


register("fractions_medium", FractionsMediumSolver())
