"""Independent correctness authority for the Ratio ladder (KAN-236).

A seed-sweep that re-derives each rung's *defining relationship* independently of
``solve()`` — "what must be true" of the answer, computed a different way — and
asserts every generated object also schema-validates. The golden fixtures are the
regression anchor; this sweep is the independent guard against a solver that is
self-consistent but wrong.

Ratio predates the invariant-test policy (V1–V3), so this retrofit gives it the
same second opinion the V6/V6b ladders already ship. The check derives the shares
from the *definition* of "sharing a total in a ratio" — a rational share of the
total, ``part_i = total × ratio_i / Σ ratio`` — using ``Fraction`` (a different
arithmetic path from the solver's integer ``//``), and asserts the parts are in
the given ratio and sum to the total. Exact arithmetic only (``Fraction`` /
integers) — no floats — so the checks are provable, not approximate.
"""

from __future__ import annotations

from fractions import Fraction

from invariants import single_part_answer, sweep_generate


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


def test_easy_invariant_second_share_of_two_term_split():
    for _seed, obj in sweep_generate("ratio_easy"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        ratio, total = p["ratio"], p["total"]

        shares = _shares_in_ratio(ratio, total)
        _assert_defining_relationship(ratio, total, shares)
        # Easy rung asks for the SECOND person's share.
        assert answer["value"] == shares[1]
        assert answer["value"] > 0


def test_medium_invariant_third_share_of_three_term_split():
    for _seed, obj in sweep_generate("ratio_medium"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        ratio, total = p["ratio"], p["total"]

        assert len(ratio) == 3
        shares = _shares_in_ratio(ratio, total)
        _assert_defining_relationship(ratio, total, shares)
        # Medium rung asks for the THIRD person's share.
        assert answer["value"] == shares[2]
        assert answer["value"] > 0


def test_hard_invariant_before_after_invariant_person():
    for _seed, obj in sweep_generate("ratio_hard"):
        answer = single_part_answer(obj)
        assert answer["type"] == "quantity" and answer["unit"] == "$"
        p = obj["parameters"]
        a, b = p["ratio_before"]
        c, d = p["ratio_after"]
        spent = p["spent"]

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
