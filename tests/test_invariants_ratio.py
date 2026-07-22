"""Independent correctness authority for the Ratio ladder (KAN-236, KAN-237).

Property-based (Hypothesis) tests that re-derive each rung's *defining
relationship* independently of ``solve()`` — "what must be true" of the answer,
computed a different way — over params generated directly from the blueprint's
parameter space (not just integer seeds), shrinking any failure to a minimal
counterexample. Every generated object also schema-validates (inside
``build_object``). The golden fixtures are the regression anchor; these tests are
the independent guard against a solver that is self-consistent but wrong.

The check derives the shares from the *definition* of "sharing a total in a
ratio" — a rational share of the total, ``part_i = total × ratio_i / Σ ratio`` —
using ``Fraction`` (a different arithmetic path from the solver's integer ``//``),
and asserts the parts are in the given ratio and sum to the total. Exact
arithmetic only (``Fraction`` / integers) — no floats — so the checks are
provable, not approximate.
"""

from __future__ import annotations

import copy
from fractions import Fraction

from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import check_consistency
from exam_engine.schema import validate_object
from hypothesis import given
from invariants import single_part_answer
from strategies import (
    build_object,
    ratio_easy_params,
    ratio_hard_params,
    ratio_medium_params,
)


def _shares_in_ratio(ratio: list[int], total: int) -> list[int]:
    """The exact shares when ``total`` is split in ``ratio``.

    Derived from the definition (rational share of the total), independent of the
    solver's ``unit_value = total // Σ ratio`` path. Every share must be a whole
    number — guaranteed by construction, and asserted here so a non-exact split
    would fail loudly rather than silently truncate.
    """
    units = sum(ratio)
    shares = [Fraction(total * r, units) for r in ratio]
    for s in shares:
        assert s.denominator == 1, ("share is not a whole number", ratio, total, s)
    return [int(s) for s in shares]


def _assert_defining_relationship(ratio: list[int], total: int, shares: list[int]) -> None:
    # The parts are in the given ratio: part_i / part_j == ratio_i / ratio_j,
    # cross-multiplied to stay in exact integers.
    for i in range(len(ratio)):
        for j in range(len(ratio)):
            assert shares[i] * ratio[j] == shares[j] * ratio[i], ("not in ratio", i, j)
    # The parts sum to the total.
    assert sum(shares) == total, ("parts do not sum to total", shares, total)


@given(params=ratio_easy_params())
def test_easy_invariant_second_share_of_two_term_split(params: dict):
    obj = build_object("ratio_easy", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    ratio, total = params["ratio"], params["total"]

    shares = _shares_in_ratio(ratio, total)
    _assert_defining_relationship(ratio, total, shares)
    # Easy rung asks for the SECOND person's share.
    assert answer["value"] == shares[1]
    assert answer["value"] > 0


@given(params=ratio_medium_params())
def test_medium_invariant_third_share_of_three_term_split(params: dict):
    obj = build_object("ratio_medium", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    ratio, total = params["ratio"], params["total"]

    assert len(ratio) == 3
    shares = _shares_in_ratio(ratio, total)
    _assert_defining_relationship(ratio, total, shares)
    # Medium rung asks for the THIRD person's share.
    assert answer["value"] == shares[2]
    assert answer["value"] > 0


@given(params=ratio_hard_params())
def test_hard_invariant_before_after_invariant_person(params: dict):
    obj = build_object("ratio_hard", params)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    a, b = params["ratio_before"]
    c, d = params["ratio_after"]
    spent = params["spent"]

    # Defining algebra, derived independently of the solver's LCM heuristic:
    # B is invariant, A_before = (a/b)·B, A_after = (c/d)·B, and A spent
    # `spent`, so B·(a/b − c/d) = spent  ⇒  B = spent·b·d / (a·d − c·b).
    denom = a * d - c * b
    assert denom > 0, ("A must strictly shrink", a, b, c, d)
    b_amount = Fraction(spent * b * d, denom)
    assert b_amount.denominator == 1, ("B is not a whole amount", b_amount)
    assert answer["value"] == int(b_amount)

    # Cross-check the two A stages recover `spent` exactly (round-trip).
    a_before = Fraction(a, b) * b_amount
    a_after = Fraction(c, d) * b_amount
    assert a_before.denominator == 1 and a_after.denominator == 1
    assert a_before - a_after == spent
    assert a_before > 0 and a_after > 0 and answer["value"] > 0


@given(params=ratio_hard_params())
def test_hard_view_mode_is_answer_independent(params: dict):
    """KAN-310: the before-after diagram's view_mode (grouped|sliced) is a pure
    rendering choice. Both modes must be schema-valid and pass the numeric
    consistency check, and neither changes the solved answer."""
    obj = build_object("ratio_hard", params)
    answer = single_part_answer(obj)
    diagram = obj["question"]["parts"][0]["diagram"]
    assert diagram is not None and diagram["type"] == "bar_model_before_after"
    assert diagram["view_mode"] == "grouped"  # solver default

    solution = get_solver("ratio_hard").solve(params)
    for mode in ("grouped", "sliced"):
        child = copy.deepcopy(obj)
        child["question"]["parts"][0]["diagram"]["view_mode"] = mode
        # Still schema-valid and still the printed answer (mode is display-only).
        assert validate_object(child) == []
        assert single_part_answer(child) == answer
        # The numeric consistency check is indifferent to the view mode.
        checks = check_consistency(child["question"]["parts"][0]["diagram"], params, solution)
        assert all(checks.values()), (mode, checks)
