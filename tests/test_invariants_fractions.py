"""Independent correctness authority for the Fractions ladder (KAN-232, KAN-237).

Property-based (Hypothesis) tests that re-derive each rung's *defining
relationship* independently of ``solve()`` over params generated directly from
the blueprint's parameter space, shrinking failures to a minimal counterexample.
Every generated object also schema-validates (inside ``build_object``). The
golden fixtures are the regression anchor; these tests are the independent guard
against a solver that is self-consistent but wrong.

Exact arithmetic only (``Fraction`` / integers) — no floats — so the checks are
provable, not approximate.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd

from hypothesis import given
from strategies import (
    build_object,
    fractions_easy_params,
    fractions_hard_params,
    fractions_medium_params,
)


@given(params=fractions_easy_params())
def test_easy_invariant_figure_is_the_answer_fraction(params: dict):
    obj = build_object("fractions_easy", params)
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


@given(params=fractions_medium_params())
def test_medium_invariant_answer_is_fraction_of_the_remainder(params: dict):
    obj = build_object("fractions_medium", params)
    answer = obj["question"]["parts"][0]["answer"]

    whole = params["whole"]
    f1 = Fraction(params["n1"], params["d1"])
    f2 = Fraction(params["n2"], params["d2"])

    # Remainder is what is left of the whole after the first fraction is
    # spent; the answer is the second fraction OF that remainder. Recomputed
    # the other way (via Fraction), it must be an integer equal to the answer.
    remainder = whole * (1 - f1)
    assert remainder.denominator == 1  # remainder is a whole number of dollars
    food = f2 * remainder
    assert food.denominator == 1
    assert int(food) == answer["value"]
    assert 0 < answer["value"] < whole


@given(params=fractions_hard_params())
def test_hard_invariant_forward_apply_recovers_the_remainder(params: dict):
    obj = build_object("fractions_hard", params)
    answer = obj["question"]["parts"][0]["answer"]

    whole = answer["value"]  # the solved unknown
    f1 = Fraction(params["n1"], params["d1"])
    f2 = Fraction(params["n2"], params["d2"])

    # Forward-apply the two successive fractions to the recovered whole and
    # recover the GIVEN `left` exactly — the inverse round-trip.
    after_first = whole * (1 - f1)
    assert after_first.denominator == 1
    after_second = after_first * (1 - f2)
    assert after_second.denominator == 1
    assert int(after_second) == params["left"]
    assert whole > params["left"]
