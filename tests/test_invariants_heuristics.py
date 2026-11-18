"""Independent correctness authority for the P8c batch 2 multi-part blueprints (EXA-143):
the named Paper 2 heuristics.

Each check reads the numbers back out of the *printed* stem and part texts (never the solver's
params or intermediates) and re-derives every part's answer a different way from ``solve()``:
supposition by trying every possible number of adult tickets, the fraction of a remainder by
searching for the money at first, the packs by counting up through whole numbers of packs,
the ages by stepping year by year, and equal number / equal amount by buying one of each at a
time. Params come from the parameter space via Hypothesis (built independently of the
solvers' samplers); later parts are checked to agree with earlier ones.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import gcd

from hypothesis import assume, given
from hypothesis import strategies as st
from strategies import build_object

_NAME = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6)


def _contract(obj: dict, marks: list[int]) -> list[dict]:
    """Lettered (a), (b)… with these marks; each scheme sums to its part's marks; working shown."""
    parts = obj["question"]["parts"]
    assert [p["label"] for p in parts] == list("abc"[: len(marks)])
    assert [p["marks"] for p in parts] == marks
    for p in parts:
        assert sum(m["mark"] for m in p["marking_scheme"]) == p["marks"]
        assert p["solution_steps"], "every part shows its working"
    assert obj["question"]["total_marks"] == sum(marks)
    return parts


def _dollars(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\$(\d+)", text)]


# --------------------------------------------------------------------------- supposition


@st.composite
def supposition_params(draw) -> dict:
    child = draw(st.integers(3, 10))
    adult = draw(st.integers(max(5, child + 1), 18))
    total = draw(st.integers(30, 120))
    n_adult = draw(st.integers(1, total - 1))
    amount = n_adult * adult + (total - n_adult) * child
    assume(amount <= 2000 and n_adult * adult > (total - n_adult) * child)
    return {
        "name": draw(_NAME),
        "total": total,
        "adult_price": adult,
        "child_price": child,
        "amount": amount,
    }


@given(params=supposition_params())
def test_supposition_found_by_trying_every_number_of_adult_tickets(params):
    obj = build_object("supposition_structured", params)
    a, b, c = _contract(obj, [1, 2, 2])
    stem = obj["question"]["stem"]
    total = int(re.search(r"sold (\d+) tickets", stem).group(1))
    adult_price, child_price, amount = _dollars(stem)
    assert {p["answer"].get("unit") for p in (a, c)} == {"$"}

    # (a): every ticket at the child price.
    assert a["answer"]["value"] == sum(child_price for _ in range(total))

    # (b): the one split of the tickets that collects exactly the printed amount.
    splits = [k for k in range(total + 1) if k * adult_price + (total - k) * child_price == amount]
    assert splits == [b["answer"]["value"]]
    assert 0 < splits[0] < total  # both kinds were sold

    # (c): money from each kind of ticket, from the split found in (b).
    adults = splits[0]
    assert c["answer"]["value"] == adults * adult_price - (total - adults) * child_price > 0


# --------------------------------------------------------------------------- fraction


_FRACTION = r"(\d+)/(\d+)"


@st.composite
def fraction_params(draw) -> dict:
    b = draw(st.integers(3, 8))
    a = draw(st.integers(1, b - 1))
    d = draw(st.integers(2, 6))
    c = draw(st.integers(1, d - 1))
    assume(gcd(a, b) == 1 and gcd(c, d) == 1)
    count = draw(st.integers(2, 8))
    on_items = count * draw(st.integers(2, 60))  # whole dollars each
    remainder = Fraction(on_items * d, c)
    money = remainder * b / (b - a)
    assume(remainder.denominator == 1 and money.denominator == 1 and 40 <= money <= 800)
    return {
        "name": draw(_NAME),
        "item": draw(st.sampled_from(["shirts", "books", "files", "caps", "towels", "mugs"])),
        "spent_first": [a, b],
        "spent_then": [c, d],
        "count": count,
        "left": int(remainder - on_items),
    }


@given(params=fraction_params())
def test_fraction_of_remainder_found_by_searching_for_the_money_at_first(params):
    obj = build_object("fraction_remainder_structured", params)
    a, b = _contract(obj, [1, 3])
    stem = obj["question"]["stem"]
    (n1, d1), (n2, d2) = (tuple(map(int, m)) for m in re.findall(_FRACTION, stem))
    count = int(re.search(r"on (\d+) identical", stem).group(1))
    left = _dollars(stem)[-1]

    # The money at first: the whole-dollar amount whose story ends with exactly $left.
    def story(money: int) -> tuple[Fraction, Fraction]:
        after_bag = money - Fraction(money * n1, d1)
        on_items = Fraction(after_bag * n2, d2)
        return on_items, after_bag - on_items

    money = next(m for m in range(1, 5000) if story(m)[1] == left)
    on_items, _ = story(money)

    # (a): what is left, as a fraction of the money at first, in its simplest form.
    ans = a["answer"]
    assert ans["type"] == "fraction" and gcd(ans["numerator"], ans["denominator"]) == 1
    assert Fraction(ans["numerator"], ans["denominator"]) == Fraction(left, money)

    # (b): the items share what was spent on them equally.
    assert b["answer"]["unit"] == "$"
    assert b["answer"]["value"] * count == on_items


# --------------------------------------------------------------------------- LCM packs


_GOODS = [
    ["paper cups", "paper plates"],
    ["pencils", "erasers"],
    ["red balloons", "blue balloons"],
    ["envelopes", "cards"],
    ["forks", "spoons"],
]


@st.composite
def packs_params(draw) -> dict:
    m = draw(st.integers(4, 12))
    n = draw(st.integers(4, 12))
    assume(m % n and n % m)
    lcm = m * n // gcd(m, n)
    assume(lcm <= 60)
    pm, pn = draw(st.integers(2, 12)), draw(st.integers(2, 12))
    set_cost = lcm // m * pm + lcm // n * pn
    budget = draw(st.integers(2 * set_cost + 1, 7 * set_cost - 1))
    assume(budget % set_cost and budget <= 600)
    return {
        "name": draw(_NAME),
        "goods": draw(st.sampled_from(_GOODS)),
        "pack": [m, n],
        "price": [pm, pn],
        "budget": budget,
    }


@given(params=packs_params())
def test_packs_counted_up_through_whole_packs(params):
    obj = build_object("lcm_packs_structured", params)
    a, b = _contract(obj, [1, 2])
    stem = obj["question"]["stem"]
    m, n = map(int, re.findall(r"packs of (\d+)", stem))
    pm, pn = _dollars(stem)
    budget = _dollars(b["text"])[0]

    # Every equal number reachable with whole packs of both kinds, smallest first.
    equal = [k for k in range(1, 2000) if k % m == 0 and k % n == 0]
    # (a): the smallest.
    assert a["answer"]["value"] == equal[0]
    # (b): the most of each the budget pays for, counted as both kinds together.
    affordable = [k for k in equal if (k // m) * pm + (k // n) * pn <= budget]
    assert b["answer"]["value"] == 2 * max(affordable)
    assert max(affordable) % a["answer"]["value"] == 0


# --------------------------------------------------------------------------- ages


@st.composite
def age_params(draw) -> dict:
    age = draw(st.integers(6, 14))
    r = draw(st.integers(1, 8))
    s = draw(st.integers(r + 1, 9))
    assume(gcd(r, s) == 1)
    # One ratio unit u: the gap is (s - r) units, the child is r units old at that time.
    units = [
        u
        for u in range(1, 61)
        if 30 <= age + (s - r) * u <= 60 and (s - r) * u >= 20 and 2 <= r * u - age <= 30
    ]
    assume(units)
    relative_age = age + (s - r) * draw(st.sampled_from(units))
    return {
        "name": draw(_NAME),
        "relative": draw(st.sampled_from(["father", "mother"])),
        "age": age,
        "relative_age": relative_age,
        "ratio_after": [r, s],
    }


@given(params=age_params())
def test_ages_stepped_year_by_year(params):
    obj = build_object("age_difference_structured", params)
    a, b = _contract(obj, [1, 2])
    stem = obj["question"]["stem"]
    age, relative_age = map(int, re.findall(r"is (\d+) years old", stem))
    r, s = map(int, re.search(r"be (\d+) : (\d+)\?", b["text"]).groups())

    # (a): count back to the year the child was born.
    years_back = next(y for y in range(100) if age - y == 0)
    assert a["answer"]["value"] == relative_age - years_back

    # (b): step forward a year at a time until the ratio holds; the gap from (a) never changes.
    years = next(y for y in range(1, 100) if (age + y) * s == (relative_age + y) * r)
    assert b["answer"]["value"] == years
    assert (relative_age + years) - (age + years) == a["answer"]["value"]


# --------------------------------------------------------------------------- equal number / amount


_SHOP = [
    ["pens", "notebooks"],
    ["pencils", "rulers"],
    ["apples", "mangoes"],
    ["buns", "sandwiches"],
    ["erasers", "files"],
]


@st.composite
def equal_params(draw) -> dict:
    pa = draw(st.integers(2, 9))
    pb = draw(st.integers(pa + 1, 12))
    pairs = draw(st.integers(1, 40))
    lcm = pa * pb // gcd(pa, pb)
    each_kind = lcm * draw(st.integers(1, max(1, 300 // lcm)))
    assume(each_kind // pa - each_kind // pb >= 2)
    more = pairs * (pb - pa)
    assume(more <= 300 and 2 * pairs <= 80)
    return {
        "names": draw(st.lists(_NAME, min_size=2, max_size=2, unique=True)),
        "goods": draw(st.sampled_from(_SHOP)),
        "price": [pa, pb],
        "more": more,
        "spent": 2 * each_kind,
    }


@given(params=equal_params())
def test_equal_number_and_equal_amount_bought_one_at_a_time(params):
    obj = build_object("equal_number_amount_structured", params)
    a, b = _contract(obj, [2, 2])
    pa, pb = _dollars(obj["question"]["stem"])
    more = _dollars(a["text"])[0]
    spent = _dollars(b["text"])[0]

    # (a): buy one of each until the dearer kind has cost exactly $more more.
    k = next(k for k in range(1, 1000) if k * pb - k * pa == more)
    assert a["answer"]["value"] == k + k

    # (b): buy each kind until each has taken exactly half the money.
    n_a = next(x for x in range(1, 1000) if x * pa * 2 == spent)
    n_b = next(x for x in range(1, 1000) if x * pb * 2 == spent)
    assert b["answer"]["value"] == n_a - n_b
