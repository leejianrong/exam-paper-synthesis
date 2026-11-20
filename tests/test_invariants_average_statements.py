"""Independent correctness authority for ``average_statements`` (EXA-158), the True / False /
Not possible to tell table about an average.

Everything is read back out of the *printed* question and statements, never the solver's
params or intermediates. From the printed facts the test builds every way the containers P, Q
and R can be filled (whole numbers, at least one each, with the stated average and, when there
is one, the stated count of S), and evaluates each printed statement in every one of those
worlds:

* true in every world   -> the key must tick "True";
* false in every world  -> "False";
* true in some, false in others -> "Not possible to tell", and the two worlds found are the
  witnesses: both fit the given facts and disagree on the statement.

The working is checked too: each "could hold a, b and c (true) or d, e and f (false)" names
two worlds that fit the facts and do make the statement true and false.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest
from exam_engine import generate
from invariants import single_part_answer

SWEEP = range(1, 301)
COLUMNS = ["True", "False", "Not possible to tell"]

_FACTS = re.compile(
    r"^(\w+) (P, Q and R|P, Q, R and S) each contain some (\w+)\. "
    r"The average number of \3 in the (\d) \w+ is (\d+)\."
    r"(?: \w+ S contains (\d+) \3\.)? For each statement, put a tick in the correct box\.$"
)
_SHARES = re.compile(r"could hold (\d+), (\d+) and (\d+) \w+ \(true\) or (\d+), (\d+) and (\d+)")

World = tuple[int, int, int]


def _facts(text: str) -> tuple[int, int, int]:
    """(how many containers, the average, what S holds or 0) as printed."""
    m = _FACTS.match(text)
    assert m, text
    n, avg = int(m.group(4)), int(m.group(5))
    assert n == (4 if m.group(2).endswith("S") else 3), text
    known = int(m.group(6)) if m.group(6) else 0
    assert (known > 0) == (n == 4), text
    return n, avg, known


def _predicate(statement: str, n: int, known: int) -> Callable[[World], bool]:
    """What the printed statement claims about a world (p, q, r)."""
    if m := re.fullmatch(r"\w+ P, Q and R contain (\d+) \w+ altogether\.", statement):
        x = int(m.group(1))
        return lambda w: w[0] + w[1] + w[2] == x
    if m := re.fullmatch(
        r"At least one of the \w+ P, Q and R contains (\d+) \w+ or more\.", statement
    ):
        x = int(m.group(1))
        return lambda w: any(v >= x for v in w)
    if m := re.fullmatch(r"Each of the \w+ P, Q and R contains fewer than (\d+) \w+\.", statement):
        x = int(m.group(1))
        return lambda w: all(v < x for v in w)
    if m := re.fullmatch(r"\w+ ([PQR]) contains exactly (\d+) \w+\.", statement):
        i, x = "PQR".index(m.group(1)), int(m.group(2))
        return lambda w: w[i] == x
    if re.fullmatch(r"\w+ P, Q and R all contain the same number of \w+\.", statement):
        return lambda w: w[0] == w[1] == w[2]
    m = re.fullmatch(
        r"If another \w+, ([ST]), with (\d+) \w+ is added, the average number of \w+ in the "
        r"(\d+) \w+ is (\d+)\.",
        statement,
    )
    assert m, f"unknown statement: {statement}"
    assert m.group(1) == "PQRST"[n] and int(m.group(3)) == n + 1, statement
    added, y = int(m.group(2)), int(m.group(4))
    # the new average is a statement about all the containers, whatever P, Q and R hold
    return lambda w: (w[0] + w[1] + w[2] + known + added) == y * (n + 1)


def _worlds(n: int, avg: int, known: int) -> list[World]:
    """Every filling of P, Q and R that fits the printed facts."""
    out = []
    for p in range(1, n * avg):
        for q in range(1, n * avg):
            r = n * avg - known - p - q
            if r < 1:
                break
            assert (p + q + r + known) == n * avg  # the stated average holds
            out.append((p, q, r))
    assert out
    return out


def check(obj: dict) -> None:
    answer = single_part_answer(obj)
    part = obj["question"]["parts"][0]
    assert obj["question"]["total_marks"] == 2
    assert answer["type"] == "tick_table" and answer["columns"] == COLUMNS
    assert len(answer["rows"]) == 3
    n, avg, known = _facts(part["text"])
    worlds = _worlds(n, avg, known)
    reasons = [s["text"] for s in part["solution_steps"]][-3:]
    for row, reason in zip(answer["rows"], reasons, strict=True):
        claim = _predicate(row["statement"], n, known)
        yes = next((w for w in worlds if claim(w)), None)
        no = next((w for w in worlds if not claim(w)), None)
        want = "Not possible to tell" if yes and no else "True" if yes else "False"
        assert row["tick"] == want, (row, yes, no)
        assert reason.endswith(f" {want}."), reason
        if want == "Not possible to tell":
            m = _SHARES.search(reason)
            assert m, reason
            shown_yes = tuple(int(g) for g in m.groups()[:3])
            shown_no = tuple(int(g) for g in m.groups()[3:])
            assert shown_yes in worlds and shown_no in worlds, reason
            assert claim(shown_yes) and not claim(shown_no), reason
    ticks = [r["tick"] for r in answer["rows"]]
    assert "Not possible to tell" in ticks and len(set(ticks)) > 1


@pytest.mark.parametrize("seed", SWEEP)
def test_every_tick_is_what_the_given_facts_decide(seed):
    check(generate("average_statements", seed))


def test_the_sweep_ticks_every_column_for_most_kinds():
    """Every column is used, and statements of each wording appear across the sweep."""
    seen: set[tuple[str, str]] = set()
    for seed in range(1, 121):
        for row in generate("average_statements", seed)["question"]["parts"][0]["answer"]["rows"]:
            seen.add((row["statement"].split()[0], row["tick"]))
    assert {t for _, t in seen} == set(COLUMNS)
    assert {w for w, _ in seen} >= {"At", "Each", "If"}
