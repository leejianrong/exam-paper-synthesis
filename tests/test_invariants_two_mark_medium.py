"""Independent correctness authority for the 2-mark medium rungs (EXA-154): ``ratio_difference``,
``percentage_remainder``, ``speed_minutes``, ``geometry_angle_opposite`` and
``geometry_area_perimeter``.

Every check reads the numbers back out of the *printed question* (its text, and for the
geometry rungs the printed figure) and re-derives the answer a different way from ``solve()``:

* ratio      — a search over every pair of amounts in the printed ratio for the one pair
               whose difference is the printed difference (no unit method);
* percentage — the whole chain as one exact product of the two "kept" (or "spent")
               fractions, in cents, never the stepwise remainder;
* speed      — cross-multiplication in minutes: distance × 60 = speed × minutes;
* angles     — the rays are given directions round O (B at 0°, so A at 180°; C at some
               bearing, D opposite it; E between A and D) and every integer bearing of C and E
               is tried; the one that reproduces both printed angles measures the asked angle;
* area       — a search over whole-number widths for the one that matches the printed
               perimeter or area, with the printed side read off the figure's label.

Two input sources: Hypothesis draws params straight from each blueprint's parameter space
(not the solver's sampler) and builds the object with :func:`strategies.build_object`; a seed
sweep runs the real pipeline (``generate``).
"""

from __future__ import annotations

import math
import re
from fractions import Fraction
from math import gcd

import pytest
from exam_engine import generate
from exam_engine.blueprints.solvers import geometry_angle_opposite as _angles
from exam_engine.blueprints.solvers import geometry_area_perimeter as _area
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 301)
_NAMES = st.sampled_from([["Aisha", "Ben"], ["Hui Ling", "Ravi"], ["Nurul Aini", "Wei Ming"]])


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


def _figure(obj: dict) -> dict:
    return obj["question"]["parts"][0]["diagram"]


# ------------------------------------------------------------------ ratio


def check_ratio(obj: dict) -> None:
    text = _text(obj)
    a, b = (int(x) for x in re.search(r"(\d+) : (\d+)", text).groups())  # type: ignore[union-attr]
    m = re.search(r"has (\d+) (more|fewer) ", text)
    assert m, text
    diff, word = int(m[1]), m[2]
    assert "altogether" in text
    found = [
        x + y
        for x in range(1, 2001)
        for y in [Fraction(x * b, a)]
        if y.denominator == 1 and (x - y if word == "more" else y - x) == diff
    ]
    assert len(found) == 1, (text, found)
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["value"] == found[0]


@st.composite
def ratio_params(draw) -> dict:
    a, b = draw(st.integers(1, 9)), draw(st.integers(1, 9))
    assume(a != b and gcd(a, b) == 1)
    return {
        "names": draw(_NAMES),
        "item": draw(st.sampled_from(["stickers", "marbles", "stamps"])),
        "ratio": [a, b],
        "difference": abs(a - b) * draw(st.integers(3, 40)),
    }


# ------------------------------------------------------------------ percentage


def check_percentage(obj: dict) -> None:
    text = _text(obj)
    total = int(re.search(r"\$(\d+)", text)[1])  # type: ignore[index]
    p1, p2 = (int(p) for p in re.findall(r"(\d+)%", text))
    assert "of the remaining money" in text
    kept_both = Fraction(100 - p1, 100) * Fraction(100 - p2, 100)
    spent_second = Fraction(100 - p1, 100) * Fraction(p2, 100)
    cents = total * 100 * (kept_both if "was left" in text else spent_second)
    assert cents.denominator == 1 and cents % 100 == 0  # whole dollars
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity" and answer["unit"] == "$"
    assert answer["value"] * 100 == cents


@st.composite
def percentage_params(draw) -> dict:
    p1 = draw(st.sampled_from(range(10, 65, 5)))
    p2 = draw(st.sampled_from(range(10, 65, 5)))
    total = 20 * draw(st.integers(5, 60))
    assume(p1 != p2 and total * (100 - p1) % 100 == 0)
    assume(total * (100 - p1) // 100 * p2 % 100 == 0)
    return {
        "name": draw(st.sampled_from(["Siti", "Ravi", "Hui Ling"])),
        "context": draw(st.sampled_from(["bag_shoes", "lamp_rug", "racket_cap"])),
        "ask": draw(st.sampled_from(["left", "second"])),
        "total": total,
        "p1": p1,
        "p2": p2,
    }


# ------------------------------------------------------------------ speed


def _minutes(text: str) -> int | None:
    m = re.search(r"(\d+) h (\d+) min", text)
    if m:
        return int(m[1]) * 60 + int(m[2])
    m = re.search(r"(\d+) minutes", text)
    return int(m[1]) if m else None


def check_speed(obj: dict) -> None:
    text = _text(obj)
    answer = single_part_answer(obj)
    assert answer["type"] == "quantity"
    speed = re.search(r"(\d+) km/h", text)
    dist = re.search(r"(\d+) km(?!/)", text)
    minutes = _minutes(text)
    if "How far" in text:
        s, m = int(speed[1]), minutes  # type: ignore[index]
        assert answer["unit"] == "km" and m is not None
        d = answer["value"]
    elif "average speed in km/h" in text:
        d, m = int(dist[1]), minutes  # type: ignore[index]
        assert answer["unit"] == "km/h" and m is not None
        s = answer["value"]
    else:
        assert "How many minutes" in text and minutes is None
        s, d = int(speed[1]), int(dist[1])  # type: ignore[index]
        assert answer["unit"] == "min"
        m = answer["value"]
    assert d * 60 == s * m  # km per hour, cross-multiplied in minutes
    assert m % 60 != 0  # the conversion is the point of the question


@st.composite
def speed_params(draw) -> dict:
    vehicle = draw(st.sampled_from(["bus", "car", "lorry", "train", "van"]))
    lo, hi = {
        "bus": (30, 60),
        "lorry": (36, 66),
        "van": (42, 78),
        "car": (48, 90),
        "train": (60, 120),
    }[vehicle]
    m = draw(st.sampled_from([15, 20, 24, 30, 36, 40, 45, 48, 50, 75, 80, 90, 100, 105]))
    s = draw(st.integers(lo, hi))
    assume(s * m % 60 == 0)
    return {
        "vehicle": vehicle,
        "kind": draw(st.sampled_from(["distance", "speed", "time"])),
        "speed": s,
        "minutes": m,
    }


# ------------------------------------------------------------------ angles


def check_angles(obj: dict) -> None:
    text = _text(obj)
    fig = _figure(obj)
    assert fig["type"] == "geometry_figure"
    assert "AB and CD are straight lines that meet at O" in text
    given_marks = {
        frozenset((m["from"], m["to"])): m["value_deg"] for m in fig["angles"] if not m["unknown"]
    }
    (unknown,) = [m for m in fig["angles"] if m["unknown"]]
    # the text prints the same two given angles as the figure (never its coordinates)
    printed = {
        frozenset((f, t)): int(v) for f, t, v in re.findall(r"∠([A-E])O([A-E]) = (\d+)°", text)
    }
    assert printed == given_marks
    ask = re.search(r"Find ∠([A-E])O([A-E])\.", text)
    assert ask and frozenset(ask.groups()) == frozenset((unknown["from"], unknown["to"]))

    def angle(bearings: dict[str, int], p: str, q: str) -> int:
        d = abs(bearings[p] - bearings[q]) % 360
        return min(d, 360 - d)

    solutions = set()
    for c in range(1, 180):  # C above the line AB, D opposite it
        for e in range(181, 360):  # E below the line, between A and D
            bearings = {"B": 0, "A": 180, "C": c, "D": c + 180, "E": e}
            if not bearings["A"] < e < bearings["D"]:
                continue
            if all(angle(bearings, *sorted(k)) == v for k, v in given_marks.items()):
                solutions.add(angle(bearings, unknown["from"], unknown["to"]))
    assert len(solutions) == 1, (text, solutions)
    # the figure is drawn to the printed values: every marked angle, measured off the points
    pts = {p["id"]: (p["x"], -p["y"]) for p in fig["points"]}  # figure y grows downwards

    def measured(a: str, b: str) -> float:
        (ox, oy), (ax, ay), (bx, by) = pts["O"], pts[a], pts[b]
        d = math.degrees(math.atan2(ay - oy, ax - ox) - math.atan2(by - oy, bx - ox)) % 360
        return min(d, 360 - d)

    for m in fig["angles"]:
        assert abs(measured(m["from"], m["to"]) - m["value_deg"]) < 0.5, (text, m)
    answer = single_part_answer(obj)
    assert answer == {"type": "integer", "value": solutions.pop(), "unit": "degrees"}


@st.composite
def angle_params(draw) -> dict:
    template = draw(st.sampled_from(["opposite_part", "opposite_sum", "line_part"]))
    if template == "opposite_part":
        r = draw(st.integers(80, 140))
        givens = {"r": r, "q": draw(st.integers(20, r - 25))}
    elif template == "opposite_sum":
        p = draw(st.integers(25, 100))
        givens = {"p": p, "q": draw(st.integers(25, 140 - p))}
    else:
        p = draw(st.integers(40, 100))
        givens = {"p": p, "q": draw(st.integers(20, 155 - p))}
    params = {"template": template, "givens": givens}
    params["angles"] = _angles._build(params)["given_map"]  # the contract map, from the builder
    return params


# ------------------------------------------------------------------ area


def check_area(obj: dict) -> None:
    text = _text(obj)
    fig = _figure(obj)
    assert fig["type"] == "geometry_figure"
    answer = single_part_answer(obj)
    assert answer["type"] == "integer"
    if text.startswith("ABCD is a square"):
        per = int(re.search(r"perimeter is (\d+) cm", text)[1])  # type: ignore[index]
        assert sum(seg.get("ticks", 0) for seg in fig["segments"]) == 4  # four equal sides
        sides = [s for s in range(1, per) if 4 * s == per]
        assert len(sides) == 1
        assert answer["unit"] == "cm^2" and answer["value"] == sides[0] ** 2
        return
    (label,) = [seg["label"] for seg in fig["segments"] if seg.get("label")]
    ab = int(re.search(r"AB = (\d+) cm", text)[1])  # type: ignore[index]
    assert label == f"{ab} cm"  # the printed figure labels the same side
    assert any(a.get("right") for a in fig["angles"])
    per = re.search(r"perimeter is (\d+) cm", text)
    area = re.search(r"area is (\d+) cm²", text)
    if per:
        widths = [w for w in range(1, 200) if 2 * (ab + w) == int(per[1])]
        assert len(widths) == 1 and widths[0] < ab
        assert answer["unit"] == "cm^2" and answer["value"] == ab * widths[0]
    else:
        widths = [w for w in range(1, 200) if ab * w == int(area[1])]  # type: ignore[index]
        assert len(widths) == 1 and widths[0] < ab
        assert answer["unit"] == "cm" and answer["value"] == 2 * (ab + widths[0])


@st.composite
def area_params(draw) -> dict:
    template = draw(st.sampled_from(["area_from_perimeter", "perimeter_from_area", "square_area"]))
    if template == "square_area":
        givens = {"side": draw(st.integers(2, 30))}
    else:
        length = draw(st.integers(4, 30))
        givens = {"length": length, "width": draw(st.integers(1, length - 1))}
    params = {"template": template, "givens": givens}
    params["lengths"] = _area._build(params)["lengths"]  # the contract map, from the builder
    return params


# ------------------------------------------------------------------ Hypothesis


@given(params=ratio_params())
def test_ratio_total_is_the_one_pair_with_the_printed_difference(params):
    check_ratio(build_object("ratio_difference", params))


@given(params=percentage_params())
def test_percentage_answer_is_one_exact_product(params):
    check_percentage(build_object("percentage_remainder", params))


@given(params=speed_params())
def test_speed_answer_cross_multiplies_in_minutes(params):
    check_speed(build_object("speed_minutes", params))


@given(params=angle_params())
def test_angle_answer_is_measured_from_the_one_matching_set_of_rays(params):
    check_angles(build_object("geometry_angle_opposite", params))


@given(params=area_params())
def test_area_answer_comes_from_the_one_matching_width(params):
    check_area(build_object("geometry_area_perimeter", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check", "variant"),
    [
        ("ratio_difference", check_ratio, "ratio"),
        ("percentage_remainder", check_percentage, "ask"),
        ("speed_minutes", check_speed, "kind"),
        ("geometry_angle_opposite", check_angles, "template"),
        ("geometry_area_perimeter", check_area, "template"),
    ],
)
def test_seed_sweep_through_the_real_sampler(code, check, variant):
    seen = set()
    for seed in SWEEP:
        obj = generate(code, seed)
        check(obj)
        seen.add(str(obj["parameters"][variant]))
    assert len(seen) >= 2  # the sweep reaches every variant of the rung
