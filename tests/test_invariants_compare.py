"""Independent correctness authority for ``decimals_compare`` and ``fractions_compare``
(P8e batch 3, EXA-145).

Both checks read the four numbers back out of the *printed question* and re-derive the answer
a different way from ``solve()`` (which sorts ``Fraction`` values):

* decimals  — each printed decimal is padded to the same number of places and the digit
              strings are compared character by character, the way a pupil is taught
              (``0.510`` vs ``0.501``: tenths equal, hundredths 1 > 0);
* fractions — a round-robin of cross-multiplications: the answer is the one fraction that
              beats each of the other three (``a/b > c/d`` iff ``a·d > c·b``).

Both also require the four numbers to be distinct and the answer to be one of them, so a
multiple-choice copy's options can be exactly the printed numbers.

Two input sources: Hypothesis property tests over each parameter space (via
:func:`strategies.build_object`) and a seed sweep through the real pipeline (``generate``).
"""

from __future__ import annotations

import re
from math import gcd

from exam_engine import generate
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


# ------------------------------------------------------------------ decimals


def _padded(texts: list[str]) -> list[str]:
    """``["0.15", "0.105"]`` -> ``["0.150", "0.105"]`` (same whole part width assumed)."""
    places = max(len(t.split(".")[1]) for t in texts)
    return [t + "0" * (places - len(t.split(".")[1])) for t in texts]


def check_decimals(obj: dict) -> None:
    m = re.fullmatch(
        r"Which is the (greatest|smallest) of the decimals "
        r"(\d+\.\d+), (\d+\.\d+), (\d+\.\d+) and (\d+\.\d+)\?",
        _text(obj),
    )
    assert m, _text(obj)
    ask, texts = m[1], [m[2], m[3], m[4], m[5]]
    assert len(set(texts)) == 4 and not any(t.endswith("0") for t in texts)
    assert len({t.split(".")[0] for t in texts}) == 1  # one whole-number part
    padded = _padded(texts)
    pick = max(padded) if ask == "greatest" else min(padded)  # string order = place order
    expected = texts[padded.index(pick)]
    answer = single_part_answer(obj)
    assert answer["type"] == "decimal" and answer["unit"] == ""
    assert str(answer["value"]) == expected, (_text(obj), answer["value"], expected)


@st.composite
def decimals_params(draw) -> dict:
    """Four decimals of mixed lengths (1-3 places), so the "longer is bigger" trap the
    blueprint requires turns up often."""
    whole = draw(st.integers(0, 9))
    parts = []
    for _ in range(4):
        places = draw(st.integers(1, 3))
        digits = draw(st.integers(1, 10**places - 1).filter(lambda k: k % 10 != 0))
        parts.append(digits * 10 ** (3 - places))
    return {
        "ask": draw(st.sampled_from(["greatest", "smallest"])),
        "thousandths": [whole * 1000 + p for p in parts],
    }


@given(params=decimals_params())
def test_decimals_answer_wins_place_by_place(params):
    check_decimals(build_object("decimals_compare", params))


def test_decimals_seed_sweep():
    asks = set()
    for seed in SWEEP:
        obj = generate("decimals_compare", seed)
        check_decimals(obj)
        asks.add(obj["parameters"]["ask"])
    assert asks == {"greatest", "smallest"}


# ------------------------------------------------------------------ fractions


def check_fractions(obj: dict) -> None:
    text = _text(obj)
    m = re.fullmatch(r"Which is the (greatest|smallest) of the fractions (.*)\?", text)
    assert m, text
    ask = m[1]
    fracs = [(int(a), int(b)) for a, b in re.findall(r"\\frac\{(\d+)\}\{(\d+)\}", m[2])]
    assert len(fracs) == 4, text
    assert all(0 < a < b and gcd(a, b) == 1 for a, b in fracs)  # proper, simplest form
    assert len({b for _, b in fracs}) == 4  # unlike denominators: a real comparison

    def beats(x: tuple[int, int], y: tuple[int, int]) -> bool:
        lhs, rhs = x[0] * y[1], y[0] * x[1]
        return lhs > rhs if ask == "greatest" else lhs < rhs

    winners = [f for f in fracs if all(beats(f, g) for g in fracs if g != f)]
    assert len(winners) == 1, text
    answer = single_part_answer(obj)
    assert answer["type"] == "fraction"
    assert (answer["numerator"], answer["denominator"]) == winners[0], text


@st.composite
def fractions_params(draw) -> dict:
    denoms = draw(st.lists(st.integers(3, 12), min_size=4, max_size=4, unique=True))
    fracs = []
    for d in denoms:
        n = draw(st.sampled_from([k for k in range(1, d) if gcd(k, d) == 1]))
        fracs.append([n, d])
    return {"ask": draw(st.sampled_from(["greatest", "smallest"])), "fractions": fracs}


@given(params=fractions_params())
def test_fractions_answer_beats_every_other_by_cross_multiplying(params):
    check_fractions(build_object("fractions_compare", params))


def test_fractions_seed_sweep():
    asks = set()
    for seed in SWEEP:
        obj = generate("fractions_compare", seed)
        check_fractions(obj)
        asks.add(obj["parameters"]["ask"])
    assert asks == {"greatest", "smallest"}
