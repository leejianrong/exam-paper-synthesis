"""Independent correctness authority for the data-table blueprints (EXA-148).

Every check reads the numbers back out of the *printed* table (``question.table``) and the
printed question text, never the solver's params or intermediates, and re-derives the answer
a different way from ``solve()``:

* postage_table — each row's range is read from its own words ("Up to 20 g", "Above 20 g,
                  up to 40 g") and each letter is tested against every range: exactly one row
                  must hold it, and the two postages are added.
* rental_table  — the meter is run hour by hour: pay the first period, then keep paying one
                  more hour while the money left covers it.
* tariff_gst    — every unit used is charged on its own at the price of the band it falls
                  in, then the GST is added as (100 + p)% of that charge with exact fractions.

Two input sources: Hypothesis draws params straight from each blueprint's parameter space
(not the solvers' samplers) and builds the object via :func:`strategies.build_object`; a seed
sweep runs the real pipeline (``generate``).
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import generate
from hypothesis import assume, given
from hypothesis import strategies as st
from invariants import single_part_answer
from strategies import build_object

SWEEP = range(1, 201)
_NAME = st.sampled_from(["Aisha", "Ben", "Hui Ling", "Nurul Aini"])


def _cents(cell: str) -> int:
    m = re.fullmatch(r"\$(\d+)\.(\d\d)", cell)
    assert m, cell
    return int(m.group(1)) * 100 + int(m.group(2))


def _table(obj: dict) -> dict:
    table = obj["question"]["table"]
    assert table["headers"] and all(len(r) == len(table["headers"]) for r in table["rows"])
    return table


def _answer_cents(answer: dict) -> int:
    assert answer["type"] == "decimal" and answer["unit"] == "$" and answer["dp"] == 2
    cents = Fraction(str(answer["value"])) * 100
    assert cents.denominator == 1, answer
    return int(cents)


# ------------------------------------------------------------------ postage


def check_postage(obj: dict) -> None:
    table = _table(obj)
    assert table["headers"] == ["Mass of letter", "Postage"]
    ranges = []
    for label, price in table["rows"]:
        above = re.search(r"Above (\d+) g", label)
        upto = re.search(r"up to (\d+) g", label, flags=re.I)
        assert upto, label
        ranges.append((int(above.group(1)) if above else 0, int(upto.group(1)), _cents(price)))
    # the rows tile the masses with no gap or overlap
    assert ranges[0][0] == 0
    assert all(a[1] == b[0] for a, b in zip(ranges, ranges[1:], strict=False))
    text = obj["question"]["parts"][0]["text"]
    masses = [int(m) for m in re.findall(r"mass of (\d+) g", text)]
    assert len(masses) == 2
    total = 0
    rows_used = []
    for mass in masses:
        fits = [i for i, (lo, hi, _) in enumerate(ranges) if lo < mass <= hi]
        assert len(fits) == 1, (mass, ranges)
        rows_used.append(fits[0])
        total += ranges[fits[0]][2]
    assert rows_used[0] != rows_used[1]
    assert _answer_cents(single_part_answer(obj)) == total


@st.composite
def postage_params(draw) -> dict:
    limits = draw(st.sampled_from([[20, 40, 100, 250, 500], [25, 50, 100, 200, 500]]))
    prices = sorted(draw(st.lists(st.integers(1, 2000), min_size=5, max_size=5, unique=True)))
    masses = draw(st.lists(st.integers(1, 500), min_size=2, max_size=2))
    return {"name": draw(_NAME), "limits": limits, "prices": prices, "masses": masses}


@given(params=postage_params())
def test_postage_by_testing_every_row(params):
    check_postage(build_object("postage_table", params))


# ------------------------------------------------------------------ rental


def check_rental(obj: dict) -> None:
    table = _table(obj)
    first_label = table["headers"][1]
    m = re.fullmatch(r"First (?:hour|(\d+) hours)", first_label)
    assert m, first_label
    first_hours = int(m.group(1) or 1)
    assert table["headers"][2] == "Each additional hour"
    text = obj["question"]["parts"][0]["text"]
    budget = int(re.search(r"has \$(\d+)\.", text).group(1)) * 100
    item = re.search(r"can rent a (.+) for\?", text).group(1)
    rows = [r for r in table["rows"] if r[0].lower() == item]
    assert len(rows) == 1, (item, table["rows"])
    first, extra = _cents(rows[0][1]), _cents(rows[0][2])
    money, hours = budget - first, first_hours
    assert money >= 0
    while money >= extra:  # one more hour at a time
        money -= extra
        hours += 1
    answer = single_part_answer(obj)
    assert answer["type"] == "integer" and answer["unit"] == "h"
    assert answer["value"] == hours > first_hours


@st.composite
def rental_params(draw) -> dict:
    fh = draw(st.sampled_from([1, 2]))
    items = draw(
        st.lists(
            st.sampled_from(["Bicycle", "Rowing boat", "Kayak", "Canoe", "Scooter", "Pedal boat"]),
            min_size=3,
            max_size=3,
            unique=True,
        )
    )
    extra = draw(st.lists(st.integers(50, 1500), min_size=3, max_size=3))
    first = [e * fh + draw(st.integers(0, 2000)) for e in extra]
    assume(all(f <= 5000 for f in first))
    return {
        "name": draw(_NAME),
        "items": items,
        "first_hours": fh,
        "first": first,
        "extra": extra,
        "pick": draw(st.integers(0, 2)),
        "budget": 100 * draw(st.integers(1, 100)),
    }


@given(params=rental_params())
def test_rental_by_running_the_meter_hour_by_hour(params):
    check_rental(build_object("rental_table", params))


# ------------------------------------------------------------------ tariff


def check_tariff(obj: dict) -> None:
    table = _table(obj)
    bands = []  # (first unit, last unit or None, cents per unit)
    edge = 0
    for label, price in table["rows"]:
        n = int(re.search(r"(\d+)", label).group(1))
        if label.startswith(("First", "Next")):
            bands.append((edge + 1, edge + n, _cents(price)))
            edge += n
        else:
            assert label.startswith("Above") and n == edge, (label, edge)
            bands.append((edge + 1, None, _cents(price)))
    stem = obj["question"]["stem"]
    usage = int(re.search(r"used (\d+) (?:m³|units)", stem).group(1))
    charge = 0
    for unit in range(1, usage + 1):  # each unit at its own band's price
        (price,) = [p for lo, hi, p in bands if lo <= unit and (hi is None or unit <= hi)]
        charge += price
    a, b = obj["question"]["parts"]
    assert _answer_cents(a["answer"]) == charge
    gst = int(re.search(r"GST of (\d+)%", b["text"]).group(1))
    assert gst == 9
    assert _answer_cents(b["answer"]) == Fraction(charge) * Fraction(100 + gst, 100)
    assert usage > edge  # the top band is used, so every row matters


@st.composite
def tariff_params(draw) -> dict:
    template = draw(st.sampled_from(["electricity", "water"]))
    if template == "water":
        l1, nxt, p1 = (
            draw(st.sampled_from([20, 30, 40])),
            draw(st.sampled_from([10, 20])),
            (110, 160),
        )
        step, over = (10, 40), (1, 30)
    else:
        l1, nxt, p1 = (
            draw(st.sampled_from([100, 150, 200])),
            draw(st.sampled_from([100, 200])),
            (18, 28),
        )
        step, over = (1, 4), (1, 200)
    first = draw(st.integers(*p1))
    second = first + draw(st.integers(*step))
    n = draw(st.integers(*over))
    before_top = l1 * first + nxt * second
    # a top price that makes the charge whole dollars (the blueprint's exactness rule)
    tops = [p for p in range(second + 1, second + 101) if (before_top + n * p) % 100 == 0]
    assume(tops)
    return {
        "name": draw(_NAME),
        "template": template,
        "limits": [l1, l1 + nxt],
        "prices": [first, second, draw(st.sampled_from(tops))],
        "usage": l1 + nxt + n,
    }


@given(params=tariff_params())
def test_tariff_by_charging_unit_by_unit(params):
    check_tariff(build_object("tariff_gst", params))


# ------------------------------------------------------------------ seed sweep


@pytest.mark.parametrize(
    ("code", "check"),
    [
        ("postage_table", check_postage),
        ("rental_table", check_rental),
        ("tariff_gst", check_tariff),
    ],
)
def test_seed_sweep(code, check):
    for seed in SWEEP:
        check(generate(code, seed))
