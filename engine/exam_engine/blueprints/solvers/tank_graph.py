"""The tank line graph (EXA-158), P6, on no ladder: water flows into a tank at different
rates and a line graph shows the volume of water against time.

* ``tank_graph``            (2 marks, medium) — how much water flowed in between two times,
  or the rate (ℓ/min) over one stretch of the graph.
* ``tank_graph_structured`` (4 = 2 + 2) — an empty tank: (a) the rate over the last stretch;
  (b) the tank's capacity is given and water keeps flowing at that rate: how many minutes
  after the start the tank is full.

The graph is drawn from the params (a ``chart`` line over a numeric time axis): its corners sit
on grid intersections (whole minutes, multiples of the volume step), so every value a question
asks about is read exactly off the gridlines. Each stretch flows at a whole number of litres per
minute; one stretch in the middle may be flat (the tap turned off).
"""

from __future__ import annotations

import random
from fractions import Fraction

from ..base import spread_sides
from ..registry import register

Slip = tuple[int | Fraction, str]

VESSELS = ("tank", "container", "barrel")
STEPS = (5, 10, 20)
_MAX_TICKS = 11  # volume gridlines above zero, so the graph stays readable


def _sample_graph(rng: random.Random, *, empty: bool) -> tuple[int, list[int], list[int]]:
    """(step, times, volumes): three stretches, corners on grid points, whole rates."""
    while True:
        step = rng.choice(STEPS)
        durations = [rng.randint(1, 4) for _ in range(3)]
        if not 6 <= sum(durations) <= 12:
            continue
        flat = rng.random() < 0.3  # the middle stretch: tap turned off
        rates = []
        for i, d in enumerate(durations):
            if flat and i == 1:
                rates.append(0)
                continue
            ok = [r for r in range(1, 41) if (r * d) % step == 0 and r * d <= 4 * step]
            rates.append(rng.choice(ok))
        if any(a == b for a, b in zip(rates, rates[1:], strict=False)):
            continue  # each corner is a real change of rate
        v0 = 0 if empty else step * rng.randint(0, 2)
        times, volumes = [0], [v0]
        for d, r in zip(durations, rates, strict=True):
            times.append(times[-1] + d)
            volumes.append(volumes[-1] + r * d)
        if volumes[-1] // step <= _MAX_TICKS - 1:
            return step, times, volumes


def rates_of(times: list[int], volumes: list[int]) -> list[Fraction]:
    return [
        Fraction(volumes[i + 1] - volumes[i], times[i + 1] - times[i])
        for i in range(len(times) - 1)
    ]


def graph_spec(params: dict) -> dict:
    times, volumes, step = params["times"], params["volumes"], params["step"]
    return {
        "type": "chart",
        "kind": "line",
        "x_axis": {"title": "Time (min)", "min": 0, "max": times[-1], "step": 1},
        "y_axis": {
            "title": "Volume of water (ℓ)",
            "min": 0,
            "max": step * (volumes[-1] // step + 1),
            "step": step,
        },
        "series": [
            {
                "name": "Volume of water",
                "points": [list(p) for p in zip(times, volumes, strict=True)],
            }
        ],
    }


def _intro(params: dict, empty: bool) -> str:
    v, times = params["vessel"], params["times"]
    start = f"Water flowed into an empty {v}" if empty else f"Water flowed into a {v}"
    off = " The tap was turned off for a while." if 0 in rates_of(times, params["volumes"]) else ""
    return (
        f"{start} from a tap at different rates.{off} The line graph shows the volume of "
        f"water in the {v} during the first {times[-1]} minutes."
    )


def _graph_checks(params: dict) -> dict[str, bool]:
    times, volumes, step = params["times"], params["volumes"], params["step"]
    rates = rates_of(times, volumes)
    return {
        "starts_at_zero": times[0] == 0,
        "corners_on_gridlines": all(v % step == 0 for v in volumes),
        "time_increasing": all(a < b for a, b in zip(times, times[1:], strict=False)),
        "never_drains": all(r >= 0 for r in rates),
        "whole_rates": all(r.denominator == 1 for r in rates),
        "corners_change_rate": all(a != b for a, b in zip(rates, rates[1:], strict=False)),
        "fits_the_axis": volumes[-1] // step <= _MAX_TICKS - 1,
    }


# --------------------------------------------------------------------------- 2 marks


class TankGraphSolver:
    ITEM_POOL = list(VESSELS)

    def sample(self, schema: dict, rng: random.Random) -> dict:
        step, times, volumes = _sample_graph(rng, empty=False)
        rates = rates_of(times, volumes)
        ask = rng.choice(("between", "rate"))
        if ask == "rate":
            a = rng.choice([i for i, r in enumerate(rates) if r > 0])
            b = a + 1
        else:
            while True:
                a, b = sorted(rng.sample(range(len(times)), 2))
                if (a > 0 or volumes[0] > 0) and volumes[b] > volumes[a]:
                    break
        return {
            "vessel": rng.choice(VESSELS),
            "step": step,
            "times": times,
            "volumes": volumes,
            "ask": ask,
            "a": a,
            "b": b,
        }

    def solve(self, params: dict) -> dict:
        t, v = params["times"], params["volumes"]
        a, b, vessel = params["a"], params["b"], params["vessel"]
        rise, span = v[b] - v[a], t[b] - t[a]
        read = f"At {t[a]} min, there were {v[a]} ℓ of water. At {t[b]} min, there were {v[b]} ℓ."
        if params["ask"] == "rate":
            rate = rise // span
            text = (
                f"At what rate did water flow into the {vessel} from {t[a]} min to {t[b]} min? "
                "Give your answer in litres per minute."
            )
            answer = {"type": "integer", "value": rate, "unit": "l/min"}
            steps = (
                f"{read} {v[b]} − {v[a]} = {rise} ℓ flowed in.",
                f"{v[b]}-{v[a]}",
                f"Rate = {rise} ℓ ÷ {span} min = {rate} ℓ/min.",
                f"{rise}/{span}",
            )
        else:
            text = f"How much water flowed into the {vessel} from {t[a]} min to {t[b]} min?"
            answer = {"type": "integer", "value": rise, "unit": "l"}
            steps = (read, f"{v[b]}", f"{v[b]} − {v[a]} = {rise} ℓ.", f"{v[b]}-{v[a]}")
        return {
            "answer": answer,
            "intermediates": {
                "question_text": f"{_intro(params, False)} {text}",
                "step1": steps[0],
                "expr1": steps[1],
                "step2": steps[2],
                "expr2": steps[3],
            },
        }

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[Slip]:
        t, v, step = params["times"], params["volumes"], params["step"]
        a, b = params["a"], params["b"]
        rise, span = v[b] - v[a], t[b] - t[a]
        if params["ask"] == "rate":
            out: list[Slip] = [
                (rise, "gave the volume that flowed in, not the rate"),
                (Fraction(v[b], t[b]), f"divided the volume at {t[b]} min by {t[b]} min"),
            ]
            for i in (a - 1, a + 1):  # the stretch beside the one asked about
                if 0 <= i < len(t) - 1:
                    out.append((rates_of(t, v)[i], "read the rate of the next stretch"))
            out.append((Fraction(rise + step, span), "misread a point by one gridline"))
            out.append((Fraction(rise - step, span), "misread a point by one gridline"))
            return out
        return [
            (v[b], f"read the volume at {t[b]} min only"),
            (v[a] + v[b], "added the two readings"),
            (rise + step, "misread a point by one gridline"),
            (rise - step, "misread a point by one gridline"),
            (v[a], f"read the volume at {t[a]} min only"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        t, v, a, b = params["times"], params["volumes"], params["a"], params["b"]
        checks = _graph_checks(params)
        checks["times_on_the_graph"] = 0 <= a < b < len(t)
        value = solution["answer"]["value"]
        if params["ask"] == "rate":
            checks["one_stretch"] = b == a + 1 and v[b] > v[a]
            checks["answer_verified"] = value * (t[b] - t[a]) == v[b] - v[a]
        else:
            checks["two_readings"] = a > 0 or v[0] > 0
            checks["answer_verified"] = value == v[b] - v[a] > 0
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return graph_spec(params)


# --------------------------------------------------------------------------- structured


class TankGraphStructuredSolver:
    ITEM_POOL = list(VESSELS)

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            step, times, volumes = _sample_graph(rng, empty=True)
            last = rates_of(times, volumes)[-1]
            if last > 0:
                break
        more = rng.randint(2, 8)
        return {
            "vessel": rng.choice(VESSELS),
            "step": step,
            "times": times,
            "volumes": volumes,
            "capacity": volumes[-1] + int(last) * more,
        }

    def solve(self, params: dict) -> dict:
        t, v, cap = params["times"], params["volumes"], params["capacity"]
        rise, span = v[-1] - v[-2], t[-1] - t[-2]
        rate = rise // span
        left = cap - v[-1]
        more = left // rate
        return {
            "answers": [
                {"type": "integer", "value": rate, "unit": "l/min"},
                {"type": "integer", "value": t[-1] + more, "unit": "min"},
            ],
            "intermediates": {
                "intro": _intro(params, True),
                "t_from": t[-2],
                "t_end": t[-1],
                "v_from": v[-2],
                "v_end": v[-1],
                "rise": rise,
                "span": span,
                "rate": rate,
                "left": left,
                "more": more,
                "full": t[-1] + more,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        t, v, cap = params["times"], params["volumes"], params["capacity"]
        rate, full = (a["value"] for a in solution["answers"])
        checks = _graph_checks(params)
        checks["starts_empty"] = v[0] == 0
        checks["last_stretch_flows"] = v[-1] > v[-2]
        checks["capacity_above_graph"] = cap > v[-1]
        checks["answers_verified"] = (
            rate * (t[-1] - t[-2]) == v[-1] - v[-2] and v[-1] + rate * (full - t[-1]) == cap
        )
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return graph_spec(params)


register("tank_graph", TankGraphSolver())
register("tank_graph_structured", TankGraphStructuredSolver())
