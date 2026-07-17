"""Independent correctness authority for the Fractions ladder (KAN-232).

A seed-sweep that re-derives each rung's *defining relationship* independently of
``solve()`` — "what must be true" of the answer, computed a different way — and
asserts every generated object also schema-validates. The golden fixtures are the
regression anchor; this sweep is the independent guard against a solver that is
self-consistent but wrong.

Exact arithmetic only (``Fraction`` / integers) — no floats — so the checks are
provable, not approximate.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd

from exam_engine import generate
from exam_engine.schema import validate_object

SWEEP = range(1, 400)


def test_easy_invariant_figure_is_the_answer_fraction():
    for seed in SWEEP:
        obj = generate("fractions_easy", seed)
        assert validate_object(obj) == [], (seed, validate_object(obj))
        part = obj["question"]["parts"][0]
        answer = part["answer"]
        fig = part["diagram"]
        num, den = answer["numerator"], answer["denominator"]

        # Defining relationship: the shaded cells ARE the answer fraction.
        assert fig["type"] == "shaded_fraction"
        assert fig["total_parts"] == den
        assert fig["shaded_parts"] == num
        # shaded/total reduces exactly to the answer fraction, which is in lowest
        # terms (so the reduction is the identity here).
        assert Fraction(fig["shaded_parts"], fig["total_parts"]) == Fraction(num, den)
        assert gcd(num, den) == 1
        assert 0 < num < den


def test_medium_invariant_answer_is_fraction_of_the_remainder():
    for seed in SWEEP:
        obj = generate("fractions_medium", seed)
        assert validate_object(obj) == [], (seed, validate_object(obj))
        p = obj["parameters"]
        answer = obj["question"]["parts"][0]["answer"]

        whole = p["whole"]
        f1 = Fraction(p["n1"], p["d1"])
        f2 = Fraction(p["n2"], p["d2"])

        # Remainder is what is left of the whole after the first fraction is
        # spent; the answer is the second fraction OF that remainder. Recomputed
        # the other way (via Fraction), it must be an integer equal to the answer.
        remainder = whole * (1 - f1)
        assert remainder.denominator == 1  # remainder is a whole number of dollars
        food = f2 * remainder
        assert food.denominator == 1
        assert int(food) == answer["value"]
        assert 0 < answer["value"] < whole


def test_hard_invariant_forward_apply_recovers_the_remainder():
    for seed in SWEEP:
        obj = generate("fractions_hard", seed)
        assert validate_object(obj) == [], (seed, validate_object(obj))
        p = obj["parameters"]
        answer = obj["question"]["parts"][0]["answer"]

        whole = answer["value"]  # the solved unknown
        f1 = Fraction(p["n1"], p["d1"])
        f2 = Fraction(p["n2"], p["d2"])

        # Forward-apply the two successive fractions to the recovered whole and
        # recover the GIVEN `left` exactly — the inverse round-trip.
        after_first = whole * (1 - f1)
        assert after_first.denominator == 1
        after_second = after_first * (1 - f2)
        assert after_second.denominator == 1
        assert int(after_second) == p["left"]
        assert whole > p["left"]
