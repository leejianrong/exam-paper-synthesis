"""EXA-156: the carrying slips the distractors hooks offer show exactly the wrong answer
their reason describes. Each value is re-derived here by doing the column working by hand
(ones column first), not with ``blueprints.base.carry_slips`` / ``sum_slip``."""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import generate, mcq

_CARRIED = re.compile(r"carried (ten|\d+ tens) (twice|when multiplying)")


def _tens(reason: str) -> int:
    word = _CARRIED.search(reason).group(1)  # type: ignore[union-attr]
    return 1 if word == "ten" else int(word.split()[0])


def _product_carry(a: int, b: int) -> int:
    """Tens carried out of the ones column of ``a × b`` written in columns."""
    ones = int(str(a)[-1]) * b
    return int(str(ones)[:-1] or "0")


def _operands(code: str, params: dict) -> tuple[int, int]:
    if code == "rate_easy":
        return params["rate"], params["time"]
    if code == "speed_easy":
        return params["speed"], params["time"]
    return params["length"] * params["width"], params["height"]  # volume_easy


@pytest.mark.parametrize("code", ["rate_easy", "speed_easy", "volume_easy"])
def test_a_multiplication_carry_slip_shows_the_real_carry(code):
    seen = 0
    for seed in range(1, 201):
        obj = generate(code, seed)
        a, b = _operands(code, obj["parameters"])
        product = a * b
        for value, why in mcq.common_wrong_answers(obj):
            if "carried" not in why:
                continue
            seen += 1
            carry = _product_carry(a, b)
            assert carry >= 1 and _tens(why) == carry, (code, seed, a, b, why)
            want = product + 10 * carry if "twice" in why else product - 10 * carry
            assert value == Fraction(want), (code, seed, a, b, value, why)
            assert ("tens" in why) == (carry > 1), why
    assert seen >= 50, (code, seen)


@pytest.mark.parametrize(
    "code", ["geometry_angle_easy", "geometry_angle_medium", "geometry_angle_hard"]
)
def test_an_addition_carry_slip_is_ten_less_than_the_answer(code):
    """Adding two angles carries at most one ten; adding it twice makes the sum 10 too big,
    so the angle found by subtracting the sum is 10 too small."""
    seen = 0
    for seed in range(1, 201):
        obj = generate(code, seed)
        answer = mcq._value(obj["question"]["parts"][0]["answer"])
        for value, why in mcq.common_wrong_answers(obj):
            if "carried" not in why:
                continue
            seen += 1
            x, y = (int(n) for n in re.findall(r"(\d+)°", why))
            assert int(str(x)[-1]) + int(str(y)[-1]) >= 10, (code, seed, why)
            assert value == answer - 10, (code, seed, value, answer, why)
    assert seen >= 10, (code, seen)
