"""EXA-158 (schema 1.15.0) the ``tick_table`` answer: a table of statements, each ticked in one
column ("True", "False", "Not possible to tell"). The statements and columns are question
content (the student paper prints them with empty boxes); each row's tick is the key.
"""

from __future__ import annotations

TRUE, FALSE, NOT_POSSIBLE = "True", "False", "Not possible to tell"
COLUMNS = (TRUE, FALSE, NOT_POSSIBLE)


def check_tick_table_consistency(answer: dict) -> dict[str, bool]:
    """The load gate (the schema already holds the columns to the known ones, unique): every
    row is ticked in one of the table's columns, and no statement is printed twice."""
    columns = answer.get("columns", [])
    rows = answer.get("rows", [])
    statements = [" ".join(r.get("statement", "").split()) for r in rows]
    return {
        "ticks_in_columns": all(r.get("tick") in columns for r in rows),
        "statements_distinct": len(set(statements)) == len(statements),
    }


def summary(answer: dict) -> str:
    """The ticks in row order, as one line ("True, False, Not possible to tell"): the answer
    where a table cannot be drawn (the multiple-choice answer grid, plain text)."""
    return ", ".join(r["tick"] for r in answer.get("rows", []))
