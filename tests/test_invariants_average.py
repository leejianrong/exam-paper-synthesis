"""Independent correctness authority for the Average ladder (P8e, EXA-117).

Every check reads the numbers back out of the *printed question text* and re-derives the
answer from the definition of an average (mean = total ÷ count, compared as an exact
``Fraction``) — never from ``solve()`` or the solver's params. Two input sources:

* Hypothesis property tests draw params straight from each blueprint's parameter space
  (not the solver's sampler) and build the object via :func:`strategies.build_object`;
* a seed sweep runs the real pipeline (``generate``), so the sampler is covered too.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import generate
from exam_engine.blueprints.solvers import average as avg
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
_NAME = st.sampled_from(avg.NAME_POOL)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def _mean(values: list[int]) -> Fraction:
    return Fraction(sum(values), len(values))


# ------------------------------------------------------------------ checks


def check_easy(obj: dict) -> None:
    text = _text(obj)
    ints = _ints(text)
    values, count = ints[:-1], ints[-1]  # "... 14, 16 and 18 marks in 3 spelling tests."
    assert count == len(values) and 3 <= count <= 5
    answer = single_part_answer(obj)
    assert answer["type"] == "integer"
    assert _mean(values) == answer["value"]  # the answer is the mean of the listed values
    assert answer["unit"] == ("$" if "$" in text else "")


def check_medium(obj: dict) -> None:
    text = _text(obj)
    ints = _ints(text)
    answer = single_part_answer(obj)
    ans = answer["value"]
    if "spelling tests" in text:
        # "took N spelling tests. ... the first N-1 tests were a, b and c. The average
        #  score for all N tests was M."
        n, first, known, n_again, mean = ints[0], ints[1], ints[2:-2], ints[-2], ints[-1]
        assert n == n_again and first == n - 1 == len(known)
        assert _mean([*known, ans]) == mean  # the full set of n scores has the stated mean
        assert answer["unit"] == "" and 0 < ans <= 20
    else:
        # "saved an average of $A a week for N weeks. ... then spent $S ..."
        weekly, weeks, spent = ints
        assert "$" in text and answer["unit"] == "$"
        assert Fraction(ans + spent, weeks) == weekly  # (left + spent) is the total saved
        assert ans > 0


def check_hard(obj: dict) -> None:
    text = _text(obj)
    n, before, third, fourth = _ints(text)
    answer = single_part_answer(obj)
    ans = answer["value"]
    if "joined" in text:
        # "average mass of N children was B kg. After X joined them, the average mass of
        #  the N+1 children became A kg. What is X's mass?"
        assert third == n + 1 and answer["unit"] == "kg"
        assert Fraction(n * before + ans, n + 1) == fourth  # mean of the new group
        assert fourth != before and 25 <= ans <= 60
    else:
        # "average height of N children ... is B cm. X is H cm tall. When X leaves the
        #  group, what is the average height of the remaining N-1 children?"
        assert "leaves" in text and fourth == n - 1 and answer["unit"] == "cm"
        assert Fraction(n * before - third, n - 1) == ans  # mean of those who remain
        assert ans != before


# ------------------------------------------------------------------ Hypothesis


@st.composite
def easy_params(draw) -> dict:
    template = draw(st.sampled_from(sorted(avg.EASY_TEMPLATES)))
    lo, hi, _ = avg.EASY_TEMPLATES[template]
    n = draw(st.integers(3, 5))
    head = draw(st.lists(st.integers(lo, hi), min_size=n - 1, max_size=n - 1))
    last = draw(st.sampled_from([v for v in range(lo, hi + 1) if (sum(head) + v) % n == 0]))
    values = [*head, last]
    assume(len(set(values)) > 1)
    return {"name": draw(_NAME), "values": values, "template": template}


@st.composite
def medium_params(draw) -> dict:
    name = draw(_NAME)
    if draw(st.booleans()):
        n = draw(st.integers(3, 5))
        head = draw(st.lists(st.integers(5, 20), min_size=n - 1, max_size=n - 1))
        last = draw(st.sampled_from([v for v in range(5, 21) if (sum(head) + v) % n == 0]))
        assume(len({*head, last}) > 1)
        return {
            "name": name,
            "kind": "missing",
            "n": n,
            "average": (sum(head) + last) // n,
            "given": head,
        }
    n, mean = draw(st.integers(3, 8)), draw(st.integers(5, 20))
    spent = 5 * draw(st.integers(1, (n * mean - 5) // 5))
    return {"name": name, "kind": "total", "n": n, "average": mean, "given": [spent]}


@st.composite
def hard_params(draw) -> dict:
    name = draw(_NAME)
    if draw(st.booleans()):
        n, before = draw(st.integers(3, 6)), draw(st.integers(30, 45))
        after = before + draw(st.sampled_from([-3, -2, -1, 1, 2, 3]))
        assume(25 <= (n + 1) * after - n * before <= 60)
        return {"name": name, "kind": "join", "n": n, "before": before, "given": after}
    n, before = draw(st.integers(4, 7)), draw(st.integers(130, 150))
    height = before + (n - 1) * draw(st.sampled_from([-4, -3, -2, -1, 1, 2, 3, 4]))
    assume(120 <= height <= 165)
    return {"name": name, "kind": "leave", "n": n, "before": before, "given": height}


@given(params=easy_params())
def test_easy_answer_is_the_mean_of_the_listed_values(params):
    check_easy(build_object("average_easy", params))


@given(params=medium_params())
def test_medium_answer_makes_the_stated_average_true(params):
    check_medium(build_object("average_medium", params))


@given(params=hard_params())
def test_hard_answer_agrees_with_both_stated_averages(params):
    check_hard(build_object("average_hard", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check"),
    [("average_easy", check_easy), ("average_medium", check_medium), ("average_hard", check_hard)],
)
def test_seed_sweep_through_the_real_sampler(code, check):
    kinds = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        kinds.add(obj["parameters"].get("kind") or obj["parameters"]["template"])
    assert len(kinds) >= 2  # the sweep reaches every variant of the rung
