"""Independent correctness authority for the Rate ladder (P8e).

Every check reads the numbers back out of the *printed question text* and re-derives the
answer a different way from ``solve()`` — never calling it or reading the solver's params:

* easy   — repeated addition: the amount in 1 time unit, added once per time unit;
* medium — direct proportion by cross-multiplication with exact ``Fraction``s
           (amount : time is the same in the given fact and in the answer);
* hard   — a minute-by-minute simulation of the meter: the first-hour price is charged
           at minute 0, and each additional period's price at the minute it starts.

Two input sources: Hypothesis property tests draw params straight from each blueprint's
parameter space (not the solver's sampler) and build the object via
:func:`strategies.build_object`; a seed sweep runs the real pipeline (``generate``).
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import generate
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
TEMPLATES = ["baker", "cranes", "printer", "typing"]
_NAME = st.sampled_from(["Aisha", "Ben", "Hui Ling", "Nurul Aini"])


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def _time_unit(text: str) -> str:
    return "min" if "minute" in text else "h"


# ------------------------------------------------------------------ checks


def check_easy(obj: dict) -> None:
    text = _text(obj)
    per_unit, units = _ints(text)  # "... prints 45 pages per minute ... in 8 minutes?"
    assert "per minute" in text or "every hour" in text
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    total = 0
    for _ in range(units):  # one time unit at a time
        total += per_unit
    assert answer["value"] == total


def check_medium(obj: dict) -> None:
    text = _text(obj)
    amount, time, asked = _ints(text)  # "... 180 pages in 4 minutes ... 7 minutes?"
    assert "At this rate" in text
    answer = single_part_answer(obj)
    ans = answer["value"]
    assert answer["type"] == "integer" and ans > 0
    if answer["unit"] == "":
        # amount : time  ==  answer : asked time   (cross-multiplied)
        assert ans * time == amount * asked
        assert asked != time
    else:
        # the asked amount takes ``ans`` time units at the same rate
        assert answer["unit"] == _time_unit(text)
        assert asked * time == amount * ans
        assert ans != time


_PRICE = re.compile(r"\$(\d+(?:\.\d\d)?)")


def _minutes(text: str) -> int:
    stay = text.split(" for ")[-1].split(".")[0]  # "3 h 30 min" / "30 min" / "4 hours"
    h = re.search(r"(\d+) (?:h\b|hours?)", stay)
    m = re.search(r"(\d+) min", stay)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def check_hard(obj: dict) -> None:
    text = _text(obj)
    first, extra = (Fraction(p) for p in _PRICE.findall(text))
    assert "for the first hour" in text
    period = 30 if "each additional half hour" in text else 60
    assert period == 30 or "each additional hour" in text
    stay = _minutes(text)
    assert stay > 60 and stay % period == 0  # whole periods: no "part thereof" ambiguity

    charged = Fraction(0)
    for minute in range(stay):
        if minute == 0:
            charged += first
        elif minute >= 60 and (minute - 60) % period == 0:
            charged += extra

    answer = single_part_answer(obj)
    assert answer["type"] == "decimal" and answer["unit"] == "$" and answer["dp"] == 2
    assert Fraction(str(answer["value"])) == charged
    assert (charged * 100).denominator == 1  # exact cents


# ------------------------------------------------------------------ Hypothesis

_RATE = {"baker": (12, 48), "cranes": (8, 30), "printer": (20, 60), "typing": (25, 60)}


@st.composite
def easy_params(draw) -> dict:
    template = draw(st.sampled_from(TEMPLATES))
    return {
        "name": draw(_NAME),
        "template": template,
        "rate": draw(st.integers(*_RATE[template])),
        "time": draw(st.integers(3, 12)),
    }


@st.composite
def medium_params(draw) -> dict:
    template = draw(st.sampled_from(TEMPLATES))
    t1, t2 = draw(st.integers(2, 9)), draw(st.integers(2, 12))
    assume(t1 != t2)
    return {
        "name": draw(_NAME),
        "template": template,
        "kind": draw(st.sampled_from(["amount", "time"])),
        "rate": draw(st.integers(*_RATE[template])),
        "t1": t1,
        "t2": t2,
    }


@st.composite
def hard_params(draw) -> dict:
    if draw(st.booleans()):
        template, period, step = "carpark", 30, 10
        first = step * draw(st.integers(15, 40))
        extra = step * draw(st.integers(5, 20))
        duration = period * draw(st.integers(3, 10))
    else:
        template, period, step = "bicycle", 60, 50
        first = step * draw(st.integers(6, 16))
        extra = step * draw(st.integers(3, 10))
        duration = period * draw(st.integers(2, 6))
    assume(extra < first)
    return {
        "name": draw(_NAME),
        "template": template,
        "first": first,
        "extra": extra,
        "duration": duration,
    }


@given(params=easy_params())
def test_easy_answer_is_the_rate_added_once_per_time_unit(params):
    check_easy(build_object("rate_easy", params))


@given(params=medium_params())
def test_medium_answer_keeps_the_stated_rate(params):
    check_medium(build_object("rate_medium", params))


@given(params=hard_params())
def test_hard_answer_matches_a_minute_by_minute_meter(params):
    check_hard(build_object("rate_hard", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check", "variant"),
    [
        ("rate_easy", check_easy, "template"),
        ("rate_medium", check_medium, "kind"),
        ("rate_hard", check_hard, "template"),
    ],
)
def test_seed_sweep_through_the_real_sampler(code, check, variant):
    seen = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        seen.add(obj["parameters"][variant])
    assert len(seen) >= 2  # the sweep reaches every variant of the rung
