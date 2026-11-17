"""Solvers for two 1-mark Booklet A measurement blueprints (P8e batch 3, EXA-145).

* ``measurement_conversion`` — a measurement in the larger unit, as a decimal ("Express
  3.45 km in m.") or in compound units ("Express 2 kg 75 g in g."), written in the smaller
  unit: km/m, kg/g, ℓ/mℓ (1 to 1000).
* ``time_duration``          — "A concert started at 10.45 a.m. and ended at 12.20 p.m.
  How many minutes did the concert last?" (12-hour clock, crossing at least one hour).

Neither is on a difficulty ladder (see ``number_sense``): each is one 1-mark skill.

Exact by construction (ADR-0014): a measurement is held as a whole number of the smaller
unit (``whole`` × 1000 + ``part``) and a time as whole minutes after midnight. Litres print
as ℓ / mℓ through :func:`units.printed_unit`; the stored unit codes stay ASCII.

The ``event`` noun (time) is cosmetic (W1a): it appears only in the YAML template.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ...units import printed_unit
from ..base import spread_sides
from ..registry import register
from .decimals import dec

# ------------------------------------------------------------------ conversion

# pair -> (larger unit, smaller unit), 1 larger = 1000 smaller
PAIRS: dict[str, tuple[str, str]] = {"km_m": ("km", "m"), "kg_g": ("kg", "g"), "l_ml": ("l", "ml")}


def _amount(params: dict) -> int:
    """The measurement in the smaller unit."""
    return params["whole"] * 1000 + params["part"]


def _quantity(params: dict) -> str:
    """How the stem prints the measurement: ``3.45 km`` or ``2 kg 75 g``."""
    big, small = (printed_unit(u) for u in PAIRS[params["pair"]])
    if params["form"] == "decimal":
        return f"{dec(Fraction(_amount(params), 1000))} {big}"
    return f"{params['whole']} {big} {params['part']} {small}"


class MeasurementConversionSolver:
    """``pair`` — km_m, kg_g or l_ml; ``form`` — decimal or mixed; ``whole`` — the whole
    number of the larger unit (1-9); ``part`` — the rest, in the smaller unit (1-999)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        pair = rng.choice(sorted(PAIRS))
        form = rng.choice(["decimal", "mixed"])
        whole = rng.randint(1, 9)
        if form == "decimal":
            places = rng.choice([1, 2, 2, 3, 3])
            if places == 1:
                part = 100 * rng.randint(1, 9)
            elif places == 2:
                part = 10 * rng.choice([k for k in range(1, 100) if k % 10])
            else:
                part = rng.choice([k for k in range(1, 1000) if k % 10])
        else:  # mostly a part below 100, where the zero in 2075 is the trap
            part = 5 * rng.randint(1, 19) if rng.random() < 0.7 else 5 * rng.randint(21, 199)
        return {"pair": pair, "form": form, "whole": whole, "part": part}

    @staticmethod
    def _ok(params: dict) -> bool:
        return 1 <= params["whole"] <= 9 and 1 <= params["part"] <= 999

    def solve(self, params: dict) -> dict:
        big, small = (printed_unit(u) for u in PAIRS[params["pair"]])
        ans = _amount(params)
        if params["form"] == "decimal":
            x = dec(Fraction(ans, 1000))
            step = f"1 {big} = 1000 {small}, so {x} {big} = {x} × 1000 {small} = {ans} {small}."
            expr = f"{x}*1000"
        else:
            w, p = params["whole"], params["part"]
            step = (
                f"{w} {big} = {w * 1000} {small}, so {w} {big} {p} {small} = "
                f"{w * 1000} {small} + {p} {small} = {ans} {small}."
            )
            expr = f"{w}*1000+{p}"
        return {
            "answer": {"type": "integer", "value": ans, "unit": PAIRS[params["pair"]][1]},
            "intermediates": {
                "quantity": _quantity(params),
                "small": small,
                "step1": step,
                "e1": expr,
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Conversion slips, in the smaller unit, best first."""
        big, small = (printed_unit(u) for u in PAIRS[params["pair"]])
        w, p = params["whole"], params["part"]
        ans = _amount(params)
        out: list[tuple[int | Fraction, str]] = []
        if params["form"] == "decimal":
            digits = dec(Fraction(ans, 1000)).split(".")[1]
            out += [
                (Fraction(ans, 10), f"multiplied by 100 instead of 1000 (1 {big} = 100 {small})"),
                (w * 1000 + int(digits), f"read .{digits} {big} as {int(digits)} {small}"),
                (w * 1000, "left out the decimal part"),
                (ans * 10, "multiplied by 10 000 instead of 1000"),
            ]
        else:
            # "2 kg 75 g" written as 2.75 kg: the part read as decimal places
            as_decimal = Fraction(w) + Fraction(p, 10 ** len(str(p)))
            out += [
                (w * 100 + p, f"took 1 {big} as 100 {small}"),
                (as_decimal * 1000, f"wrote {w} {big} {p} {small} as {dec(as_decimal)} {big}"),
                (w * 1000, f"left out the {p} {small}"),
            ]
            if p < 100:  # the missing zero: 2 kg 75 g as 2 kg 750 g
                out.append((w * 1000 + p * 10, f"wrote {p} {small} as {p * 10} {small}"))
            out.append((w + p, f"added {w} and {p}"))
        out.append(((w + 1) * 1000, f"rounded up to {w + 1} {big} before converting"))
        return [(v, why) for v, why in out if v != ans]

    def validate(self, params: dict, solution: dict) -> dict:
        ans = solution["answer"]["value"]
        checks = {
            "params_in_range": self._ok(params),
            "unit_is_the_smaller_one": solution["answer"]["unit"] == PAIRS[params["pair"]][1],
            # converted back: the answer in the larger unit is the measurement asked about
            "answer_verified": Fraction(ans, 1000)
            == params["whole"] + Fraction(params["part"], 1000),
        }
        return {"ok": all(checks.values()), "checks": checks}


# ------------------------------------------------------------------ time

EVENT_POOL = [
    "concert",
    "school play",
    "football match",
    "piano lesson",
    "boat tour",
    "movie",
    "talk",
    "swimming lesson",
    "magic show",
]

_EARLIEST, _LATEST = 7 * 60, 22 * 60 + 55  # 7 a.m. to 10.55 p.m.


def clock(minutes: int) -> str:
    """A time of day on the 12-hour clock as PSLE prints it: ``10.45 a.m.``, ``12.20 p.m.``,
    ``11 a.m.``, ``12 noon``."""
    h, m = divmod(minutes, 60)
    if (h, m) == (12, 0):
        return "12 noon"
    suffix = "a.m." if h < 12 else "p.m."
    h12 = h % 12 or 12
    return f"{h12}.{m:02d} {suffix}" if m else f"{h12} {suffix}"


def _hm(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return " ".join(x for x in (f"{h} h" if h else "", f"{m} min" if m else "") if x)


class TimeDurationSolver:
    """``start`` — minutes after midnight; ``duration`` — whole minutes (a multiple of 5);
    ``event`` — cosmetic."""

    ITEM_POOL = EVENT_POOL

    def sample(self, schema: dict, rng: random.Random) -> dict:
        borrow = rng.random() < 2 / 3  # the end's minutes fewer than the start's
        while True:
            start = 5 * rng.randint(_EARLIEST // 5, _LATEST // 5)
            duration = 5 * rng.randint(5, 34)  # 25 min to 2 h 50 min
            params = {"event": rng.choice(EVENT_POOL), "start": start, "duration": duration}
            if self._ok(params) and ((start + duration) % 60 < start % 60) == borrow:
                return params

    @staticmethod
    def _ok(params: dict) -> bool:
        start, duration = params["start"], params["duration"]
        end = start + duration
        return (
            start % 5 == 0
            and duration % 5 == 0
            and 25 <= duration <= 170
            and start >= _EARLIEST
            and end <= _LATEST
            and start % 60 != 0  # the working goes via the next whole hour
            and end % 60 != 0
            and end // 60 > start // 60  # crosses at least one whole hour
        )

    def solve(self, params: dict) -> dict:
        start, duration = params["start"], params["duration"]
        end = start + duration
        hour = start - start % 60 + 60  # the next whole hour
        first, rest = hour - start, end - hour
        rest_text = f"{_hm(rest)} = {rest} min" if rest >= 60 else f"{rest} min"
        return {
            "answer": {"type": "integer", "value": duration, "unit": "min"},
            "intermediates": {
                "start_text": clock(start),
                "end_text": clock(end),
                "step1": f"From {clock(start)} to {clock(hour)} is {first} min.",
                "e1": f"60-{start % 60}",
                "step2": f"From {clock(hour)} to {clock(end)} is {rest_text}.",
                "e2": f"{rest // 60}*60+{rest % 60}",
                "step3": f"Time taken = {first} min + {rest} min = {duration} min.",
                "e3": f"{first}+{rest}",
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Clock-arithmetic slips, in minutes, best first."""
        start, duration = params["start"], params["duration"]
        end = start + duration
        (h1, m1), (h2, m2) = divmod(start, 60), divmod(end, 60)
        out: list[tuple[int | Fraction, str]] = [
            ((h2 * 100 + m2) - (h1 * 100 + m1), "subtracted the times as if 1 h were 100 min"),
        ]
        if m2 < m1:
            out.append(
                ((h2 - h1) * 60 + (m1 - m2), "took the smaller minutes from the larger minutes")
            )
        out += [
            (duration + 60, "counted one hour too many"),
            (duration - 60, "counted one hour too few"),
            ((h2 - h1) * 60, "counted the whole hours only"),
            (duration - (60 - m1), "left out the minutes up to the next whole hour"),
            (duration - m2, "left out the minutes after the last whole hour"),
        ]
        return [(v, why) for v, why in out if v != duration and v > 0]

    def validate(self, params: dict, solution: dict) -> dict:
        start, duration = params["start"], params["duration"]
        ans = solution["answer"]["value"]
        checks = {
            "params_in_range": self._ok(params),
            # counted forward from the start, the answer lands on the end time
            "answer_verified": clock(start + ans) == clock(start + duration),
        }
        return {"ok": all(checks.values()), "checks": checks}


register("measurement_conversion", MeasurementConversionSolver())
register("time_duration", TimeDurationSolver())
