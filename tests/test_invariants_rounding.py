"""Independent correctness authority for ``whole_numbers_rounding`` (P8e batch 3, EXA-145).

The check reads the number and the place back out of the *printed question* and finds the
answer by brute force, never by the solver's ``(n + place/2) // place`` formula: every
multiple of the place from 0 to 10 000 is a candidate, the nearest one to the number wins,
and a tie goes to the larger (primary-school rounding: 7550 to the nearest hundred is 7600).

Two input sources: a Hypothesis property test over the parameter space (via
:func:`strategies.build_object`) and a seed sweep through the real pipeline (``generate``).
"""

from __future__ import annotations

import re

from exam_engine import generate
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
PLACES = {"ten": 10, "hundred": 100, "thousand": 1000}


def check(obj: dict) -> None:
    text = obj["question"]["parts"][0]["text"]
    m = re.fullmatch(r"Round (\d{4}) to the nearest (ten|hundred|thousand)\.", text)
    assert m, text
    n, place = int(m[1]), PLACES[m[2]]
    assert n % place != 0  # there is something to round
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == ""
    candidates = range(0, 10_001, place)
    best = min(candidates, key=lambda c: (abs(n - c), -c))  # nearest; a tie goes up
    assert answer["value"] == best, (text, answer["value"], best)


@given(number=st.integers(1001, 9999), place=st.sampled_from([10, 100, 1000]))
def test_answer_is_the_nearest_multiple_of_the_place(number, place):
    check(build_object("whole_numbers_rounding", {"number": number, "place": place}))


def test_seed_sweep_through_the_real_sampler():
    places, traps = set(), 0
    for seed in SWEEP:
        obj = generate("whole_numbers_rounding", seed)
        check(obj)
        n, place = obj["parameters"]["number"], obj["parameters"]["place"]
        places.add(place)
        # the double-rounding trap: the deciding digit is 4 and the one after it 5 or more
        traps += place >= 100 and n // (place // 10) % 10 == 4 and n // (place // 100) % 10 >= 5
    assert places == {10, 100, 1000}
    assert traps >= len(SWEEP) // 6, traps
