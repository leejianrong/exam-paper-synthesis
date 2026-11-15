"""Independent correctness authority for the P8c multi-part blueprints.

Each check reads the numbers back out of the *printed* stem and part texts (never the
solver's params or intermediates) and re-derives every part's answer a different way
from ``solve()``: the ratio parts by brute-force search over whole numbers, the speed
parts with exact fractions, the volume parts by multiplying back. Params come from the
blueprint's parameter space via Hypothesis (built independently of the solvers'
samplers), and the (b) answers are checked to build on the (a) answers.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import gcd

from hypothesis import assume, given
from hypothesis import strategies as st
from strategies import build_object

_NAME = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6)
_ITEMS = ["stickers", "marbles", "stamps", "beads", "cards", "pencils"]


def _lcm(x: int, y: int) -> int:
    return x * y // gcd(x, y)


def _marks_contract(obj: dict, labels: list[str], marks: list[int]) -> list[dict]:
    """Labelled (a), (b)… with these marks; each marking scheme sums to its part's marks."""
    parts = obj["question"]["parts"]
    assert [p["label"] for p in parts] == labels
    assert [p["marks"] for p in parts] == marks
    for p in parts:
        assert sum(m["mark"] for m in p["marking_scheme"]) == p["marks"]
        assert p["solution_steps"], "every part shows its working"
    assert obj["question"]["total_marks"] == sum(marks)
    return parts


# --------------------------------------------------------------------------- ratio


@st.composite
def ratio_params(draw) -> dict:
    p = draw(st.integers(2, 7))
    q = draw(st.integers(1, p - 1))
    r = draw(st.integers(1, 7))
    s = draw(st.integers(1, 7))
    assume(gcd(p, q) == 1 and gcd(r, s) == 1 and r != s)
    assume(p + q <= 10 and r + s <= 10)
    assume(Fraction(r, r + s) < Fraction(p, p + q))  # the first person gives some away
    total = _lcm(p + q, r + s) * draw(st.integers(1, 12))
    assume(20 <= total <= 600)
    names = draw(st.lists(_NAME, min_size=2, max_size=2, unique=True))
    return {
        "names": names,
        "item": draw(st.sampled_from(_ITEMS)),
        "ratio_before": [p, q],
        "more": (p - q) * total // (p + q),
        "ratio_after": [r, s],
    }


@given(params=ratio_params())
def test_ratio_parts_found_by_search_over_whole_numbers(params):
    obj = build_object("ratio_structured", params)
    a, b = _marks_contract(obj, ["a", "b"], [2, 3])
    stem = obj["question"]["stem"]
    p, q = map(int, re.search(r"was (\d+) : (\d+)\.", stem).groups())
    more = int(re.search(r"had (\d+) more", stem).group(1))
    r, s = map(int, re.search(r"became (\d+) : (\d+)\.", b["text"]).groups())

    # (a): the only whole-number pair with A - B = more and A : B = p : q.
    first, second = next((x + more, x) for x in range(1, 1000) if (x + more) * q == x * p)
    assert a["answer"]["value"] == first + second

    # (b): give k one at a time until the ratio is r : s; the total (a) is unchanged.
    k = next(k for k in range(1, first) if (first - k) * s == (second + k) * r)
    assert b["answer"]["value"] == k
    assert (first - k) + (second + k) == a["answer"]["value"]


# --------------------------------------------------------------------------- speed


# Every whole-number trip in the parameter space: out at v1 for t1 h, back at a different
# whole v2 in whole hours, with a whole average speed (enumerated, not sampled).
_TRIPS = [
    (v1, t1, v1 * t1 // t2)
    for t1 in range(2, 6)
    for t2 in range(1, 7)
    for v1 in range(30, 101)
    if t2 != t1
    and (v1 * t1) % t2 == 0
    and 30 <= v1 * t1 // t2 <= 100
    and (2 * v1 * t1) % (t1 + t2) == 0
]


@st.composite
def speed_params(draw) -> dict:
    v1, t1, v2 = draw(st.sampled_from(_TRIPS))
    return {
        "name": draw(_NAME),
        "speed_out": v1,
        "time_out": t1,
        "speed_back": v2,
    }


@given(params=speed_params())
def test_speed_parts_rederived_with_exact_fractions(params):
    obj = build_object("speed_structured", params)
    a, b = _marks_contract(obj, ["a", "b"], [1, 3])
    stem = obj["question"]["stem"]
    v_out, v_back = map(int, re.findall(r"average speed of (\d+) km/h", stem))
    t_out = int(re.search(r"took (\d+) hours", stem).group(1))
    assert a["answer"]["unit"] == "km" and b["answer"]["unit"] == "km/h"

    # (a): the distance is the one the outward speed covers in the outward time.
    distance = a["answer"]["value"]
    assert Fraction(distance, t_out) == v_out

    # (b): there and back over the total time — never the mean of the two speeds.
    whole_time = t_out + Fraction(distance, v_back)
    assert Fraction(b["answer"]["value"]) == Fraction(2 * distance) / whole_time
    assert b["answer"]["value"] != Fraction(v_out + v_back, 2)


# --------------------------------------------------------------------------- volume


_BASES_A = [(20, 25), (20, 40), (25, 40), (40, 50), (30, 50), (50, 20)]
_BASES_B = [(20, 15), (20, 20), (25, 20), (30, 20), (30, 25), (40, 20), (40, 30), (50, 30)]


@st.composite
def volume_params(draw) -> dict:
    length, width = draw(st.sampled_from(_BASES_A))
    length_b, width_b = draw(st.sampled_from(_BASES_B))
    depth = draw(st.integers(5, 55))
    volume = length * width * depth
    assume(volume % 1000 == 0 and volume % (length_b * width_b) == 0)
    level = volume // (length_b * width_b)
    height = draw(st.integers(max(depth + 1, 10), 60))
    assume(5 <= level < 60 and level != depth)
    height_b = draw(st.integers(max(level + 1, 10), 60))
    return {
        "length": length,
        "width": width,
        "height": height,
        "depth": depth,
        "length_b": length_b,
        "width_b": width_b,
        "height_b": height_b,
    }


@given(params=volume_params())
def test_volume_parts_multiply_back_to_the_printed_tanks(params):
    obj = build_object("volume_structured", params)
    a, b = _marks_contract(obj, ["a", "b"], [2, 3])
    stem = obj["question"]["stem"]
    tanks = [tuple(map(int, m)) for m in re.findall(r"(\d+) cm by (\d+) cm by (\d+) cm", stem)]
    (la, wa, ha), (lb, wb, hb) = tanks
    depth = int(re.search(r"depth of (\d+) cm", stem).group(1))
    assert depth < ha  # the water fits in tank A as described

    # (a): litres back to cm³ is exactly the water's box in tank A.
    assert a["answer"]["unit"] == "l"
    assert a["answer"]["value"] * 1000 == la * wa * depth

    # (b): the same water (from (a)) as a box on tank B's base, and it does not overflow.
    assert b["answer"]["unit"] == "cm"
    assert b["answer"]["value"] * lb * wb == a["answer"]["value"] * 1000
    assert 0 < b["answer"]["value"] < hb
