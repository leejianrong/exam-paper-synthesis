"""Solvers for the P5 multi-part blueprints (EXA-117): Paper 2 Section B questions a P5 paper
can use (every other multi-part blueprint is P6), each worth 4 marks, on three topics a P5
Section B otherwise barely touches.

* ``tap_tank_structured`` (Volume, 4 = 2 + 2) — an empty cuboid tank and a tap at r ℓ a
  minute: (a) how long the tank takes to fill; (b) the water level after t minutes.
* ``savings_structured`` (Money, 4 = 2 + 2) — two children save different sums every week,
  the one who saves less starts with more: (a) one child's money after w weeks; (b) after how
  many weeks they have the same amount.
* ``garden_path_structured`` (Geometry (Area & Perimeter), 4 = 2 + 2) — a path of even width
  round a rectangular garden: (a) the area of the path; (b) the cost of a fence along its
  outer edge.

Every quantity is whole (money in whole cents) by construction (ADR-0014).
"""

from __future__ import annotations

import random

from ..registry import register
from .decimals import money, money_answer, plain, stem_money
from .ratio_hard import NAME_POOL
from .volume import cuboid_spec

# --------------------------------------------------------------------------- tap and tank

_TANK_SIDES = (20, 25, 30, 40, 50, 60, 75, 80)


class TapTankStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            length = rng.choice(_TANK_SIDES)
            width = rng.choice([s for s in _TANK_SIDES if s <= length])
            params = {
                "length": length,
                "width": width,
                "height": 5 * rng.randint(4, 12),
                "rate": rng.randint(2, 12),
                "minutes": rng.randint(1, 30),
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        l, w, h = params["length"], params["width"], params["height"]  # noqa: E741
        rate, minutes = params["rate"], params["minutes"]
        volume = l * w * h
        capacity = volume // 1000
        fill_time = capacity // rate
        poured = minutes * rate
        base = l * w
        level = poured * 1000 // base
        return {
            "answers": [
                {"type": "integer", "value": fill_time, "unit": "min"},
                {"type": "integer", "value": level, "unit": "cm"},
            ],
            "intermediates": {
                "volume": volume,
                "capacity": capacity,
                "fill_time": fill_time,
                "poured": poured,
                "poured_cm3": poured * 1000,
                "base": base,
                "level": level,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        l, w, h = params["length"], params["width"], params["height"]  # noqa: E741
        rate, minutes = params["rate"], params["minutes"]
        fill_time, level = (a["value"] for a in solution["answers"])
        checks = {
            "whole_litres": (l * w * h) % 1000 == 0,
            "whole_minutes": (l * w * h) % (1000 * rate) == 0,
            "fill_time_sized": 4 <= fill_time <= 40,
            "tap_stops_early": 0 < minutes < fill_time,
            "whole_level": (minutes * rate * 1000) % (l * w) == 0,
            "level_readable": 5 <= level < h,
            "answers_verified": fill_time * rate * 1000 == l * w * h
            and level * l * w == minutes * rate * 1000,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return cuboid_spec(params["length"], params["width"], params["height"])


# --------------------------------------------------------------------------- savings


class SavingsStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            slow = 10 * rng.randint(10, 60)  # cents a week
            gap = 10 * rng.randint(4, 30)  # how much more the other saves a week
            meet = rng.randint(4, 16)
            behind = 50 * rng.randint(4, 60)
            params = {
                "names": rng.sample(NAME_POOL, 2),
                "save": [slow, slow + gap],
                "start": [behind + gap * meet, behind],
                "weeks": rng.randint(3, 10),
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        (save_a, save_b), (start_a, start_b) = params["save"], params["start"]
        weeks = params["weeks"]
        saved_a = weeks * save_a
        after = start_a + saved_a
        diff_start = start_a - start_b
        diff_week = save_b - save_a
        meet = diff_start // diff_week
        return {
            "answers": [money_answer(after), {"type": "integer", "value": meet}],
            "intermediates": {
                "save_a_text": stem_money(save_a),
                "save_b_text": stem_money(save_b),
                "start_a_text": stem_money(start_a),
                "start_b_text": stem_money(start_b),
                "save_a_money": stem_money(save_a),
                "save_b_money": stem_money(save_b),
                "start_a_money": stem_money(start_a),
                "start_b_money": stem_money(start_b),
                "saved_a_money": stem_money(saved_a),
                "after_money": money(after),
                "diff_start_money": stem_money(diff_start),
                "diff_week_money": stem_money(diff_week),
                "save_a_plain": plain(save_a),
                "save_b_plain": plain(save_b),
                "start_a_plain": plain(start_a),
                "start_b_plain": plain(start_b),
                "saved_a_plain": plain(saved_a),
                "diff_start_plain": plain(diff_start),
                "diff_week_plain": plain(diff_week),
                "meet": meet,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        (save_a, save_b), (start_a, start_b) = params["save"], params["start"]
        weeks = params["weeks"]
        after, meet = solution["answers"][0]["value"], solution["answers"][1]["value"]
        checks = {
            "two_children": params["names"][0] != params["names"][1],
            "slower_starts_ahead": save_b > save_a and start_a > start_b > 0,
            "whole_weeks": (start_a - start_b) % (save_b - save_a) == 0,
            "meet_sized": 4 <= meet <= 16,
            "parts_differ": weeks != meet,
            "realistic": start_a <= 15000 and save_b <= 1000,
            "answers_verified": round(after * 100) == start_a + weeks * save_a
            and start_a + meet * save_a == start_b + meet * save_b,
        }
        return {"ok": all(checks.values()), "checks": checks}


# --------------------------------------------------------------------------- garden path


class GardenPathStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            length = rng.randint(8, 30)
            params = {
                "length": length,
                "width": rng.randint(5, length - 2),
                "path": rng.randint(1, 3),
                "price": rng.randint(4, 15),
            }
            if self.validate(params, self.solve(params))["ok"]:
                return params

    def solve(self, params: dict) -> dict:
        length, width, path = params["length"], params["width"], params["path"]
        outer_l, outer_w = length + 2 * path, width + 2 * path
        outer_area = outer_l * outer_w
        garden_area = length * width
        perimeter = 2 * (outer_l + outer_w)
        cost = perimeter * params["price"]
        return {
            "answers": [
                {"type": "integer", "value": outer_area - garden_area, "unit": "m^2"},
                {"type": "quantity", "value": cost, "unit": "$"},
            ],
            "intermediates": {
                "outer_l": outer_l,
                "outer_w": outer_w,
                "outer_area": outer_area,
                "garden_area": garden_area,
                "path_area": outer_area - garden_area,
                "perimeter": perimeter,
                "cost": cost,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        length, width, path = params["length"], params["width"], params["path"]
        area, cost = (a["value"] for a in solution["answers"])
        checks = {
            "a_real_rectangle": length > width >= 5,
            "path_narrow": 1 <= path <= 3 and 2 * path < width,
            "realistic": cost <= 2000,
            "answers_verified": area == 2 * path * (length + width + 2 * path)
            and cost == 2 * (length + width + 4 * path) * params["price"],
        }
        return {"ok": all(checks.values()), "checks": checks}


register("tap_tank_structured", TapTankStructuredSolver())
register("savings_structured", SavingsStructuredSolver())
register("garden_path_structured", GardenPathStructuredSolver())
