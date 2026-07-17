"""Solver for ``fractions_hard``: successive fractions of a remainder with an
unknown whole — an inverse (work-backwards) question (DIFFICULTY.md — hard
Fractions rung: Direction + Hidden structure + more steps).

Someone spends ``n1/d1`` of an unknown sum, then ``n2/d2`` of the *remainder*,
and is left with ``left``; recover the original sum. Working backwards:
``after_first = left × d2 ÷ (d2 − n2)`` then ``original = after_first × d1 ÷
(d1 − n1)``.

Answer type: quantity in ``$`` (a clean positive integer). Everything is exact
*by construction* (ADR-0014): an original ``whole = d1 · d2 · k`` is chosen, from
which ``left = k · (d1 − n1) · (d2 − n2)`` is derived, so both reverse divisions
reproduce integers and recover ``whole`` exactly. No diagram (as the Percentage
ladder did — the bar-model check is ratio-specific).
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


class FractionsHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        d1 = rng.randint(_FRAC_MIN, _FRAC_MAX)
        n1 = rng.randint(1, d1 - 1)
        d2 = rng.randint(_FRAC_MIN, _FRAC_MAX)
        n2 = rng.randint(1, d2 - 1)
        k = rng.randint(_K_MIN, _K_MAX)
        # whole = d1*d2*k -> left = k*(d1-n1)*(d2-n2); both reverse steps are exact.
        left = k * (d1 - n1) * (d2 - n2)
        return {"name": name, "n1": n1, "d1": d1, "n2": n2, "d2": d2, "left": left}

    def solve(self, params: dict) -> dict:
        n1, d1 = params["n1"], params["d1"]
        n2, d2 = params["n2"], params["d2"]
        left = params["left"]
        kept1_num = d1 - n1
        kept2_num = d2 - n2
        remainder = left * d2 // kept2_num  # money after the first purchase
        answer_value = remainder * d1 // kept1_num  # money at first
        return {
            "answer": {"type": "quantity", "value": answer_value, "unit": "$"},
            "intermediates": {
                "kept1_num": kept1_num,
                "kept2_num": kept2_num,
                "remainder": remainder,
                "answer_value": answer_value,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        n1, d1 = params["n1"], params["d1"]
        n2, d2 = params["n2"], params["d2"]
        left = params["left"]
        inter = solution["intermediates"]
        kept1_num = d1 - n1
        kept2_num = d2 - n2
        checks: dict[str, bool] = {}
        checks["remainder_divides"] = left * d2 % kept2_num == 0
        remainder = left * d2 // kept2_num
        checks["original_divides"] = remainder * d1 % kept1_num == 0
        answer_value = remainder * d1 // kept1_num
        checks["remainder_verified"] = inter["remainder"] == remainder
        checks["answer_verified"] = (
            inter["answer_value"] == answer_value and solution["answer"]["value"] == answer_value
        )
        # Round-trip: forward-apply the two fractions to the recovered whole and
        # recover the stated `left` exactly.
        after_first = kept1_num * answer_value // d1
        after_second = kept2_num * after_first // d2
        checks["round_trip"] = (
            kept1_num * answer_value % d1 == 0
            and kept2_num * after_first % d2 == 0
            and after_second == left
        )
        checks["proper_fractions"] = 0 < n1 < d1 and 0 < n2 < d2
        checks["within_level"] = left > 0 and answer_value > left
        return {"ok": all(checks.values()), "checks": checks}


register("fractions_hard", FractionsHardSolver())
