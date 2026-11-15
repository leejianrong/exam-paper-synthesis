"""EXA-122 — the "common wrong answer" hooks of the speed, volume, angle, area and chart
solvers (``Solver.distractors``), checked through the real ``generate`` -> ``mcq.to_mcq``.

For every blueprint, over a seed sweep:

* the hook offers wrong answers, each with a reason, and the multiple-choice copy is built
  mostly from them (at least two of its three wrong options in >= 90% of seeds);
* the copy still verifies as engine-proven (``verify_snapshot``);
* at least one named mistake is re-derived *independently* from the printed question
  (numbers parsed out of the text and the drawn figure, never from the solver) and must be
  among the hook's values.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

SEEDS = range(1, 101)

CODES = [
    "speed_easy",
    "speed_medium",
    "speed_hard",
    "volume_easy",
    "volume_medium",
    "volume_hard",
    "geometry_angle_easy",
    "geometry_angle_medium",
    "geometry_angle_hard",
    "geometry_area_easy",
    "geometry_area_medium",
    "geometry_area_hard",
    "statistics_chart_easy",
    "statistics_chart_medium",
    "statistics_chart_hard",
]

# speed_hard: the gap is (s1 + s2) x a whole number of hours, so the one mistake that is
# always exact is "the mean of the two speeds" (twice the answer). The others (the
# difference of the speeds, one speed only) are offered when they come to at most 1 dp
# (about a third of questions, e.g. 2.5 h); a recurring 10/3 h is never rounded into a
# made-up option, so the generic near misses fill in.
MIN_TWO_FROM_HOOK: dict[str, float] = {"speed_hard": 0.3}


def _part(obj: dict) -> dict:
    return obj["question"]["parts"][0]


def _text(obj: dict) -> str:
    return f"{obj['question'].get('stem') or ''} {_part(obj)['text']}"


def _options(obj: dict) -> list[str]:
    return [o["text"] for o in _part(obj)["answer"]["options"]]


@pytest.mark.parametrize("code", CODES)
def test_the_hook_supplies_most_wrong_options(code):
    two_from_hook = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        assert mcq.convertible(obj), (code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked, (code, seed)
        assert all(isinstance(why, str) and why.strip() for _, why in hooked), (code, seed)
        answer = _part(obj)["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        wrong = [t for t in _options(m) if t != mcq.answer_text(answer)]
        assert len(wrong) == 3
        from_hook = sum(t in hook_texts for t in wrong)
        assert from_hook >= 1, (code, seed, _options(m))
        two_from_hook += from_hook >= 2
    assert two_from_hook / len(SEEDS) >= MIN_TWO_FROM_HOOK.get(code, 0.9), two_from_hook


# --- independent re-derivations from the printed question -----------------------------


def _nums(pattern: str, text: str) -> list[int]:
    return [int(x) for x in re.findall(pattern, text)]


def _labels(obj: dict) -> dict[str, int]:
    """Labelled segment lengths of the drawn figure, keyed ``"A-B"``."""
    out = {}
    for s in _part(obj)["diagram"].get("segments", []):
        m = re.fullmatch(r"(\d+) cm", s.get("label") or "")
        if m:
            out[f"{s['from']}-{s['to']}"] = int(m.group(1))
    return out


def _pi(text: str) -> Fraction:
    return Fraction(22, 7) if "π = 22/7" in text else Fraction(314, 100)


def _given_angles(obj: dict) -> list[int]:
    return [a["value_deg"] for a in _part(obj)["diagram"]["angles"] if not a["unknown"]]


def _angle(name: str, text: str) -> int:
    return int(re.search(rf"∠{name} = (\d+)°", text).group(1))


def _expected_mistake(obj: dict) -> tuple[Fraction, str]:
    """One named mistake, re-derived from what the pupil sees."""
    code, text = obj["blueprint_code"], _text(obj)
    if code == "speed_easy":
        (speed,) = _nums(r"(\d+) km/h", text)
        (time,) = _nums(r"for (\d+) h", text)
        return Fraction(speed + time), "added the speed and the time"
    if code == "speed_medium":
        d1, d2 = _nums(r"(\d+) km", text)
        t1, t2 = _nums(r"(\d+) h\b", text)
        return (Fraction(d1, t1) + Fraction(d2, t2)) / 2, "the mean of the two speeds"
    if code == "speed_hard":
        (gap,) = _nums(r"(\d+) km apart", text)
        s1, s2 = _nums(r"(\d+) km/h", text)
        return Fraction(gap) / Fraction(s1 + s2, 2), "the mean of the two speeds"
    if code == "volume_easy":
        length, width, _ = _nums(r"(\d+) cm", text)
        return Fraction(length * width), "the area of the base only"
    if code == "volume_medium":
        length, width, height, _ = _nums(r"(\d+) cm(?!³)", text)
        return Fraction(length * width * height, 1000), "the capacity of the whole tank"
    if code == "volume_hard":
        length, width, _, _, after = _nums(r"(\d+) cm", text)
        return Fraction(length * width * after), "used the new level, not the rise"
    if code == "geometry_angle_easy":
        given = sum(_given_angles(obj))
        if "meet at the point" in text:
            return Fraction(given), "the reflex angle"
        return Fraction(360 - given), "used 360°"
    if code == "geometry_angle_medium":
        if "BCD is a straight line" in text:
            return Fraction(180 - _angle("ACD", text)), "found ∠ACB"
        (given,) = _given_angles(obj)
        if "Find ∠ABC" in text:
            return Fraction(180 - given), "forgot to halve"
        return Fraction(180 - given), "subtracted only one base angle"
    if code == "geometry_angle_hard":
        if "rhombus" in text:
            return Fraction(180 - _angle("ABC", text)), "forgot to halve"
        return Fraction(180 - _angle("DAB", text)), "stopped at the angle beside ∠DAB"
    if code == "geometry_area_easy":
        if "rectangle measuring" in text:
            w, h = _nums(r"(\d+) cm", text)
            return Fraction(2 * (w + h)), "the perimeter"
        if "square of side" in text:
            (s,) = _nums(r"(\d+) cm", text)
            return Fraction(4 * s), "the perimeter"
        b, h = _nums(r"(\d+) cm", text)
        return Fraction(b * h), "forgot to halve"
    if code == "geometry_area_medium":
        lab = _labels(obj)
        if "L-shaped" in text:
            return Fraction(lab["A-B"] * lab["F-A"]), "forgot to take away the corner"
        if "house shape" in text:
            w, h_rect, h_tri = lab["C-D"], lab["B-C"], lab["A-M"]
            return Fraction(w * h_rect + w * h_tri), "forgot to halve the triangle"
        if "Find its width" in text:
            area, length = _nums(r"(\d+) cm", text)
            return Fraction(2 * area, length), "used the triangle formula"
        r = lab["O-T"]
        if "Find its area" in text:
            return _pi(text) * r * r, "the whole circle"
        return _pi(text) * r, "the curved edge only"
    if code == "geometry_area_hard":
        lab = _labels(obj)
        if "quarter circle" in text:
            s = lab["A-B"]
            return _pi(text) * s * s / 4, "the quarter circle"
        if "running track" in text:
            straight, r = lab["TL-TR"], lab["OL-TL"]
            return 2 * straight + _pi(text) * r, "only one semicircle"
        b, h = lab["A-B"], lab["T-O"]
        return b * h + _pi(text) * Fraction(b, 2) ** 2 / 2, "forgot to halve the triangle"
    diagram = _part(obj)["diagram"]
    if code == "statistics_chart_easy":
        cats = diagram["x_axis"]["categories"]
        values = dict(zip(cats, diagram["series"][0]["values"], strict=True))
        a, b = re.search(r"(?:on|did) (\w+) (?:collect )?than (?:on )?(\w+)\?", text).groups()
        return Fraction(values[a] + values[b]), "the total, not the difference"
    if code == "statistics_chart_medium":
        shown = [s["value"] for s in diagram["sectors"] if s["show_value"]]
        return Fraction(100 - sum(shown)), "gave the percentage"
    assert code == "statistics_chart_hard"
    (mean,) = _nums(r"was (\d+)\.", text)
    known = [v for v in diagram["series"][0]["values"] if v is not None]
    return Fraction(4 * mean - sum(known)), "used 4 months for the total"


@pytest.mark.parametrize("code", CODES)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    for seed in SEEDS:
        obj = generate(code, seed)
        value, name = _expected_mistake(obj)
        hooked = [v for v, _ in mcq.common_wrong_answers(obj)]
        assert value in hooked, (code, seed, name, value, hooked)


def test_speed_hard_offers_a_whole_number_of_hours_never_a_distance():
    """The motivating bug: a speed question's options must be times, not km or km/h."""
    obj = generate("speed_hard", 3)
    m = mcq.to_mcq(obj, 3)
    assert all(t.endswith(" h") for t in _options(m))
    assert "used the mean of the two speeds" in _part(m)["marking_scheme"][0]["description"]
