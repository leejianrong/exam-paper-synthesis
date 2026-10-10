"""Solvers for the ``statistics_chart`` ladder (T7): reading a drawn chart.

The chart is the question: the figure is built from the same params the maths uses,
so the printed chart *is* the data the answer key is derived from.

* easy   — bar chart, read two bars and find how many more (a difference).
* medium — pie chart with one sector's percentage hidden: find it (100 minus the
           others), then take that percentage of the stated total.
* hard   — line chart of five months with the last point not plotted: the stem gives
           the mean of all five, find the missing value (5 x mean minus the four read).

Constraints hold by construction (ADR-0014): every plotted value is a multiple of the
axis step (so it can be read off the gridlines exactly), pie percentages are multiples
of 5 and the total a multiple of 20 (so a percentage of it is a whole number), and the
step is a multiple of 5 (so the mean of five step-multiples is a whole number).
"""

from __future__ import annotations

import random

from ..registry import register

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
_CLASSES = ["5A", "5B", "5C", "5D", "5E"]
_KIDS = ["Ali", "Bala", "Chen", "Dina", "Emma"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May"]

# Bar-chart contexts: (key, intro, categories, x title, y title, "how many more" question).
BAR_CONTEXTS = {
    "books": (
        "The bar graph shows the number of books borrowed from the school library each day.",
        _DAYS,
        "Day",
        "Number of books",
        "How many more books were borrowed on {a} than on {b}?",
    ),
    "cans": (
        "The bar graph shows the number of cans each class collected for recycling.",
        _CLASSES,
        "Class",
        "Number of cans",
        "How many more cans did {a} collect than {b}?",
    ),
    "cones": (
        "The bar graph shows the number of ice-cream cones sold at a stall each day.",
        _DAYS,
        "Day",
        "Number of cones",
        "How many more cones were sold on {a} than on {b}?",
    ),
    "stickers": (
        "The bar graph shows the number of stickers collected by five pupils.",
        _KIDS,
        "Pupil",
        "Number of stickers",
        "How many more stickers did {a} collect than {b}?",
    ),
}

# Pie contexts: (key, intro with {total}, question with {label}, sector labels).
PIE_CONTEXTS = {
    "fruit": (
        "The pie chart shows the favourite fruit of {total} pupils.",
        "How many pupils chose {label}?",
        ["Apple", "Banana", "Orange", "Grape"],
    ),
    "sport": (
        "The pie chart shows the favourite sport of {total} pupils.",
        "How many pupils chose {label}?",
        ["Football", "Swimming", "Badminton", "Netball"],
    ),
    "transport": (
        "The pie chart shows how {total} pupils travel to school.",
        "How many pupils travel to school by {label}?",
        ["bus", "car", "train", "bicycle"],
    ),
}

# Line contexts: (key, thing sold, graph intro, question).
LINE_CONTEXTS = {
    "vases": (
        "vases",
        "The line graph shows the number of vases a shop sold in the first four "
        "months of the year.",
    ),
    "tickets": (
        "tickets",
        "The line graph shows the number of tickets sold for a school play "
        "in the first four months of rehearsals.",
    ),
    "plants": (
        "plants",
        "The line graph shows the number of plants a nursery sold in the "
        "first four months of the year.",
    ),
}

_STEPS = (5, 10, 20, 50)


def bar_spec(ctx: str, values: list[int], step: int) -> dict:
    _, cats, xt, yt, _ = BAR_CONTEXTS[ctx]
    top = step * (max(values) // step + 1)
    return {
        "type": "chart",
        "kind": "bar",
        "x_axis": {"title": xt, "categories": list(cats)},
        "y_axis": {"title": yt, "min": 0, "max": top, "step": step},
        "series": [{"name": yt, "values": list(values)}],
    }


class StatisticsChartEasySolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        ctx = rng.choice(sorted(BAR_CONTEXTS))
        step = rng.choice(_STEPS)
        while True:
            values = [step * rng.randint(1, 8) for _ in range(5)]
            a, b = rng.sample(range(5), 2)
            if values[a] > values[b]:
                break
        return {"context": ctx, "step": step, "values": values, "a": a, "b": b}

    def solve(self, params: dict) -> dict:
        intro, cats, _, _, q = BAR_CONTEXTS[params["context"]]
        v, a, b = params["values"], params["a"], params["b"]
        ans = v[a] - v[b]
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "question_text": f"{intro} {q.format(a=cats[a], b=cats[b])}",
                "step1": f"Read the graph: {cats[a]} is {v[a]} and {cats[b]} is {v[b]}.",
                "step2": f"{v[a]} - {v[b]} = {ans}.",
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        v, step, a, b = params["values"], params["step"], params["a"], params["b"]
        checks = {
            "five_bars": len(v) == 5,
            "readable_on_gridlines": all(x % step == 0 and x > 0 for x in v),
            "a_greater_than_b": a != b and v[a] > v[b],
            "answer_verified": solution["answer"]["value"] == v[a] - v[b],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return bar_spec(params["context"], params["values"], params["step"])


class StatisticsChartMediumSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        ctx = rng.choice(sorted(PIE_CONTEXTS))
        total = 20 * rng.randint(5, 20)
        while True:
            cuts = sorted(rng.sample(range(1, 20), 3))  # 3 cut points -> 4 parts of 5%
            percents = [5 * (hi - lo) for lo, hi in zip([0, *cuts], [*cuts, 20], strict=True)]
            if all(p >= 10 for p in percents):
                break
        return {"context": ctx, "total": total, "percents": percents, "hidden": rng.randrange(4)}

    def solve(self, params: dict) -> dict:
        intro, q, labels = PIE_CONTEXTS[params["context"]]
        p, h, total = params["percents"], params["hidden"], params["total"]
        shown = [x for i, x in enumerate(p) if i != h]
        missing = 100 - sum(shown)
        ans = missing * total // 100
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "question_text": (f"{intro.format(total=total)} {q.format(label=labels[h])}"),
                "step1": f"{labels[h]}: 100% - {' - '.join(f'{x}%' for x in shown)} = {missing}%.",
                "step2": f"{missing}% of {total} = {missing} / 100 x {total} = {ans}.",
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        p, h, total = params["percents"], params["hidden"], params["total"]
        checks = {
            "four_sectors": len(p) == 4 and 0 <= h < 4,
            "sums_to_100": sum(p) == 100,
            "multiples_of_5": all(x % 5 == 0 and x >= 10 for x in p),
            "total_multiple_of_20": total % 20 == 0,
            "answer_verified": solution["answer"]["value"] * 100 == p[h] * total,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        _, _, labels = PIE_CONTEXTS[params["context"]]
        return {
            "type": "chart",
            "kind": "pie",
            "value_unit": "%",
            "sectors": [
                {"label": labels[i], "value": x, "show_value": i != params["hidden"]}
                for i, x in enumerate(params["percents"])
            ],
        }


class StatisticsChartHardSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        ctx = rng.choice(sorted(LINE_CONTEXTS))
        step = rng.choice((10, 20, 50))
        known = [step * rng.randint(2, 9) for _ in range(4)]
        missing = step * rng.randint(2, 9)
        return {"context": ctx, "step": step, "known": known, "mean": (sum(known) + missing) // 5}

    def solve(self, params: dict) -> dict:
        thing, intro = LINE_CONTEXTS[params["context"]]
        known, mean = params["known"], params["mean"]
        ans = 5 * mean - sum(known)
        return {
            "answer": {"type": "integer", "value": ans, "unit": ""},
            "intermediates": {
                "question_text": (
                    f"{intro} The mean number of {thing} sold in the five months from "
                    f"January to May was {mean}. How many {thing} were sold in May?"
                ),
                "step1": f"Total for 5 months = 5 x {mean} = {5 * mean}.",
                "step2": (
                    f"Jan to Apr = {' + '.join(str(x) for x in known)} = {sum(known)}, "
                    f"so May = {5 * mean} - {sum(known)} = {ans}."
                ),
                "answer_value": ans,
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        known, step, mean = params["known"], params["step"], params["mean"]
        ans = solution["answer"]["value"]
        checks = {
            "four_known": len(known) == 4,
            "readable_on_gridlines": all(x % step == 0 and x > 0 for x in known),
            "mean_is_whole": (sum(known) + ans) % 5 == 0,
            "answer_positive": ans > 0,
            "mean_verified": (sum(known) + ans) == 5 * mean,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        thing, _ = LINE_CONTEXTS[params["context"]]
        step, known = params["step"], params["known"]
        return {
            "type": "chart",
            "kind": "line",
            "x_axis": {"title": "Month", "categories": list(_MONTHS)},
            "y_axis": {
                "title": f"Number of {thing}",
                "min": 0,
                "max": step * (max(known) // step + 1),
                "step": step,
            },
            "series": [{"name": f"Number of {thing}", "values": [*known, None]}],
        }


register("statistics_chart_easy", StatisticsChartEasySolver())
register("statistics_chart_medium", StatisticsChartMediumSolver())
register("statistics_chart_hard", StatisticsChartHardSolver())
