"""Solver for ``speed_minutes`` (EXA-154): speed, distance or time with the time in minutes.
The 2-mark medium rung between ``speed_easy`` (distance = speed × whole hours) and
``speed_medium`` (average speed over two legs, 3 marks): the speed is in km/h but the time
is given, or asked for, in minutes, so the pupil must convert before (or after) dividing.

* ``distance`` — "A van travelled at an average speed of 54 km/h for 40 minutes. How far did
  the van travel?"  40 min = 40/60 h, 54 × 40/60 = 36 km.
* ``speed``    — "A van travelled 36 km in 40 minutes. What was its average speed in km/h?"
* ``time``     — "A van travelled 36 km at an average speed of 54 km/h. How many minutes did
  the journey take?"

A time over an hour prints as "1 h 15 min". Exact by construction (ADR-0014): the minutes
are never a whole number of hours, and the speed is drawn so that speed × minutes is a
multiple of 60, which makes the distance a whole number of km.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..registry import register

# vehicle -> km/h range (multiples of 3 keep many minute values usable).
VEHICLES: dict[str, tuple[int, int]] = {
    "bus": (30, 60),
    "lorry": (36, 66),
    "van": (42, 78),
    "car": (48, 90),
    "train": (60, 120),
}
MINUTES = [15, 20, 24, 30, 36, 40, 45, 48, 50, 75, 80, 90, 100, 105]
# Asking for the speed or the time: minutes whose common slips (1 h taken as 100 min, the
# speed divided by the distance) are whole numbers, so the multiple-choice copy can use them.
MINUTES_ASKED = [15, 24, 30, 36, 45, 48, 75, 90]
KINDS = ("distance", "speed", "time")


def minutes_text(m: int) -> str:
    """``40 minutes`` / ``1 h 15 min``."""
    if m < 60:
        return f"{m} minutes"
    h, rest = divmod(m, 60)
    return f"{h} h {rest} min"


def hours_text(h: Fraction) -> str:
    """``2/3`` / ``1 1/4`` (a mixed number over an hour), as a PSLE working writes it."""
    whole, rest = divmod(h.numerator, h.denominator)
    if not whole:
        return f"{rest}/{h.denominator}"
    return f"{whole} {rest}/{h.denominator}" if rest else str(whole)


ASKED = {"distance": "distance in km", "speed": "speed in km/h", "time": "time in minutes"}


def _build(params: dict) -> dict:
    v, kind, s, m = params["vehicle"], params["kind"], params["speed"], params["minutes"]
    d = s * m // 60
    t = minutes_text(m)
    hours = Fraction(m, 60)
    h = hours_text(hours)
    conv = f"{m} min = {m}/60 h = {h} h."
    if m > 60:
        conv = f"{t} = " + conv
    if kind == "distance":
        text = (
            f"A {v} travelled at an average speed of {s} km/h for {t}. How far did the {v} travel?"
        )
        steps = [
            (conv, f"{m}/60"),
            (f"Distance = {s} km/h × {h} h = {d} km.", f"{s}*{m}/60"),
        ]
        answer = {"type": "quantity", "value": d, "unit": "km"}
    elif kind == "speed":
        text = f"A {v} travelled {d} km in {t}. What was its average speed in km/h?"
        steps = [
            (conv, f"{m}/60"),
            (f"Speed = {d} km ÷ {h} h = {s} km/h.", f"{d}*60/{m}"),
        ]
        answer = {"type": "quantity", "value": s, "unit": "km/h"}
    else:
        text = (
            f"A {v} travelled {d} km at an average speed of {s} km/h. "
            f"How many minutes did the journey take?"
        )
        steps = [
            (f"Time = {d} km ÷ {s} km/h = {h} h.", f"{d}/{s}"),
            (f"{h} h = {h} × 60 min = {m} min.", f"{d}*60/{s}"),
        ]
        answer = {"type": "quantity", "value": m, "unit": "min"}
    return {"text": text, "steps": steps, "answer": answer, "distance": d}


class SpeedMinutesSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        vehicle = rng.choice(sorted(VEHICLES))
        kind = rng.choice(KINDS)
        lo, hi = VEHICLES[vehicle]
        while True:
            m = rng.choice(MINUTES if kind == "distance" else MINUTES_ASKED)
            speeds = [
                s for s in range(lo, hi + 1) if s * m % 60 == 0 and (kind != "speed" or s % 3 == 0)
            ]
            if speeds:
                break
        return {
            "vehicle": vehicle,
            "kind": kind,
            "speed": rng.choice(speeds),
            "minutes": m,
        }

    def solve(self, params: dict) -> dict:
        built = _build(params)
        (s1, e1), (s2, e2) = built["steps"]
        return {
            "answer": built["answer"],
            "intermediates": {
                "question_text": built["text"],
                "asked": ASKED[params["kind"]],
                "step1": s1,
                "expr1": e1,
                "step2": s2,
                "expr2": e2,
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers in the answer's own unit (EXA-122), best first."""
        s, m, kind = params["speed"], params["minutes"], params["kind"]
        d = Fraction(s * m, 60)
        # "1 h 15 min" read as 1.15 h (or as 115 min): a real slip with mixed units
        slip_h = Fraction(100 + m - 60, 100) if m > 60 else None
        slip = f"took {minutes_text(m)} as {float(slip_h)} h" if slip_h else ""
        if kind == "distance":
            out = [
                (Fraction(s * m, 100), f"took {m} min as {m}/100 h"),
                (s, "the distance in 1 hour (the speed)"),
                (Fraction(s * 60, m), "divided the speed by the time instead of multiplying"),
            ]
            if slip_h:
                out.insert(0, (s * slip_h, slip))
            return out
        if kind == "speed":
            out = [
                (d * 100 / m, f"took {m} min as {m}/100 h"),
                (d, "took the distance as the speed (as if it took 1 hour)"),
                (d * m / 60, "multiplied by the time instead of dividing"),
                (d / m, "the distance in 1 minute, not in 1 hour"),
            ]
            if slip_h:
                out.insert(0, (d / slip_h, slip))
            return out
        out = [
            (d * 100 / s, "took 1 h as 100 min"),
            (s * 60 / d, "divided the speed by the distance"),
            (d * s / 60, "multiplied the distance by the speed"),
        ]
        if slip_h:
            out.insert(0, (100 + m - 60, f"wrote {minutes_text(m)} as {100 + m - 60} min"))
        return out

    def validate(self, params: dict, solution: dict) -> dict:
        s, m, kind = params["speed"], params["minutes"], params["kind"]
        checks: dict[str, bool] = {}
        checks["not_whole_hours"] = m % 60 != 0
        checks["whole_km"] = s * m % 60 == 0
        d = s * m // 60
        expected = {"distance": d, "speed": s, "time": m}[kind]
        checks["answer_verified"] = solution["answer"]["value"] == expected
        checks["speed_in_range"] = (
            VEHICLES[params["vehicle"]][0] <= s <= VEHICLES[params["vehicle"]][1]
        )
        checks["positive"] = d > 0
        return {"ok": all(checks.values()), "checks": checks}


register("speed_minutes", SpeedMinutesSolver())
