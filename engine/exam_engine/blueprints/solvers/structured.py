"""Solvers for the P8c multi-part (Paper 2 Section B) blueprints.

Each blueprint is a shared stem with parts (a) and (b), where (b) builds on (a)'s
answer. ``solve`` returns ``"answers"`` (one per part, in YAML ``parts`` order) instead
of the single-part ``"answer"``; :func:`exam_engine.canonical.assemble` pairs each with
its part's marks, marking scheme and steps.

* ``ratio_structured``  (5 marks) — A:B = p:q and A has n more: (a) the total;
  (b) after A gives some to B the ratio is r:s — how many did A give? (The total is
  unchanged, so (b) needs (a).)
* ``speed_structured``  (4 marks) — out at v1 km/h for t1 h, back at v2 km/h (whole or
  half hours back, ~100 trips):
  (a) the distance; (b) the average speed for the whole (round) journey.
* ``volume_structured`` (5 marks) — tank A with water to a depth: (a) the litres of
  water; (b) all of it poured into an empty tank B — the height of the water there.

Every quantity is a whole number by construction (ADR-0014).
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from ..registry import register
from .ratio_hard import NAME_POOL
from .volume import litre_step

# Plural countable items (cosmetic ``item`` role). ``a``-article rule is irrelevant for
# plurals, but the pool still avoids leading vowels like the other item pools.
ITEM_POOL = ["stickers", "marbles", "stamps", "beads", "cards", "pencils"]


def _lcm(x: int, y: int) -> int:
    return x * y // gcd(x, y)


# --------------------------------------------------------------------------- ratio


_RATIO_TOTAL_MAX = 600


class RatioStructuredSolver:
    ITEM_POOL = ITEM_POOL

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            p, q = rng.randint(2, 7), rng.randint(1, 6)
            r, s = rng.randint(1, 7), rng.randint(1, 7)
            if p <= q or gcd(p, q) != 1 or r == s or gcd(r, s) != 1:
                continue
            if p + q > 10 or r + s > 10:
                continue
            if r * (p + q) >= p * (r + s):  # A must end with a smaller share (A gives)
                continue
            units = _lcm(p + q, r + s)
            w = rng.randint(1, 12)
            total = units * w
            if total > _RATIO_TOTAL_MAX or total < 20:
                continue
            u1 = total // (p + q)
            return {
                "names": rng.sample(NAME_POOL, 2),
                "item": rng.choice(ITEM_POOL),
                "ratio_before": [p, q],
                "more": (p - q) * u1,
                "ratio_after": [r, s],
            }

    def solve(self, params: dict) -> dict:
        p, q = params["ratio_before"]
        r, s = params["ratio_after"]
        more = params["more"]
        u1 = more // (p - q)
        total = (p + q) * u1
        u2 = total // (r + s)
        a_before = p * u1
        a_after = r * u2
        given = a_before - a_after
        # No unit: the items are a cosmetic noun outside the controlled unit vocabulary.
        return {
            "answers": [
                {"type": "integer", "value": total},
                {"type": "integer", "value": given},
            ],
            "intermediates": {
                "diff_units": p - q,
                "diff_units_text": "1 unit" if p - q == 1 else f"{p - q} units",
                # One unit of difference IS the value of one unit: say it once, not twice.
                "diff_tail": "" if p - q == 1 else f", so {p - q} units = {more}",
                "unit_line": (
                    f"So 1 unit = {more}."
                    if p - q == 1
                    else f"1 unit = {more} ÷ {p - q} = {u1}."
                ),
                "u1": u1,
                "sum_before": p + q,
                "total": total,
                "sum_after": r + s,
                "u2": u2,
                "a_before": a_before,
                "a_after": a_after,
                "given": given,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        p, q = params["ratio_before"]
        r, s = params["ratio_after"]
        more = params["more"]
        inter = solution["intermediates"]
        total, given = (a["value"] for a in solution["answers"])
        checks = {
            "a_has_more": p > q and more > 0,
            "unit_whole": more % (p - q) == 0,
            "total_splits_after": total % (r + s) == 0,
            "a_gives_some": 0 < given < inter["a_before"],
            "within_level": total <= _RATIO_TOTAL_MAX,
            "answers_verified": (
                inter["a_before"] - (total - inter["a_before"]) == more
                and (inter["a_before"] - given) * s == (total - inter["a_before"] + given) * r
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- speed


_SPEED_MIN, _SPEED_MAX = 30, 90  # km/h: realistic road speeds
_TIME_OUT = range(2, 7)  # whole hours out
_TIME_BACK_HALVES = range(2, 17)  # 1 h to 8 h back, in half hours
_DISTANCE_MAX = 480  # km


def _hours(t: Fraction) -> str:
    """``3`` or ``2.5`` (half hours print as a decimal, as in the PSLE answer key)."""
    return str(t.numerator) if t.denominator == 1 else f"{float(t):g}"


def speed_trips() -> list[tuple[int, int, int]]:
    """Every trip ``(v1, t1, v2)`` the blueprint may ask about: out at a whole ``v1`` km/h for
    ``t1`` whole hours, back at a different whole ``v2`` taking whole or half hours, with a
    whole average speed (ADR-0014). Enumerated once so sampling is uniform over trips."""
    out = []
    for t1 in _TIME_OUT:
        for v1 in range(_SPEED_MIN, _SPEED_MAX + 1):
            distance = v1 * t1
            if distance > _DISTANCE_MAX:
                continue
            for halves in _TIME_BACK_HALVES:
                t2 = Fraction(halves, 2)
                v2, avg = distance / t2, 2 * distance / (t1 + t2)
                if t2 == t1 or v2.denominator != 1 or avg.denominator != 1:
                    continue
                if _SPEED_MIN <= v2 <= _SPEED_MAX:
                    out.append((v1, t1, int(v2)))
    return out


_TRIPS = speed_trips()


class SpeedStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        v1, t1, v2 = rng.choice(_TRIPS)
        return {
            "name": rng.choice(NAME_POOL),
            "speed_out": v1,
            "time_out": t1,
            "speed_back": v2,
        }

    def solve(self, params: dict) -> dict:
        v1, t1, v2 = params["speed_out"], params["time_out"], params["speed_back"]
        distance = v1 * t1
        time_back = Fraction(distance, v2)
        total_distance = 2 * distance
        total_time = t1 + time_back
        avg = total_distance / total_time
        return {
            "answers": [
                {"type": "quantity", "value": distance, "unit": "km"},
                {"type": "quantity", "value": int(avg), "unit": "km/h"},
            ],
            "intermediates": {
                "distance": distance,
                "time_back": _hours(time_back),
                "total_distance": total_distance,
                "total_time": _hours(total_time),
                "avg": int(avg),
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        v1, t1, v2 = params["speed_out"], params["time_out"], params["speed_back"]
        distance, avg = (a["value"] for a in solution["answers"])
        time_back = Fraction(v1 * t1, v2)
        checks = {
            "return_time_half_hours": (2 * time_back).denominator == 1,
            "speeds_differ": v1 != v2,
            "speeds_in_range": all(_SPEED_MIN <= v <= _SPEED_MAX for v in (v1, v2)),
            "distance_in_range": distance <= _DISTANCE_MAX,
            "avg_whole": avg * (t1 + time_back) == 2 * distance,
            "answers_verified": distance == v1 * t1,
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- volume


# (length, width) bases in cm for tank A (small litre step) and tank B.
_BASES_A = [(20, 25), (20, 40), (25, 40), (40, 50), (30, 50), (50, 20)]
# No tank B base of 1000 cm²: there the height in cm would just repeat the litres from (a).
_BASES_B = [(20, 15), (20, 20), (25, 20), (30, 20), (30, 25), (40, 20), (40, 30), (50, 30)]
_HEIGHT_MAX = 60


class VolumeStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            length, width = rng.choice(_BASES_A)
            step = litre_step(length, width)
            depth = step * rng.randint(1, 20)
            height = 5 * (depth // 5 + rng.randint(1, 3))  # a round height above the water
            if depth < 5 or height > _HEIGHT_MAX:
                continue
            length_b, width_b = rng.choice(_BASES_B)
            volume = length * width * depth
            if volume % (length_b * width_b):
                continue
            level_b = volume // (length_b * width_b)
            height_b = 5 * (level_b // 5 + rng.randint(1, 3))
            if level_b < 5 or level_b == depth or height_b > _HEIGHT_MAX:
                continue
            return {
                "length": length,
                "width": width,
                "height": height,
                "depth": depth,
                "length_b": length_b,
                "width_b": width_b,
                "height_b": height_b,
            }

    def solve(self, params: dict) -> dict:
        l, w, d = params["length"], params["width"], params["depth"]  # noqa: E741
        base_b = params["length_b"] * params["width_b"]
        volume = l * w * d
        litres = volume // 1000
        level_b = volume // base_b
        return {
            "answers": [
                {"type": "integer", "value": litres, "unit": "l"},
                {"type": "integer", "value": level_b, "unit": "cm"},
            ],
            "intermediates": {
                "volume": volume,
                "litres": litres,
                "base_b": base_b,
                "level_b": level_b,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        l, w, d = params["length"], params["width"], params["depth"]  # noqa: E741
        base_b = params["length_b"] * params["width_b"]
        litres, level_b = (a["value"] for a in solution["answers"])
        checks = {
            "water_fits_a": 0 < d < params["height"],
            "whole_litres": (l * w * d) % 1000 == 0,
            "whole_level_b": (l * w * d) % base_b == 0,
            "water_fits_b": 0 < level_b < params["height_b"],
            "b_not_a_repeat": base_b != 1000,
            "answers_verified": litres * 1000 == l * w * d and level_b * base_b == l * w * d,
        }
        return {"ok": all(checks.values()), "checks": checks}


register("ratio_structured", RatioStructuredSolver())
register("speed_structured", SpeedStructuredSolver())
register("volume_structured", VolumeStructuredSolver())
