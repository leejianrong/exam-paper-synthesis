"""Independent correctness authority for the tank line-graph blueprints (EXA-158).

Every check reads the graph back out of the *drawn SVG*, never the spec or the solver's params:
each tick label is paired with the gridline it sits beside, which gives the pixel scale of both
axes; the plotted polyline is then read back in minutes and litres. The answer is re-derived
from those readings and the numbers the question prints:

* tank_graph            — "from a min to b min": the litres read at b minus those read at a,
                          divided by (b − a) when the question asks for a rate.
* tank_graph_structured — (a) the same rate; (b) the litres still needed to reach the printed
                          capacity, at the rate in (a), added to the time the graph ends.

Each corner the question needs must sit on a grid intersection, so the pupil can read it exactly.
Two input sources: Hypothesis draws params from each blueprint's parameter space and builds the
object via :func:`strategies.build_object`; a seed sweep runs the real pipeline.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from math import gcd

import pytest
from exam_engine import canonical, generate
from exam_engine.diagram import render_svg
from hypothesis import assume, given
from hypothesis import strategies as st
from strategies import build_object

SWEEP = range(1, 201)
_NS = "{http://www.w3.org/2000/svg}"


def _scale(pairs: list[tuple[float, float]]) -> tuple[Fraction, Fraction]:
    """(pixels per unit, pixel of zero) from (value, pixel) pairs, all of them on one line."""
    (v0, p0), (v1, p1) = min(pairs), max(pairs)
    per = (Fraction(p1) - Fraction(p0)) / (Fraction(v1) - Fraction(v0))
    for v, p in pairs:
        assert abs(Fraction(p0) + (Fraction(v) - Fraction(v0)) * per - Fraction(p)) < Fraction(
            1, 100
        ), "tick labels are not evenly spaced"
    return per, Fraction(p0) - Fraction(v0) * per


def read_graph(svg: str) -> list[tuple[Fraction, Fraction]]:
    """The plotted line's corners as (minutes, litres), read off the drawing."""
    root = ET.fromstring(svg)
    lines = [
        {k: float(e.get(k)) for k in ("x1", "y1", "x2", "y2")} for e in root.iter(f"{_NS}line")
    ]
    horizontal = [ln["y1"] for ln in lines if ln["y1"] == ln["y2"]]
    vertical = [ln["x1"] for ln in lines if ln["x1"] == ln["x2"]]
    ys, xs = [], []
    for t in root.iter(f"{_NS}text"):
        if not re.fullmatch(r"\d+", (t.text or "").strip()):
            continue
        v, x, y = int(t.text), float(t.get("x")), float(t.get("y"))
        if t.get("text-anchor") == "end":  # a volume label, left of its gridline
            near = min(horizontal, key=lambda g: abs(g - y))
            assert abs(near - y) < 8
            ys.append((v, near))
        else:  # a time label, under its gridline
            near = min(vertical, key=lambda g: abs(g - x))
            assert abs(near - x) < 1
            xs.append((v, x))
    xper, x0 = _scale(xs)
    yper, y0 = _scale(ys)
    (poly,) = list(root.iter(f"{_NS}polyline"))
    corners = []
    for pt in poly.get("points").split():
        px, py = (Fraction(c) for c in pt.split(","))
        # to the nearest 1/100: the drawing's coordinates are printed to 3 decimals
        corners.append(
            (
                Fraction(round((px - x0) / xper * 100), 100),
                Fraction(round((py - y0) / yper * 100), 100),
            )
        )
    return corners


def _on_grid(v: Fraction, step: int) -> bool:
    return abs(v - round(v / step) * step) < Fraction(1, 50)


def litres_at(corners: list[tuple[Fraction, Fraction]], t: int) -> Fraction:
    """The volume the graph shows at ``t`` min: a corner, read exactly."""
    hits = [v for m, v in corners if abs(m - t) < Fraction(1, 50)]
    assert len(hits) == 1, f"{t} min is not a corner of the graph"
    return Fraction(round(hits[0]))


def _volume_step(svg: str) -> int:
    labels = sorted(int(m) for m in re.findall(r'text-anchor="end"[^>]*>(\d+)<', svg))
    return labels[1] - labels[0]


def check_tank(obj: dict) -> None:
    canonical.load(obj)
    part = obj["question"]["parts"][0]
    svg = render_svg(part["diagram"])
    corners = read_graph(svg)
    step = _volume_step(svg)
    assert corners[0][0] == 0
    assert all(_on_grid(m, 1) and _on_grid(v, step) for m, v in corners)
    assert all(
        b[1] >= a[1] for a, b in zip(corners, corners[1:], strict=False)
    )  # water only flows in
    ta, tb = (int(x) for x in re.search(r"from (\d+) min to (\d+) min", part["text"]).groups())
    rise = litres_at(corners, tb) - litres_at(corners, ta)
    answer = part["answer"]
    if "At what rate" in part["text"]:
        assert answer["unit"] == "l/min"
        assert answer["value"] == rise / (tb - ta)
    else:
        assert answer["unit"] == "l"
        assert answer["value"] == rise > 0


def check_tank_structured(obj: dict) -> None:
    canonical.load(obj)
    q = obj["question"]
    a, b = q["parts"]
    svg = render_svg(a["diagram"])
    corners = read_graph(svg)
    step = _volume_step(svg)
    assert "empty" in q["stem"] and corners[0] == (0, 0)
    assert all(_on_grid(m, 1) and _on_grid(v, step) for m, v in corners)
    ta, tb = (int(x) for x in re.search(r"from (\d+) min to (\d+) min", a["text"]).groups())
    rate = (litres_at(corners, tb) - litres_at(corners, ta)) / (tb - ta)
    assert a["answer"]["unit"] == "l/min" and a["answer"]["value"] == rate > 0
    # (b): the graph ends at its last corner; water keeps flowing at the rate in (a)
    end_t, end_v = corners[-1][0], litres_at(corners, int(corners[-1][0]))
    assert tb == end_t  # (a) asks about the stretch that (b) continues
    capacity = int(re.search(r"can hold (\d+) ℓ", b["text"]).group(1))
    assert capacity > end_v
    assert b["answer"]["unit"] == "min"
    assert b["answer"]["value"] == end_t + (capacity - end_v) / rate


# ------------------------------------------------------------------ Hypothesis


@st.composite
def graphs(draw, *, empty: bool) -> dict:
    step = draw(st.sampled_from([5, 10, 20]))
    durations = [draw(st.integers(1, 4)) for _ in range(3)]
    assume(6 <= sum(durations) <= 12)
    rates = []
    for d in durations:  # whole litres a minute, the stretch rising a whole number of steps
        unit = step // gcd(step, d)
        rates.append(unit * draw(st.integers(0, 4 * step // (unit * d))))
    rises = [r * d for r, d in zip(rates, durations, strict=True)]
    assume(all(a != b for a, b in zip(rates, rates[1:], strict=False)))
    v0 = 0 if empty else step * draw(st.integers(0, 2))
    times, volumes = [0], [v0]
    for d, r in zip(durations, rises, strict=True):
        times.append(times[-1] + d)
        volumes.append(volumes[-1] + r)
    assume(volumes[-1] // step <= 10)
    return {
        "vessel": draw(st.sampled_from(["tank", "container", "barrel"])),
        "step": step,
        "times": times,
        "volumes": volumes,
    }


@st.composite
def tank_params(draw) -> dict:
    g = draw(graphs(empty=False))
    a, b = sorted(draw(st.lists(st.integers(0, 3), min_size=2, max_size=2, unique=True)))
    ask = draw(st.sampled_from(["between", "rate"]))
    if ask == "rate":
        b = a + 1
    return {**g, "ask": ask, "a": a, "b": b}


@given(params=tank_params())
def test_tank_graph_from_the_drawn_line(params):
    check_tank(build_object("tank_graph", params))


@st.composite
def tank_structured_params(draw) -> dict:
    g = draw(graphs(empty=True))
    last = (g["volumes"][3] - g["volumes"][2]) // (g["times"][3] - g["times"][2])
    assume(last > 0)
    return {**g, "capacity": g["volumes"][3] + last * draw(st.integers(1, 10))}


@given(params=tank_structured_params())
def test_tank_graph_structured_from_the_drawn_line(params):
    check_tank_structured(build_object("tank_graph_structured", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check"),
    [("tank_graph", check_tank), ("tank_graph_structured", check_tank_structured)],
)
def test_seed_sweep(code, check):
    for seed in SWEEP:
        check(generate(code, seed))


def test_the_reader_reads_a_hand_made_graph():
    """The SVG reader itself, on a graph whose corners are known."""
    spec = {
        "type": "chart",
        "kind": "line",
        "x_axis": {"title": "Time (min)", "min": 0, "max": 8, "step": 1},
        "y_axis": {"title": "Volume of water (ℓ)", "min": 0, "max": 60, "step": 10},
        "series": [{"name": "Volume", "points": [[0, 10], [3, 40], [5, 40], [8, 50]]}],
    }
    assert read_graph(render_svg(spec)) == [(0, 10), (3, 40), (5, 40), (8, 50)]
