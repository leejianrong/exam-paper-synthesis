"""Independent correctness authority for the Decimals ladder (P8e).

Every check reads the numbers back out of the *printed question text* (as ``Decimal``) and
re-derives the answer a different way from ``solve()``, which it never calls:

* easy   — ``Decimal`` arithmetic on the printed operands; a division is checked by
           multiplying the answer back (answer × divisor = dividend);
* medium — cross-multiplication: answer × n = (cost of n) × m, and the price of one item
           is a whole number of cents;
* hard   — what is left plus every purchase (quantity × price) adds up to the money she had.

Two input sources: Hypothesis property tests draw params straight from each blueprint's
parameter space (not the solver's sampler) and build the object via
:func:`strategies.build_object`; a seed sweep runs the real pipeline (``generate``).
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from exam_engine import generate
from exam_engine.blueprints.solvers import decimals as dec
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
_CENT = Decimal("0.01")


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _answer(obj: dict) -> Decimal:
    return Decimal(str(single_part_answer(obj)["value"]))


def _places(x: Decimal) -> int:
    return max(0, -x.normalize().as_tuple().exponent)  # type: ignore[operator]


# ------------------------------------------------------------------ checks


def check_easy(obj: dict) -> None:
    m = re.fullmatch(r"Find the value of (\d+\.\d+) ([×÷]) (\d+)\.", _text(obj))
    assert m, _text(obj)
    a, sign, factor = Decimal(m[1]), m[2], int(m[3])
    assert not m[1].endswith("0") and 1 <= _places(a) <= 3  # a real decimal, no padding
    assert factor in {d * 10**k for d in range(2, 10) for k in range(3)}
    answer = single_part_answer(obj)
    ans = _answer(obj)
    if sign == "×":
        assert ans == a * factor
    else:
        assert ans * factor == a  # multiply back: the quotient is exact
        assert ans != ans.to_integral_value()
    assert ans > 0 and _places(ans) <= 2
    # whole -> integer, otherwise a decimal, printed without padding zeros
    assert answer["type"] == ("integer" if ans == ans.to_integral_value() else "decimal")
    assert answer["unit"] == ""


def check_medium(obj: dict) -> None:
    m = re.fullmatch(
        r"(\d+) ([a-z ]+) cost \$(\d+\.\d\d)\. How much do (\d+) such \2 cost\?", _text(obj)
    )
    assert m, _text(obj)
    n, cost, k = int(m[1]), Decimal(m[3]), int(m[4])
    answer = single_part_answer(obj)
    ans = _answer(obj)
    assert answer["type"] == "decimal" and answer["dp"] == 2 and answer["unit"] == "$"
    assert ans * n == cost * k  # same price per item: ans / k == cost / n
    assert (cost / n) % _CENT == 0  # one item costs a whole number of cents
    assert ans % _CENT == 0 and ans > 0 and n != k


_BUY = re.compile(
    r"(\d+) (?:kg|packets|loaves|trays|bottles) of [a-z]+ at \$(\d+\.\d\d) (?:per kg|each)"
)


def check_hard(obj: dict) -> None:
    text = _text(obj)
    m = re.fullmatch(r"With \$(\d+), (.+) bought (.+)\. How much money did \2 have left\?", text)
    assert m, text
    budget = Decimal(m[1])
    buys = [(int(q), Decimal(p)) for q, p in _BUY.findall(m[3])]
    assert len(buys) == 2 and all(2 <= q <= 6 for q, _ in buys)  # two purchases
    assert m[2] == obj["parameters"]["name"]
    answer = single_part_answer(obj)
    left = _answer(obj)
    assert answer["type"] == "decimal" and answer["dp"] == 2 and answer["unit"] == "$"
    assert left + sum(q * p for q, p in buys) == budget  # left + spent = what she had
    assert left > 0 and left % _CENT == 0


# ------------------------------------------------------------------ Hypothesis

_FACTOR = st.builds(lambda d, k: d * 10**k, st.integers(2, 9), st.integers(0, 2))


@st.composite
def easy_params(draw) -> dict:
    factor = draw(_FACTOR)
    if draw(st.booleans()):
        dp = draw(st.integers(1, 3))
        digits = draw(st.integers(1, 99999))
        assume(digits % 10 != 0)
        a = Decimal(digits).scaleb(-dp)
        product = a * factor
        assume(a < 100 and _places(product) <= 2 and product < 1000)
        return {"op": "multiply", "digits": digits, "dp": dp, "factor": factor}
    q = Decimal(draw(st.integers(1, 999))).scaleb(-draw(st.integers(1, 2)))
    assume(q != q.to_integral_value())
    a = (q * factor).normalize()
    dp = _places(a)
    assume(dp >= 1 and a < 100)
    return {"op": "divide", "digits": int(a.scaleb(dp)), "dp": dp, "factor": factor}


@st.composite
def medium_params(draw) -> dict:
    unit = 5 * draw(st.integers(7, 199))
    assume(unit % 100 != 0)
    n = draw(st.integers(2, 9))
    m = draw(st.integers(2, 12).filter(lambda k: k != n))
    return {"item": draw(st.sampled_from(dec.ITEM_POOL)), "n": n, "cost": n * unit, "m": m}


@st.composite
def hard_params(draw) -> dict:
    goods = draw(st.lists(st.sampled_from(sorted(dec.GOODS)), min_size=2, max_size=2, unique=True))
    qty = draw(st.lists(st.integers(2, 6), min_size=2, max_size=2))
    price = [5 * draw(st.integers(dec.GOODS[g][2] // 5, dec.GOODS[g][3] // 5)) for g in goods]
    assume(all(p % 100 for p in price))
    spent = sum(q * p for q, p in zip(qty, price, strict=True))
    budget = draw(st.sampled_from([20, 30, 50, 100]))
    assume(budget * 100 - spent >= 100)
    return {
        "name": draw(st.sampled_from(dec.NAME_POOL)),
        "goods": goods,
        "qty": qty,
        "price": price,
        "budget": budget,
    }


@given(params=easy_params())
def test_easy_answer_is_the_printed_product_or_quotient(params):
    check_easy(build_object("decimals_easy", params))


@given(params=medium_params())
def test_medium_answer_keeps_the_same_price_per_item(params):
    check_medium(build_object("decimals_medium", params))


@given(params=hard_params())
def test_hard_answer_plus_the_shopping_is_the_money_she_had(params):
    check_hard(build_object("decimals_hard", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check", "variant"),
    [
        ("decimals_easy", check_easy, lambda p: (p["op"], p["factor"] >= 10)),
        ("decimals_medium", check_medium, lambda p: p["item"]),
        ("decimals_hard", check_hard, lambda p: tuple(p["goods"])),
    ],
)
def test_seed_sweep_through_the_real_sampler(code, check, variant):
    seen = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        seen.add(variant(obj["parameters"]))
    assert len(seen) >= 4  # the sweep reaches every variant of the rung
