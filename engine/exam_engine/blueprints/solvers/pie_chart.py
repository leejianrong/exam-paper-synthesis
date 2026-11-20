"""Pie charts with sectors in fractions or percentages (EXA-158), P6, on no ladder.

The pie is drawn from the params: each sector's angle is its share of the whole, and a
``fraction`` pie prints each share as a stacked fraction in lowest terms. One sector of a
fraction pie is left unlabelled; the pupil finds it as the rest of the whole.

* ``pie_fraction``        (1 mark, easy)    — what fraction of the whole is the unlabelled sector.
* ``pie_percent_more``    (2 marks, medium) — a percentage pie and the total: how much more on
  one sector than on another.
* ``pie_fraction_amount`` (3 marks, hard)   — a fraction pie, the amount of one labelled sector:
  the amount of the unlabelled sector (find its fraction, the whole, then its share).

Exact by construction (ADR-0014): a fraction pie is ``parts`` of a common denominator ``den``;
the whole in ``pie_fraction_amount`` is ``den × unit``, so every sector is a whole number of
dollars or minutes; a percentage pie's sectors are multiples of 5 and its total a multiple of
20, so each sector is a whole number of dollars.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..base import spread_sides
from ..registry import register
from .rate import NAME_POOL

Slip = tuple[int | Fraction, str]

# context: (intro, sector labels, "of the ... did {name} spend on", amount unit)
CONTEXTS = {
    "money": (
        "The pie chart shows how {name} spent a sum of money.",
        ["Food", "Transport", "Books", "Toys", "Clothes"],
        "money",
        "$",
    ),
    "time": (
        "The pie chart shows how {name} spent some free time on a Saturday.",
        ["Reading", "Games", "Music", "Sports", "Chores"],
        "time",
        "min",
    ),
}
DENOMINATORS = (6, 8, 10, 12)
_MIN_PART = {6: 1, 8: 1, 10: 2, 12: 2}  # every sector at least 36° (a readable label)


def frac(f: Fraction) -> str:
    """``3/8``: how a fraction prints in the question and the working."""
    return f"{f.numerator}/{f.denominator}"


def fractions_of(params: dict) -> list[Fraction]:
    return [Fraction(p, params["den"]) for p in params["parts"]]


def _unlike(parts: list[int], den: int, hidden: int) -> bool:
    """The labelled fractions have unlike denominators: the pupil must convert to add them."""
    return len({Fraction(p, den).denominator for i, p in enumerate(parts) if i != hidden}) >= 2


def _sample_pie(rng: random.Random) -> tuple[int, list[int], int]:
    """(den, parts, hidden): 3 or 4 readable sectors, the labelled ones in unlike fractions."""
    den = rng.choice(DENOMINATORS)
    while True:
        cuts = sorted(rng.sample(range(1, den), rng.choice((3, 4)) - 1))
        parts = [b - a for a, b in zip([0, *cuts], [*cuts, den], strict=True)]
        hidden = rng.randrange(len(parts))
        if min(parts) >= _MIN_PART[den] and _unlike(parts, den, hidden):
            return den, parts, hidden


def _amount(unit: str, v: int) -> str:
    return f"${v}" if unit == "$" else f"{v} min"


def _rest_step(params: dict) -> str:
    fs, h = fractions_of(params), params["hidden"]
    shown = " − ".join(frac(f) for i, f in enumerate(fs) if i != h)
    label = CONTEXTS[params["context"]][1][h]
    return f"Fraction for {label} = 1 − {shown} = {frac(fs[h])}."


def _rest_expr(params: dict) -> str:
    fs, h = fractions_of(params), params["hidden"]
    return "1" + "".join(f"-{frac(f)}" for i, f in enumerate(fs) if i != h)


def _fraction_spec(params: dict) -> dict:
    labels = CONTEXTS[params["context"]][1]
    return {
        "type": "chart",
        "kind": "pie",
        "value_unit": "fraction",
        "sectors": [
            {"label": labels[i], "value": p, "show_value": i != params["hidden"]}
            for i, p in enumerate(params["parts"])
        ],
    }


def _fraction_checks(params: dict) -> dict[str, bool]:
    parts, den, h = params["parts"], params["den"], params["hidden"]
    return {
        "sectors_fill_the_pie": sum(parts) == den and den in DENOMINATORS,
        "sectors_readable": all(p >= _MIN_PART[den] for p in parts),
        "one_unlabelled_sector": 0 <= h < len(parts),
        "unlike_denominators": 0 <= h < len(parts) and _unlike(parts, den, h),
    }


# --------------------------------------------------------------------------- 1 mark


class PieFractionSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        den, parts, hidden = _sample_pie(rng)
        return {
            "name": rng.choice(NAME_POOL),
            "context": rng.choice(sorted(CONTEXTS)),
            "den": den,
            "parts": parts,
            "hidden": hidden,
        }

    def solve(self, params: dict) -> dict:
        intro, labels, what, _ = CONTEXTS[params["context"]]
        h, name = params["hidden"], params["name"]
        f = Fraction(1) - sum(x for i, x in enumerate(fractions_of(params)) if i != h)
        return {
            "answer": {"type": "fraction", "numerator": f.numerator, "denominator": f.denominator},
            "intermediates": {
                "question_text": (
                    f"{intro.format(name=name)} What fraction of the {what} did {name} "
                    f"spend on {labels[h].lower()}? Give your answer in its simplest form."
                ),
                "step1": _rest_step(params),
                "expr1": _rest_expr(params),
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        fs, h = fractions_of(params), params["hidden"]
        labels = CONTEXTS[params["context"]][1]
        out: list[Slip] = [(1 - fs[h], "the labelled sectors added up, not the rest")]
        for i in ((h + 1) % len(fs), (h - 1) % len(fs)):
            out.append((fs[i], f"read the {labels[i]} sector instead"))
        out.append((Fraction(1, len(fs)), "took every sector to be the same size"))
        out.append(
            (Fraction(params["parts"][h], params["den"] - params["parts"][h]), "part to the rest")
        )
        return out

    def validate(self, params: dict, solution: dict) -> dict:
        a = solution["answer"]
        checks = _fraction_checks(params)
        checks["answer_verified"] = (
            Fraction(a["numerator"], a["denominator"]) == fractions_of(params)[params["hidden"]]
        )
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _fraction_spec(params)


# --------------------------------------------------------------------------- 2 marks


class PiePercentMoreSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        n = rng.choice((4, 5))
        while True:
            cuts = sorted(rng.sample(range(1, 20), n - 1))
            percents = [5 * (b - a) for a, b in zip([0, *cuts], [*cuts, 20], strict=True)]
            if min(percents) >= 10 and len(set(percents)) >= 3:
                break
        while True:
            more, less = rng.sample(range(n), 2)
            if percents[more] > percents[less]:
                break
        return {
            "name": rng.choice(NAME_POOL),
            "total": 20 * rng.randint(6, 30),
            "percents": percents,
            "more": more,
            "less": less,
        }

    def solve(self, params: dict) -> dict:
        labels = CONTEXTS["money"][1]
        p, t, name = params["percents"], params["total"], params["name"]
        x, y = params["more"], params["less"]
        diff = p[x] - p[y]
        ans = diff * t // 100
        return {
            "answer": {"type": "integer", "value": ans, "unit": "$"},
            "intermediates": {
                "question_text": (
                    f"The pie chart shows how {name} spent ${t}. How much more did {name} "
                    f"spend on {labels[x].lower()} than on {labels[y].lower()}?"
                ),
                "step1": f"{labels[x]} − {labels[y]} = {p[x]}% − {p[y]}% = {diff}%.",
                "expr1": f"{p[x]}-{p[y]}",
                "step2": f"{diff}% of ${t} = {diff} ÷ 100 × ${t} = ${ans}.",
                "expr2": f"{diff}/100*{t}",
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        labels = CONTEXTS["money"][1]
        p, t, x, y = params["percents"], params["total"], params["more"], params["less"]
        return [
            (Fraction(p[x] * t, 100), f"the amount spent on {labels[x].lower()} only"),
            (p[x] - p[y], "gave the difference in percent, not in dollars"),
            (Fraction(p[y] * t, 100), f"the amount spent on {labels[y].lower()} only"),
            (Fraction((p[x] + p[y]) * t, 100), "added the two sectors"),
            (Fraction((100 - p[x] + p[y]) * t, 100), "took the difference from 100%"),
            (Fraction((p[x] - p[y] - 5) * t, 100), "misread a sector by 5%"),
            (Fraction((p[x] - p[y] + 5) * t, 100), "misread a sector by 5%"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        p, t, x, y = params["percents"], params["total"], params["more"], params["less"]
        checks = {
            "sums_to_100": sum(p) == 100,
            "multiples_of_5": all(v % 5 == 0 and v >= 10 for v in p),
            "total_multiple_of_20": t % 20 == 0,
            "more_than": x != y and p[x] > p[y],
            "answer_verified": solution["answer"]["value"] * 100 == (p[x] - p[y]) * t,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        labels = CONTEXTS["money"][1]
        return {
            "type": "chart",
            "kind": "pie",
            "value_unit": "%",
            "sectors": [{"label": labels[i], "value": v} for i, v in enumerate(params["percents"])],
        }


# --------------------------------------------------------------------------- 3 marks


class PieFractionAmountSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        context = rng.choice(sorted(CONTEXTS))
        while True:
            den, parts, hidden = _sample_pie(rng)
            # a labelled sector of another size (an equal one would make the answer the given)
            knowns = [i for i, p in enumerate(parts) if p != parts[hidden]]
            if knowns:
                known = rng.choice(knowns)
                break
        top = 300 if context == "money" else 240  # the whole: at most $300 or 4 h
        return {
            "name": rng.choice(NAME_POOL),
            "context": context,
            "den": den,
            "parts": parts,
            "hidden": hidden,
            "known": known,
            "unit": rng.randint(2, top // den),
        }

    def solve(self, params: dict) -> dict:
        intro, labels, what, unit = CONTEXTS[params["context"]]
        h, k, u, name = params["hidden"], params["known"], params["unit"], params["name"]
        fs = fractions_of(params)
        given = params["parts"][k] * u
        whole = params["den"] * u
        ans = params["parts"][h] * u
        return {
            "answer": {"type": "integer", "value": ans, "unit": unit},
            "intermediates": {
                "question_text": (
                    f"{intro.format(name=name)} {name} spent {_amount(unit, given)} on "
                    f"{labels[k].lower()}. How much {what} did {name} spend on "
                    f"{labels[h].lower()}?"
                ),
                "step1": _rest_step(params),
                "expr1": _rest_expr(params),
                "step2": (
                    f"{frac(fs[k])} of the {what} is {_amount(unit, given)}, so the whole = "
                    f"{given} ÷ {frac(fs[k])} = {_amount(unit, whole)}."
                ),
                "expr2": f"{given}/({frac(fs[k])})",
                "step3": (
                    f"{labels[h]} = {frac(fs[h])} × {_amount(unit, whole)} = {_amount(unit, ans)}."
                ),
                "expr3": f"{frac(fs[h])}*{whole}",
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        fs, h, k, u = fractions_of(params), params["hidden"], params["known"], params["unit"]
        given, whole = params["parts"][k] * u, params["den"] * u
        slips: list[Slip] = [
            (whole, "gave the whole, not the unlabelled sector"),
            (fs[k] * given, "multiplied by the fraction instead of dividing"),
            (whole - params["parts"][h] * u, "the labelled sectors together"),
            (given + params["parts"][h] * u, "added the given amount on"),
            (fs[h] * given, "took the fraction of the given amount"),
            (Fraction(given) / fs[h], "divided by the unlabelled sector's fraction"),
            (u, f"stopped at the value of one {frac(Fraction(1, params['den']))} part"),
            (abs(given - params["parts"][h] * u), "the difference between the two sectors"),
        ]
        # every amount in the question is whole dollars or minutes; so is a believable slip
        return [(v, why) for v, why in slips if Fraction(v).denominator == 1]

    def validate(self, params: dict, solution: dict) -> dict:
        fs, h, k = fractions_of(params), params["hidden"], params["known"]
        whole = params["den"] * params["unit"]
        checks = _fraction_checks(params)
        checks["known_is_labelled"] = k != h and 0 <= k < len(fs) and fs[k] != fs[h]
        checks["answer_verified"] = Fraction(solution["answer"]["value"]) == fs[h] * whole
        checks["given_matches_whole"] = fs[k] * whole == params["parts"][k] * params["unit"]
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _fraction_spec(params)


register("pie_fraction", PieFractionSolver())
register("pie_percent_more", PiePercentMoreSolver())
register("pie_fraction_amount", PieFractionAmountSolver())
