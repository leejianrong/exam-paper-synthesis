"""Solvers for the ``decimals`` ladder (P8e): the four operations on decimals and money.

* easy   — multiply or divide a decimal by a whole number, tens or hundreds
           ("Find the value of 3.6 × 40." / "Find the value of 7.25 ÷ 5.").
* medium — unitary money: "4 notebooks cost $9.60. How much do 7 such notebooks cost?"
* hard   — change from shopping: "With $50, Mrs Lim bought 3 kg of rice at $2.35 per kg
           and 4 packets of milk at $3.40 each. How much money did Mrs Lim have left?"

Exact by construction (ADR-0014): every decimal is held as an integer count of its
smallest place (``digits`` with ``dp`` decimal places, or whole cents) and the maths runs
on integers / ``Fraction`` — never on floats. A float appears only as the canonical
answer's ``value`` (built from the exact 2-dp string, so it prints back exactly).

* easy   — ``divide`` draws the quotient (1–2 dp) first and multiplies it back up, so the
           division is exact; ``multiply`` keeps ``dp - k <= 2`` places in the product.
* medium — the price of one item is drawn in whole cents, so the total for ``n`` divides.
* hard   — the budget is a whole number of dollars above what was spent.

Names (hard) and item nouns (medium) are cosmetic (W1a): they appear only in the YAML
templates and never reach ``solve()``.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register

# Singapore-appropriate shoppers (PSLE style, R1.6). Titles avoid any pronoun in the text.
NAME_POOL = [
    "Mrs Lim",
    "Mr Tan",
    "Mdm Siti",
    "Mr Kumar",
    "Mrs Wong",
    "Mdm Chua",
    "Mr Rahman",
    "Mrs Pillai",
]


def dec(x: Fraction) -> str:
    """An exact terminating decimal without trailing zeros: ``3.6``, ``144``, ``0.09``."""
    for places in range(7):
        scaled = x * 10**places
        if scaled.denominator == 1:
            n = int(scaled)
            if places == 0:
                return str(n)
            sign, n = ("-", -n) if n < 0 else ("", n)
            whole, frac = divmod(n, 10**places)
            return f"{sign}{whole}.{frac:0{places}d}"
    raise AssertionError(f"not a short terminating decimal: {x}")


def money(cents: int) -> str:
    """``$9.60`` — always two decimal places."""
    return f"${cents // 100}.{cents % 100:02d}"


def plain(cents: int) -> str:
    """``9.60`` — a cents amount for a step's ``expr``."""
    return money(cents)[1:]


def money_answer(cents: int) -> dict:
    return {"type": "decimal", "value": float(plain(cents)), "dp": 2, "unit": "$"}


# ------------------------------------------------------------------ easy

_MAX_EASY = Fraction(1000)  # keep the numbers primary-school sized
FACTORS = frozenset(d * 10**k for d in range(2, 10) for k in range(3))  # 2-9, 20-90, 200-900


def easy_operand(params: dict) -> Fraction:
    return Fraction(params["digits"], 10 ** params["dp"])


def easy_value(params: dict) -> Fraction:
    a, factor = easy_operand(params), params["factor"]
    return a * factor if params["op"] == "multiply" else a / factor


def _places(x: Fraction) -> int:
    return next(p for p in range(7) if (x * 10**p).denominator == 1)


class DecimalsEasySolver:
    """``digits``/``dp`` — the decimal operand (``digits`` ÷ 10^``dp``, last digit non-zero);
    ``factor`` — the whole number (2–9, or 20–90 / 200–900)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            op = rng.choice(["multiply", "divide"])
            factor = rng.randint(2, 9) * 10 ** rng.randint(0, 2)
            if op == "multiply":
                dp = rng.randint(1, 3)
                digits = rng.randint(11, 99 if dp == 1 else 999)
            else:  # draw the quotient, then the dividend is quotient × factor
                q_dp = rng.randint(1, 2)
                quotient = Fraction(rng.randint(1, 99 if q_dp == 1 else 999), 10**q_dp)
                a = quotient * factor
                dp = _places(a)
                digits = int(a * 10**dp)
            params = {"op": op, "digits": digits, "dp": dp, "factor": factor}
            if self._ok(params):
                return params

    @staticmethod
    def _ok(params: dict) -> bool:
        a, value = easy_operand(params), easy_value(params)
        return (
            params["digits"] % 10 != 0  # the operand really has dp places
            and 1 <= params["dp"] <= 3
            and _places(value) <= 2
            and 0 < value < _MAX_EASY
            and a < 100
            # a division shows a decimal answer, never a whole number
            and (params["op"] == "multiply" or value.denominator != 1)
        )

    def solve(self, params: dict) -> dict:
        a, factor, value = easy_operand(params), params["factor"], easy_value(params)
        sign = "×" if params["op"] == "multiply" else "÷"
        tens = 1
        while factor % (tens * 10) == 0:
            tens *= 10
        if tens > 1:
            first = a * (factor // tens) if sign == "×" else a / (factor // tens)
            working = (
                f"{dec(a)} {sign} {factor} = {dec(a)} {sign} {factor // tens} {sign} {tens} "
                f"= {dec(first)} {sign} {tens} = {dec(value)}."
            )
        else:
            working = f"{dec(a)} {sign} {factor} = {dec(value)}."
        if value.denominator == 1:
            answer: dict = {"type": "integer", "value": int(value), "unit": ""}
        else:
            answer = {"type": "decimal", "value": float(dec(value)), "dp": None, "unit": ""}
        return {
            "answer": answer,
            "intermediates": {
                "a": dec(a),
                "sign": sign,
                "expr_op": "*" if sign == "×" else "/",
                "step1": working,
                "answer_value": dec(value),
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        a, factor = easy_operand(params), params["factor"]
        ans = Fraction(str(solution["answer"]["value"]))
        checks = {
            "params_in_range": self._ok(params),
            "factor_shape": factor in FACTORS,
            # the defining relationship, checked the other way round for a division
            "answer_verified": (
                ans == a * factor if params["op"] == "multiply" else ans * factor == a
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ medium

# Plural nouns a teacher may swap to (W1a item role): "4 {item} cost ...".
ITEM_POOL = [
    "notebooks",
    "pens",
    "files",
    "rulers",
    "markers",
    "mugs",
    "towels",
    "storybooks",
    "bottles of juice",
    "packets of biscuits",
]


class DecimalsMediumSolver:
    """``n`` items cost ``cost`` cents altogether; find the cost of ``m`` such items."""

    ITEM_POOL = ITEM_POOL

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            unit = 5 * rng.randint(7, 199)  # 35¢ .. $9.95, a whole number of 5 cents
            if unit % 100 == 0:
                continue
            n = rng.randint(2, 9)
            m = rng.choice([k for k in range(2, 13) if k != n])
            return {"item": rng.choice(ITEM_POOL), "n": n, "cost": n * unit, "m": m}

    def solve(self, params: dict) -> dict:
        n, cost, m = params["n"], params["cost"], params["m"]
        unit = cost // n
        ans = m * unit
        return {
            "answer": money_answer(ans),
            "intermediates": {
                "cost_text": money(cost),
                "cost_plain": plain(cost),
                "unit_text": money(unit),
                "unit_plain": plain(unit),
                "answer_text": money(ans),
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        n, cost, m = params["n"], params["cost"], params["m"]
        ans = Fraction(str(solution["answer"]["value"])) * 100
        checks = {
            "shape": 2 <= n <= 9 and 2 <= m <= 12 and m != n,
            "whole_cents_each": cost % n == 0 and (cost // n) % 100 != 0,
            "answer_whole_cents": ans.denominator == 1,
            # unitary method, checked by cross-multiplication: ans / m == cost / n
            "answer_verified": ans * n == cost * m,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ hard

# good -> (phrase with {q} and {p}, noun for the working, price range in cents)
GOODS: dict[str, tuple[str, str, int, int]] = {
    "rice": ("{q} kg of rice at {p} per kg", "rice", 185, 395),
    "apples": ("{q} kg of apples at {p} per kg", "apples", 290, 595),
    "milk": ("{q} packets of milk at {p} each", "milk", 195, 445),
    "bread": ("{q} loaves of bread at {p} each", "bread", 165, 345),
    "eggs": ("{q} trays of eggs at {p} each", "eggs", 285, 595),
    "juice": ("{q} bottles of juice at {p} each", "juice", 115, 395),
}
BUDGETS = (20, 30, 50, 100)  # whole dollars


def _spent(params: dict) -> int:
    return sum(q * p for q, p in zip(params["qty"], params["price"], strict=True))


class DecimalsHardSolver:
    """``goods`` — two of :data:`GOODS`; ``qty`` and ``price`` (cents) per good;
    ``budget`` — whole dollars the shopper had."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            goods = rng.sample(sorted(GOODS), 2)
            qty = [rng.randint(2, 6) for _ in goods]
            price = [5 * rng.randint(GOODS[g][2] // 5, GOODS[g][3] // 5) for g in goods]
            if any(p % 100 == 0 for p in price):
                continue
            spent = sum(q * p for q, p in zip(qty, price, strict=True))
            budgets = [b for b in BUDGETS if b * 100 - spent >= 100]
            if not budgets:
                continue
            return {
                "name": rng.choice(NAME_POOL),
                "goods": goods,
                "qty": qty,
                "price": price,
                "budget": rng.choice(budgets[:2]),  # one of the two closest notes
            }

    def solve(self, params: dict) -> dict:
        goods, qty, price, budget = (
            params["goods"],
            params["qty"],
            params["price"],
            params["budget"],
        )
        costs = [q * p for q, p in zip(qty, price, strict=True)]
        spent = sum(costs)
        ans = budget * 100 - spent
        bought = " and ".join(
            GOODS[g][0].format(q=q, p=money(p)) for g, q, p in zip(goods, qty, price, strict=True)
        )
        inter = {"budget_text": f"${budget}", "bought": bought}
        for i, (g, q, p, c) in enumerate(zip(goods, qty, price, costs, strict=True), start=1):
            inter[f"step{i}"] = f"Cost of the {GOODS[g][1]} = {q} × {money(p)} = {money(c)}."
            inter[f"expr{i}"] = f"{q}*{plain(p)}"
        inter.update(
            {
                "step3": f"Total spent = {money(costs[0])} + {money(costs[1])} = {money(spent)}.",
                "expr3": f"{plain(costs[0])}+{plain(costs[1])}",
                "step4": f"Money left = ${budget} - {money(spent)} = {money(ans)}.",
                "expr4": f"{budget}-{plain(spent)}",
            }
        )
        return {"answer": money_answer(ans), "intermediates": inter}

    def validate(self, params: dict, solution: dict) -> dict:
        goods, qty, price = params["goods"], params["qty"], params["price"]
        left = Fraction(str(solution["answer"]["value"])) * 100
        checks = {
            "two_different_goods": len(goods) == 2 and len(set(goods)) == 2,
            "goods_realistic": all(
                GOODS[g][2] <= p <= GOODS[g][3] and p % 5 == 0 and p % 100 != 0 and 2 <= q <= 6
                for g, q, p in zip(goods, qty, price, strict=True)
            ),
            "budget_note": params["budget"] in BUDGETS,
            "money_left": left.denominator == 1 and left >= 100,
            # what is left plus what was spent is the money she started with
            "answer_verified": left + _spent(params) == params["budget"] * 100,
        }
        return {"ok": all(checks.values()), "checks": checks}


register("decimals_easy", DecimalsEasySolver())
register("decimals_medium", DecimalsMediumSolver())
register("decimals_hard", DecimalsHardSolver())
