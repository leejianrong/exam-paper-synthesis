"""Solvers for the ``average`` ladder (P8e, EXA-117): average = total ÷ number of items.

* easy   — the average of 3 to 5 whole numbers (test scores, pages read, money saved).
* medium — a missing value given the average of a group (``missing``), or the total from
           an average followed by one more step (``total``: money left after spending).
* hard   — the average changes when someone joins (find the newcomer's mass) or leaves
           (find the new average height of the rest).

The person's ``name`` is cosmetic (W1a): it appears only in the YAML templates, which
interleave it with the number-bearing fragments the solver builds, so ``solve()`` never
reads it. Every answer is a whole number by construction (ADR-0014):

* easy   — the last value is drawn so the total divides by the count;
* medium — ``missing``: the unknown score is drawn first, then the average is the exact
           quotient; ``total``: the spending is a multiple of $5 below the total saved;
* hard   — a newcomer of value ``before + (n + 1) d`` moves the average by exactly ``d``;
           a leaver of value ``before + (n - 1) d`` moves it by exactly ``-d``.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register

# Singapore-appropriate given names (PSLE style, R1.6).
NAME_POOL = [
    "Aisha",
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

# easy template -> (value range, unit). Money is whole dollars.
EASY_TEMPLATES: dict[str, tuple[int, int, str]] = {
    "tests": (8, 20, ""),
    "pages": (10, 40, ""),
    "savings": (2, 15, "$"),
}

_SCORE_MIN, _SCORE_MAX = 5, 20  # medium ``missing``: spelling-test scores
_JOIN_MASS = (25, 60)  # hard ``join``: a child's mass in kg
_LEAVE_HEIGHT = (120, 165)  # hard ``leave``: a child's height in cm


def _money(v: int, unit: str) -> str:
    return f"${v}" if unit == "$" else str(v)


def _listing(values: list[int], unit: str = "") -> str:
    """``14, 16 and 18`` (or ``$5, $6 and $7``)."""
    shown = [_money(v, unit) for v in values]
    return ", ".join(shown[:-1]) + " and " + shown[-1]


def _sum_text(values: list[int], unit: str = "") -> str:
    return " + ".join(_money(v, unit) for v in values)


# ------------------------------------------------------------------ easy


class AverageEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(EASY_TEMPLATES))
        lo, hi, _ = EASY_TEMPLATES[template]
        n = rng.randint(3, 5)
        while True:
            head = [rng.randint(lo, hi) for _ in range(n - 1)]
            last = [v for v in range(lo, hi + 1) if (sum(head) + v) % n == 0]
            values = [*head, rng.choice(last)]
            if len(set(values)) > 1:
                break
        return {"name": rng.choice(NAME_POOL), "values": values, "template": template}

    def solve(self, params: dict) -> dict:
        values, template = params["values"], params["template"]
        unit = EASY_TEMPLATES[template][2]
        n, total = len(values), sum(values)
        ans = total // n
        given = {
            "tests": (
                f" scored {_listing(values)} marks in {n} spelling tests. What was ",
                "'s average score?",
            ),
            "pages": (
                f" read {_listing(values)} pages of a storybook on {n} days. "
                "On average, how many pages did ",
                " read each day?",
            ),
            "savings": (
                f" saved {_listing(values, unit)} in {n} weeks. "
                "What was the average amount of money ",
                " saved each week?",
            ),
        }[template]
        return {
            "answer": {"type": "integer", "value": ans, "unit": unit},
            "intermediates": {
                "s1": given[0],
                "s2": given[1],
                "step1": f"Total = {_sum_text(values, unit)} = {_money(total, unit)}.",
                "step2": f"Average = {_money(total, unit)} ÷ {n} = {_money(ans, unit)}.",
                "answer_value": ans,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), best first."""
        values = params["values"]
        n, total = len(values), sum(values)
        ordered = sorted(values)
        median = Fraction(ordered[(n - 1) // 2] + ordered[n // 2], 2)
        return [
            (total, "the total, not divided by the number of items"),
            (Fraction(total, n - 1), f"divided by {n - 1}, not {n}"),
            (median, "the middle value, not the average"),
            (Fraction(max(values) + min(values), 2), "averaged the largest and smallest only"),
            (Fraction(total, n + 1), f"divided by {n + 1}, not {n}"),
            (Fraction(total - values[-1], n), "left out the last value when adding"),
            (Fraction(total - values[-1], n - 1), "averaged all but the last value"),
            (Fraction(total, 2), "divided by 2, not by the number of items"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        values = params["values"]
        lo, hi, _ = EASY_TEMPLATES[params["template"]]
        ans = solution["answer"]["value"]
        checks = {
            "values_in_range": 3 <= len(values) <= 5 and all(lo <= v <= hi for v in values),
            "not_all_equal": len(set(values)) > 1,
            "whole_number_average": sum(values) % len(values) == 0,
            "answer_verified": ans * len(values) == sum(values),
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ medium


class AverageMediumSolver:
    """``given``: ``missing`` -> the first ``n - 1`` scores; ``total`` -> ``[spent]``."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        if rng.random() < 0.5:
            n = rng.randint(3, 5)
            while True:
                scores = [rng.randint(_SCORE_MIN, _SCORE_MAX) for _ in range(n)]
                if sum(scores) % n == 0 and len(set(scores)) > 1:
                    break
            return {
                "name": name,
                "kind": "missing",
                "n": n,
                "average": sum(scores) // n,
                "given": scores[:-1],
            }
        n = rng.randint(3, 8)
        average = rng.randint(5, 20)
        spent = 5 * rng.randint(1, (n * average - 5) // 5)
        return {"name": name, "kind": "total", "n": n, "average": average, "given": [spent]}

    def solve(self, params: dict) -> dict:
        n, avg, given = params["n"], params["average"], params["given"]
        total = n * avg
        if params["kind"] == "missing":
            ans, unit = total - sum(given), ""
            s = (
                f" took {n} spelling tests.",
                f"'s scores for the first {n - 1} tests were {_listing(given)}. "
                f"The average score for all {n} tests was {avg}. What was",
                "'s score for the last test?",
            )
            step1 = f"Total score for the {n} tests = {n} × {avg} = {total}."
            step2 = (
                f"Score for the last test = {total} − " + " − ".join(map(str, given)) + f" = {ans}."
            )
        else:
            spent = given[0]
            ans, unit = total - spent, "$"
            s = (
                f" saved an average of ${avg} a week for {n} weeks.",
                f" then spent ${spent} on a present. How much money did",
                " have left?",
            )
            step1 = f"Total amount saved = {n} × ${avg} = ${total}."
            step2 = f"Amount left = ${total} − ${spent} = ${ans}."
        return {
            "answer": {"type": "integer", "value": ans, "unit": unit},
            "intermediates": {
                "s1": s[0],
                "s2": s[1],
                "s3": s[2],
                "step1": step1,
                "step2": step2,
                "answer_value": ans,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), best first."""
        n, avg, given = params["n"], params["average"], params["given"]
        total = n * avg
        if params["kind"] == "missing":
            return [
                (avg, "the average, not the missing score"),
                ((n - 1) * avg - sum(given), f"multiplied the average by {n - 1}, not {n}"),
                (Fraction(sum(given), n - 1), "the average of the other scores"),
                (total, "the total score of all the tests"),
                (total - sum(given[1:]), "left out the first score when subtracting"),
            ]
        spent = given[0]
        return [
            (total, "the total saved, without taking away the present"),
            (avg - spent, "took the present away from one week's savings"),
            (total + spent, "added the cost of the present"),
            (Fraction(total - spent, n), f"divided the money left by {n}"),
            ((n - 1) * avg - spent, f"multiplied the average by {n - 1}, not {n}"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        n, avg, given, kind = params["n"], params["average"], params["given"], params["kind"]
        ans = solution["answer"]["value"]
        if kind == "missing":
            full = [*given, ans]
            checks = {
                "shape": 3 <= n <= 5 and len(given) == n - 1,
                "scores_in_range": all(_SCORE_MIN <= v <= _SCORE_MAX for v in full),
                "not_all_equal": len(set(full)) > 1,
                "answer_verified": sum(full) == n * avg,
            }
        else:
            checks = {
                "shape": 3 <= n <= 8 and len(given) == 1,
                "spent_in_range": given[0] % 5 == 0 and 5 <= given[0] < n * avg,
                "answer_verified": ans + given[0] == n * avg and ans > 0,
            }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ hard


class AverageHardSolver:
    """``given``: ``join`` -> the group's new average mass (kg); ``leave`` -> the leaver's
    height (cm). ``n`` is the size of the group *before* the change."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        name = rng.choice(NAME_POOL)
        if rng.random() < 0.5:
            while True:
                n, before, d = (
                    rng.randint(3, 6),
                    rng.randint(30, 45),
                    rng.choice([-3, -2, -1, 1, 2, 3]),
                )
                newcomer = before + (n + 1) * d
                if _JOIN_MASS[0] <= newcomer <= _JOIN_MASS[1]:
                    break
            return {"name": name, "kind": "join", "n": n, "before": before, "given": before + d}
        while True:
            n, before = rng.randint(4, 7), rng.randint(130, 150)
            d = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
            leaver = before + (n - 1) * d
            if _LEAVE_HEIGHT[0] <= leaver <= _LEAVE_HEIGHT[1]:
                break
        return {"name": name, "kind": "leave", "n": n, "before": before, "given": leaver}

    def solve(self, params: dict) -> dict:
        n, before, given = params["n"], params["before"], params["given"]
        total = n * before
        if params["kind"] == "join":
            new_total = (n + 1) * given
            ans, unit = new_total - total, "kg"
            s = (
                f"The average mass of {n} children was {before} kg. After ",
                f" joined them, the average mass of the {n + 1} children became {given} kg. "
                "What is ",
                "'s mass?",
            )
            steps = (
                f"Total mass of the {n} children = {n} × {before} = {total} kg.",
                f"Total mass of the {n + 1} children = {n + 1} × {given} = {new_total} kg.",
                f"Mass of the child who joined = {new_total} − {total} = {ans} kg.",
            )
        else:
            rest = total - given
            ans, unit = rest // (n - 1), "cm"
            s = (
                f"The average height of {n} children in a group is {before} cm. One of them, ",
                f", is {given} cm tall. When ",
                f" leaves the group, what is the average height of the remaining {n - 1} children?",
            )
            steps = (
                f"Total height of the {n} children = {n} × {before} = {total} cm.",
                f"Total height of the remaining {n - 1} children = {total} − {given} = {rest} cm.",
                f"New average height = {rest} ÷ {n - 1} = {ans} cm.",
            )
        return {
            "answer": {"type": "integer", "value": ans, "unit": unit},
            "intermediates": {
                "s1": s[0],
                "s2": s[1],
                "s3": s[2],
                "step1": steps[0],
                "step2": steps[1],
                "step3": steps[2],
                "answer_value": ans,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (EXA-122), best first."""
        n, before, given = params["n"], params["before"], params["given"]
        if params["kind"] == "join":
            return [
                (given, "the new average, not the newcomer's mass"),
                (before, "the old average"),
                ((n + 1) * given, "the total mass of the group, not the newcomer's"),
                (n * (given - before), f"used {n} children for both totals"),
                ((n + 1) * (given - before), f"used {n + 1} children for both totals"),
            ]
        rest = n * before - given
        return [
            (Fraction(rest, n), f"divided by {n}, not {n - 1}"),
            (before, "the old average"),
            (2 * before - given, "took the whole difference off the average"),
            (rest, "the total height, not divided"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        n, before, given, kind = params["n"], params["before"], params["given"], params["kind"]
        ans = solution["answer"]["value"]
        if kind == "join":
            checks = {
                "group_size": 3 <= n <= 6,
                "average_changes": given != before,
                "newcomer_realistic": _JOIN_MASS[0] <= ans <= _JOIN_MASS[1],
                "answer_verified": n * before + ans == (n + 1) * given,
            }
        else:
            checks = {
                "group_size": 4 <= n <= 7,
                "leaver_realistic": _LEAVE_HEIGHT[0] <= given <= _LEAVE_HEIGHT[1],
                "whole_number_average": (n * before - given) % (n - 1) == 0,
                "average_changes": given != before,
                "answer_verified": n * before - given == (n - 1) * ans,
            }
        return {"ok": all(checks.values()), "checks": checks}


register("average_easy", AverageEasySolver())
register("average_medium", AverageMediumSolver())
register("average_hard", AverageHardSolver())
