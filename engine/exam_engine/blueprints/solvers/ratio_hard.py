"""Solver for ``ratio_hard``: before-after ratio with an invariant quantity
(DIFFICULTY.md — hard Ratio rung: hidden structure + work-backwards).

Two people A=``names[0]`` and B=``names[1]``. B is *invariant* (unchanged). Before,
A:B = ``ratio_before``; A then spends ``$spent``; after, A:B = ``ratio_after``. The
standard heuristic equalises the invariant person's units across both stages: scale
each ratio so B occupies ``L = lcm(b, d)`` units. A's units then fall from
``a_before_units`` to ``a_after_units``; the drop of ``delta_units`` equals ``$spent``,
so one unit = ``spent / delta_units`` and B's amount = ``L × unit_value``.

Answer type: quantity in ``$`` (a clean positive integer). Everything is exact
integers *by construction* (ADR-0014): ``spent`` is sampled as ``delta_units *
unit_value`` so the work-backwards division is exact.
"""

from __future__ import annotations

import random
from math import gcd

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

_UNIT_VALUE_MIN = 5
_UNIT_VALUE_MAX = 40
_B_AMOUNT_MAX = 2000


def _lcm(x: int, y: int) -> int:
    return x * y // gcd(x, y)


class RatioHardSolver:
    # ctx keys (params + intermediates) that carry money — scaled by change-to-decimals (V3).
    MONEY_KEYS = {"spent", "unit_value", "b_amount"}

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            names = rng.sample(NAME_POOL, 2)
            a, b = rng.randint(1, 9), rng.randint(1, 9)
            c, d = rng.randint(1, 9), rng.randint(1, 9)
            ga, gc = gcd(a, b), gcd(c, d)
            a, b = a // ga, b // ga
            c, d = c // gc, d // gc
            # Reduced pairs must stay in range and be non-degenerate.
            if gcd(a, b) != 1 or gcd(c, d) != 1:
                continue
            if b == d:  # LCM step must be non-trivial
                continue
            if a * d <= c * b:  # require a/b > c/d (A strictly shrinks)
                continue
            L = _lcm(b, d)
            a_before_units = a * L // b
            a_after_units = c * L // d
            delta_units = a_before_units - a_after_units
            if delta_units <= 0:
                continue
            unit_value = rng.randint(_UNIT_VALUE_MIN, _UNIT_VALUE_MAX)
            spent = delta_units * unit_value
            b_amount = L * unit_value
            if spent < 1 or b_amount > _B_AMOUNT_MAX:
                continue
            return {
                "names": names,
                "ratio_before": [a, b],
                "ratio_after": [c, d],
                "spent": spent,
            }

    def solve(self, params: dict) -> dict:
        a, b = params["ratio_before"]
        c, d = params["ratio_after"]
        spent = params["spent"]
        L = _lcm(b, d)
        a_before_units = a * L // b
        a_after_units = c * L // d
        delta_units = a_before_units - a_after_units
        unit_value = spent // delta_units
        b_amount = L * unit_value
        return {
            "answer": {"type": "quantity", "value": b_amount, "unit": "$"},
            "intermediates": {
                "L": L,
                "a_before_units": a_before_units,
                "a_after_units": a_after_units,
                "delta_units": delta_units,
                "unit_value": unit_value,
                "b_amount": b_amount,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        a, b = params["ratio_before"]
        c, d = params["ratio_after"]
        spent = params["spent"]
        inter = solution["intermediates"]
        L = inter["L"]
        a_before_units = inter["a_before_units"]
        a_after_units = inter["a_after_units"]
        delta_units = inter["delta_units"]
        unit_value = inter["unit_value"]
        b_amount = inter["b_amount"]

        checks: dict[str, bool] = {}
        checks["spent_divisible_by_delta"] = delta_units != 0 and spent % delta_units == 0
        checks["ratios_consistent"] = a_before_units * b == a * L and a_after_units * d == c * L
        checks["answer_verified"] = (
            solution["answer"]["value"] == b_amount and b_amount == L * unit_value
        )
        a_before = a_before_units * unit_value
        a_after = a_after_units * unit_value
        checks["within_level"] = (
            b_amount <= _B_AMOUNT_MAX
            and a_before > 0
            and a_after > 0
            and b_amount > 0
            and unit_value > 0
            and a_before - a_after == spent
        )
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        """Build the before-after aid bar model (A5, ADR-0007) in *equalised* units.

        Deterministic — derived only from params + solved intermediates, so the
        pipeline (and the resulting canonical object) stays reproducible.
        """
        a_name, b_name = params["names"]
        spent = params["spent"]
        inter = solution["intermediates"]
        L = inter["L"]
        a_before_units = inter["a_before_units"]
        a_after_units = inter["a_after_units"]
        unit_value = inter["unit_value"]
        b_amount = inter["b_amount"]
        return {
            "type": "bar_model_before_after",
            "stages": [
                {
                    "name": "Before",
                    "bars": [
                        {"label": a_name, "units": a_before_units},
                        {"label": b_name, "units": L},
                    ],
                },
                {
                    "name": "After",
                    "bars": [
                        {"label": a_name, "units": a_after_units},
                        {"label": b_name, "units": L},
                    ],
                },
            ],
            "annotations": [
                {"label": f"1 unit = ${unit_value}"},
                {"label": f"{a_name} spent = ${spent}"},
            ],
            "total_bracket": {"label": f"{b_name} = ${b_amount}"},
        }


register("ratio_hard", RatioHardSolver())
