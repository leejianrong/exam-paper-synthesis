"""EXA-122 / EXA-149 — the "common wrong answers" hooks of the Circles ladder.

For the multiple-choice rungs (easy, 1 mark; medium, 2 marks: Booklet A), over many seeds
through the real ``generate()``: the hook offers named mistakes, at least two of the copy's
three wrong options come from it in ≥ 90% of seeds, and the copy stays engine-proven. Then
the typical slips (radius / diameter, half / whole circle, the straight edges) are
re-derived *independently* from the printed question text and must be among the hook's
values. The hard rung (3 marks) is never multiple choice, but its numeric questions still
name their wrong answers; an answer in terms of π has none.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

SEEDS = range(1, 121)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


@pytest.mark.parametrize("code", ["circles_easy", "circles_medium"])
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert len(hooked) >= 3 and all(why.strip() for _, why in hooked), (code, seed)
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        from_hook += sum(t in hook_texts for t in wrong) >= 2
    assert from_hook >= 0.9 * len(SEEDS), (code, from_hook)


def _pi(text: str) -> Fraction:
    return Fraction(22, 7) if "π = 22/7" in text else Fraction(314, 100)


def _n(pattern: str, text: str) -> int:
    m = re.search(pattern, text)
    assert m, (pattern, text)
    return int(m[1])


def easy_slips(text: str) -> list[Fraction]:
    """Radius / diameter confusion, and a whole circle for a part of one."""
    p = _pi(text)
    if "quarter circle" in text:  # the whole circle
        r = _n(r"radius (\d+) cm", text)
        return [p * r * r]
    if "radius" in text:
        r = _n(r"radius (\d+) cm", text)
        if "circumference" in text:
            return [p * r]  # π × r: the radius taken as the diameter
        if "semicircle" in text:
            return [p * r * r]  # forgot to halve
        return [p * (2 * r) ** 2]  # doubled the radius, then squared
    d = _n(r"diameter (\d+) cm", text)
    if "circumference" in text:
        return [2 * p * d]  # 2 × π × d
    if "semicircle" in text:
        return [p * d * d / 2]
    return [p * d * d]  # the diameter as the radius


def medium_slips(text: str) -> list[Fraction]:
    """Counting an edge that does not bound the figure, or a whole circle for a semicircle."""
    p = _pi(text)
    if "quarter circle" in text:  # the curved edge only
        r = _n(r"radius (\d+) cm", text)
        return [2 * p * r / 4]
    if "made up of a square" in text:
        s = _n(r"side (\d+) cm", text)
        if "perimeter" in text:  # all four sides
            return [4 * s + p * s / 2]
        return [s * s + p * (Fraction(s, 2)) ** 2]  # a whole circle
    m = re.search(r"measuring (\d+) cm by (\d+) cm", text)
    L, W = int(m[1]), int(m[2])
    if "perimeter" in text:  # the side that was cut out, counted anyway
        return [2 * L + 2 * W + p * W / 2]
    return [L * W + p * (Fraction(W, 2)) ** 2 / 2]  # added the semicircle instead


def hard_slips(text: str) -> list[Fraction]:
    """Leaving out a part of the shaded region's outline, or half of the region."""
    p = _pi(text)
    if "ABCD is a rectangle" in text:
        s = _n(r"AD = (\d+) cm", text)
        if "perimeter" in text:  # forgot the straight edge AB
            return [p * s]
        return [2 * s * s - p * s * s / 4]  # took away one quarter circle
    s = _n(r"side (\d+) cm", text)
    if "centre C" in text:  # the leaf: only half of it
        return [p * s * s / 4 - Fraction(s * s, 2)]
    return [s * s - p * s * s / 4]  # the corner only, without the semicircle


DERIVE = {"circles_easy": easy_slips, "circles_medium": medium_slips, "circles_hard": hard_slips}


@pytest.mark.parametrize("code", list(DERIVE))
def test_a_named_slip_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        if obj["question"]["parts"][0]["answer"]["type"] == "expression":
            assert mcq.common_wrong_answers(obj) == []
            assert not mcq.convertible(obj)
            continue
        values = [v for v, _ in mcq.common_wrong_answers(obj)]
        assert len(values) >= 3, (code, seed)
        for slip in DERIVE[code](_text(obj)):
            assert slip in values, (code, seed, _text(obj), slip)
