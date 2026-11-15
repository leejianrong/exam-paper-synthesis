"""Independent correctness authority for the Algebra ladder (P8e).

Every check reads the numbers back out of the *printed question text* (and, for the worked
steps, the printed algebra) and re-derives the answer a different way — never from
``solve()`` or the solver's params:

* easy   — the printed LaTeX expression is parsed by this module's own tiny evaluator
           (``\\frac``, implicit multiplication ``5n`` / ``3(n + 4)``) with the printed value
           substituted for the letter, computed exactly as a ``Fraction``;
* medium — the story is re-priced item by item from the printed prices, and every algebraic
           expression the worked solution prints (``$(8p + 10)``, ``$20p``…) must evaluate to
           the same total at the printed value of the letter;
* hard   — the story is replayed for every candidate ``x`` (brute force): exactly one whole
           ``x`` makes the stated total true, and it is the printed answer.

Two input sources: Hypothesis property tests draw params straight from each blueprint's
parameter space (not the solver's sampler) and build the object via
:func:`strategies.build_object`; a seed sweep runs the real pipeline (``generate``).
"""

from __future__ import annotations

import ast
import operator
import re
from fractions import Fraction

import pytest
from exam_engine import generate
from exam_engine.blueprints.solvers import algebra as alg
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
_NAME = st.sampled_from(alg.NAME_POOL)
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


# ------------------------------------------------------------------ a tiny LaTeX evaluator


def evaluate(latex: str, letter: str, value: int) -> Fraction:
    """Exactly evaluate a printed expression such as ``\\frac{3y - 2}{4}`` or ``4p + 2(p + 3)``
    with ``letter = value``."""
    s = latex.replace(r"\times", "*").replace(r"\div", "/").replace(" ", "")
    while r"\frac" in s:
        s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))", s)
    s = re.sub(rf"(?<=[\d)]){letter}", f"*{letter}", s)  # 5n -> 5*n
    s = re.sub(r"(?<=[\d)a-z])\(", "*(", s)  # 3(n+4) -> 3*(n+4)
    s = s.replace(letter, f"({value})")
    assert re.fullmatch(r"[\d+\-*/()]+", s), (latex, s)

    def ev(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return Fraction(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        raise AssertionError(f"unexpected syntax in {latex!r}")

    return ev(ast.parse(s, mode="eval"))


def test_the_evaluator_itself():
    assert evaluate("5n - 7", "n", 9) == 38
    assert evaluate(r"\frac{3y - 2}{4}", "y", 6) == 4
    assert evaluate(r"\frac{m}{7} + 9", "m", 28) == 13
    assert evaluate("3(k + 4)", "k", 6) == 30
    assert evaluate("4p + 2(p + 3)", "p", 5) == 36
    assert evaluate(r"5 \times 4x", "x", 2) == 40


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _math(text: str) -> list[str]:
    return re.findall(r"\\\((.+?)\\\)", text)


# ------------------------------------------------------------------ checks

_EASY = re.compile(r"Find the value of \\\((.+)\\\) when \\\(([a-z]) = (\d+)\\\)\.")


def check_easy(obj: dict) -> None:
    m = _EASY.fullmatch(_text(obj))
    assert m, _text(obj)
    expr, letter, value = m.group(1), m.group(2), int(m.group(3))
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    assert answer["value"] >= 1
    assert evaluate(expr, letter, value) == answer["value"]
    # the worked steps' printed algebra agrees at every equals sign
    for step in obj["question"]["parts"][0]["solution_steps"]:
        for piece in _math(step["text"]):
            sides = piece.split("=")
            vals = {evaluate(side, letter, value) for side in sides if side.strip() != letter}
            assert len(vals) == 1, (step["text"], vals)


_MEDIUM = re.compile(
    r"(?P<name>.+) buys (?P<k1>\d+) (?P<ones>\S+) and (?P<k2>\d+) (?P<twos>\S+)\. "
    r"A (?P<one>\S+) costs \$\\\((?P<x>[a-z])\\\)\. A (?P<two>\S+) costs "
    r"(?:\$(?P<more>\d+) more than|\$(?P<less>\d+) less than|(?P<times>\d+) times as much as)"
    r" a (?P=one)\. Find the total amount of money (?P=name) pays when "
    r"\\\((?P=x) = (?P<v>\d+)\\\)\."
)


def check_medium(obj: dict) -> None:
    m = _MEDIUM.fullmatch(_text(obj))
    assert m, _text(obj)
    k1, k2, v, x = int(m["k1"]), int(m["k2"]), int(m["v"]), m["x"]
    if m["more"]:
        price2 = v + int(m["more"])
    elif m["less"]:
        price2 = v - int(m["less"])
    else:
        price2 = v * int(m["times"])
    assert price2 >= 1 and price2 != v and k1 != k2
    # the bill, item by item
    bill = sum([v] * k1) + sum([price2] * k2)
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == "$"
    assert answer["value"] == bill
    # every expression in the letter that the worked total prints is worth the bill
    total_step = obj["question"]["parts"][0]["solution_steps"][-1]["text"]
    exprs = [e for e in _math(total_step) if x in e]
    assert len(exprs) == 2, total_step  # the expression, then its simplified form
    assert all(evaluate(e, x, v) == bill for e in exprs)


_HARD = re.compile(
    r"(?P<a>.+) has \\\(x\\\) (?P<thing>\w+)\. (?P<b>.+) has "
    r"(?:(?P<times>\d+) times as many (?P=thing) as|(?P<more>\d+) more (?P=thing) than) (?P=a)\. "
    r"(?P=b) (?:gives away (?P<give>\d+)|gets (?P<get>\d+) more) (?P=thing)\. "
    r"They now have (?P<total>\d+) (?P=thing) altogether\. Find the value of \\\(x\\\)\."
)


def _story(m: re.Match, x: int) -> int | None:
    """Replay the story with ``x``: how many altogether at the end (None if impossible)."""
    a = x
    b = x * int(m["times"]) if m["times"] else x + int(m["more"])
    if m["give"]:
        if b < int(m["give"]):
            return None
        b -= int(m["give"])
    else:
        b += int(m["get"])
    return a + b


def check_hard(obj: dict) -> None:
    m = _HARD.fullmatch(_text(obj))
    assert m, _text(obj)
    total = int(m["total"])
    solutions = [x for x in range(1, total + 1) if _story(m, x) == total]
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    assert solutions == [answer["value"]]
    assert m["a"] != m["b"]
    if m["times"]:
        assert int(m["times"]) >= 3  # PSLE says "twice", never "2 times"
    if m["give"]:  # the giver still has some left
        b = answer["value"] * int(m["times"]) if m["times"] else answer["value"] + int(m["more"])
        assert b - int(m["give"]) >= 1
    # the printed expression for the total is right at the answer
    step1 = obj["question"]["parts"][0]["solution_steps"][0]["text"]
    for side in _math(step1)[0].split("="):
        assert evaluate(side, "x", answer["value"]) == total


# ------------------------------------------------------------------ Hypothesis


@st.composite
def easy_params(draw) -> dict:
    form = draw(st.sampled_from(["add", "sub", "bracket", "frac_add", "frac_sub"]))
    letter = draw(st.sampled_from(["n", "x", "y", "k", "m", "p"]))
    a, b, c, n = draw(st.integers(2, 9)), draw(st.integers(1, 20)), 1, draw(st.integers(2, 12))
    if form == "sub":
        assume(a * n > b)
    if form == "bracket":
        b = draw(st.integers(1, 9))
    if form == "frac_add":
        n = a * draw(st.integers(2, 9))
    if form == "frac_sub":
        c = draw(st.integers(2, 5))
        assume(a * n > b and (a * n - b) % c == 0)
    return {"form": form, "letter": letter, "a": a, "b": b, "c": c, "n": n}


@st.composite
def medium_params(draw) -> dict:
    kind = draw(st.sampled_from(["more", "less", "times"]))
    k1, k2 = draw(st.integers(2, 6)), draw(st.integers(2, 6))
    assume(k1 != k2)
    if kind == "times":
        d, p = draw(st.integers(3, 5)), draw(st.integers(2, 9))
    elif kind == "more":
        d, p = draw(st.integers(1, 9)), draw(st.integers(2, 12))
    else:
        d = draw(st.integers(1, 8))
        p = draw(st.integers(d + 1, 15))
    return {
        "name": draw(_NAME),
        "items": draw(st.sampled_from(sorted(alg.ITEM_PAIRS))),
        "letter": draw(st.sampled_from(["p", "x", "y", "k"])),
        "kind": kind,
        "k1": k1,
        "k2": k2,
        "d": d,
        "p": p,
    }


@st.composite
def hard_params(draw) -> dict:
    relation = draw(st.sampled_from(["times", "more"]))
    change = draw(st.sampled_from(["give", "get"]))
    x = draw(st.integers(5, 60))
    m = draw(st.integers(3, 6)) if relation == "times" else draw(st.integers(3, 30))
    g = draw(st.integers(2, 20))
    other = m * x if relation == "times" else x + m
    if change == "give":
        assume(other - g >= 1)
        other -= g
    else:
        other += g
    assume(not (relation == "more" and m == g and change == "give"))
    names = draw(st.lists(_NAME, min_size=2, max_size=2, unique=True))
    return {
        "names": names,
        "thing": draw(st.sampled_from(["stickers", "marbles", "stamps", "beads", "cards"])),
        "relation": relation,
        "change": change,
        "m": m,
        "g": g,
        "total": x + other,
    }


@given(params=easy_params())
def test_easy_answer_is_the_printed_expression_at_the_printed_value(params):
    check_easy(build_object("algebra_easy", params))


@given(params=medium_params())
def test_medium_answer_is_the_bill_item_by_item(params):
    check_medium(build_object("algebra_medium", params))


@given(params=hard_params())
def test_hard_answer_is_the_only_x_that_makes_the_story_true(params):
    check_hard(build_object("algebra_hard", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check", "variant"),
    [
        ("algebra_easy", check_easy, lambda p: p["form"]),
        ("algebra_medium", check_medium, lambda p: p["kind"]),
        ("algebra_hard", check_hard, lambda p: (p["relation"], p["change"])),
    ],
)
def test_seed_sweep_through_the_real_sampler(code, check, variant):
    seen = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        seen.add(variant(obj["parameters"]))
    assert len(seen) >= 3  # the sweep reaches every variant of the rung
