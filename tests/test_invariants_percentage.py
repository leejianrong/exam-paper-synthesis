"""Independent correctness authority for the Percentage ladder (KAN-236, KAN-237).

Property-based (Hypothesis) tests that re-derive each rung's *defining
relationship* independently of ``solve()`` over params generated directly from
the blueprint's parameter space, shrinking failures to a minimal counterexample.
Every generated object also schema-validates (inside ``build_object``). The
golden fixtures are the regression anchor; these tests are the independent guard
against a solver that is self-consistent but wrong.

The checks derive from the *definitions* — "X% of W" is ``W × X / 100``; a %
change scales by ``(100 ± X) / 100``; a reverse-percentage inverts that scaling
exactly — computed with ``Fraction`` (a different arithmetic path from the
solver's integer ``//``). Both directions (increase / decrease) are exercised via
parametrisation. Exact arithmetic only (``Fraction`` / integers) — no floats.
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import (
    build_object,
    percentage_easy_params,
    percentage_hard_params,
    percentage_medium_params,
)


def _factor(percent: int, direction: str) -> int:
    """The multiplier numerator over 100 for a % increase/decrease."""
    assert direction in {"increase", "decrease"}, direction
    return 100 + percent if direction == "increase" else 100 - percent


@given(params=percentage_easy_params())
def test_easy_invariant_percent_of_whole(params: dict):
    obj = build_object("percentage_easy", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    percent, whole = params["percent"], params["whole"]

    # Defining relationship: answer is X% of the whole, i.e. whole × X / 100.
    part = Fraction(whole * percent, 100)
    assert part.denominator == 1, ("X% of whole is not exact", part)
    assert answer["value"] == int(part)
    # Cross-multiplied form (exact integers): answer × 100 == percent × whole.
    assert answer["value"] * 100 == percent * whole
    assert 0 < answer["value"] < whole  # 0 < percent < 100 by construction


@pytest.mark.parametrize("direction", ["increase", "decrease"])
@given(data=st.data())
def test_medium_invariant_percentage_change(direction: str, data: st.DataObject):
    params = data.draw(percentage_medium_params(direction))
    obj = build_object("percentage_medium", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    original, percent = params["original"], params["percent"]
    assert params["direction"] == direction

    # Defining relationship: the new value scales the original by (100 ± X)/100.
    factor = _factor(percent, direction)
    new_value = Fraction(original * factor, 100)
    assert new_value.denominator == 1, ("scaled value is not exact", new_value)
    assert answer["value"] == int(new_value)

    # The change amount is X% of the original, and points the right way.
    change = Fraction(original * percent, 100)
    assert change.denominator == 1
    if direction == "increase":
        assert answer["value"] == original + int(change)
        assert answer["value"] > original
    else:
        assert answer["value"] == original - int(change)
        assert answer["value"] < original
    assert answer["value"] > 0


@pytest.mark.parametrize("direction", ["increase", "decrease"])
@given(data=st.data())
def test_hard_invariant_reverse_percentage(direction: str, data: st.DataObject):
    params = data.draw(percentage_hard_params(direction))
    obj = build_object("percentage_hard", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    percent, new_value = params["percent"], params["new_value"]
    assert params["direction"] == direction

    # The trap: new_value is factor% of the original, not 100%. Recover the
    # original by inverting that scaling — new_value × 100 / (100 ± X).
    factor = _factor(percent, direction)
    assert factor > 0
    original = Fraction(new_value * 100, factor)
    assert original.denominator == 1, ("reverse-% is not exact", original)
    assert answer["value"] == int(original)

    # Forward round-trip: re-applying the change to the recovered original
    # reproduces the given new_value exactly.
    assert Fraction(int(original) * factor, 100) == new_value
    assert answer["value"] > 0
