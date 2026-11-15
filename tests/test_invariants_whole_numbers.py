"""Independent correctness authority for the Whole Numbers ladder (P8e).

Every check reads the numbers back out of the *printed question text* and re-derives the
answer a different way from ``solve()``:

* easy   — the printed expression is parsed by Python (× → ``*``, ÷ → ``/``, − → ``-``) so
           Python's own operator precedence decides the order; every sub-expression is
           evaluated as an exact ``Fraction`` and must be a positive whole number ≤ 999;
* medium — a brute-force search: the least count ``b`` with ``b × size ≥ amount`` (round up)
           or the greatest ``b`` with ``b × size ≤ amount`` (round down);
* hard   — a brute-force search over the number of pupils for the one count that makes both
           the "left over" and the "short of" statements true.

Two input sources: Hypothesis property tests draw params straight from each blueprint's
parameter space and build the object via :func:`strategies.build_object`; a seed sweep runs
the real pipeline (``generate``), so the sampler is covered too.
"""

from __future__ import annotations

import ast
import re
from fractions import Fraction

import pytest
from exam_engine import generate
from exam_engine.blueprints.solvers import whole_numbers as wn
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
UP = {"boats", "cupcakes"}
DOWN = {"rope", "pens", "eggs"}


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


# ------------------------------------------------------------------ checks


def _exact(node: ast.AST, seen: list[Fraction]) -> Fraction:
    """Evaluate a parsed arithmetic expression exactly, recording every sub-result."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        value = Fraction(node.value)
    elif isinstance(node, ast.BinOp):
        left, right = _exact(node.left, seen), _exact(node.right, seen)
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        else:
            assert isinstance(node.op, ast.Div), ast.dump(node)
            value = left / right
    else:
        raise AssertionError(f"unexpected syntax {ast.dump(node)}")
    seen.append(value)
    return value


def check_easy(obj: dict) -> None:
    text = _text(obj)
    m = re.fullmatch(r"Find the value of (.+)\.", text)
    assert m, text
    printed = m.group(1)
    assert "*" not in printed and "/" not in printed and "-" not in printed  # print symbols
    assert any(op in printed for op in "×÷")
    source = printed.replace("×", "*").replace("÷", "/").replace("−", "-")
    seen: list[Fraction] = []
    value = _exact(ast.parse(source, mode="eval").body, seen)
    # every number, intermediate result and the answer is a positive whole number <= 999
    assert all(v.denominator == 1 and 0 < v <= 999 for v in seen), (text, seen)
    answer = single_part_answer(obj)
    assert answer == {"type": "integer", "value": int(value), "unit": ""}


def check_medium(obj: dict) -> None:
    text = _text(obj)
    amount, size = max(_ints(text)), min(_ints(text))
    assert len(_ints(text)) == 2 and amount > size >= 2
    assert amount % size != 0  # the remainder is never 0
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    if "least number" in text:  # round up: everything must fit
        expected = next(b for b in range(1, amount + 1) if b * size >= amount)
    else:  # round down: only complete groups count
        assert "greatest number" in text or "filled completely" in text
        expected = max(b for b in range(0, amount + 1) if b * size <= amount)
    assert answer["value"] == expected >= 2


def check_hard(obj: dict) -> None:
    text = _text(obj)
    small, left, big, short = _ints(text)  # "{a} each ... {left} left over ... {b} ... {short}"
    assert "left over" in text and "short of" in text and big > small
    pupils = [p for p in range(1, 1000) if small * p + left == big * p - short]
    assert len(pupils) == 1 and pupils[0] >= 2
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    assert answer["value"] == small * pupils[0] + left == big * pupils[0] - short


# ------------------------------------------------------------------ Hypothesis


@st.composite
def easy_params(draw) -> dict:
    form = draw(st.sampled_from(sorted(wn.EASY_FORMS)))
    small = st.integers(2, 12)
    if form == "sub_div_mul":
        c, q, d = draw(small), draw(small), draw(small)
        nums = [q * d + draw(st.integers(1, 200)), q * c, c, d]
    elif form == "add_mul_bracket":
        d = draw(st.integers(1, 50))
        nums = [draw(st.integers(1, 200)), draw(small), d + draw(st.integers(1, 20)), d]
    elif form == "bracket_div_mul":
        c, q = draw(small), draw(st.integers(1, 30))
        a = draw(st.integers(1, q * c))
        assume(q * c - a >= 1)
        nums = [a, q * c - a, c, draw(small)]
    else:
        a, b, d, q = draw(small), draw(small), draw(small), draw(small)
        assume(a * b > q)
        nums = [a, b, q * d, d]
    return {"form": form, "nums": nums}


@st.composite
def medium_params(draw) -> dict:
    d = draw(st.integers(2, 9))
    n = d * draw(st.integers(2, 100)) + draw(st.integers(1, d - 1))
    assume(n <= 999)
    return {"context": draw(st.sampled_from(sorted(UP | DOWN))), "n": n, "d": d}


@st.composite
def hard_params(draw) -> dict:
    a, k, pupils = draw(st.integers(2, 9)), draw(st.integers(1, 5)), draw(st.integers(2, 60))
    gap = k * pupils
    assume(gap >= 4)
    left = draw(st.integers(2, min(gap - 2, 200)))
    assume(gap - left <= 200 and a * pupils + left <= 999)
    return {
        "name": draw(st.sampled_from(wn.NAME_POOL)),
        "item": draw(st.sampled_from(wn.ITEM_POOL)),
        "a": a,
        "b": a + k,
        "left": left,
        "short": gap - left,
    }


@given(params=easy_params())
def test_easy_answer_follows_pythons_order_of_operations(params):
    check_easy(build_object("whole_numbers_easy", params))


@given(params=medium_params())
def test_medium_answer_is_the_brute_forced_round_up_or_down(params):
    check_medium(build_object("whole_numbers_medium", params))


@given(params=hard_params())
def test_hard_answer_satisfies_both_the_excess_and_the_shortage(params):
    check_hard(build_object("whole_numbers_hard", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check", "variants"),
    [
        ("whole_numbers_easy", check_easy, 4),
        ("whole_numbers_medium", check_medium, 5),
        ("whole_numbers_hard", check_hard, len(wn.ITEM_POOL)),
    ],
)
def test_seed_sweep_through_the_real_sampler(code, check, variants):
    kinds = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        p = obj["parameters"]
        kinds.add(p.get("form") or p.get("context") or p["item"])
    assert len(kinds) >= variants  # the sweep reaches every variant of the rung
