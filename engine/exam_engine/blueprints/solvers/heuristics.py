"""Solvers for the P8c batch 2 multi-part blueprints (EXA-143): Paper 2 Section B questions
built on the named PSLE heuristics (docs/planning/editor/REAL-PAPER-COMPARISON.md Part 2).

* ``supposition_structured`` (5 = 1 + 2 + 2) — tickets at two prices, the number sold and the
  money collected: (a) the money if every ticket had been the cheaper kind; (b) how many of
  the dearer kind, by supposition; (c) how much more came from one kind than the other.
* ``fraction_remainder_structured`` (4 = 1 + 3) — a fraction of the money on one thing, a
  fraction of the remainder on some identical items, a sum left: (a) the fraction left;
  (b) the cost of each item, working back from (a).
* ``lcm_packs_structured`` (3 = 1 + 2) — two goods in packs of m and n, the same number of
  each: (a) the smallest number (the LCM); (b) the most of both a budget buys.
* ``age_difference_structured`` (3 = 1 + 2) — two ages now: (a) the age difference (it never
  changes); (b) in how many years the ages are in a given ratio.
* ``equal_number_amount_structured`` (4 = 2 + 2) — two goods at two prices: (a) an equal
  number of each, a difference in money spent; (b) an equal amount on each, the money spent.

Every quantity is a whole number by construction (ADR-0014); ``validate`` rejects the
degenerate cases (nothing of one kind, a remainder that never matters, a ratio that is
already true now).
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from ..registry import register
from .ratio_hard import NAME_POOL


def _lcm(x: int, y: int) -> int:
    return x * y // gcd(x, y)


def _money(value: int) -> dict:
    return {"type": "quantity", "value": value, "unit": "$"}


def _count(value: int) -> dict:
    return {"type": "integer", "value": value}


def _units(n: int) -> str:
    return "1 unit" if n == 1 else f"{n} units"


# --------------------------------------------------------------------------- supposition


class SuppositionStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            child = rng.randint(3, 10)
            adult = child + rng.randint(2, 8)
            total = rng.randint(30, 120)
            n_adult = rng.randint(total // 4, 3 * total // 4)
            params = {
                "name": rng.choice(NAME_POOL),
                "total": total,
                "adult_price": adult,
                "child_price": child,
                "amount": n_adult * adult + (total - n_adult) * child,
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        total, adult_price = params["total"], params["adult_price"]
        child_price, amount = params["child_price"], params["amount"]
        all_child = total * child_price
        extra = amount - all_child
        price_diff = adult_price - child_price
        adult = extra // price_diff
        child = total - adult
        adult_amount, child_amount = adult * adult_price, child * child_price
        more = adult_amount - child_amount
        return {
            "answers": [_money(all_child), _count(adult), _money(more)],
            "intermediates": {
                "all_child": all_child,
                "extra": extra,
                "price_diff": price_diff,
                "adult": adult,
                "child": child,
                "adult_amount": adult_amount,
                "child_amount": child_amount,
                "more": more,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        total, adult_price = params["total"], params["adult_price"]
        child_price, amount = params["child_price"], params["amount"]
        all_child, adult, more = (a["value"] for a in solution["answers"])
        extra = amount - all_child
        checks = {
            "adult_dearer": adult_price > child_price,
            "whole_number_of_adults": extra % (adult_price - child_price) == 0,
            "both_kinds_sold": 0 < adult < total,
            "adult_money_more": more > 0,
            "within_level": amount <= 2000,
            "answers_verified": (
                adult * adult_price + (total - adult) * child_price == amount
                and more == adult * adult_price - (total - adult) * child_price
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- fraction


class FractionRemainderStructuredSolver:
    ITEM_POOL = ["shirts", "books", "files", "caps", "towels", "mugs"]

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            b = rng.randint(3, 8)
            a = rng.randint(1, b - 1)
            d = rng.randint(2, 6)
            c = rng.randint(1, d - 1)
            if gcd(a, b) != 1 or gcd(c, d) != 1:
                continue
            count = rng.randint(2, 8)
            on_items = count * rng.randint(2, 60)
            remainder = Fraction(on_items * d, c)
            money = remainder * b / (b - a)
            if money.denominator != 1 or remainder.denominator != 1:
                continue
            params = {
                "name": rng.choice(NAME_POOL),
                "item": rng.choice(self.ITEM_POOL),
                "spent_first": [a, b],
                "spent_then": [c, d],
                "count": count,
                "left": int(remainder) - on_items,
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        a, b = params["spent_first"]
        c, d = params["spent_then"]
        count, left = params["count"], params["left"]
        frac_left = Fraction(b - a, b) * Fraction(d - c, d)
        money = left / frac_left
        remainder = money * Fraction(b - a, b)
        on_items = remainder * Fraction(c, d)
        each = on_items / count
        return {
            "answers": [
                {
                    "type": "fraction",
                    "numerator": frac_left.numerator,
                    "denominator": frac_left.denominator,
                },
                _money(int(each)),
            ],
            "intermediates": {
                "kept_first": b - a,
                "kept_then": d - c,
                "left_num": frac_left.numerator,
                "left_den": frac_left.denominator,
                "money": int(money),
                # "$66 ÷ 1 × 8" reads oddly: a unit fraction is just "8 × $66".
                "money_calc": (
                    f"{frac_left.denominator} × ${left}"
                    if frac_left.numerator == 1
                    else f"${left} ÷ {frac_left.numerator} × {frac_left.denominator}"
                ),
                "remainder": int(remainder),
                "on_items": int(on_items),
                "each": int(each),
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        a, b = params["spent_first"]
        c, d = params["spent_then"]
        count, left = params["count"], params["left"]
        frac_left = Fraction(b - a, b) * Fraction(d - c, d)
        money = left / frac_left
        remainder = money * Fraction(b - a, b)
        on_items = remainder * Fraction(c, d)
        answer_frac = solution["answers"][0]
        each = solution["answers"][1]["value"]
        checks = {
            "proper_fractions": 0 < a < b and 0 < c < d,
            "simplest_fractions": gcd(a, b) == 1 and gcd(c, d) == 1,
            "whole_money": money.denominator == 1 and remainder.denominator == 1,
            "whole_cost_each": (on_items / count).denominator == 1,
            "realistic_amounts": 40 <= money <= 800 and 2 <= each <= 60,
            "answers_verified": (
                Fraction(answer_frac["numerator"], answer_frac["denominator"]) == frac_left
                and each * count == on_items
                and money - money * Fraction(a, b) - on_items == left
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- LCM packs


# Plural goods sold in packs; the pair is part of the story, not a cosmetic slot.
_PACK_GOODS = [
    ["paper cups", "paper plates"],
    ["pencils", "erasers"],
    ["red balloons", "blue balloons"],
    ["envelopes", "cards"],
    ["forks", "spoons"],
]


class LcmPacksStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            m, n = rng.sample(range(4, 13), 2)
            price = [rng.randint(2, 12), rng.randint(2, 12)]
            params = {
                "name": rng.choice(NAME_POOL),
                "goods": rng.choice(_PACK_GOODS),
                "pack": [m, n],
                "price": price,
                "budget": 0,
            }
            lcm = _lcm(m, n)
            set_cost = lcm // m * price[0] + lcm // n * price[1]
            params["budget"] = rng.randint(2, 6) * set_cost + rng.randint(1, set_cost - 1)
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        m, n = params["pack"]
        pm, pn = params["price"]
        budget = params["budget"]
        lcm = _lcm(m, n)
        packs_m, packs_n = lcm // m, lcm // n
        set_cost = packs_m * pm + packs_n * pn
        sets = budget // set_cost
        total = sets * 2 * lcm
        return {
            "answers": [_count(lcm), _count(total)],
            "intermediates": {
                "lcm": lcm,
                "packs_m": packs_m,
                "packs_n": packs_n,
                "set_cost": set_cost,
                "sets": sets,
                "sets_cost": sets * set_cost,
                "next_sets": sets + 1,
                "next_cost": (sets + 1) * set_cost,
                "pair": 2 * lcm,
                "total": total,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        m, n = params["pack"]
        pm, pn = params["price"]
        budget = params["budget"]
        lcm, total = (a["value"] for a in solution["answers"])
        set_cost = lcm // m * pm + lcm // n * pn
        checks = {
            "packs_differ": m != n,
            "neither_pack_divides_the_other": m % n != 0 and n % m != 0,
            "lcm_small": lcm <= 60,
            "budget_leaves_change": budget % set_cost != 0,
            "several_sets": 2 <= budget // set_cost <= 6,
            "within_level": budget <= 600,
            "answers_verified": (
                lcm % m == 0
                and lcm % n == 0
                and total == 2 * lcm * (budget // set_cost)
                and (total // 2 // m) * pm + (total // 2 // n) * pn <= budget
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- ages


class AgeDifferenceStructuredSolver:
    ITEM_POOL = ["father", "mother"]  # the a-article rule rules out uncle and aunt

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            age = rng.randint(6, 14)
            diff = rng.randint(24, 40)
            r = rng.randint(1, 6)
            s = rng.randint(r + 1, 9)
            params = {
                "name": rng.choice(NAME_POOL),
                "relative": rng.choice(self.ITEM_POOL),
                "age": age,
                "relative_age": age + diff,
                "ratio_after": [r, s],
            }
            if (
                gcd(r, s) == 1
                and diff % (s - r) == 0
                and self.validate(params, self.solve(params))["ok"]
            ):
                return params

    def solve(self, params: dict) -> dict:
        age, relative_age = params["age"], params["relative_age"]
        r, s = params["ratio_after"]
        diff = relative_age - age
        unit = diff // (s - r)
        then = r * unit
        years = then - age
        return {
            "answers": [_count(diff), _count(years)],
            "intermediates": {
                "diff": diff,
                "diff_units": s - r,
                "diff_units_text": _units(s - r),
                "unit_line": (
                    f"So 1 unit = {diff} years."
                    if s - r == 1
                    else f"1 unit = {diff} ÷ {s - r} = {unit} years."
                ),
                "unit": unit,
                "then": then,
                "relative_then": s * unit,
                "years": years,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        age, relative_age = params["age"], params["relative_age"]
        r, s = params["ratio_after"]
        diff, years = (a["value"] for a in solution["answers"])
        checks = {
            "relative_older": relative_age - age >= 20,
            "ratio_simplest": gcd(r, s) == 1 and r < s,
            "whole_unit": diff % (s - r) == 0,
            "in_the_future": 2 <= years <= 30,
            "realistic_ages": relative_age + years <= 80,
            "answers_verified": (
                diff == relative_age - age and (age + years) * s == (relative_age + years) * r
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- equal number/amount


# (cheaper, dearer) plural goods.
_SHOP_GOODS = [
    ["pens", "notebooks"],
    ["pencils", "rulers"],
    ["apples", "mangoes"],
    ["buns", "sandwiches"],
    ["erasers", "files"],
]


class EqualNumberAmountStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            pa = rng.randint(2, 9)
            pb = rng.randint(pa + 1, min(12, 3 * pa))
            pairs = rng.randint(6, 40)
            half = _lcm(pa, pb) * rng.randint(1, 8)
            params = {
                "names": rng.sample(NAME_POOL, 2),
                "goods": rng.choice(_SHOP_GOODS),
                "price": [pa, pb],
                "more": pairs * (pb - pa),
                "spent": 2 * half,
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        pa, pb = params["price"]
        more, spent = params["more"], params["spent"]
        price_diff = pb - pa
        pairs = more // price_diff
        total = 2 * pairs
        half = spent // 2
        n_a, n_b = half // pa, half // pb
        return {
            "answers": [_count(total), _count(n_a - n_b)],
            "intermediates": {
                "price_diff": price_diff,
                "pairs": pairs,
                "total": total,
                "half": half,
                "n_a": n_a,
                "n_b": n_b,
                "n_diff": n_a - n_b,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        pa, pb = params["price"]
        more, spent = params["more"], params["spent"]
        total, n_diff = (a["value"] for a in solution["answers"])
        half = spent // 2
        checks = {
            "second_dearer": pb > pa,
            "whole_pairs": more % (pb - pa) == 0 and more > 0,
            "equal_halves_whole": spent % 2 == 0 and half % pa == 0 and half % pb == 0,
            "realistic": total <= 80 and spent <= 600 and more <= 300,
            "a_real_difference": n_diff >= 2,
            "answers_verified": (
                (total // 2) * (pb - pa) == more and (half // pa) - (half // pb) == n_diff
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


register("supposition_structured", SuppositionStructuredSolver())
register("fraction_remainder_structured", FractionRemainderStructuredSolver())
register("lcm_packs_structured", LcmPacksStructuredSolver())
register("age_difference_structured", AgeDifferenceStructuredSolver())
register("equal_number_amount_structured", EqualNumberAmountStructuredSolver())
