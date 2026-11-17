"""Solver for ``percentage_remainder`` (EXA-154): a percentage of the whole, then a percentage
of what is left. The 2-mark medium rung between ``percentage_easy`` (X% of an amount) and
``percentage_medium`` (an increase or decrease, 3 marks): the second percentage is of the
remainder, not of the whole.

    "Siti had $400. Siti spent 25% of the money on a bag and 40% of the remaining money on a
     pair of shoes. How much money did Siti have left?"   75% of $400 = $300, 60% of $300 = $180.

Two asks (``ask``): the money left at the end, or the cost of the second purchase. The
person's ``name`` is cosmetic (W1a); the purchases are a ``context`` choice the wording is
built from. Exact by construction (ADR-0014): both percentages are multiples of 5 and the
amount is drawn until every step is a whole number of dollars.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register
from .ratio_easy import NAME_POOL

# context -> (first purchase, second purchase), each with its article.
CONTEXTS: dict[str, tuple[str, str]] = {
    "bag_shoes": ("a bag", "a pair of shoes"),
    "book_calculator": ("a book", "a calculator"),
    "watch_wallet": ("a watch", "a wallet"),
    "lamp_rug": ("a lamp", "a rug"),
    "racket_cap": ("a racket", "a cap"),
}

_PCT = range(10, 65, 5)  # 10% .. 60%
_TOTAL_STEP, _TOTAL_MIN, _TOTAL_MAX = 20, 100, 1200


def _the(thing: str) -> str:
    """``a pair of shoes`` -> ``the pair of shoes``."""
    return "the " + thing.split(" ", 1)[1]


class PercentageRemainderSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            p1, p2 = rng.choice(_PCT), rng.choice(_PCT)
            total = _TOTAL_STEP * rng.randint(_TOTAL_MIN // _TOTAL_STEP, _TOTAL_MAX // _TOTAL_STEP)
            rest = total * (100 - p1)
            if p1 != p2 and rest % 100 == 0 and (rest // 100) * p2 % 100 == 0:
                break
        return {
            "name": rng.choice(NAME_POOL),
            "context": rng.choice(sorted(CONTEXTS)),
            "ask": rng.choice(["left", "second"]),
            "total": total,
            "p1": p1,
            "p2": p2,
        }

    def solve(self, params: dict) -> dict:
        total, p1, p2 = params["total"], params["p1"], params["p2"]
        first, second = CONTEXTS[params["context"]]
        rest = total * (100 - p1) // 100
        spent2 = rest * p2 // 100
        left = rest - spent2
        if params["ask"] == "left":
            ask = "How much money was left?"
            step2 = f"Money left = (100% − {p2}%) of ${rest} = {100 - p2}% × ${rest} = ${left}."
            expr2 = f"{100 - p2}*{rest}/100"
            answer = left
        else:
            ask = f"How much did {_the(second)} cost?"
            step2 = f"Cost of {_the(second)} = {p2}% of ${rest} = {p2}% × ${rest} = ${spent2}."
            expr2 = f"{p2}*{rest}/100"
            answer = spent2
        return {
            "answer": {"type": "quantity", "value": answer, "unit": "$"},
            "intermediates": {
                "first": first,
                "second": second,
                "ask_text": ask,
                "rest": rest,
                "keep1": 100 - p1,
                "step2": step2,
                "expr2": expr2,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), in $, best first."""
        total, p1, p2 = params["total"], params["p1"], params["p2"]
        rest = Fraction(total * (100 - p1), 100)
        spent2 = rest * p2 / 100
        if params["ask"] == "left":
            return [
                (total - Fraction(total * (p1 + p2), 100), "took both percentages of the whole"),
                (rest, "the money left after the first purchase only"),
                (spent2, "the cost of the second purchase, not the money left"),
                (Fraction(total * p1, 100), "the cost of the first purchase"),
            ]
        return [
            (Fraction(total * p2, 100), f"{p2}% of the whole, not of the remaining money"),
            (rest - spent2, "the money left, not the cost"),
            (Fraction(total * p1, 100), "the cost of the first purchase"),
            (rest, "the remaining money after the first purchase"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        total, p1, p2 = params["total"], params["p1"], params["p2"]
        checks: dict[str, bool] = {}
        rest = Fraction(total * (100 - p1), 100)
        spent2 = rest * p2 / 100
        checks["whole_dollars"] = rest.denominator == 1 and spent2.denominator == 1
        expected = rest - spent2 if params["ask"] == "left" else spent2
        checks["answer_verified"] = Fraction(solution["answer"]["value"]) == expected
        checks["within_level"] = 0 < p1 < 100 and 0 < p2 < 100 and expected > 0
        return {"ok": all(checks.values()), "checks": checks}


register("percentage_remainder", PercentageRemainderSolver())
