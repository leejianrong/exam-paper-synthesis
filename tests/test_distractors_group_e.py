"""EXA-122 / EXA-154 — the "common wrong answers" hooks of the 2-mark medium rungs
(``ratio_difference``, ``percentage_remainder``, ``speed_minutes``, ``geometry_angle_opposite``,
``geometry_area_perimeter``).

For every blueprint, over many seeds through the real ``generate()``: the hook offers named
mistakes, at least two of the multiple-choice copy's three wrong options come from it in
≥ 90% of seeds, and the copy stays engine-proven. Then one named mistake per blueprint is
re-derived *independently* from the printed question (its text, or the printed figure) and
must be among the hook's values with that reason.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

SEEDS = range(1, 101)


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _ints(pattern: str, text: str) -> list[int]:
    return [int(x) for x in re.findall(pattern, text)]


# --- independent re-derivations: (the mistake's value, a phrase of its reason) -------------


def _ratio(obj: dict) -> tuple[Fraction, str]:
    """Took the printed difference as 1 unit, then multiplied by all the units."""
    text = _text(obj)
    a, b = _ints(r"(\d+) : ", text)[0], _ints(r" : (\d+)", text)[0]
    diff = _ints(r"has (\d+) (?:more|fewer)", text)[0]
    return Fraction((a + b) * diff), "as 1 unit"


def _percentage(obj: dict) -> tuple[Fraction, str]:
    """Both percentages taken of the whole amount."""
    text = _text(obj)
    total = _ints(r"\$(\d+)", text)[0]
    p1, p2 = _ints(r"(\d+)%", text)
    if "was left" in text:
        return Fraction(total * (100 - p1 - p2), 100), "both percentages of the whole"
    return Fraction(total * p2, 100), "of the whole, not of the remaining money"


def _speed(obj: dict) -> tuple[Fraction, str]:
    """Minutes read as hundredths of an hour (or an hour as 100 minutes)."""
    text = _text(obj)
    km_h = _ints(r"(\d+) km/h", text)
    km = _ints(r"(\d+) km(?!/)", text)
    hm = re.search(r"(\d+) h (\d+) min", text)
    mins = int(hm[1]) * 60 + int(hm[2]) if hm else (_ints(r"(\d+) minutes", text) or [0])[0]
    if "How far" in text:
        return Fraction(km_h[0] * mins, 100), "/100 h"
    if "average speed in km/h" in text:
        return Fraction(km[0] * 100, mins), "/100 h"
    return Fraction(km[0] * 100, km_h[0]), "took 1 h as 100 min"


def _angle(obj: dict) -> tuple[Fraction, str]:
    """The two given angles added (they are read off the printed figure)."""
    fig = obj["question"]["parts"][0]["diagram"]
    given = [m["value_deg"] for m in fig["angles"] if not m["unknown"]]
    if "Find ∠BOC" in _text(obj):  # here adding is right: the slip is subtracting
        return Fraction(abs(given[0] - given[1])), "subtracted the two given angles"
    return Fraction(sum(given)), "added the two given angles"


def _area(obj: dict) -> tuple[Fraction, str]:
    """Stopped at the missing side (or, for a square, at one side)."""
    text = _text(obj)
    if "square" in text:
        return Fraction(_ints(r"perimeter is (\d+)", text)[0], 4), "one side only"
    ab = _ints(r"AB = (\d+)", text)[0]
    if "perimeter is" in text:
        return Fraction(_ints(r"perimeter is (\d+)", text)[0], 2) - ab, "BC only"
    return Fraction(_ints(r"area is (\d+)", text)[0], ab), "BC only"


DERIVE = {
    "ratio_difference": _ratio,
    "percentage_remainder": _percentage,
    "speed_minutes": _speed,
    "geometry_angle_opposite": _angle,
    "geometry_area_perimeter": _area,
}


@pytest.mark.parametrize("code", DERIVE)
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


@pytest.mark.parametrize("code", DERIVE)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        value, phrase = DERIVE[code](obj)
        hooked = mcq.common_wrong_answers(obj)
        reasons = [why for v, why in hooked if v == value]
        assert reasons, (code, seed, _text(obj), value, hooked)
        assert any(phrase in why for why in reasons), (code, seed, phrase, reasons)


def test_a_mixed_unit_time_offers_the_decimal_hours_slip():
    # "1 h 15 min" read as 1.15 h: 48 km/h x 1.15 h = 55.2 km
    obj = generate("speed_minutes", 1)
    obj["parameters"].update({"kind": "distance", "speed": 48, "minutes": 75})
    values = dict(mcq.common_wrong_answers(obj))
    assert values[Fraction("55.2")] == "took 1 h 15 min as 1.15 h"
