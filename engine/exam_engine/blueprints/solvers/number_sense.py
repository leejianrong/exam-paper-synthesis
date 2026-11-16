"""Solvers for three 1-mark Booklet A number-sense blueprints (P8e batch 3, EXA-145).

* ``whole_numbers_rounding`` — "Round 7549 to the nearest hundred." (a 4-digit number, to the
  nearest ten, hundred or thousand).
* ``decimals_compare``       — "Which is the smallest of the decimals 0.15, 0.51, 0.105 and
  0.501?" (the same digits in different places, the classic trap).
* ``fractions_compare``      — "Which is the greatest of the fractions 3/4, 5/8, 2/3 and 7/12?"

None of them is on a difficulty ladder: each is one recall-and-apply skill worth 1 mark with no
harder rung of the *same* skill, so "make harder / easier" would only hop to an unrelated
subtype. They exist to give Paper 1 Booklet A its ten distinct 1-mark questions.

Exact by construction (ADR-0014): decimals are held as whole thousandths and fractions as
``(numerator, denominator)`` pairs in lowest terms, and the comparisons run on ``Fraction``.

Each has a ``distractors`` hook (EXA-122). For the two "which is the greatest / smallest"
blueprints the hook offers exactly the other three listed numbers, so a multiple-choice copy's
four options are the four numbers in the question, as on a real paper.
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import lcm

from ..registry import register
from .decimals import dec

# ------------------------------------------------------------------ rounding

PLACE_NAMES = {10: "ten", 100: "hundred", 1000: "thousand"}
PLACE_COLUMNS = {1: "ones", 10: "tens", 100: "hundreds", 1000: "thousands"}


def round_to(n: int, place: int) -> int:
    """Round half up, as primary school does: 7550 to the nearest hundred is 7600."""
    return (n + place // 2) // place * place


def _digit(n: int, column: int) -> int:
    return n // column % 10


class WholeNumbersRoundingSolver:
    """``number`` — a 4-digit whole number, not already a multiple of ``place``;
    ``place`` — 10, 100 or 1000."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            place = rng.choice([10, 100, 1000])
            n = rng.randint(1001, 9999)
            if place >= 100 and rng.random() < 0.5:
                # the double-rounding trap: 7549 -> 7550 -> 7600 (nearest hundred is 7500)
                below = place // 10  # the deciding digit is 4, the one after it 5-9
                n = (
                    n
                    - n % place
                    + 4 * below
                    + rng.randint(5, 9) * (below // 10)
                    + rng.randint(0, below // 10 - 1)
                )
            params = {"number": n, "place": place}
            # prefer numbers with three distinct rounding slips (fair options; not a rule)
            if self._ok(params) and len(self.distractors(params, {})) >= 3:
                return params

    @staticmethod
    def _ok(params: dict) -> bool:
        n, place = params["number"], params["place"]
        # a 4-digit number to the nearest thousand may round to 10000; it still prints whole
        return 1001 <= n <= 9999 and place in PLACE_NAMES and n % place != 0

    def solve(self, params: dict) -> dict:
        n, place = params["number"], params["place"]
        ans = round_to(n, place)
        d, r = _digit(n, place), _digit(n, place // 10)
        col, right = PLACE_COLUMNS[place], PLACE_COLUMNS[place // 10]
        way = "5 or more, so round up" if r >= 5 else "less than 5, so round down"
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "place_name": PLACE_NAMES[place],
                "step1": f"The digit in the {col} place is {d}. The digit to its right, in the "
                f"{right} place, is {r}.",
                "step2": f"{r} is {way}: {n} ≈ {ans}.",
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Rounding slips, best first: the wrong way, one digit at a time from the right, the
        wrong place."""
        n, place = params["number"], params["place"]
        ans = round_to(n, place)
        down = n - n % place
        out: list[tuple[int | Fraction, str]] = []
        stepwise, p = n, 10  # 7549 -> 7550 -> 7600: the named trap, so it comes first
        while p <= place:
            stepwise = round_to(stepwise, p)
            p *= 10
        out.append((stepwise, "rounded one digit at a time, starting from the ones"))
        if ans == down:
            out.append((down + place, "rounded up instead of down"))
        else:
            out.append((down, "rounded down instead of up"))
        for other in sorted(PLACE_NAMES, key=lambda q: abs(len(str(q)) - len(str(place)))):
            if other != place:
                out.append((round_to(n, other), f"rounded to the nearest {PLACE_NAMES[other]}"))
        right = place // 10  # 7146 to the nearest hundred: 7106, only the tens digit made 0
        if right > 1:
            column = PLACE_COLUMNS[right]
            out.append((n - _digit(n, right) * right, f"changed only the {column} digit to 0"))
        seen: set[int | Fraction] = {ans}
        kept = []
        for v, why in out:
            if v not in seen:
                kept.append((v, why))
                seen.add(v)
        return kept

    def validate(self, params: dict, solution: dict) -> dict:
        n, place = params["number"], params["place"]
        ans = solution["answer"]["value"]
        checks = {
            "params_in_range": self._ok(params),
            "answer_is_a_multiple_of_the_place": ans % place == 0,
            # the nearest multiple: within half a place, and a tie goes up
            "answer_verified": 2 * abs(n - ans) < place or (2 * (ans - n) == place),
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ comparing

ORDINALS = ["", "second", "third"]
ASK = ("greatest", "smallest")


def _ranked(values: list[Fraction], ask: str) -> list[Fraction]:
    """Greatest first for ``greatest``, smallest first for ``smallest``."""
    return sorted(values, reverse=ask == "greatest")


def _listing(texts: list[str]) -> str:
    return ", ".join(texts[:-1]) + " and " + texts[-1]


def _unique_pick(values: list[Fraction], key, best) -> Fraction | None:
    """The one value whose ``key`` is ``best`` (max or min) over ``values``, if unique."""
    keys = [key(v) for v in values]
    target = best(keys)
    hits = [v for v, k in zip(values, keys, strict=True) if k == target]
    return hits[0] if len(hits) == 1 else None


def _with_reasons(
    values: list[Fraction], ask: str, traps: list[tuple[Fraction | None, str]]
) -> list[tuple[int | Fraction, str]]:
    """Every listed value except the answer, each once: the named traps first, then the rest
    by rank ("the second greatest")."""
    ranked = _ranked(values, ask)
    answer = ranked[0]
    out: list[tuple[int | Fraction, str]] = []
    seen = {answer}
    for v, why in traps:
        if v is not None and v not in seen:
            out.append((v, why))
            seen.add(v)
    opposite = "smallest" if ask == "greatest" else "greatest"
    for i, v in enumerate(ranked[1:], start=1):
        if v not in seen:
            last = i == len(ranked) - 1
            out.append((v, f"gave the {opposite}" if last else f"the {ORDINALS[i]} {ask}"))
            seen.add(v)
    return out


def _decimal_digits(x: Fraction) -> str:
    """The digits after the point as printed: ``0.105`` -> ``"105"``."""
    return dec(x).split(".")[1]


class DecimalsCompareSolver:
    """``ask`` — greatest or smallest; ``thousandths`` — the four decimals, as whole
    thousandths (``150`` is 0.15), in print order."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            whole = rng.choice([0, 0, 0, 1, 2, 3, 4, 5])
            a, b = rng.sample(range(1, 10), 2)
            family = [
                a * 100 + b * 10,  # 0.ab
                b * 100 + a * 10,  # 0.ba
                a * 100 + b,  # 0.a0b
                b * 100 + a,  # 0.b0a
                a * 100,  # 0.a
                b * 100,  # 0.b
            ]
            picked = [whole * 1000 + t for t in rng.sample(family, 4)]
            params = {"ask": rng.choice(ASK), "thousandths": picked}
            if self._ok(params) and self._trap(params) is not None:
                return params

    @staticmethod
    def _values(params: dict) -> list[Fraction]:
        return [Fraction(t, 1000) for t in params["thousandths"]]

    def _ok(self, params: dict) -> bool:
        values = self._values(params)
        return (
            len(set(values)) == 4
            and all(v.denominator != 1 for v in values)  # every one a real decimal
            and len({int(v) for v in values}) == 1  # one whole-number part
        )

    def _trap(self, params: dict) -> Fraction | None:
        """The pick of a pupil who reads the digits after the point as a whole number
        (0.105 "beats" 0.51), when that is not the answer."""
        values, ask = self._values(params), params["ask"]
        pick = _unique_pick(
            values, lambda v: int(_decimal_digits(v)), max if ask == "greatest" else min
        )
        return pick if pick != _ranked(values, ask)[0] else None

    def solve(self, params: dict) -> dict:
        values, ask = self._values(params), params["ask"]
        ranked = _ranked(values, ask)
        sign = " > " if ask == "greatest" else " < "
        padded = [f"{float(v):.3f}" for v in values]
        return {
            "answer": {"type": "decimal", "value": float(dec(ranked[0])), "dp": None, "unit": ""},
            "intermediates": {
                "ask": ask,
                "listing": _listing([dec(v) for v in values]),
                "step1": f"Write each decimal with 3 decimal places: {', '.join(padded)}.",
                "step2": "Compare the tenths, then the hundredths, then the thousandths: "
                + sign.join(f"{float(v):.3f}" for v in ranked)
                + ".",
                "step3": f"The {ask} is {dec(ranked[0])}.",
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """The other three decimals, each with the slip that picks it."""
        values, ask = self._values(params), params["ask"]
        greatest = ask == "greatest"
        longest = _unique_pick(values, lambda v: len(_decimal_digits(v)), max if greatest else min)
        return _with_reasons(
            values,
            ask,
            [
                (self._trap(params), "read the digits after the decimal point as a whole number"),
                (
                    longest,
                    "took the decimal with the most digits as the greatest"
                    if greatest
                    else "took the decimal with the fewest digits as the smallest",
                ),
            ],
        )

    def validate(self, params: dict, solution: dict) -> dict:
        values = self._values(params)
        ans = Fraction(str(solution["answer"]["value"]))
        checks = {
            "params_in_range": self._ok(params),
            "has_a_trap": self._trap(params) is not None,
            "answer_listed": ans in values,
            "answer_verified": all(
                (ans >= v if params["ask"] == "greatest" else ans <= v) for v in values
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


_FRAC_DENOMS = range(3, 13)
_MAX_LCD = 120


def _tex(f: Fraction) -> str:
    return rf"\(\frac{{{f.numerator}}}{{{f.denominator}}}\)"


def _slash(f: Fraction, denominator: int | None = None) -> str:
    if denominator is None:
        return f"{f.numerator}/{f.denominator}"
    return f"{f.numerator * denominator // f.denominator}/{denominator}"


class FractionsCompareSolver:
    """``ask`` — greatest or smallest; ``fractions`` — four proper fractions in lowest terms,
    with different denominators, as ``[numerator, denominator]`` in print order."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            denoms = rng.sample(list(_FRAC_DENOMS), 4)
            if lcm(*denoms) > _MAX_LCD:
                continue
            fracs = []
            for d in denoms:
                n = rng.choice([k for k in range(1, d) if Fraction(k, d).denominator == d])
                fracs.append([n, d])
            params = {"ask": rng.choice(ASK), "fractions": fracs}
            if self._ok(params) and any(v is not None for v, _ in self._traps(params)):
                return params

    @staticmethod
    def _values(params: dict) -> list[Fraction]:
        return [Fraction(n, d) for n, d in params["fractions"]]

    def _ok(self, params: dict) -> bool:
        fracs, values = params["fractions"], self._values(params)
        return (
            all(0 < n < d and Fraction(n, d).denominator == d for n, d in fracs)
            and len({d for _, d in fracs}) == 4
            and len(set(values)) == 4
            and lcm(*(d for _, d in fracs)) <= _MAX_LCD
        )

    def _traps(self, params: dict) -> list[tuple[Fraction | None, str]]:
        """The picks of two common misreadings, when they are not the answer."""
        values, ask = self._values(params), params["ask"]
        answer = _ranked(values, ask)[0]
        best = max if ask == "greatest" else min
        by_denom = _unique_pick(values, lambda v: v.denominator, best)
        by_numer = _unique_pick(values, lambda v: v.numerator, best)
        return [
            (
                by_denom if by_denom != answer else None,
                f"took the fraction with the {'largest' if ask == 'greatest' else 'smallest'} "
                f"denominator as the {ask}",
            ),
            (by_numer if by_numer != answer else None, "compared the numerators only"),
        ]

    def solve(self, params: dict) -> dict:
        values, ask = self._values(params), params["ask"]
        ranked = _ranked(values, ask)
        lcd = lcm(*(v.denominator for v in values))
        sign = " > " if ask == "greatest" else " < "
        return {
            "answer": {
                "type": "fraction",
                "numerator": ranked[0].numerator,
                "denominator": ranked[0].denominator,
            },
            "intermediates": {
                "ask": ask,
                "listing": _listing([_tex(v) for v in values]),
                "step1": f"Write the fractions with the common denominator {lcd}: "
                + ", ".join(f"{_slash(v)} = {_slash(v, lcd)}" for v in values)
                + ".",
                "step2": "Compare the numerators: "
                + sign.join(_slash(v, lcd) for v in ranked)
                + f". The {ask} is {_slash(ranked[0])}.",
                "answer_expr": _slash(ranked[0]),
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """The other three fractions, each with the slip that picks it."""
        return _with_reasons(self._values(params), params["ask"], self._traps(params))

    def validate(self, params: dict, solution: dict) -> dict:
        values = self._values(params)
        a = solution["answer"]
        ans = Fraction(a["numerator"], a["denominator"])
        checks = {
            "params_in_range": self._ok(params),
            "has_a_trap": any(v is not None for v, _ in self._traps(params)),
            "answer_listed": ans in values,
            # cross-multiplication, not the common denominator the working uses
            "answer_verified": all(
                (
                    a["numerator"] * v.denominator >= v.numerator * a["denominator"]
                    if params["ask"] == "greatest"
                    else a["numerator"] * v.denominator <= v.numerator * a["denominator"]
                )
                for v in values
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


register("whole_numbers_rounding", WholeNumbersRoundingSolver())
register("decimals_compare", DecimalsCompareSolver())
register("fractions_compare", FractionsCompareSolver())
