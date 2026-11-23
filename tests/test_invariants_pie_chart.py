"""Independent correctness authority for the pie-chart blueprints (EXA-158).

Every check reads the pie back out of the *drawn SVG*, never the spec or the solver's params:
each sector's angle comes from its arc's end points, and its printed value from the label
drawn after it (a name, then a stacked fraction or "name n%"). The printed values must agree
with the angles (a sector printed 3/8 really is 3/8 of the circle), and the answer is
re-derived from the printed values and the numbers in the question:

* pie_fraction        — the unlabelled sector is 1 minus the printed fractions (and its angle).
* pie_percent_more    — (the first named sector's % − the second's) of the printed total.
* pie_fraction_amount — the given amount ÷ its sector's printed fraction is the whole; the
                        unlabelled sector's share of it is the answer.

Two input sources: Hypothesis draws params from each blueprint's parameter space and builds the
object via :func:`strategies.build_object`; a seed sweep runs the real pipeline.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest
from exam_engine import canonical, generate
from exam_engine.chart import leaked_hidden_values
from exam_engine.diagram import render_svg
from hypothesis import given
from hypothesis import strategies as st
from strategies import build_object

SWEEP = range(1, 201)
_NS = "{http://www.w3.org/2000/svg}"
_ARC = re.compile(
    r"M ([\d.]+) ([\d.]+) L ([\d.]+) ([\d.]+) A [\d.]+ [\d.]+ 0 ([01]) 1 ([\d.]+) ([\d.]+) Z"
)


def read_pie(svg: str) -> list[dict]:
    """Each sector in drawing order: its share of the circle (from the arc), its name and the
    value printed beside it (a Fraction, a percentage as an int, or None when unlabelled)."""
    sectors: list[dict] = []
    for el in ET.fromstring(svg):
        if el.tag == f"{_NS}path":
            cx, cy, x0, y0, large, x1, y1 = (float(v) for v in _ARC.fullmatch(el.get("d")).groups())
            a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
            sweep = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            assert (sweep > math.pi) == (large == 1)
            sectors.append({"share": sweep / (2 * math.pi), "texts": []})
        elif el.tag == f"{_NS}text" and sectors:
            sectors[-1]["texts"].append(el.text.strip())
    for s in sectors:
        texts = s.pop("texts")
        if m := re.fullmatch(r"(.+) (\d+)%", texts[0]):
            assert len(texts) == 1
            s["name"], s["value"] = m.group(1), int(m.group(2))
        else:
            s["name"] = texts[0]
            assert len(texts) in (1, 3)
            s["value"] = Fraction(int(texts[1]), int(texts[2])) if len(texts) == 3 else None
    return sectors


def _close(share: float, f: Fraction) -> bool:
    return abs(share - float(f)) < 1e-4


def _fraction_pie(obj: dict) -> tuple[list[dict], dict]:
    canonical.load(obj)
    part = obj["question"]["parts"][0]
    spec = part["diagram"]
    svg = render_svg(spec)
    assert leaked_hidden_values(spec, svg) == []
    sectors = read_pie(svg)
    labelled = [s for s in sectors if s["value"] is not None]
    (blank,) = [s for s in sectors if s["value"] is None]
    for s in labelled:
        assert s["value"].denominator > 1 and math.gcd(*s["value"].as_integer_ratio()) == 1
        assert _close(s["share"], s["value"])  # printed fraction = drawn angle
    rest = 1 - sum(s["value"] for s in labelled)
    assert rest > 0 and _close(blank["share"], rest)
    return sectors, {"blank": blank, "rest": rest, "text": part["text"], "part": part}


def check_pie_fraction(obj: dict) -> None:
    _, r = _fraction_pie(obj)
    assert f"spend on {r['blank']['name'].lower()}?" in r["text"]
    a = r["part"]["answer"]
    assert Fraction(a["numerator"], a["denominator"]) == r["rest"]
    assert math.gcd(a["numerator"], a["denominator"]) == 1


def check_pie_fraction_amount(obj: dict) -> None:
    sectors, r = _fraction_pie(obj)
    m = re.search(r"spent (\$(\d+)|(\d+) min) on (\w+)\.", r["text"])
    given_amount = int(m.group(2) or m.group(3))
    (known,) = [s for s in sectors if s["name"].lower() == m.group(4)]
    assert known["value"] is not None and known is not r["blank"]
    whole = given_amount / known["value"]
    assert f"spend on {r['blank']['name'].lower()}?" in r["text"]
    a = r["part"]["answer"]
    assert a["unit"] == ("$" if m.group(2) else "min")
    assert a["value"] == r["rest"] * whole


def check_pie_percent_more(obj: dict) -> None:
    canonical.load(obj)
    part = obj["question"]["parts"][0]
    sectors = read_pie(render_svg(part["diagram"]))
    assert sum(s["value"] for s in sectors) == 100
    assert all(_close(s["share"], Fraction(s["value"], 100)) for s in sectors)
    m = re.search(
        r"spent \$(\d+)\. How much more did .+ spend on (\w+) than on (\w+)\?", part["text"]
    )
    total = int(m.group(1))
    pct = {s["name"].lower(): s["value"] for s in sectors}
    more, less = pct[m.group(2)], pct[m.group(3)]
    assert part["answer"]["unit"] == "$"
    assert part["answer"]["value"] == Fraction(more - less, 100) * total > 0


# ------------------------------------------------------------------ Hypothesis

_NAMES = st.sampled_from(["Aisha", "Ben", "Hui Ling", "Nurul Aini"])


@st.composite
def fraction_pies(draw) -> dict:
    den = draw(st.sampled_from([6, 8, 10, 12]))
    n = draw(st.integers(3, 4))
    cuts = sorted(
        draw(st.lists(st.integers(1, den - 1), min_size=n - 1, max_size=n - 1, unique=True))
    )
    parts = [b - a for a, b in zip([0, *cuts], [*cuts, den], strict=True)]
    return {
        "name": draw(_NAMES),
        "context": draw(st.sampled_from(["money", "time"])),
        "den": den,
        "parts": parts,
        "hidden": draw(st.integers(0, n - 1)),
    }


@given(params=fraction_pies())
def test_pie_fraction_from_the_drawn_pie(params):
    check_pie_fraction(build_object("pie_fraction", params))


@st.composite
def fraction_amount_params(draw) -> dict:
    p = draw(fraction_pies())
    known = draw(st.integers(0, len(p["parts"]) - 1))
    return {**p, "known": known, "unit": draw(st.integers(1, 50))}


@given(params=fraction_amount_params())
def test_pie_fraction_amount_from_the_drawn_pie(params):
    check_pie_fraction_amount(build_object("pie_fraction_amount", params))


@st.composite
def percent_params(draw) -> dict:
    n = draw(st.integers(4, 5))
    spare = 20 - 2 * n  # every sector at least 10%: 10% each, then the rest
    cuts = sorted(draw(st.lists(st.integers(0, spare), min_size=n - 1, max_size=n - 1)))
    percents = [5 * (2 + b - a) for a, b in zip([0, *cuts], [*cuts, spare], strict=True)]
    more, less = draw(st.permutations(range(n)).map(lambda p: (p[0], p[1])))
    return {
        "name": draw(_NAMES),
        "total": 20 * draw(st.integers(5, 30)),
        "percents": percents,
        "more": more,
        "less": less,
    }


@given(params=percent_params())
def test_pie_percent_more_from_the_drawn_pie(params):
    check_pie_percent_more(build_object("pie_percent_more", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check"),
    [
        ("pie_fraction", check_pie_fraction),
        ("pie_percent_more", check_pie_percent_more),
        ("pie_fraction_amount", check_pie_fraction_amount),
    ],
)
def test_seed_sweep(code, check):
    for seed in SWEEP:
        check(generate(code, seed))


def test_the_reader_reads_a_hand_made_pie():
    spec = {
        "type": "chart",
        "kind": "pie",
        "value_unit": "fraction",
        "sectors": [
            {"label": "Food", "value": 3},
            {"label": "Books", "value": 2, "show_value": False},
            {"label": "Toys", "value": 7},
        ],
    }
    got = read_pie(render_svg(spec))
    assert [(s["name"], s["value"]) for s in got] == [
        ("Food", Fraction(1, 4)),
        ("Books", None),
        ("Toys", Fraction(7, 12)),
    ]
    assert [round(s["share"] * 12, 4) for s in got] == [3, 2, 7]
