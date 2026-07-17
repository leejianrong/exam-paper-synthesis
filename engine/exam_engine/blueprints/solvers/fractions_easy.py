"""Solver for ``fractions_easy``: read the fraction of a figure that is shaded
(DIFFICULTY.md — easy Fractions rung; plan decision D1 — the mandatory
``shaded_fraction`` figure).

Answer type: the canonical **fraction** (numerator/denominator). The figure is a
*mandatory* aid: its ``total_parts``/``shaded_parts`` equal the answer's
denominator/numerator exactly, so the printed figure is provably the printed
answer (ADR-0007/0012).

Constraints are satisfied *by construction* (ADR-0014): ``numerator`` and
``denominator`` are sampled coprime with ``0 < numerator < denominator``, so the
fraction is already in simplest form and ``shaded_parts == numerator``,
``total_parts == denominator`` hold without any reduction.
"""

from __future__ import annotations

import random
from math import gcd

from ..registry import register

_SHAPES = ["rectangle", "circle", "bar"]
_DENOM_MIN = 2
_DENOM_MAX = 12


class FractionsEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        shape = rng.choice(_SHAPES)
        # Proper fraction in lowest terms: 0 < numerator < denominator, gcd == 1.
        while True:
            denominator = rng.randint(_DENOM_MIN, _DENOM_MAX)
            numerator = rng.randint(1, denominator - 1)
            if gcd(numerator, denominator) == 1:
                break
        return {"shape": shape, "numerator": numerator, "denominator": denominator}

    def solve(self, params: dict) -> dict:
        numerator = params["numerator"]
        denominator = params["denominator"]
        return {
            "answer": {
                "type": "fraction",
                "numerator": numerator,
                "denominator": denominator,
            },
            "intermediates": {},
        }

    def validate(self, params: dict, solution: dict) -> dict:
        numerator = params["numerator"]
        denominator = params["denominator"]
        answer = solution["answer"]
        checks: dict[str, bool] = {}
        checks["simplest_form"] = gcd(numerator, denominator) == 1
        checks["proper_fraction"] = 0 < numerator < denominator
        checks["answer_verified"] = (
            answer["numerator"] == numerator and answer["denominator"] == denominator
        )
        checks["within_level"] = _DENOM_MIN <= denominator <= _DENOM_MAX
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        """Build the mandatory ``shaded_fraction`` figure (plan D1).

        Deterministic — ``total_parts``/``shaded_parts`` come straight from the
        answer's denominator/numerator, so the figure is provably the answer.
        """
        return {
            "type": "shaded_fraction",
            "shape": params["shape"],
            "total_parts": params["denominator"],
            "shaded_parts": params["numerator"],
        }


register("fractions_easy", FractionsEasySolver())
