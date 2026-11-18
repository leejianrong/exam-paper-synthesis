"""Solvers for the data-table blueprints (EXA-148): the question prints a table
(``question.table``, built by each solver's ``table()``) and the pupil reads it.

* ``postage_table``  (2 marks, medium) — a postage table by mass bands; two letters in
  different bands: the total postage.
* ``rental_table``   (3 marks, hard)   — rental charges for three items (a first-period
  price, then a price for each additional hour); with a budget, the greatest number of whole
  hours one item can be rented for.
* ``tariff_gst``     (4 marks, multi-part) — a water or electricity tariff in three bands:
  (a) the charge before GST; (b) the bill with 9% GST.

Money is integer cents throughout and every answer is exact (ADR-0014): the tariff's
charge before GST is a whole number of dollars, so 9% of it is a whole number of cents.
The table cells are display strings ("$1.21", "First 40 m³"); the person's ``name`` is
cosmetic (W1a) and appears only in the YAML templates.
"""

from __future__ import annotations

import random
import zlib
from fractions import Fraction

from ..registry import register
from .rate import NAME_POOL, money, money2

GST_PERCENT = 9


def _num2(cents: int) -> str:
    """A cents amount as a 2-dp number for an ``expr`` (``6.00``)."""
    return f"{cents // 100}.{cents % 100:02d}"


def _dollars(cents: int) -> float:
    return cents / 100


def _money_answer(cents: int) -> dict:
    return {"type": "decimal", "value": _dollars(cents), "dp": 2, "unit": "$"}


def _increasing(xs: list[int]) -> bool:
    return all(a < b for a, b in zip(xs, xs[1:], strict=False))


Slip = tuple[int | Fraction, str]


def _spread(slips: list[Slip], answer: Fraction, params: dict) -> list[Slip]:
    """``slips`` (best first) with the first two chosen both below, one either side of, or both
    above ``answer``, by a key from the numbers in ``params``.

    A multiple-choice copy prints its options in ascending order and takes the first wrong
    options from the hook in order (``mcq._last_pick`` moves only the last), so without this
    the answer would sit in the same place every time. Values a copy cannot use (not
    positive, the answer, more than 20 times off) or that repeat count for neither side.
    (Open PR #233, EXA-156, adds a shared ``spread_sides`` doing the same for every hook.)"""
    seen: set[Fraction] = set()
    below: list[Slip] = []
    above: list[Slip] = []
    for slip in slips:
        v = Fraction(slip[0])
        if v > 0 and v != answer and answer / 20 <= v <= answer * 20 and v not in seen:
            seen.add(v)
            (below if v < answer else above).append(slip)
    numbers = [params[k] for k in sorted(params) if k != "name"]
    key = zlib.crc32(repr(numbers).encode())
    first = [below[:2], below[:1] + above[:1], above[:2]][key % 3]
    if len(first) < 2:
        first = below[:1] + above[:1]
    return [*first, *(s for s in slips if s not in first)]


# --------------------------------------------------------------------------- postage

POSTAGE_LIMITS = ([20, 40, 100, 250, 500], [25, 50, 100, 200, 500])


def mass_band(limits: list[int], mass: int) -> int:
    """Index of the row ``mass`` falls in: up to ``limits[0]``, then above each limit up to
    the next (an upper limit is inclusive)."""
    return next(i for i, hi in enumerate(limits) if mass <= hi)


def postage_rows(limits: list[int], prices: list[int]) -> list[list[str]]:
    rows = [[f"Up to {limits[0]} g", money2(prices[0])]]
    for lo, hi, p in zip(limits, limits[1:], prices[1:], strict=False):
        rows.append([f"Above {lo} g, up to {hi} g", money2(p)])
    return rows


class PostageTableSolver:
    """``prices`` are cents per letter for each row of ``limits`` (grams)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        limits = list(rng.choice(POSTAGE_LIMITS))
        prices = [rng.randint(30, 60)]
        for _ in limits[1:]:
            prices.append(prices[-1] + 5 * rng.randint(2, 12))
        i, j = sorted(rng.sample(range(len(limits)), 2))
        masses = []
        for k in (i, j):
            lo = limits[k - 1] if k else 0
            # sometimes exactly on the upper limit, which is still in this row
            masses.append(limits[k] if rng.random() < 0.25 else rng.randint(lo + 1, limits[k]))
        if rng.random() < 0.5:
            masses.reverse()
        return {"name": rng.choice(NAME_POOL), "limits": limits, "prices": prices, "masses": masses}

    def table(self, params: dict, solution: dict) -> dict:
        return {
            "caption": "Postage for letters",
            "headers": ["Mass of letter", "Postage"],
            "rows": postage_rows(params["limits"], params["prices"]),
        }

    def solve(self, params: dict) -> dict:
        limits, prices = params["limits"], params["prices"]
        m1, m2 = params["masses"]
        p1, p2 = (prices[mass_band(limits, m)] for m in (m1, m2))
        total = p1 + p2
        return {
            "answer": _money_answer(total),
            "intermediates": {
                "m1": m1,
                "m2": m2,
                "p1": money2(p1),
                "p2": money2(p2),
                "e1": _num2(p1),
                "e2": _num2(p2),
                "total": money2(total),
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        """Table-reading slips, as money (cents → dollars): rows above give less, rows below
        more, so the options fall on both sides of the answer."""
        limits, prices = params["limits"], params["prices"]
        lo, hi = sorted(mass_band(limits, m) for m in params["masses"])
        total = prices[lo] + prices[hi]
        cents: list[tuple[int, str]] = [
            (prices[hi], "found the postage of one letter only"),
            (2 * prices[hi], "charged both letters at the heavier rate"),
            (2 * prices[lo], "charged both letters at the lighter rate"),
        ]
        if lo > 0:
            cents.append((prices[lo - 1] + prices[hi], "read the row above"))
        if hi - 1 > lo:
            cents.append((prices[lo] + prices[hi - 1], "read the row above"))
        if lo + 1 < hi:
            cents.append((prices[lo + 1] + prices[hi], "read the row below"))
        if hi + 1 < len(prices):
            cents.append((prices[lo] + prices[hi + 1], "read the row below"))
        combined = sum(params["masses"])
        if combined <= limits[-1]:
            cents.append((prices[mass_band(limits, combined)], "looked up the total mass"))
        slips: list[Slip] = [(Fraction(c, 100), why) for c, why in cents]
        return _spread(slips, Fraction(total, 100), params)

    def validate(self, params: dict, solution: dict) -> dict:
        limits, prices, masses = params["limits"], params["prices"], params["masses"]
        cents = round(solution["answer"]["value"] * 100)
        bands = [mass_band(limits, m) for m in masses] if max(masses) <= limits[-1] else []
        checks = {
            "standard_limits": limits in [list(t) for t in POSTAGE_LIMITS],
            "prices_rise_with_mass": len(prices) == len(limits) and _increasing(prices),
            "masses_in_table": len(masses) == 2 and min(masses) > 0 and bool(bands),
            "letters_in_different_rows": len(set(bands)) == 2,
            # the total equals the price of the row each letter's mass fits under
            "answer_verified": bool(bands)
            and cents
            == sum(
                next(p for hi, p in zip(limits, prices, strict=True) if m <= hi) for m in masses
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- rental

RENTAL_ITEMS = ["Bicycle", "Rowing boat", "Kayak", "Canoe", "Scooter", "Pedal boat"]
_MAX_HOURS = 12


def rental_hours(budget: int, first: int, extra: int, first_hours: int) -> int:
    """The most whole hours ``budget`` pays for (all cents)."""
    return first_hours + (budget - first) // extra


def _first_label(first_hours: int) -> str:
    return "First hour" if first_hours == 1 else f"First {first_hours} hours"


class RentalTableSolver:
    """``first``/``extra`` are cents per item (the first period, each additional hour);
    ``pick`` is the row asked about; ``budget`` is whole dollars, in cents."""

    mcq_whole = True  # rented for whole hours, so every option is too

    def sample(self, schema: dict, rng: random.Random) -> dict:
        first_hours = rng.choice([1, 2])
        while True:
            items = rng.sample(RENTAL_ITEMS, 3)
            extra = [50 * rng.randint(4, 16) for _ in items]
            first = [e * first_hours + 50 * rng.randint(1, 8) for e in extra]
            pick = rng.randrange(3)
            budget = 100 * rng.randint(15, 90)
            left = budget - first[pick]
            if left < 3 * extra[pick] or left % extra[pick] == 0:
                continue  # at least three extra hours, and some money left over
            if rental_hours(budget, first[pick], extra[pick], first_hours) > _MAX_HOURS:
                continue
            if len(set(extra)) < 3:
                continue
            return {
                "name": rng.choice(NAME_POOL),
                "items": items,
                "first_hours": first_hours,
                "first": first,
                "extra": extra,
                "pick": pick,
                "budget": budget,
            }

    def table(self, params: dict, solution: dict) -> dict:
        return {
            "caption": "Rental charges",
            "headers": ["Item", _first_label(params["first_hours"]), "Each additional hour"],
            "rows": [
                [item, money2(f), money2(e)]
                for item, f, e in zip(
                    params["items"], params["first"], params["extra"], strict=True
                )
            ],
        }

    def solve(self, params: dict) -> dict:
        k, fh, budget = params["pick"], params["first_hours"], params["budget"]
        first, extra = params["first"][k], params["extra"][k]
        left = budget - first
        more, rem = divmod(left, extra)
        hours = fh + more
        return {
            "answer": {"type": "integer", "value": hours, "unit": "h"},
            "intermediates": {
                "item": params["items"][k].lower(),
                "budget": money(budget),
                "budget2": money2(budget),
                "first_text": "the first hour" if fh == 1 else f"the first {fh} hours",
                "first": money2(first),
                "left": money2(left),
                "extra": money2(extra),
                "more": more,
                "more_hours": f"{more} more {'hour' if more == 1 else 'hours'}",
                "rem": money2(rem),
                "fh": fh,
                "hours": hours,
                "e_left": f"{_num2(budget)}-{_num2(first)}",
                "e_more": f"({_num2(left)}-{_num2(rem)})/{_num2(extra)}",
                "e_hours": f"{fh}+{more}",
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        """Whole numbers of hours, on both sides of the answer."""
        k, fh, budget = params["pick"], params["first_hours"], params["budget"]
        first, extra = params["first"][k], params["extra"][k]
        hours = rental_hours(budget, first, extra, fh)
        slips: list[Slip] = [
            ((budget - first) // extra, "left out the first period's hours"),
            (hours + 1, "rounded the extra hours up"),
            (fh + (budget - first) // first, "charged the extra hours at the first-period price"),
            (fh + budget // extra, "did not take the first-period charge off the money"),
            (budget // extra, "charged every hour at the additional-hour price"),
        ]
        if fh > 1:
            slips.append((hours - fh + 1, "counted the first period as one hour"))
            slips.append((hours + fh, "counted the first period's hours twice"))
        slips.append((hours - 1, "took the first hour off the total twice"))
        slips.append((budget * fh // first, "charged every hour at the first-period rate"))
        for j in (k - 1, k + 1):
            if 0 <= j < 3 and budget >= params["first"][j]:
                other = rental_hours(budget, params["first"][j], params["extra"][j], fh)
                slips.append((other, "read another item's row"))
        return _spread(slips, Fraction(hours), params)

    def validate(self, params: dict, solution: dict) -> dict:
        k, fh, budget = params["pick"], params["first_hours"], params["budget"]
        first, extra = params["first"], params["extra"]
        hours = solution["answer"]["value"]
        ok_rows = len(params["items"]) == len(first) == len(extra) == 3 and 0 <= k < 3
        spent = first[k] + (hours - fh) * extra[k] if ok_rows else 0
        checks = {
            "three_distinct_items": ok_rows and len(set(params["items"])) == 3,
            "first_period_costs_at_least_its_hours": ok_rows
            and all(f >= e * fh for f, e in zip(first, extra, strict=True)),
            "whole_dollar_budget": budget % 100 == 0,
            "at_least_one_extra_hour": ok_rows and hours > fh,
            "money_left_over": ok_rows and (budget - first[k]) % extra[k] != 0,
            "within_level": hours <= _MAX_HOURS,
            # the hours fit the budget and one more hour would not
            "answer_verified": ok_rows and spent <= budget < spent + extra[k],
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- tariff

# template -> (noun, unit as printed, unit for "per", first limits, next band sizes,
#              first price range in cents, step range in cents, usage past the top band)
TARIFFS: dict[str, dict] = {
    "water": {
        "what": "water",
        "unit": "m³",
        "per": "m³",
        "first": (20, 30, 40),
        "next": (10, 20),
        "price": (110, 160),
        "step": (10, 40),
        "over": (1, 30),
    },
    "electricity": {
        "what": "electricity",
        "unit": "units",
        "per": "unit",
        "first": (100, 150, 200),
        "next": (100, 200),
        "price": (18, 28),
        "step": (1, 4),
        "over": (1, 200),
    },
}


def _amount(template: str, n: int) -> str:
    return f"{n} m³" if template == "water" else f"{n} {'unit' if n == 1 else 'units'}"


def tariff_rows(template: str, limits: list[int], prices: list[int]) -> list[list[str]]:
    l1, l2 = limits
    return [
        [f"First {_amount(template, l1)}", money2(prices[0])],
        [f"Next {_amount(template, l2 - l1)}", money2(prices[1])],
        [f"Above {_amount(template, l2)}", money2(prices[2])],
    ]


def tariff_charge(limits: list[int], prices: list[int], usage: int) -> tuple[int, ...]:
    """Cents charged in each band for ``usage``."""
    l1, l2 = limits
    return (l1 * prices[0], (l2 - l1) * prices[1], (usage - l2) * prices[2])


class TariffGstSolver:
    """``limits`` are the two band edges, ``prices`` the cents per m³ or unit in each of the
    three bands, ``usage`` the amount used (in the top band)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(TARIFFS))
        t = TARIFFS[template]
        while True:
            l1 = rng.choice(t["first"])
            limits = [l1, l1 + rng.choice(t["next"])]
            p1 = rng.randint(*t["price"])
            p2 = p1 + rng.randint(*t["step"])
            prices = [p1, p2, p2 + rng.randint(*t["step"])]
            usage = limits[1] + rng.randint(*t["over"])
            if sum(tariff_charge(limits, prices, usage)) % 100 == 0:  # whole dollars
                return {
                    "name": rng.choice(NAME_POOL),
                    "template": template,
                    "limits": limits,
                    "prices": prices,
                    "usage": usage,
                }

    def table(self, params: dict, solution: dict) -> dict:
        t = TARIFFS[params["template"]]
        return {
            "caption": f"{t['what'].capitalize()} charges",
            "headers": [f"{t['what'].capitalize()} used in a month", f"Price per {t['per']}"],
            "rows": tariff_rows(params["template"], params["limits"], params["prices"]),
        }

    def solve(self, params: dict) -> dict:
        template, limits, prices = params["template"], params["limits"], params["prices"]
        usage = params["usage"]
        l1, l2 = limits
        c1, c2, c3 = tariff_charge(limits, prices, usage)
        before = c1 + c2 + c3
        gst = before * GST_PERCENT // 100
        total = before + gst

        def amt(n: int) -> str:
            return _amount(template, n)

        return {
            "answers": [_money_answer(before), _money_answer(total)],
            "intermediates": {
                "what": TARIFFS[template]["what"],
                "used": amt(usage),
                "gst_percent": GST_PERCENT,
                "step1": f"Charge for the first {amt(l1)} = {l1} × {money2(prices[0])} "
                f"= {money2(c1)}.",
                "expr1": f"{l1}*{_num2(prices[0])}",
                "step2": f"Charge for the next {amt(l2 - l1)} = {l2 - l1} × "
                f"{money2(prices[1])} = {money2(c2)}.",
                "expr2": f"{l2 - l1}*{_num2(prices[1])}",
                "step3": f"Amount above {amt(l2)} = {usage} − {l2} = {amt(usage - l2)}. "
                f"Charge for it = {usage - l2} × {money2(prices[2])} = {money2(c3)}.",
                "expr3": f"{usage - l2}*{_num2(prices[2])}",
                "step4": f"Charge before GST = {money2(c1)} + {money2(c2)} + {money2(c3)} "
                f"= {money2(before)}.",
                "expr4": f"{_num2(c1)}+{_num2(c2)}+{_num2(c3)}",
                "step5": f"GST = {GST_PERCENT}% × {money2(before)} = {money2(gst)}.",
                "expr5": f"{GST_PERCENT}/100*{_num2(before)}",
                "step6": f"Amount paid altogether = {money2(before)} + {money2(gst)} "
                f"= {money2(total)}.",
                "expr6": f"{_num2(before)}+{_num2(gst)}",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        t = TARIFFS[params["template"]]
        limits, prices, usage = params["limits"], params["prices"], params["usage"]
        before, total = (round(a["value"] * 100) for a in solution["answers"])
        checks = {
            "standard_bands": len(limits) == 2
            and limits[0] in t["first"]
            and limits[1] - limits[0] in t["next"],
            "prices_rise_by_band": len(prices) == 3 and _increasing(prices),
            "usage_reaches_top_band": t["over"][0] <= usage - limits[-1] <= t["over"][1],
            "whole_dollars_before_gst": before % 100 == 0,
            # each unit charged at its band's price, then 109% of that
            "answers_verified": before
            == sum(
                prices[0 if u <= limits[0] else 1 if u <= limits[1] else 2]
                for u in range(1, usage + 1)
            )
            and Fraction(total) == Fraction(before * (100 + GST_PERCENT), 100),
        }
        return {"ok": all(checks.values()), "checks": checks}


register("postage_table", PostageTableSolver())
register("rental_table", RentalTableSolver())
register("tariff_gst", TariffGstSolver())
