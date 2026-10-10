"""Independent correctness authority for the Statistics (Charts) and Volume ladders (T7).

Every check re-derives the answer from the *drawn figure* plus the numbers the stem
prints — never from the solver's params — so a figure that disagrees with its stem, or
an answer that disagrees with the figure, fails here. Params come straight from each
blueprint's parameter space (Hypothesis), not from the solver's sampler.
"""

from __future__ import annotations

import re
from math import gcd

from exam_engine import canonical
from exam_engine.blueprints.solvers import statistics_chart as sc
from exam_engine.blueprints.solvers import volume as vol
from exam_engine.chart import check_chart_consistency, leaked_hidden_values
from exam_engine.diagram import render_svg
from hypothesis import given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object


def _part(obj: dict) -> dict:
    return obj["question"]["parts"][0]


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


# --------------------------- Statistics (Charts) ---------------------------


@st.composite
def chart_easy_params(draw) -> dict:
    ctx = draw(st.sampled_from(sorted(sc.BAR_CONTEXTS)))
    step = draw(st.sampled_from([5, 10, 20, 50]))
    values = [step * draw(st.integers(1, 8)) for _ in range(5)]
    a, b = draw(st.permutations(range(5)).map(lambda p: (p[0], p[1])))
    if values[a] <= values[b]:
        a, b = b, a
    return {"context": ctx, "step": step, "values": values, "a": a, "b": b}


@given(params=chart_easy_params())
def test_chart_easy_answer_is_the_difference_of_the_two_bars_named_in_the_stem(params):
    obj = build_object("statistics_chart_easy", params)
    part = _part(obj)
    spec = part["diagram"]
    assert all(check_chart_consistency(spec).values())
    cats = spec["x_axis"]["categories"]
    bars = dict(zip(cats, spec["series"][0]["values"], strict=True))
    named = [c for c in cats if re.search(rf"\b{re.escape(c)}\b", part["text"])]
    assert len(named) == 2  # the question names exactly two categories
    first = min(named, key=lambda c: part["text"].index(c))  # "more ... on A than on B"
    second = next(c for c in named if c != first)
    assert single_part_answer(obj)["value"] == bars[first] - bars[second] > 0


@st.composite
def chart_medium_params(draw) -> dict:
    """Four sectors, each a multiple of 5 and at least 10%, summing to 100."""
    a = draw(st.integers(2, 12))
    b = draw(st.integers(2, 18 - a - 2))
    c = draw(st.integers(2, 20 - a - b - 2))
    parts = [a, b, c, 20 - a - b - c]
    return {
        "context": draw(st.sampled_from(sorted(sc.PIE_CONTEXTS))),
        "total": 20 * draw(st.integers(5, 20)),
        "percents": [5 * x for x in draw(st.permutations(parts))],
        "hidden": draw(st.integers(0, 3)),
    }


@given(params=chart_medium_params())
def test_chart_medium_hidden_sector_is_the_rest_of_100_percent_of_the_total(params):
    obj = build_object("statistics_chart_medium", params)
    part = _part(obj)
    spec = part["diagram"]
    assert all(check_chart_consistency(spec).values())
    hidden = [s for s in spec["sectors"] if not s["show_value"]]
    assert len(hidden) == 1
    missing = 100 - sum(s["value"] for s in spec["sectors"] if s["show_value"])
    assert missing == hidden[0]["value"] > 0
    total = _ints(part["text"])[0]  # the only number in the stem is the pupil total
    assert single_part_answer(obj)["value"] * 100 == missing * total
    assert hidden[0]["label"] in part["text"]  # the question asks about the hidden sector
    assert leaked_hidden_values(spec, render_svg(spec)) == []


@st.composite
def chart_hard_params(draw) -> dict:
    step = draw(st.sampled_from([10, 20, 50]))
    known = [step * draw(st.integers(2, 9)) for _ in range(4)]
    missing = step * draw(st.integers(2, 9))
    return {
        "context": draw(st.sampled_from(sorted(sc.LINE_CONTEXTS))),
        "step": step,
        "known": known,
        "mean": (sum(known) + missing) // 5,
    }


@given(params=chart_hard_params())
def test_chart_hard_five_month_mean_pins_down_the_unplotted_month(params):
    obj = build_object("statistics_chart_hard", params)
    part = _part(obj)
    spec = part["diagram"]
    assert all(check_chart_consistency(spec).values())
    values = spec["series"][0]["values"]
    assert len(values) == 5 and values[-1] is None  # May is not plotted
    mean = int(re.search(r"was (\d+)\.", part["text"]).group(1))
    ans = single_part_answer(obj)["value"]
    assert (sum(values[:4]) + ans) / 5 == mean  # mean of all five months, from the figure
    assert ans > 0


# ------------------------------- Volume -------------------------------------


@given(
    dims=st.tuples(*[st.integers(3, 20)] * 3),
    template=st.sampled_from(["box", "block"]),
)
def test_volume_easy_is_the_product_of_the_drawn_edges(dims, template):
    params = dict(zip(("length", "width", "height"), dims, strict=True), template=template)
    obj = build_object("volume_easy", params)
    part = _part(obj)
    d = part["diagram"]["dims"]
    assert _ints(part["text"]) == [d["length"], d["width"], d["height"]]
    answer = single_part_answer(obj)
    assert answer["unit"] == "cm^3"
    assert answer["value"] == d["length"] * d["width"] * d["height"]


@st.composite
def volume_medium_params(draw) -> dict:
    length, width = draw(st.sampled_from(vol._BASES))
    step = 1000 // gcd(1000, length * width)  # depth step that holds whole litres
    lo = -(-5 // step)  # smallest unit count with depth >= 5 cm
    depth_units = draw(st.integers(lo, 60 // step - lo))
    empty_units = draw(st.integers(lo, (60 - depth_units * step) // step))
    return {
        "length": length,
        "width": width,
        "depth": depth_units * step,
        "empty": empty_units * step,
    }


@given(params=volume_medium_params())
def test_volume_medium_litres_to_fill_come_from_the_drawn_tank(params):
    obj = build_object("volume_medium", params)
    part = _part(obj)
    spec = part["diagram"]
    d, fill = spec["dims"], spec["fill"]["height"]
    assert 0 < fill < d["height"]
    assert _ints(part["text"])[:4] == [d["length"], d["width"], d["height"], fill]
    cm3 = d["length"] * d["width"] * (d["height"] - fill)
    answer = single_part_answer(obj)
    assert answer["unit"] == "l"
    assert answer["value"] * 1000 == cm3  # exact: a whole number of litres


@given(
    length=st.integers(4, 10).map(lambda x: 5 * x),
    width=st.integers(3, 8).map(lambda x: 5 * x),
    before=st.integers(8, 30),
    rise=st.integers(2, 9),
    room=st.integers(1, 10),
)
def test_volume_hard_block_volume_is_base_area_times_the_water_rise(
    length, width, before, rise, room
):
    params = {"length": length, "width": width, "before": before, "rise": rise, "room": room}
    obj = build_object("volume_hard", params)
    part = _part(obj)
    a, b = (p["figure"] for p in part["diagram"]["panels"])
    assert a["dims"] == b["dims"]  # the same tank in both panels
    d = a["dims"]
    assert b["fill"]["height"] > a["fill"]["height"] and b["fill"]["height"] <= d["height"]
    assert str(b["fill"]["height"]) in part["text"] and str(a["fill"]["height"]) in part["text"]
    rise_drawn = b["fill"]["height"] - a["fill"]["height"]
    answer = single_part_answer(obj)
    assert answer["unit"] == "cm^3"
    assert answer["value"] == d["length"] * d["width"] * rise_drawn
    canonical.load(obj)  # the per-panel gate agrees too
