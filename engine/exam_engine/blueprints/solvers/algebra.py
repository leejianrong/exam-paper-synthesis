"""Solvers for the ``algebra`` ladder (P8e): algebraic expressions and simple equations (P6).

* easy   — evaluate a simple expression for a given whole-number value of the letter:
           ``an + b``, ``an - b``, ``a(n + b)``, ``n/a + b`` or ``(an - b)/c``.
* medium — evaluate a story expression: the total cost of two kinds of items when one
           costs $p and the other costs $d more / $d less / m times as much.
* hard   — form and solve a simple linear equation from a story: one person has x items,
           the other has m times as many (or e more); the other then gives some away (or
           gets some more), and the new total is given.

Every answer is numeric (not the ``expression`` type), so every rung converts to multiple
choice. Letters print in KaTeX (``\\(5n - 7\\)``), so they come out in italics the way PSLE
prints them, with ``5n`` rather than ``5 × n``.

Person names are cosmetic (W1a): they appear only in the YAML templates, which interleave
them with the number-bearing fragments the solver builds, so ``solve()`` never reads them.
Every value is a whole number by construction (ADR-0014):

* easy   — ``n`` is drawn as a multiple of ``a`` for ``n/a + b``; for ``(an - b)/c`` the
           result is drawn first and ``b`` is derived so the division is exact;
* medium — prices are whole dollars, so the total is too;
* hard   — ``x`` is drawn first and the stated total is computed from it.
"""

from __future__ import annotations

import random

from ..registry import register

# Singapore-appropriate given names (PSLE style, R1.6).
NAME_POOL = [
    "Ali",
    "Ben",
    "Chloe",
    "Devi",
    "Ethan",
    "Faridah",
    "Gopal",
    "Hui Ling",
    "Ismail",
    "Jia En",
    "Kavya",
    "Lucas",
]

LETTERS = ["n", "x", "y", "k", "m", "p"]

# ------------------------------------------------------------------ easy

EASY_FORMS = ["add", "sub", "bracket", "frac_add", "frac_sub"]


def easy_expression(form: str, letter: str, a: int, b: int, c: int) -> str:
    """The expression as LaTeX (without the ``\\(…\\)`` delimiters)."""
    return {
        "add": f"{a}{letter} + {b}",
        "sub": f"{a}{letter} - {b}",
        "bracket": f"{a}({letter} + {b})",
        "frac_add": rf"\frac{{{letter}}}{{{a}}} + {b}",
        "frac_sub": rf"\frac{{{a}{letter} - {b}}}{{{c}}}",
    }[form]


def easy_value(form: str, a: int, b: int, c: int, n: int) -> tuple[int, int]:
    """``(first step value, answer)``; the answer is exact by construction."""
    if form == "add":
        return a * n, a * n + b
    if form == "sub":
        return a * n, a * n - b
    if form == "bracket":
        return n + b, a * (n + b)
    if form == "frac_add":
        return n // a, n // a + b
    top = a * n - b
    return top, top // c


class AlgebraEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        form = rng.choice(EASY_FORMS)
        letter = rng.choice(LETTERS)
        c = 1
        if form == "add":
            a, b, n = rng.randint(2, 9), rng.randint(1, 20), rng.randint(2, 12)
        elif form == "sub":
            while True:
                a, b, n = rng.randint(2, 9), rng.randint(1, 20), rng.randint(2, 12)
                if a * n - b >= 1:
                    break
        elif form == "bracket":
            a, b, n = rng.randint(2, 9), rng.randint(1, 9), rng.randint(2, 12)
        elif form == "frac_add":
            a, b = rng.randint(2, 9), rng.randint(1, 20)
            n = a * rng.randint(2, 9)
        else:
            while True:
                a, c, n = rng.randint(2, 9), rng.randint(2, 5), rng.randint(2, 12)
                # b = a*n - c*result, with 1 <= b <= 20: pick the result to make b fit
                results = [r for r in range(1, a * n) if 1 <= a * n - c * r <= 20]
                if results:
                    b = a * n - c * rng.choice(results)
                    break
        return {"form": form, "letter": letter, "a": a, "b": b, "c": c, "n": n}

    def solve(self, params: dict) -> dict:
        form, x = params["form"], params["letter"]
        a, b, c, n = params["a"], params["b"], params["c"], params["n"]
        first, ans = easy_value(form, a, b, c, n)
        expr = easy_expression(form, x, a, b, c)
        if form in ("add", "sub"):
            op = "+" if form == "add" else "-"
            steps = (
                rf"\({a}{x} = {a} \times {n} = {first}\)",
                rf"\({expr} = {first} {op} {b} = {ans}\)",
            )
            exprs = (f"{a}*{n}", f"{first}{op}{b}")
        elif form == "bracket":
            steps = (
                rf"\({x} + {b} = {n} + {b} = {first}\)",
                rf"\({expr} = {a} \times {first} = {ans}\)",
            )
            exprs = (f"{n}+{b}", f"{a}*{first}")
        elif form == "frac_add":
            steps = (
                rf"\(\frac{{{x}}}{{{a}}} = {n} \div {a} = {first}\)",
                rf"\({expr} = {first} + {b} = {ans}\)",
            )
            exprs = (f"{n}/{a}", f"{first}+{b}")
        else:
            steps = (
                rf"\({a}{x} - {b} = {a} \times {n} - {b} = {first}\)",
                rf"\({expr} = {first} \div {c} = {ans}\)",
            )
            exprs = (f"{a}*{n}-{b}", f"{first}/{c}")
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "s1": rf"Find the value of \({expr}\) when \({x} = {n}\).",
                "step1": f"When \\({x} = {n}\\), {steps[0]}.",
                "step2": f"{steps[1]}.",
                "expr1": exprs[0],
                "expr2": exprs[1],
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        form = params["form"]
        a, b, c, n = params["a"], params["b"], params["c"], params["n"]
        ans = solution["answer"]["value"]
        if form == "frac_add":
            truth_num, truth_den = n + a * b, a  # n/a + b = (n + ab)/a
        elif form == "frac_sub":
            truth_num, truth_den = a * n - b, c
        else:
            truth_num, truth_den = (
                {"add": a * n + b, "sub": a * n - b, "bracket": a * n + a * b}[form],
                1,
            )
        checks = {
            "unused_divisor_is_one": (c == 1) == (form != "frac_sub"),
            "exact": truth_num % truth_den == 0,
            "positive_whole_answer": ans >= 1,
            "answer_verified": ans * truth_den == truth_num,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ medium

# pair key -> (first item, its plural, second item, its plural)
ITEM_PAIRS: dict[str, tuple[str, str, str, str]] = {
    "pen_file": ("pen", "pens", "file", "files"),
    "pencil_ruler": ("pencil", "pencils", "ruler", "rulers"),
    "cup_plate": ("cup", "cups", "plate", "plates"),
    "notebook_bag": ("notebook", "notebooks", "bag", "bags"),
    "cap_shirt": ("cap", "caps", "T-shirt", "T-shirts"),
}
MEDIUM_KINDS = ["more", "less", "times"]


def second_price(kind: str, p: int, d: int) -> int:
    """The second item's price when the first costs ``p``."""
    return {"more": p + d, "less": p - d, "times": d * p}[kind]


class AlgebraMediumSolver:
    """``d`` is $d more / $d less, or ``d`` times as much, depending on ``kind``."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        kind = rng.choice(MEDIUM_KINDS)
        k1 = rng.randint(2, 6)
        k2 = rng.choice([k for k in range(2, 7) if k != k1])
        if kind == "times":
            d, p = rng.randint(3, 5), rng.randint(2, 9)  # "3 times as much", never "2 times"
        elif kind == "more":
            d, p = rng.randint(1, 9), rng.randint(2, 12)
        else:
            d = rng.randint(1, 8)
            p = rng.randint(d + 1, 15)
        return {
            "name": rng.choice(NAME_POOL),
            "items": rng.choice(sorted(ITEM_PAIRS)),
            "letter": rng.choice(["p", "x", "y", "k"]),
            "kind": kind,
            "k1": k1,
            "k2": k2,
            "d": d,
            "p": p,
        }

    def solve(self, params: dict) -> dict:
        kind, x = params["kind"], params["letter"]
        k1, k2, d, p = params["k1"], params["k2"], params["d"], params["p"]
        one, ones, two, twos = ITEM_PAIRS[params["items"]]
        q = second_price(kind, p, d)
        cost1, cost2 = k1 * p, k2 * q
        ans = cost1 + cost2
        relation = {
            "more": f"${d} more than",
            "less": f"${d} less than",
            "times": f"{d} times as much as",
        }[kind]
        second = {"more": f"{x} + {d}", "less": f"{x} - {d}", "times": f"{d}{x}"}[kind]
        # in terms of the letter, PSLE style: $2(p + 3), $(5 × 4p) = $20p, $(6p + 6)
        if kind == "times":
            second_cost = rf"\({k2} \times {d}{x}\) = $\({k2 * d}{x}\)"
            total = rf"\(({k1}{x} + {k2 * d}{x})\) = $\({k1 + k2 * d}{x}\)"
        else:
            op = "+" if kind == "more" else "-"
            second_cost = rf"\({k2}({second})\)"
            total = rf"\(({k1}{x} + {k2}({second}))\) = $\(({k1 + k2}{x} {op} {k2 * d})\)"
        worked = {
            "more": f"{k2} × (${p} + ${d})",
            "less": f"{k2} × (${p} - ${d})",
            "times": f"{k2} × {d} × ${p}",
        }[kind]
        second_expr = {
            "more": f"{k2}*({p}+{d})",
            "less": f"{k2}*({p}-{d})",
            "times": f"{k2}*{d}*{p}",
        }[kind]
        return {
            "answer": {"type": "integer", "value": ans, "unit": "$"},
            "intermediates": {
                "s1": (
                    f" buys {k1} {ones} and {k2} {twos}. A {one} costs $\\({x}\\). "
                    f"A {two} costs {relation} a {one}. Find the total amount of money "
                ),
                "s2": f" pays when \\({x} = {p}\\).",
                "step1": f"Cost of {k1} {ones} = $\\({k1}{x}\\) = {k1} × ${p} = ${cost1}.",
                "step2": f"Cost of {k2} {twos} = ${second_cost} = {worked} = ${cost2}.",
                "step3": f"Total cost = ${total} = ${cost1} + ${cost2} = ${ans}.",
                "expr1": f"{k1}*{p}",
                "expr2": second_expr,
                "expr3": f"{cost1}+{cost2}",
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        kind, k1, k2, d, p = (params[k] for k in ("kind", "k1", "k2", "d", "p"))
        ans = solution["answer"]["value"]
        q = second_price(kind, p, d)
        checks = {
            "different_counts": k1 != k2,
            "second_item_costs_money": q >= 1 and q != p,
            "multiple_reads_naturally": kind != "times" or 3 <= d <= 5,
            # the total, read back as k1 lots of p and k2 lots of the second price
            "answer_verified": ans - k1 * p == k2 * q and ans > 0,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ hard

THINGS = ["stickers", "marbles", "stamps", "beads", "cards"]
HARD_RELATIONS = ["times", "more"]
HARD_CHANGES = ["give", "get"]


def hard_terms(relation: str, m: int, change: str, g: int) -> tuple[int, int]:
    """``(coefficient of x, constant)`` of the total at the end.

    ``relation == "times"``: the second person has ``m x``; ``"more"``: ``x + m``.
    ``change == "give"``: the second person gives away ``g``; ``"get"``: gets ``g`` more.
    """
    coeff, const = (m + 1, 0) if relation == "times" else (2, m)
    return coeff, const + (g if change == "get" else -g)


class AlgebraHardSolver:
    """``m`` is the multiple (``times``) or the difference (``more``); ``g`` the change."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        relation = rng.choice(HARD_RELATIONS)
        change = rng.choice(HARD_CHANGES)
        while True:
            x = rng.randint(5, 60)
            m = rng.randint(3, 6) if relation == "times" else rng.randint(3, 30)
            g = rng.randint(2, 20)
            coeff, const = hard_terms(relation, m, change, g)
            second = m * x if relation == "times" else x + m
            if const != 0 and (change == "get" or second - g >= 1):
                break
        return {
            "names": rng.sample(NAME_POOL, 2),
            "thing": rng.choice(THINGS),
            "relation": relation,
            "change": change,
            "m": m,
            "g": g,
            "total": coeff * x + const,
        }

    def solve(self, params: dict) -> dict:
        relation, change, thing = params["relation"], params["change"], params["thing"]
        m, g, total = params["m"], params["g"], params["total"]
        coeff, const = hard_terms(relation, m, change, g)
        rhs = total - const
        ans = rhs // coeff
        sign = "+" if change == "get" else "-"
        if relation == "times":
            rel_text = f" has {m} times as many {thing} as "
            at_first = f"x + {m}x"
        else:
            rel_text = f" has {m} more {thing} than "
            at_first = f"x + x + {m}"
        const_op = "+" if const > 0 else "-"
        step1 = (
            rf"Number of {thing} they have at the end = \({at_first} {sign} {g}"
            rf" = {coeff}x {const_op} {abs(const)}\)."
        )
        lhs = f"{coeff}x {const_op} {abs(const)}"
        undo = "-" if const > 0 else "+"
        action = f" gives away {g} {thing}." if change == "give" else f" gets {g} more {thing}."
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "s1": rf" has \(x\) {thing}. ",
                "s2": rel_text,
                "s3": ". ",
                "s4": (
                    f"{action} They now have {total} {thing} altogether. "
                    r"Find the value of \(x\)."
                ),
                "step1": step1,
                "step2": (
                    rf"\({lhs} = {total}\), so \({coeff}x = {total} {undo} {abs(const)}"
                    rf" = {rhs}\)."
                ),
                "step3": rf"\(x = {rhs} \div {coeff} = {ans}\).",
                "expr2": f"{total}{undo}{abs(const)}",
                "expr3": f"{rhs}/{coeff}",
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        relation, change = params["relation"], params["change"]
        m, g, total = params["m"], params["g"], params["total"]
        x = solution["answer"]["value"]
        first = x
        second = m * x if relation == "times" else x + m
        second_after = second - g if change == "give" else second + g
        coeff, const = hard_terms(relation, m, change, g)
        checks = {
            "positive_whole_x": x >= 1,
            "change_matters": const != 0,
            "enough_to_give": second_after >= 1,
            # the story, replayed with the answer: the two counts add up to the stated total
            "answer_verified": first + second_after == total,
            "multiple_reads_naturally": relation == "more" or 3 <= m <= 6,
            "unique": coeff * x + const == total and coeff >= 2,
        }
        return {"ok": all(checks.values()), "checks": checks}


register("algebra_easy", AlgebraEasySolver())
register("algebra_medium", AlgebraMediumSolver())
register("algebra_hard", AlgebraHardSolver())
