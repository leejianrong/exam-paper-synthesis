"""Solver for ``ratio_easy``: two people share a sum in a 2-term ratio;
find the second person's share (DIFFICULTY.md — easy Ratio rung).

Answer type: quantity in ``$`` (a clean positive integer). Constraints are
satisfied *by construction* (ADR-0014): total is sampled as ``sum(ratio) *
unit_value`` so every share is a positive integer and division is exact.
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

_UNIT_VALUE_MIN = 2
_UNIT_VALUE_MAX = 50
_TOTAL_MIN = 6
_TOTAL_MAX = 2000


class RatioEasySolver:
    # ctx keys (params + intermediates) that carry money — scaled by change-to-decimals (V3).
    MONEY_KEYS = {"total", "unit_value", "answer_value"}

    def sample(self, schema: dict, rng: random.Random) -> dict:
        names = rng.sample(NAME_POOL, 2)
        # 2-term ratio, terms 1..9, the two terms unequal (keeps it meaningful).
        while True:
            ratio = [rng.randint(1, 9), rng.randint(1, 9)]
            if ratio[0] != ratio[1]:
                break
        unit_value = rng.randint(_UNIT_VALUE_MIN, _UNIT_VALUE_MAX)
        total = sum(ratio) * unit_value  # exact by construction; stays in [6, 2000]
        return {"names": names, "ratio": ratio, "total": total}

    def solve(self, params: dict) -> dict:
        ratio = params["ratio"]
        total = params["total"]
        units_total = sum(ratio)
        unit_value = total // units_total
        answer_value = ratio[1] * unit_value
        return {
            "answer": {"type": "quantity", "value": answer_value, "unit": "$"},
            "intermediates": {
                "units_total": units_total,
                "unit_value": unit_value,
                "answer_value": answer_value,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        ratio = params["ratio"]
        total = params["total"]
        units_total = sum(ratio)
        checks: dict[str, bool] = {}
        checks["divides_evenly"] = total % units_total == 0
        unit_value = total // units_total
        shares = [r * unit_value for r in ratio]
        checks["sums_to_total"] = sum(shares) == total
        checks["answer_verified"] = solution["answer"]["value"] == shares[1]
        checks["within_level"] = _TOTAL_MIN <= total <= _TOTAL_MAX and all(s > 0 for s in shares)
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        """Build the aid bar model (A5, ADR-0007): one bar per ratio term.

        Deterministic — derived only from params + solved intermediates, so the
        pipeline (and the resulting canonical object) stays reproducible.
        """
        names = params["names"]
        ratio = params["ratio"]
        total = params["total"]
        unit_value = solution["intermediates"]["unit_value"]
        return {
            "type": "bar_model",
            "bars": [{"label": name, "units": r} for name, r in zip(names, ratio, strict=True)],
            "annotations": [
                {"from_unit": 0, "to_unit": 1, "label": f"1 unit = ${unit_value}"},
            ],
            # Vertical curly brace across all bars → the combined total (1.1.0).
            "total_bracket": {"label": f"Total = ${total}"},
        }


register("ratio_easy", RatioEasySolver())
