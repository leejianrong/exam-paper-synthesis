"""Independent correctness authority for the Percentage ladder (KAN-236).

A seed-sweep that re-derives each rung's *defining relationship* independently of
``solve()`` — "what must be true" of the answer, computed a different way — and
asserts every generated object also schema-validates. The golden fixtures are the
regression anchor; this sweep is the independent guard against a solver that is
self-consistent but wrong.

Percentage predates the invariant-test policy (V6 added the ladder without one),
so this retrofit gives it the same second opinion the other V6/V6b ladders ship.
The checks derive from the *definitions* — "X% of W" is ``W × X / 100``; a % change
scales by ``(100 ± X) / 100``; a reverse-percentage inverts that scaling exactly —
computed with ``Fraction`` (a different arithmetic path from the solver's integer
``//``). Exact arithmetic only (``Fraction`` / integers) — no floats — so the
checks are provable, not approximate.
"""

from __future__ import annotations

from fractions import Fraction

from invariants import single_part_answer, sweep_generate


def _factor(percent: int, direction: str) -> int:
    """The multiplier numerator over 100 for a % increase/decrease."""
    assert direction in {"increase", "decrease"}, direction
    return 100 + percent if direction == "increase" else 100 - percent


def test_easy_invariant_percent_of_whole():
    for _seed, obj in sweep_generate("percentage_easy"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        percent, whole = p["percent"], p["whole"]

        # Defining relationship: answer is X% of the whole, i.e. whole × X / 100.
        part = Fraction(whole * percent, 100)
        assert part.denominator == 1, ("X% of whole is not exact", part)
        assert answer["value"] == int(part)
        # Cross-multiplied form (exact integers): answer × 100 == percent × whole.
        assert answer["value"] * 100 == percent * whole
        assert 0 < answer["value"] < whole  # 0 < percent < 100 by construction


def test_medium_invariant_percentage_change():
    seen: set[str] = set()
    for _seed, obj in sweep_generate("percentage_medium"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        original, percent, direction = p["original"], p["percent"], p["direction"]
        seen.add(direction)

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
    assert seen == {"increase", "decrease"}


def test_hard_invariant_reverse_percentage():
    seen: set[str] = set()
    for _seed, obj in sweep_generate("percentage_hard"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        percent, direction, new_value = p["percent"], p["direction"], p["new_value"]
        seen.add(direction)

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
    assert seen == {"increase", "decrease"}
