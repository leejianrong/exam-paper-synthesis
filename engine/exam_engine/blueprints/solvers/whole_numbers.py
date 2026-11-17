"""Solvers for the ``whole_numbers`` ladder (P8e): the four operations on whole numbers.

* easy   — order of operations: "Find the value of 48 − 12 ÷ 4 × 3." in one of four forms.
* medium — division with a remainder that must be interpreted: round **up** (the least number
           of boats / boxes needed) or **down** (the greatest number of pieces / pens / full
           trays). The remainder is never 0.
* hard   — excess and shortage: "If each pupil gets 5 sweets, 12 are left; if each gets 7,
           there is a shortage of 4." Pupils = (12 + 4) ÷ (7 − 5); sweets = 5 × pupils + 12.

Every quantity is a whole number by construction (ADR-0014): each division is built from a
quotient drawn first (``b = q × c``), the remainder is drawn from ``1 .. d - 1``, and the
excess + shortage is drawn as a multiple of the difference in shares.

The teacher's ``name`` and the ``item`` noun (hard) are cosmetic (W1a): they appear only in
the YAML templates, so ``solve()`` never reads them.

Each rung has a ``distractors`` hook (EXA-122): the wrong answers pupils really give —
working left to right, ignoring the brackets, giving the remainder or rounding the wrong way,
forgetting the leftover sweets. The samplers still prefer numbers whose worked-solution
intermediates would make fair options (written before the hook, when ``mcq.to_mcq`` offered
those intermediates); that preference is kept so the parameter space and goldens are unchanged,
and ``mcq.to_mcq``'s own give-away guard now does the rest. Not a correctness rule.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from fractions import Fraction
from itertools import combinations

from ..base import spread_sides
from ..registry import register

MAX_VALUE = 999  # every printed number, intermediate and answer stays at most this

# ------------------------------------------------------------------ fairness helpers


def _near_step(ans: int) -> int:
    """The near-miss step ``mcq.distractor_values`` uses: 1 below 100, then 10, 100, ..."""
    return max(1, 10 ** (len(str(ans)) - 2))


def _fair(ans: int, wrong: list[int]) -> bool:
    """``wrong`` (the distractors, best first) are usable, distinct and not symmetric."""
    if ans in wrong or len(set(wrong)) != len(wrong):
        return False
    if not all(v > 0 and ans <= 8 * v and v <= 8 * ans for v in wrong):
        return False
    return not any(x + y == 2 * ans for x, y in combinations(wrong, 2))


def _draw(rng: random.Random, attempt: Callable[[random.Random], dict | None]) -> dict:
    while True:
        params = attempt(rng)
        if params is not None:
            return params


# ------------------------------------------------------------------ easy

# form -> how it prints, with a, b, c, d the four numbers in reading order.
EASY_FORMS: dict[str, str] = {
    "sub_div_mul": "{a} − {b} ÷ {c} × {d}",
    "add_mul_bracket": "{a} + {b} × ({c} − {d})",
    "bracket_div_mul": "({a} + {b}) ÷ {c} × {d}",
    "mul_sub_div": "{a} × {b} − {c} ÷ {d}",
}


def _easy_steps(form: str, nums: list[int]) -> list[tuple[str, str, int]]:
    """The three steps of the working as ``(text, expr, value)``; the last is the answer.

    Assumes the numbers are valid (``validate`` checks them); integer division is exact.
    """
    a, b, c, d = nums
    if form == "sub_div_mul":
        q = b // c
        p = q * d
        return [
            (f"Divide first: {b} ÷ {c} = {q}.", f"{b}/{c}", q),
            (f"Then multiply: {q} × {d} = {p}.", f"{q}*{d}", p),
            (f"Then subtract: {a} − {p} = {a - p}.", f"{a}-{p}", a - p),
        ]
    if form == "add_mul_bracket":
        k = c - d
        m = b * k
        return [
            (f"Brackets first: {c} − {d} = {k}.", f"{c}-{d}", k),
            (f"Then multiply: {b} × {k} = {m}.", f"{b}*{k}", m),
            (f"Then add: {a} + {m} = {a + m}.", f"{a}+{m}", a + m),
        ]
    if form == "bracket_div_mul":
        s = a + b
        q = s // c
        return [
            (f"Brackets first: {a} + {b} = {s}.", f"{a}+{b}", s),
            (f"Then divide: {s} ÷ {c} = {q}.", f"{s}/{c}", q),
            (f"Then multiply: {q} × {d} = {q * d}.", f"{q}*{d}", q * d),
        ]
    # mul_sub_div
    m = a * b
    q = c // d
    return [
        (f"Multiply: {a} × {b} = {m}.", f"{a}*{b}", m),
        (f"Divide: {c} ÷ {d} = {q}.", f"{c}/{d}", q),
        (f"Then subtract: {m} − {q} = {m - q}.", f"{m}-{q}", m - q),
    ]


def _easy_attempt(rng: random.Random) -> dict | None:
    form = rng.choice(sorted(EASY_FORMS))
    if form == "sub_div_mul":
        c, q, d = rng.randint(2, 9), rng.randint(2, 12), rng.randint(2, 9)
        p = q * d
        nums = [rng.randint(p + 2, p + 8 * q), q * c, c, d]
    elif form == "add_mul_bracket":
        k, b, d = rng.randint(2, 9), rng.randint(2, 6), rng.randint(1, 20)
        nums = [rng.randint(2, (8 - b) * k), b, d + k, d]
    elif form == "bracket_div_mul":
        c, q, d = rng.randint(2, 9), rng.randint(2, 15), rng.randint(2, 8)
        s = q * c
        if s < 4:
            return None
        a = rng.randint(2, s - 2)
        nums = [a, s - a, c, d]
    else:
        a, b, q, d = rng.randint(2, 12), rng.randint(2, 9), rng.randint(2, 12), rng.randint(2, 9)
        nums = [a, b, q * d, d]
    params = {"form": form, "nums": nums}
    if not _easy_ok(params):
        return None
    steps = _easy_steps(form, nums)
    ans = steps[-1][2]
    # distractors: the intermediates, latest first, then the near miss above the answer
    return params if _fair(ans, [steps[1][2], steps[0][2], ans + _near_step(ans)]) else None


def _easy_ok(params: dict) -> bool:
    form, nums = params["form"], params["nums"]
    a, b, c, d = nums
    if form not in EASY_FORMS or not all(1 <= v <= MAX_VALUE for v in nums):
        return False
    exact = {
        "sub_div_mul": b % c == 0,
        "add_mul_bracket": c > d,
        "bracket_div_mul": (a + b) % c == 0,
        "mul_sub_div": c % d == 0,
    }[form]
    if not exact:
        return False
    return all(1 <= v <= MAX_VALUE for _, _, v in _easy_steps(form, nums))


class WholeNumbersEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        return _draw(rng, _easy_attempt)

    def solve(self, params: dict) -> dict:
        form, nums = params["form"], params["nums"]
        a, b, c, d = nums
        steps = _easy_steps(form, nums)
        ans = steps[-1][2]
        inter: dict = {"expression": EASY_FORMS[form].format(a=a, b=b, c=c, d=d)}
        for i, (text, expr, _) in enumerate(steps, start=1):
            inter[f"step{i}"], inter[f"e{i}"] = text, expr
        inter["answer_value"] = ans
        return {"answer": {"type": "integer", "value": ans, "unit": ""}, "intermediates": inter}

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Order-of-operations slips, best first (whole, positive ones survive mcq's filter)."""
        form = params["form"]
        a, b, c, d = (Fraction(v) for v in params["nums"])
        if form == "sub_div_mul":  # a − b ÷ c × d
            return [
                ((a - b) / c * d, "worked left to right, ignoring the order of operations"),
                ((a - b / c) * d, "subtracted before multiplying"),
                (a - b / (c * d), "multiplied before dividing"),
                (b / c * d, "forgot to subtract from the first number"),
            ]
        if form == "add_mul_bracket":  # a + b × (c − d)
            return [
                ((a + b) * (c - d), "added before multiplying"),
                (a + b * c - d, "ignored the brackets"),
                ((a + b) * c - d, "ignored the brackets and worked left to right"),
                (b * (c - d), "forgot to add the first number"),
            ]
        if form == "bracket_div_mul":  # (a + b) ÷ c × d
            return [
                ((a + b) / (c * d), "multiplied before dividing"),
                (a + b / c * d, "ignored the brackets"),
                ((a + b) * c / d, "swapped the division and the multiplication"),
                ((a + b) / c, "forgot to multiply by the last number"),
                ((a + b) / c + d, "added the last number instead of multiplying"),
                ((a + b) * d, "forgot to divide"),
            ]
        # a × b − c ÷ d
        return [
            ((a * b - c) / d, "worked left to right, ignoring the order of operations"),
            (a * (b - c) / d, "subtracted before multiplying"),
            (a * b - c, "forgot to divide"),
            (a * b + c / d, "added instead of subtracting"),
            (a * b - d, "subtracted the divisor instead of the quotient"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        form, (a, b, c, d) = params["form"], params["nums"]
        ok = _easy_ok(params)
        ans = solution["answer"]["value"]
        # the defining relationship, rearranged so no division is needed
        verified = (
            ok
            and {
                "sub_div_mul": (a - ans) * c == b * d,
                "add_mul_bracket": ans - a == b * (c - d),
                "bracket_div_mul": ans * c == (a + b) * d,
                "mul_sub_div": (a * b - ans) * d == c,
            }[form]
        )
        checks = {
            "exact_and_in_range": ok,
            "answer_whole_and_positive": isinstance(ans, int) and 1 <= ans <= MAX_VALUE,
            "answer_verified": bool(verified),
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ medium

# context -> (direction, question, "q × d" step, "left over" step, final step), filled with
# n (the amount to share), d (the size of each group), q, r (quotient, remainder), qd, ans.
MEDIUM_CONTEXTS: dict[str, tuple[str, str, str, str, str]] = {
    "boats": (
        "up",
        "{n} people are going on a boat ride. Each boat can carry {d} people. "
        "What is the least number of boats needed?",
        "{q} boats can carry {q} × {d} = {qd} people.",
        "{n} − {qd} = {r} people are left, so 1 more boat is needed.",
        "Least number of boats = {q} + 1 = {ans}.",
    ),
    "cupcakes": (
        "up",
        "A baker has {n} cupcakes. Each box can hold {d} cupcakes. "
        "What is the least number of boxes needed to pack all the cupcakes?",
        "{q} boxes can hold {q} × {d} = {qd} cupcakes.",
        "{n} − {qd} = {r} cupcakes are left, so 1 more box is needed.",
        "Least number of boxes = {q} + 1 = {ans}.",
    ),
    "rope": (
        "down",
        "A rope {n} m long is cut into pieces. Each piece is {d} m long. "
        "What is the greatest number of pieces that can be cut?",
        "{q} pieces use {q} × {d} = {qd} m of rope.",
        "{n} − {qd} = {r} m is left, which is too short for another piece.",
        "Greatest number of pieces = {ans}.",
    ),
    "pens": (
        "down",
        "Each pen costs ${d}. What is the greatest number of pens that can be bought with ${n}?",
        "{q} pens cost {q} × ${d} = ${qd}.",
        "${n} − ${qd} = ${r} is left, which is not enough for another pen.",
        "Greatest number of pens = {ans}.",
    ),
    "eggs": (
        "down",
        "{n} eggs are packed into trays. Each tray holds {d} eggs. "
        "How many trays can be filled completely?",
        "{q} trays hold {q} × {d} = {qd} eggs.",
        "{n} − {qd} = {r} eggs are left, which is not enough to fill another tray.",
        "Number of trays filled completely = {ans}.",
    ),
}


def _medium_answer(context: str, n: int, d: int) -> int:
    q = n // d
    return q + 1 if MEDIUM_CONTEXTS[context][0] == "up" else q


def _medium_attempt(rng: random.Random) -> dict | None:
    context = rng.choice(sorted(MEDIUM_CONTEXTS))
    d, q = rng.randint(3, 9), rng.randint(4, 20)
    r = rng.randint(2, d - 1)
    n = q * d + r
    ans = _medium_answer(context, n, d)
    # distractors: r and q × d (latest first), then q (round up) or the near miss (round down)
    third = q if MEDIUM_CONTEXTS[context][0] == "up" else ans + _near_step(ans)
    if not _fair(ans, [r, q * d, third]):
        return None
    return {"context": context, "n": n, "d": d}


class WholeNumbersMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        return _draw(rng, _medium_attempt)

    def solve(self, params: dict) -> dict:
        context, n, d = params["context"], params["n"], params["d"]
        q, r = divmod(n, d)
        ans = _medium_answer(context, n, d)
        _, question, made, left, final = MEDIUM_CONTEXTS[context]
        f = {"n": n, "d": d, "q": q, "r": r, "qd": q * d, "ans": ans}
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "s1": question.format(**f),
                "step1": f"{n} ÷ {d} = {q} remainder {r}.",
                "e1": f"({n}-{r})/{d}",
                "step2": made.format(**f),
                "e2": f"{q}*{d}",
                "step3": left.format(**f),
                "e3": f"{n}-{q * d}",
                "step4": final.format(**f),
                "e4": f"{q}+1" if ans == q + 1 else f"{q}",
                "answer_value": ans,
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Misreading the remainder, best first."""
        q, r = divmod(params["n"], params["d"])
        if MEDIUM_CONTEXTS[params["context"]][0] == "up":
            wrong = [
                (q, "rounded down, leaving the remainder out"),
                (r, "gave the remainder"),
                (q + r, "added the remainder to the quotient"),
                (params["d"], "gave the size of each group"),
            ]
        else:
            wrong = [
                (q + 1, "rounded up, although what is left is not enough for one more"),
                (r, "gave the remainder"),
                (q + r, "added the remainder to the quotient"),
                (params["d"], "gave the size of each group"),
            ]
        return wrong

    def validate(self, params: dict, solution: dict) -> dict:
        context, n, d = params["context"], params["n"], params["d"]
        ans = solution["answer"]["value"]
        direction = MEDIUM_CONTEXTS[context][0]
        if direction == "up":  # the least ans with ans × d >= n
            verified = (ans - 1) * d < n <= ans * d
        else:  # the greatest ans with ans × d <= n
            verified = ans * d <= n < (ans + 1) * d
        checks = {
            "remainder_not_zero": n % d != 0,
            "at_least_two_groups": n // d >= 2,
            "answer_verified": verified,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ hard

# Teachers (PSLE style). Cosmetic: the templates avoid pronouns, so any name reads right.
NAME_POOL = [
    "Mrs Tan",
    "Mr Lim",
    "Miss Wong",
    "Mdm Siti",
    "Mr Kumar",
    "Mrs Lee",
    "Mr Ong",
    "Miss Chen",
]
# Curated plural nouns a teacher may swap ``item`` to (W1a item role).
ITEM_POOL = ["sweets", "stickers", "pencils", "stamps", "marbles", "biscuits"]


def _hard_numbers(params: dict) -> dict:
    a, b, left, short = params["a"], params["b"], params["left"], params["short"]
    k, g = b - a, left + short
    p = g // k
    return {"k": k, "g": g, "p": p, "ap": a * p, "ans": a * p + left}


def _hard_attempt(rng: random.Random) -> dict | None:
    a, k, p = rng.randint(2, 9), rng.randint(2, 5), rng.randint(6, 40)
    g = k * p
    left = rng.randint(2, g - 2)
    params = {"a": a, "b": a + k, "left": left, "short": g - left}
    h = _hard_numbers(params)
    if h["ans"] > MAX_VALUE:
        return None
    # distractors: a × pupils (left out the leftovers), the pupils, the excess + shortage
    if not _fair(h["ans"], [h["ap"], p, g]):
        return None
    return params


class WholeNumbersHardSolver:
    ITEM_POOL = ITEM_POOL

    def sample(self, schema: dict, rng: random.Random) -> dict:
        params = _draw(rng, _hard_attempt)
        return {"name": rng.choice(NAME_POOL), "item": rng.choice(ITEM_POOL), **params}

    def solve(self, params: dict) -> dict:
        h = _hard_numbers(params)
        return {
            "answer": {"type": "integer", "value": h["ans"], "unit": ""},
            "intermediates": {
                "k": h["k"],
                "g": h["g"],
                "p": h["p"],
                "ap": h["ap"],
                "answer_value": h["ans"],
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Excess-and-shortage slips, best first."""
        a, b, left, short = params["a"], params["b"], params["left"], params["short"]
        k = b - a
        p = (left + short) // k
        out: list[tuple[int | Fraction, str]] = [
            (a * p, "forgot the leftover"),
            (p, "gave the number of pupils"),
            (b * p, "added the shortage instead of taking it away"),
            (b * p + left, f"gave {b} each and added the leftover"),
            (a * (p + 1) + left, "counted one pupil too many"),
            (left + short, "gave the leftover and the shortage added together"),
        ]
        # used the difference of the leftover and the shortage to find the pupils
        p_wrong = Fraction(abs(left - short), k)
        if p_wrong:
            out.append((a * p_wrong + left, "subtracted the shortage from the leftover"))
        out.append((a * p - short, "took away the shortage instead of adding the leftover"))
        return out

    def validate(self, params: dict, solution: dict) -> dict:
        a, b, left, short = params["a"], params["b"], params["left"], params["short"]
        ans = solution["answer"]["value"]
        k = b - a
        p = (left + short) // k if k > 0 else 0
        checks = {
            "shares_differ": k > 0,
            "whole_number_of_pupils": k > 0 and (left + short) % k == 0 and p >= 2,
            "excess_condition": ans == a * p + left,
            "shortage_condition": ans == b * p - short,
            "answer_in_range": 1 <= ans <= MAX_VALUE,
        }
        return {"ok": all(checks.values()), "checks": checks}


register("whole_numbers_easy", WholeNumbersEasySolver())
register("whole_numbers_medium", WholeNumbersMediumSolver())
register("whole_numbers_hard", WholeNumbersHardSolver())
