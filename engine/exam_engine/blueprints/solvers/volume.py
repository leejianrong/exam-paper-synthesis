"""Solvers for the ``volume`` ladder (T7): cuboids and water in a tank.

The solid is drawn from the same params the maths uses (``solid`` / ``panels``).

* easy   — volume of a cuboid from its three drawn edges (cm^3).
* medium — a tank part-filled with water: litres still needed to fill it to the brim.
* hard   — displacement: a block is lowered into the tank (before / after panels);
           find the block's volume from the rise in water level (cm^3).

Constraints hold by construction (ADR-0014). Medium: a tank of base area A cm^2 holds
A x h / 1000 litres, a whole number only when h is a multiple of ``1000 / gcd(1000, A)``,
so the empty depth is drawn as such a multiple. Hard: the answer is an integer product.
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from ..base import carry_slips, spread_sides
from ..registry import register

# (length, width) pairs in cm whose base area has a small litre step.
_BASES = [(20, 25), (20, 40), (25, 40), (40, 50), (30, 50), (25, 20), (50, 20)]
_MAX_HEIGHT = 60


def litre_step(length: int, width: int) -> int:
    """Smallest depth (cm) that holds a whole number of litres in this base."""
    return 1000 // gcd(1000, length * width)


def cuboid_spec(length: int, width: int, height: int) -> dict:
    return {
        "type": "solid",
        "kind": "cuboid",
        "dims": {"length": length, "width": width, "height": height},
        "unit": "cm",
    }


def tank_spec(length: int, width: int, height: int, depth: int) -> dict:
    return {
        "type": "solid",
        "kind": "container",
        "dims": {"length": length, "width": width, "height": height},
        "unit": "cm",
        "fill": {"height": depth},
    }


class VolumeEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        return {
            "length": rng.randint(3, 20),
            "width": rng.randint(3, 20),
            "height": rng.randint(3, 20),
            "template": rng.choice(["box", "block"]),
        }

    def solve(self, params: dict) -> dict:
        l, w, h = params["length"], params["width"], params["height"]  # noqa: E741
        ans = l * w * h
        thing = "box" if params["template"] == "box" else "wooden block"
        return {
            "answer": {"type": "integer", "value": ans, "unit": "cm^3"},
            "intermediates": {
                "question_text": (
                    f"A {thing} is a cuboid {l} cm long, {w} cm wide and {h} cm tall. "
                    "Find its volume in cm³."
                ),
                "step1": f"Volume = length × width × height = {l} × {w} × {h}.",
                "step2": f"{l} × {w} × {h} = {ans} cm³.",
                "answer_value": ans,
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong volumes (cm³), best first (EXA-122)."""
        l, w, h = params["length"], params["width"], params["height"]  # noqa: E741
        return [
            (l * w, "the area of the base only"),
            (2 * (l * w + w * h + l * h), "the total area of the faces"),
            (l + w + h, "added the three edges"),
            (4 * (l + w + h), "the total length of the edges"),
            (max(l, w, h) ** 3, f"took every edge as {max(l, w, h)} cm"),
            *carry_slips(l * w, h),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        dims = (params["length"], params["width"], params["height"])
        checks = {
            "dims_in_range": all(3 <= d <= 20 for d in dims),
            "answer_verified": solution["answer"]["value"] == dims[0] * dims[1] * dims[2],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return cuboid_spec(params["length"], params["width"], params["height"])


class VolumeMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        length, width = rng.choice(_BASES)
        step = litre_step(length, width)
        while True:
            depth, empty = step * rng.randint(1, 30), step * rng.randint(1, 30)
            if depth >= 5 and empty >= 5 and depth + empty <= _MAX_HEIGHT:
                break
        return {"length": length, "width": width, "depth": depth, "empty": empty}

    def solve(self, params: dict) -> dict:
        l, w, d, e = params["length"], params["width"], params["depth"], params["empty"]  # noqa: E741
        h = d + e
        ans = l * w * e // 1000
        return {
            "answer": {"type": "integer", "value": ans, "unit": "l"},
            "intermediates": {
                "height": h,
                "question_text": (
                    f"A rectangular tank measures {l} cm by {w} cm by {h} cm. It contains "
                    f"water to a depth of {d} cm. How many more litres of water are needed "
                    "to fill the tank to the brim? (1 ℓ = 1000 cm³)"
                ),
                "step1": f"Empty depth = {h} − {d} = {e} cm.",
                "step2": (f"Volume still needed = {l} × {w} × {e} = {l * w * e} cm³ = {ans} ℓ."),
                "answer_value": ans,
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong answers (litres), best first (EXA-122)."""
        l, w, d, e = params["length"], params["width"], params["depth"], params["empty"]  # noqa: E741
        return [
            (Fraction(l * w * (d + e), 1000), "the capacity of the whole tank"),
            (Fraction(l * w * d, 1000), "the water already in the tank"),
            (Fraction(l * w * e, 100), "divided by 100 instead of 1000"),
            (Fraction(l * w * e, 10000), "divided by 10 000 instead of 1000"),
            (l * w * e, "forgot to convert cm³ to litres"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        l, w, d, e = params["length"], params["width"], params["depth"], params["empty"]  # noqa: E741
        checks = {
            "whole_litres": (l * w * e) % 1000 == 0,
            "fits_the_page": d >= 5 and e >= 5 and d + e <= _MAX_HEIGHT,
            "answer_verified": solution["answer"]["value"] * 1000 == l * w * e,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return tank_spec(
            params["length"], params["width"], params["depth"] + params["empty"], params["depth"]
        )


class VolumeHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        return {
            "length": 5 * rng.randint(4, 10),
            "width": 5 * rng.randint(3, 8),
            "before": rng.randint(8, 30),
            "rise": rng.randint(2, 9),
            "room": rng.randint(3, 10),
        }

    def solve(self, params: dict) -> dict:
        l, w, b, r = params["length"], params["width"], params["before"], params["rise"]  # noqa: E741
        h = b + r + params["room"]
        ans = l * w * r
        return {
            "answer": {"type": "integer", "value": ans, "unit": "cm^3"},
            "intermediates": {
                "height": h,
                "question_text": (
                    f"A rectangular tank is {l} cm long, {w} cm wide and {h} cm tall. "
                    f"It contains water to a depth of {b} cm. A solid metal block is "
                    f"lowered into the tank until it is completely under the water, and "
                    f"the water level rises to {b + r} cm. Find the volume of the block "
                    "in cm³."
                ),
                "step1": f"Rise in water level = {b + r} − {b} = {r} cm.",
                "step2": f"Volume of block = {l} × {w} × {r} = {ans} cm³.",
                "answer_value": ans,
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong block volumes (cm³), best first (EXA-122)."""
        l, w, b, r = params["length"], params["width"], params["before"], params["rise"]  # noqa: E741
        h = b + r + params["room"]
        return [
            (l * w * (b + r), "used the new water level, not the rise"),
            (l * w * b, "used the water level before"),
            (l * w * h, "the capacity of the tank"),
            (l * w, "the area of the base only"),
            (l * r, "left out the width"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        l, w, b, r = params["length"], params["width"], params["before"], params["rise"]  # noqa: E741
        checks = {
            "no_overflow": params["room"] >= 1 and b + r < b + r + params["room"],
            "rise_positive": r >= 1,
            "answer_verified": solution["answer"]["value"] == l * w * r,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        l, w, b, r = params["length"], params["width"], params["before"], params["rise"]  # noqa: E741
        h = b + r + params["room"]
        return {
            "type": "panels",
            "panels": [
                {"title": "Before", "figure": tank_spec(l, w, h, b)},
                {"title": "After", "figure": tank_spec(l, w, h, b + r)},
            ],
        }


register("volume_easy", VolumeEasySolver())
register("volume_medium", VolumeMediumSolver())
register("volume_hard", VolumeHardSolver())
