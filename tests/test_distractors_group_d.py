"""EXA-122 / EXA-145 — the "common wrong answers" hooks of the P8e batch 3 one-mark
blueprints (rounding, comparing decimals and fractions, measurement conversion, time).

For every blueprint, over many seeds through the real ``generate()``: the hook offers named
mistakes, at least two of the multiple-choice copy's three wrong options come from it in
≥ 90% of seeds, and the copy stays engine-proven. Then at least one named mistake is
re-derived *independently* from the printed question text and must be among the hook's values.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

CODES = [
    "whole_numbers_rounding",
    "decimals_compare",
    "fractions_compare",
    "measurement_conversion",
    "time_duration",
]
SEEDS = range(1, 101)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


@pytest.mark.parametrize("code", CODES)
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked and all(why.strip() for _, why in hooked), (code, seed)
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 0.9 * len(SEEDS), (code, from_hook)


# ------------------------------------------------------------------ independent re-derivations


def rounding(text: str) -> list[Fraction]:
    """Rounded the wrong way: the multiple of the place on the other side of the number."""
    m = re.search(r"Round (\d+) to the nearest (ten|hundred|thousand)", text)
    n, place = int(m[1]), {"ten": 10, "hundred": 100, "thousand": 1000}[m[2]]
    below = max(k for k in range(0, n + 1, place))
    nearer_below = n - below < below + place - n
    return [Fraction(below + place if nearer_below else below)]


def decimals_compare(text: str) -> list[Fraction]:
    """Read the digits after the point as a whole number (0.105 "beats" 0.51)."""
    ask = "greatest" if "greatest" in text else "smallest"
    nums = re.findall(r"\d+\.(\d+)", text)
    whole = re.search(r"(\d+)\.\d+", text)[1]
    pick = (max if ask == "greatest" else min)(nums, key=int)
    return [Fraction(f"{whole}.{pick}")]


def fractions_compare(text: str) -> list[Fraction]:
    """Every listed fraction but the answer is someone's pick: all three are offered."""
    fracs = [Fraction(int(a), int(b)) for a, b in re.findall(r"frac\{(\d+)\}\{(\d+)\}", text)]
    best = max(fracs) if "greatest" in text else min(fracs)
    return [f for f in fracs if f != best]


def measurement_conversion(text: str) -> list[Fraction]:
    """Took 1 big unit as 100 small units."""
    mixed = re.search(r"Express (\d+) \S+ (\d+) \S+ in", text)
    if mixed:
        return [Fraction(int(mixed[1]) * 100 + int(mixed[2]))]
    return [Fraction(re.search(r"Express (\d+\.\d+) ", text)[1]) * 100]


def time_duration(text: str) -> list[Fraction]:
    """Subtracted the clock times as if 1 hour were 100 minutes (on the 24-hour clock)."""

    def hhmm(h: str, mi: str | None, suffix: str) -> int:
        hour = int(h) % 12 + (12 if suffix in ("p.m.", "noon") else 0)
        return hour * 100 + int(mi or 0)

    times = re.findall(r"(\d{1,2})(?:\.(\d\d))? (a\.m\.|p\.m\.|noon)", text)
    start, end = (hhmm(*t) for t in times)
    return [Fraction(end - start)]


DERIVE = {
    "whole_numbers_rounding": rounding,
    "decimals_compare": decimals_compare,
    "fractions_compare": fractions_compare,
    "measurement_conversion": measurement_conversion,
    "time_duration": time_duration,
}


@pytest.mark.parametrize("code", CODES)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        values = [v for v, _ in mcq.common_wrong_answers(obj)]
        for mistake in DERIVE[code](_text(obj)):
            assert mistake in values, (code, seed, _text(obj), mistake)
