"""Solvers for the ``rate`` ladder (P8e): work done at a steady rate, and tiered charges.

* easy   — rate × time: "prints 45 pages per minute ... in 8 minutes?"
* medium — the unitary method: "prints 180 pages in 4 minutes ... in 7 minutes?" (``amount``)
           or the inverse ask "... how many minutes to print 315 pages?" (``time``).
* hard   — a tiered charge: a first-hour price, then a price for each additional block
           (half hour in a car park, hour for a bicycle), for a whole number of blocks.

The person's ``name`` is cosmetic (W1a): it appears only in the YAML templates, which
interleave it with the number-bearing fragments the solver builds, so ``solve()`` never
reads it. Exact by construction (ADR-0014):

* easy / medium — the rate is drawn first and every printed amount is ``rate × time``, so
                  the rate (and the inverse-ask time) is a whole number;
* hard          — prices are integer cents and the stay is a whole number of blocks past
                  the first hour; the answer is a 2-dp money amount built from cents.
"""

from __future__ import annotations

import random

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


# context -> wording + the rate range (whole items per time unit). No litres/ml contexts.
CONTEXTS: dict[str, dict] = {
    "printer": {
        "owner": "'s printer",  # the subject reads "{name}'s printer"
        "does": "prints",
        "do": "print",
        "done": "printed",
        "noun": "pages",
        "per": "per minute",
        "time": "minute",
        "unit": "min",
        "rate": (20, 60),
    },
    "baker": {
        "owner": "",
        "does": "bakes",
        "do": "bake",
        "done": "baked",
        "noun": "buns",
        "per": "every hour",
        "time": "hour",
        "unit": "h",
        "rate": (12, 48),
    },
    "cranes": {
        "owner": "",
        "does": "folds",
        "do": "fold",
        "done": "folded",
        "noun": "paper cranes",
        "per": "every hour",
        "time": "hour",
        "unit": "h",
        "rate": (8, 30),
    },
    "typing": {
        "owner": "",
        "does": "types",
        "do": "type",
        "done": "typed",
        "noun": "words",
        "per": "per minute",
        "time": "minute",
        "unit": "min",
        "rate": (25, 60),
    },
}

EASY_TIME = (3, 12)
MEDIUM_T1 = (2, 9)
MEDIUM_T2 = (2, 12)

# hard template -> (block minutes, first-price cents range, extra-price cents range,
#                   price step in cents, duration minutes range)
CHARGES: dict[str, tuple[int, tuple[int, int], tuple[int, int], int, tuple[int, int]]] = {
    "carpark": (30, (150, 400), (50, 200), 10, (90, 300)),
    "bicycle": (60, (300, 800), (150, 500), 50, (120, 360)),
}


def _plural(word: str, n: int) -> str:
    return word if n == 1 else word + "s"


def money(cents: int) -> str:
    """Prices in the question: ``$6`` for whole dollars, else ``$2.50``."""
    return f"${cents // 100}" if cents % 100 == 0 else f"${cents // 100}.{cents % 100:02d}"


def money2(cents: int) -> str:
    """Amounts in the working: always 2 dp (``$6.00``)."""
    return f"${cents // 100}.{cents % 100:02d}"


def _num2(cents: int) -> str:
    """A cents amount as a 2-dp number for an ``expr`` (``6.00``)."""
    return f"{cents // 100}.{cents % 100:02d}"


def duration_text(minutes: int, template: str) -> str:
    """``3 h 30 min`` / ``4 h`` / ``30 min`` (car park), ``4 hours`` (bicycle)."""
    h, m = divmod(minutes, 60)
    if template == "bicycle":
        return f"{h} {_plural('hour', h)}"
    if not h:
        return f"{m} min"
    return f"{h} h {m} min" if m else f"{h} h"


# ------------------------------------------------------------------ easy


class RateEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(CONTEXTS))
        rate = rng.randint(*CONTEXTS[template]["rate"])
        return {
            "name": rng.choice(NAME_POOL),
            "template": template,
            "rate": rate,
            "time": rng.randint(*EASY_TIME),
        }

    def solve(self, params: dict) -> dict:
        c = CONTEXTS[params["template"]]
        rate, t = params["rate"], params["time"]
        ans = rate * t
        times = _plural(c["time"], t)
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "s1": f"{c['owner']} {c['does']} {rate} {c['noun']} {c['per']}. "
                f"How many {c['noun']} does ",
                "s2": f"{c['owner']} {c['do']} in {t} {times}?",
                "step1": f"Number of {c['noun']} {c['done']} in 1 {c['time']} = {rate}.",
                "expr1": f"{rate}",
                "step2": f"Number of {c['noun']} {c['done']} in {t} {times} "
                f"= {rate} × {t} = {ans}.",
                "expr2": f"{rate}*{t}",
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        lo, hi = CONTEXTS[params["template"]]["rate"]
        rate, t = params["rate"], params["time"]
        ans = solution["answer"]["value"]
        checks = {
            "rate_in_range": lo <= rate <= hi,
            "time_in_range": EASY_TIME[0] <= t <= EASY_TIME[1],
            "answer_verified": ans // t == rate and ans % t == 0,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ medium


class RateMediumSolver:
    """``kind``: ``amount`` asks how many items in ``t2``; ``time`` asks how long for
    ``rate × t2`` items. ``t1`` is the time in the given fact (``rate × t1`` items)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(CONTEXTS))
        t1 = rng.randint(*MEDIUM_T1)
        t2 = rng.choice([t for t in range(MEDIUM_T2[0], MEDIUM_T2[1] + 1) if t != t1])
        return {
            "name": rng.choice(NAME_POOL),
            "template": template,
            "kind": rng.choice(["amount", "time"]),
            "rate": rng.randint(*CONTEXTS[template]["rate"]),
            "t1": t1,
            "t2": t2,
        }

    def solve(self, params: dict) -> dict:
        c = CONTEXTS[params["template"]]
        rate, t1, t2 = params["rate"], params["t1"], params["t2"]
        q1, q2 = rate * t1, rate * t2
        s1 = f"{c['owner']} {c['does']} {q1} {c['noun']} in {t1} {_plural(c['time'], t1)}. "
        step1 = f"Number of {c['noun']} {c['done']} in 1 {c['time']} = {q1} ÷ {t1} = {rate}."
        if params["kind"] == "amount":
            ans, unit = q2, ""
            s1 += f"At this rate, how many {c['noun']} can "
            s2 = f"{c['owner']} {c['do']} in {t2} {_plural(c['time'], t2)}?"
            step2 = (
                f"Number of {c['noun']} {c['done']} in {t2} {_plural(c['time'], t2)} "
                f"= {rate} × {t2} = {q2}."
            )
            expr2 = f"{rate}*{t2}"
        else:
            ans, unit = t2, c["unit"]
            s1 += f"At this rate, how many {c['time']}s does "
            s2 = f"{c['owner']} take to {c['do']} {q2} {c['noun']}?"
            step2 = (
                f"Time taken to {c['do']} {q2} {c['noun']} = {q2} ÷ {rate} "
                f"= {t2} {_plural(c['time'], t2)}."
            )
            expr2 = f"{q2}/{rate}"
        return {
            "answer": {"type": "integer", "value": ans, "unit": unit},
            "intermediates": {
                "s1": s1,
                "s2": s2,
                "step1": step1,
                "expr1": f"{q1}/{t1}",
                "step2": step2,
                "expr2": expr2,
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        c = CONTEXTS[params["template"]]
        rate, t1, t2 = params["rate"], params["t1"], params["t2"]
        ans = solution["answer"]["value"]
        q1 = rate * t1
        if params["kind"] == "amount":
            # ans / t2 == q1 / t1, cross-multiplied
            verified = ans * t1 == q1 * t2 and solution["answer"]["unit"] == ""
        else:
            # (rate × t2) items take ans time units: (rate × t2) / ans == q1 / t1
            verified = rate * t2 * t1 == q1 * ans and solution["answer"]["unit"] == c["unit"]
        checks = {
            "rate_in_range": c["rate"][0] <= rate <= c["rate"][1],
            "times_in_range": MEDIUM_T1[0] <= t1 <= MEDIUM_T1[1]
            and MEDIUM_T2[0] <= t2 <= MEDIUM_T2[1],
            "times_differ": t1 != t2,
            "answer_verified": verified,
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ hard


class RateHardSolver:
    """``first``/``extra`` are prices in cents; ``duration`` is the stay in minutes, a
    whole number of blocks past the first hour."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(CHARGES))
        block, first_rng, extra_rng, step, dur_rng = CHARGES[template]
        while True:
            first = step * rng.randint(first_rng[0] // step, first_rng[1] // step)
            extra = step * rng.randint(extra_rng[0] // step, extra_rng[1] // step)
            if extra < first:
                break
        duration = block * rng.randint(dur_rng[0] // block, dur_rng[1] // block)
        return {
            "name": rng.choice(NAME_POOL),
            "template": template,
            "first": first,
            "extra": extra,
            "duration": duration,
        }

    def solve(self, params: dict) -> dict:
        template = params["template"]
        first, extra, duration = params["first"], params["extra"], params["duration"]
        block = CHARGES[template][0]
        blocks = (duration - 60) // block
        extra_total = blocks * extra
        total = first + extra_total
        stay = duration_text(duration, template)
        if template == "carpark":
            s1 = (
                f"A car park charges {money(first)} for the first hour and {money(extra)} "
                "for each additional half hour. "
            )
            s2 = f" parked there for {stay}. How much did "
            after = duration_text(duration - 60, template)
            step1 = (
                f"Time after the first hour = {stay} - 1 h = {after} "
                f"= {blocks} {_plural('half hour', blocks)}."
            )
            expr1 = f"({duration}-60)/30"
            what = _plural("half hour", blocks)
        else:
            s1 = (
                f"A shop rents out bicycles at {money(first)} for the first hour and "
                f"{money(extra)} for each additional hour. "
            )
            s2 = f" rented a bicycle for {stay}. How much did "
            hours = duration // 60
            step1 = f"Number of additional hours = {hours} - 1 = {blocks}."
            expr1 = f"{hours}-1"
            what = _plural("hour", blocks)
        return {
            "answer": {"type": "decimal", "value": total / 100, "dp": 2, "unit": "$"},
            "intermediates": {
                "s1": s1,
                "s2": s2,
                "s3": " pay?",
                "step1": step1,
                "expr1": expr1,
                "step2": f"Charge for the {blocks} additional {what} = {blocks} × "
                f"{money2(extra)} = {money2(extra_total)}.",
                "expr2": f"{blocks}*{_num2(extra)}",
                "step3": f"Total amount paid = {money2(first)} + {money2(extra_total)} "
                f"= {money2(total)}.",
                "expr3": f"{_num2(first)}+{_num2(extra_total)}",
                "answer_value": money2(total),
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        block, first_rng, extra_rng, step, dur_rng = CHARGES[params["template"]]
        first, extra, duration = params["first"], params["extra"], params["duration"]
        answer = solution["answer"]
        cents = round(answer["value"] * 100)
        checks = {
            "prices_in_range": first_rng[0] <= first <= first_rng[1]
            and extra_rng[0] <= extra <= extra_rng[1]
            and first % step == 0
            and extra % step == 0,
            "first_hour_costs_more": extra < first,
            "whole_blocks_past_first_hour": dur_rng[0] <= duration <= dur_rng[1]
            and duration % block == 0
            and duration > 60,
            "exact_cents": abs(answer["value"] * 100 - cents) < 1e-6,
            # the charge less the first hour buys a whole number of extra blocks
            "answer_verified": (cents - first) % extra == 0
            and (cents - first) // extra * block + 60 == duration,
        }
        return {"ok": all(checks.values()), "checks": checks}


register("rate_easy", RateEasySolver())
register("rate_medium", RateMediumSolver())
register("rate_hard", RateHardSolver())
