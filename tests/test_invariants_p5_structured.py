"""Independent correctness authority for the P5 multi-part blueprints (EXA-117).

Each check reads the numbers back out of the *printed* stem and part texts (never the solver's
params or intermediates) and re-derives every part's answer a different way from ``solve()``:
the tank by pouring the tap's litres in minute by minute and stacking 1 cm layers of water,
the savings by adding each week's money in turn, and the path by counting the 1 m squares
round the garden and walking its outer edge metre by metre. Params come from the parameter
space via Hypothesis (built independently of the solvers' samplers), and a seed sweep covers
the samplers too.
"""

from __future__ import annotations

import re

import pytest
from exam_engine import generate
from hypothesis import assume, given
from hypothesis import strategies as st
from strategies import build_object

_NAME = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6)
SEEDS = range(1, 81)


def _contract(obj: dict, marks: list[int]) -> list[dict]:
    """Lettered (a), (b) with these marks; each scheme sums to its part's marks; working shown."""
    parts = obj["question"]["parts"]
    assert [p["label"] for p in parts] == list("ab")
    assert [p["marks"] for p in parts] == marks
    for p in parts:
        assert sum(m["mark"] for m in p["marking_scheme"]) == p["marks"]
        assert p["solution_steps"], "every part shows its working"
    assert obj["question"]["total_marks"] == sum(marks)
    return parts


def _cents(text: str) -> list[int]:
    """Every printed amount of money, in cents ($26 and $26.00 alike)."""
    return [int(d) * 100 + int(c or 0) for d, c in re.findall(r"\$(\d+)(?:\.(\d\d))?", text)]


# --------------------------------------------------------------------------- tap and tank


def _check_tank(obj: dict) -> None:
    a, b = _contract(obj, [2, 2])
    stem = obj["question"]["stem"]
    l, w, h = (int(x) for x in re.search(r"(\d+) cm by (\d+) cm by (\d+) cm", stem).groups())  # noqa: E741
    rate = int(re.search(r"at (\d+) ℓ per minute", stem).group(1))
    minutes = int(re.search(r"for (\d+) minutes", b["text"]).group(1))
    assert "empty" in stem.lower()
    # the drawn tank is the tank in the stem
    assert a["diagram"]["dims"] == {"length": l, "width": w, "height": h}

    # (a): pour the tap's litres (1 ℓ = 1000 cm³) in, a minute at a time, until it is full.
    water, t = 0, 0
    while water < l * w * h:
        water += rate * 1000
        t += 1
    assert water == l * w * h, "the tank fills on a whole minute"
    assert a["answer"] == {"type": "integer", "value": t, "unit": "min"}

    # (b): stack 1 cm layers of water over the base until the poured water is used up.
    poured, level = minutes * rate * 1000, 0
    while poured > 0:
        poured -= l * w
        level += 1
    assert poured == 0, "the water stands at a whole number of cm"
    assert b["answer"] == {"type": "integer", "value": level, "unit": "cm"}
    assert 0 < minutes < t and 0 < level < h  # the tap stops before the tank is full


@st.composite
def tank_params(draw) -> dict:
    l, w = draw(st.sampled_from([20, 25, 40, 50, 80])), draw(st.sampled_from([20, 25, 40, 50]))  # noqa: E741
    h = 5 * draw(st.integers(4, 12))
    assume((l * w * h) % 1000 == 0)
    litres = l * w * h // 1000
    rates = [r for r in range(2, 13) if litres % r == 0 and 4 <= litres // r <= 40]
    assume(rates)
    rate = draw(st.sampled_from(rates))
    stops = [
        m
        for m in range(1, litres // rate)
        if (m * rate * 1000) % (l * w) == 0 and m * rate * 1000 // (l * w) >= 5
    ]
    assume(stops)
    return {
        "length": l,
        "width": w,
        "height": h,
        "rate": rate,
        "minutes": draw(st.sampled_from(stops)),
    }


@given(params=tank_params())
def test_tank_by_pouring_minute_by_minute_and_stacking_layers(params):
    _check_tank(build_object("tap_tank_structured", params))


@pytest.mark.parametrize("seed", SEEDS)
def test_tank_sampler(seed):
    _check_tank(generate("tap_tank_structured", seed))


# --------------------------------------------------------------------------- savings


def _check_savings(obj: dict) -> None:
    a, b = _contract(obj, [2, 2])
    stem = obj["question"]["stem"]
    first, second = re.match(r"(.+?) has \$.*?\. (.+?) has \$", stem).groups()
    start_a, save_a, start_b, save_b = _cents(stem)
    weeks = int(re.search(r"after (\d+) weeks", a["text"]).group(1))
    assert a["text"].startswith(f"How much money will {first} have")
    assert first in b["text"] and second in b["text"] and first != second

    # (a): add each week's savings in turn.
    money = start_a
    for _ in range(weeks):
        money += save_a
    ans = a["answer"]
    assert ans["type"] == "decimal" and ans["unit"] == "$" and ans["dp"] == 2
    assert round(ans["value"] * 100) == money

    # (b): week by week until the two amounts are equal (the one behind saves more).
    x, y, week = start_a, start_b, 0
    while x > y:
        x, y, week = x + save_a, y + save_b, week + 1
    assert x == y, "they draw level on a whole week"
    assert b["answer"] == {"type": "integer", "value": week}
    assert week > 1 and week != weeks


@st.composite
def savings_params(draw) -> dict:
    slow = 10 * draw(st.integers(10, 60))
    gap = 10 * draw(st.integers(4, 30))
    meet = draw(st.integers(4, 16))
    behind = 50 * draw(st.integers(4, 60))
    weeks = draw(st.integers(3, 10))
    assume(weeks != meet)
    names = draw(st.lists(_NAME, min_size=2, max_size=2, unique=True))
    return {
        "names": names,
        "save": [slow, slow + gap],
        "start": [behind + gap * meet, behind],
        "weeks": weeks,
    }


@given(params=savings_params())
def test_savings_by_adding_each_week_in_turn(params):
    _check_savings(build_object("savings_structured", params))


@pytest.mark.parametrize("seed", SEEDS)
def test_savings_sampler(seed):
    _check_savings(generate("savings_structured", seed))


# --------------------------------------------------------------------------- garden path


def _check_path(obj: dict) -> None:
    a, b = _contract(obj, [2, 2])
    stem = obj["question"]["stem"]
    length, width = (int(x) for x in re.search(r"(\d+) m by (\d+) m", stem).groups())
    path = int(re.search(r"path (\d+) m wide", stem).group(1))
    price = _cents(b["text"])[0] // 100

    # (a): count the 1 m squares of the path: inside the outer edge, outside the garden.
    squares = sum(
        1
        for x in range(-path, length + path)
        for y in range(-path, width + path)
        if not (0 <= x < length and 0 <= y < width)
    )
    assert a["answer"] == {"type": "integer", "value": squares, "unit": "m^2"}

    # (b): walk the outer edge metre by metre, paying for each metre of fence.
    x, y, metres = -path, -path, 0
    long, short = length + 2 * path, width + 2 * path
    for dx, dy, n in ((1, 0, long), (0, 1, short), (-1, 0, long), (0, -1, short)):
        for _ in range(n):
            x, y, metres = x + dx, y + dy, metres + 1
    assert (x, y) == (-path, -path), "the walk closes"
    assert b["answer"] == {"type": "quantity", "value": metres * price, "unit": "$"}


@st.composite
def path_params(draw) -> dict:
    length = draw(st.integers(8, 30))
    width = draw(st.integers(5, min(length - 2, 28)))  # as the solver and schema
    path = draw(st.integers(1, 3))
    price = draw(st.integers(4, 15))
    assume(2 * path < width and 2 * (length + width + 4 * path) * price <= 2000)
    return {"length": length, "width": width, "path": path, "price": price}


@given(params=path_params())
def test_path_by_counting_squares_and_walking_the_fence(params):
    _check_path(build_object("garden_path_structured", params))


@pytest.mark.parametrize("seed", SEEDS)
def test_path_sampler(seed):
    _check_path(generate("garden_path_structured", seed))
