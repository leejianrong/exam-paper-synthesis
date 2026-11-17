"""Independent correctness authority for ``time_duration`` (P8e batch 3, EXA-145).

The check reads the two clock times back out of the *printed question* (12-hour clock:
``10.45 a.m.``, ``12.20 p.m.``, ``11 a.m.``, ``12 noon``), turns each into a 24-hour
``(hour, minute)`` pair with its own parser, then *counts forward one minute at a time* from
the start until the clock shows the end time. The count must equal the answer. ``solve()``
never counts: it stores the duration and prints the end time from it.

Two input sources: a Hypothesis property test over the parameter space (via
:func:`strategies.build_object`) and a seed sweep through the real pipeline (``generate``).
"""

from __future__ import annotations

import re

from exam_engine import generate
from exam_engine.blueprints.solvers.measurement import EVENT_POOL
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
_TIME = r"(\d{1,2})(?:\.(\d\d))? (a\.m\.|p\.m\.|noon)"


def _clock(hour: str, minute: str | None, suffix: str) -> tuple[int, int]:
    h, m = int(hour), int(minute or 0)
    assert 1 <= h <= 12 and 0 <= m <= 59
    if suffix == "noon":
        assert (h, m) == (12, 0)
        return 12, 0
    if suffix == "a.m.":
        return (0 if h == 12 else h), m
    return (12 if h == 12 else h + 12), m


def check(obj: dict) -> None:
    text = obj["question"]["parts"][0]["text"]
    m = re.fullmatch(
        rf"A ([a-z ]+) started at {_TIME} and ended at {_TIME} on the same day\. "
        r"How many minutes did the \1 last\?",
        text,
    )
    assert m, text
    start, end = _clock(m[2], m[3], m[4]), _clock(m[5], m[6], m[7])
    count, (h, mi) = 0, start
    while (h, mi) != end:
        mi += 1
        if mi == 60:
            h, mi = h + 1, 0
        count += 1
        assert h < 24 and count <= 24 * 60, text  # the same day, so the end is reached
    answer = single_part_answer(obj)
    assert answer == {"type": "integer", "value": count, "unit": "min"}, (text, answer)
    assert end[0] > start[0]  # the lesson crosses at least one whole hour


@st.composite
def params(draw) -> dict:
    return {
        "event": draw(st.sampled_from(EVENT_POOL)),
        "start": 5 * draw(st.integers(84, 275)),
        "duration": 5 * draw(st.integers(5, 34)),
    }


@given(p=params())
def test_counting_forward_from_the_start_reaches_the_end(p):
    check(build_object("time_duration", p))


def test_seed_sweep_through_the_real_sampler():
    morning = afternoon = across_noon = borrow = 0
    for seed in SWEEP:
        obj = generate("time_duration", seed)
        check(obj)
        start, duration = obj["parameters"]["start"], obj["parameters"]["duration"]
        end = start + duration
        morning += end < 12 * 60
        afternoon += start > 12 * 60
        across_noon += start < 12 * 60 < end
        borrow += end % 60 < start % 60
    assert min(morning, afternoon, across_noon) > 0
    assert borrow >= len(SWEEP) // 2  # most need "borrowing" an hour, the real difficulty
