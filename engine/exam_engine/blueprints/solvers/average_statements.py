"""``average_statements`` (EXA-158): a True / False / Not possible to tell table about an
average.

Jars P, Q and R (and sometimes S, whose count is given) each hold a whole number of sweets, at
least one. Only the average is given, so the pupil knows the total in P, Q and R but not how it
is shared. Each statement is decided from that total ``t`` alone:

* ``total``       "P, Q and R contain x altogether": True iff x = t.
* ``at_least``    "at least one of them contains x or more": the fullest jar holds at least
                  ⌈t/3⌉ (shared as evenly as possible) and at most t − 2 (the others hold 1
                  each), so True when x ≤ ⌈t/3⌉, False when x > t − 2, else not possible to tell.
* ``all_fewer``   "each of them contains fewer than x": True when x > t − 2, False when
                  x ≤ ⌈t/3⌉, else not possible to tell.
* ``exact``       "jar Q contains exactly x": one jar can hold anything from 1 to t − 2, so
                  False outside that, else not possible to tell (never True).
* ``equal``       "all contain the same number": False when t is not a multiple of 3, else
                  not possible to tell (never True).
* ``new_average`` "if another jar with e is added, the average is y": determined by the total
                  of all the jars, so True or False.

"Not possible to tell" is shown in the working by two ways of filling the jars that fit the
given facts and disagree on the statement.
"""

from __future__ import annotations

import random

from ...tick_table import COLUMNS, FALSE, NOT_POSSIBLE, TRUE
from ..registry import register

# context -> (container, containers, item, one item)
CONTEXTS: dict[str, tuple[str, str, str, str]] = {
    "jars": ("jar", "jars", "sweets", "sweet"),
    "boxes": ("box", "boxes", "pens", "pen"),
    "bags": ("bag", "bags", "marbles", "marble"),
    "tins": ("tin", "tins", "biscuits", "biscuit"),
}
KINDS = ("total", "at_least", "all_fewer", "exact", "equal", "new_average")
ORDINALS = ("1st", "2nd", "3rd")
_AVERAGE = (12, 30)


def _ceil3(t: int) -> int:
    return -(-t // 3)


def _free_total(params: dict) -> int:
    """The sweets in jars P, Q and R together."""
    return params["count"] * params["average"] - (params["known"] or 0)


def _possible(kind: str, t: int) -> tuple[str, ...]:
    """The ticks a statement of ``kind`` can have when P, Q and R hold ``t`` together."""
    return {
        "total": (TRUE, FALSE),
        "at_least": (TRUE, FALSE, NOT_POSSIBLE),
        "all_fewer": (TRUE, FALSE, NOT_POSSIBLE),
        "exact": (FALSE, NOT_POSSIBLE),
        "equal": (FALSE,) if t % 3 else (NOT_POSSIBLE,),
        "new_average": (TRUE, FALSE),
    }[kind]


def _new_average(params: dict, added: int) -> tuple[int, int]:
    """(total of all the jars with the added one, how many jars then)."""
    n = params["count"]
    return n * params["average"] + added, n + 1


def _row(rng: random.Random, params: dict, kind: str, tick: str) -> dict:
    """A statement of ``kind`` whose tick is ``tick``."""
    t = _free_total(params)
    lo, hi = _ceil3(t), t - 2
    if kind == "total":
        slip = 4 * params["average"] if params["count"] == 4 else params["average"] + 3
        return {"kind": kind, "x": t if tick == TRUE else slip}
    # Each range runs up to the boundary where the tick changes, so the sweep tries both sides.
    below = rng.randint(max(2, lo - 5), lo)  # some container holds this many or more
    above = rng.choice((t - 1, t))  # no container can hold this many
    unsure = rng.choice((lo + 1, hi, rng.randint(lo + 1, min(hi, lo + params["average"]))))
    if kind == "at_least":
        x = {TRUE: below, FALSE: above, NOT_POSSIBLE: unsure}[tick]
        return {"kind": kind, "x": x}
    if kind == "all_fewer":
        x = {TRUE: above, FALSE: below, NOT_POSSIBLE: unsure}[tick]
        return {"kind": kind, "x": x}
    if kind == "exact":
        x = above if tick == FALSE else rng.choice((unsure, below, hi))
        return {"kind": kind, "x": x, "who": rng.choice("PQR")}
    if kind == "equal":
        return {"kind": kind, "x": 0}
    n = params["count"]
    whole = [
        e
        for e in range(2, 2 * params["average"] + 1)
        if (n * params["average"] + e) % (n + 1) == 0 and e != params["average"]
    ]
    added = rng.choice(whole)
    total, jars = _new_average(params, added)
    right = total // jars
    slips = [(params["average"] + added) / 2, total / n, right + 1]
    wrong = next(int(s) for s in slips if s == int(s) and int(s) != right and s > 0)
    return {"kind": kind, "x": right if tick == TRUE else wrong, "added": added}


class AverageStatementsSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        count = rng.choice((3, 4))
        average = rng.randint(*_AVERAGE)
        known = rng.randint(5, 2 * average) if count == 4 else None
        params: dict = {
            "context": rng.choice(sorted(CONTEXTS)),
            "count": count,
            "average": average,
            "known": known,
        }
        t = _free_total(params)
        while True:
            kinds = rng.sample(KINDS, 3)
            ticks = [rng.choice(_possible(k, t)) for k in kinds]
            if NOT_POSSIBLE in ticks and len(set(ticks)) > 1:
                break
        params["rows"] = [_row(rng, params, k, tick) for k, tick in zip(kinds, ticks, strict=True)]
        return params

    def solve(self, params: dict) -> dict:
        container, containers, item, one = CONTEXTS[params["context"]]
        n, avg, known = params["count"], params["average"], params["known"]
        t = _free_total(params)
        lo, hi = _ceil3(t), t - 2
        label = "P, Q, R and S" if n == 4 else "P, Q and R"
        setup = (
            f"{containers.capitalize()} {label} each contain some {item}. "
            f"The average number of {item} in the {n} {containers} is {avg}."
        )
        steps = [f"Total in the {n} {containers} = {n} × {avg} = {n * avg} {item}."]
        if n == 4:
            setup += f" {container.capitalize()} S contains {known} {item}."
            steps.append(f"Total in {containers} P, Q and R = {n * avg} − {known} = {t} {item}.")
        pqr = f"{containers} P, Q and R"
        new = "S" if n == 3 else "T"

        def count(x: int) -> str:
            return f"{x} {one if x == 1 else item}"

        def shares(values: list[int]) -> str:
            return f"{values[0]}, {values[1]} and {values[2]} {item}"

        even = [t // 3 + (1 if i < t % 3 else 0) for i in range(3)]
        lopsided = [t - 2, 1, 1]
        at_most_one = (
            f"the other two {containers} hold at least 1 {one} each, "
            f"so no {container} holds more than {t} − 2 = {count(hi)}"
        )

        rows, reasons = [], []
        for i, row in enumerate(params["rows"]):
            kind, x = row["kind"], row["x"]
            if kind == "total":
                text = f"{pqr[0].upper()}{pqr[1:]} contain {count(x)} altogether."
                tick = TRUE if x == t else FALSE
                why = f"they contain {count(t)} altogether" + ("" if tick == TRUE else f", not {x}")
            elif kind in ("at_least", "all_fewer"):
                if kind == "at_least":
                    text = f"At least one of the {pqr} contains {count(x)} or more."
                    tick = TRUE if x <= lo else FALSE if x > hi else NOT_POSSIBLE
                    yes, no = lopsided, even
                else:
                    text = f"Each of the {pqr} contains fewer than {count(x)}."
                    tick = TRUE if x > hi else FALSE if x <= lo else NOT_POSSIBLE
                    yes, no = even, lopsided
                if tick == NOT_POSSIBLE:
                    why = f"they could hold {shares(yes)} (true) or {shares(no)} (false)"
                elif (tick == TRUE) == (kind == "at_least"):
                    why = (
                        f"if each held fewer than {count(x)}, they would hold at most "
                        f"3 × {x - 1} = {3 * (x - 1)} altogether, fewer than {t}"
                    )
                else:
                    why = at_most_one
            elif kind == "exact":
                who = row["who"]
                text = f"{container.capitalize()} {who} contains exactly {count(x)}."
                tick = NOT_POSSIBLE if 1 <= x <= hi else FALSE
                if tick == FALSE:
                    why = at_most_one
                else:
                    other = x + 1 if x + 1 <= hi else x - 1
                    worlds = []
                    for v in (x, other):
                        rest = t - v
                        others = [rest - rest // 2, rest // 2]
                        values = others[:]
                        values.insert("PQR".index(who), v)
                        worlds.append(values)
                    why = (
                        f"{pqr} could hold {shares(worlds[0])} (true) "
                        f"or {shares(worlds[1])} (false)"
                    )
            elif kind == "equal":
                text = f"{pqr[0].upper()}{pqr[1:]} all contain the same number of {item}."
                if t % 3:
                    tick = FALSE
                    why = f"{t} ÷ 3 is not a whole number"
                else:
                    tick = NOT_POSSIBLE
                    third = t // 3
                    why = (
                        f"they could hold {shares([third] * 3)} (true) "
                        f"or {shares([third + 1, third - 1, third])} (false)"
                    )
            else:
                added = row["added"]
                total, jars = _new_average(params, added)
                text = (
                    f"If another {container}, {new}, with {count(added)} is added, the average "
                    f"number of {item} in the {jars} {containers} is {x}."
                )
                tick = TRUE if x * jars == total else FALSE
                why = f"({n * avg} + {added}) ÷ {jars} = {total // jars}"
            rows.append({"statement": text, "tick": tick})
            reasons.append(f"{ORDINALS[i]} statement: {why}. {tick}.")
        return {
            "answer": {"type": "tick_table", "columns": list(COLUMNS), "rows": rows},
            "intermediates": {
                "setup": setup,
                "step1": " ".join(steps),
                "reason1": reasons[0],
                "reason2": reasons[1],
                "reason3": reasons[2],
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        t = _free_total(params)
        rows = params["rows"]
        ticks = [r["tick"] for r in solution["answer"]["rows"]]
        checks = {
            "known_iff_four": (params["known"] is not None) == (params["count"] == 4),
            "three_statements": len(rows) == 3,
            "kinds_distinct": len({r["kind"] for r in rows}) == 3,
            "each_container_can_hold_one": t >= 9,
            "some_not_possible": NOT_POSSIBLE in ticks,
            "ticks_vary": len(set(ticks)) > 1,
            "numbers_positive": all(r["x"] >= 2 or r["kind"] == "equal" for r in rows),
            "new_average_whole": all(
                _new_average(params, r["added"])[0] % (params["count"] + 1) == 0
                for r in rows
                if r["kind"] == "new_average"
            ),
        }
        return {"ok": all(checks.values()), "checks": checks}


register("average_statements", AverageStatementsSolver())
