"""EXA-89 — tier-2 edits: a teacher changes the free numbers of a generated question.

A blueprint marks the numbers a teacher may type as ``edit: free`` (with a ``label``) in its
``param_roles``; every other number stays as generated. Everything worked out from the free
numbers (shares, the unit value, the answer, the working, the bar model) is re-solved, never
typed, so the answer key stays engine-proven. This module describes the free numbers and
checks a proposed change; the edit itself is :func:`exam_engine.edits.apply`
(``set-numbers``), which rebuilds the question through :func:`pipeline.build_from_params`.

A refusal is an :class:`EditNotApplicable` whose ``reason`` is a sentence a teacher can act
on: the range a number must lie in, or the solver's own ``number_problem`` ("$125 can't be
shared in the ratio 2 : 3 in whole dollars ...").
"""

from __future__ import annotations

from collections.abc import Mapping

from .blueprints.registry import get_solver, load_blueprint
from .errors import EditNotApplicable

OP = "set-numbers"


def number_slots(code: str) -> list[dict]:
    """The free numbers of blueprint ``code``, for building the edit form.

    One entry per ``edit: free`` parameter: ``{key, label, list, minimum, maximum}`` (``sep``
    too when the YAML gives one, e.g. ``":"`` for a ratio). ``list`` says the parameter holds
    several numbers; their count is the question's own. Empty when the blueprint has none
    (or its solver cannot explain a refusal, so the edit is never offered half-built).
    """
    spec = load_blueprint(code)
    if getattr(get_solver(code), "number_problem", None) is None:
        return []
    props = spec.parameter_schema.get("properties") or {}
    slots = []
    for key, entry in spec.param_roles.items():
        if entry.get("edit") != "free":
            continue
        prop = props[key]
        is_list = prop.get("type") == "array"
        bounds = prop["items"] if is_list else prop
        slot = {
            "key": key,
            "label": entry["label"],
            "list": is_list,
            "minimum": bounds.get("minimum"),
            "maximum": bounds.get("maximum"),
        }
        if entry.get("sep"):
            slot["sep"] = entry["sep"]
        slots.append(slot)
    return slots


def _whole(label: str, value: object, lo: int | None, hi: int | None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EditNotApplicable(OP, f"{label} must be a whole number.")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise EditNotApplicable(OP, f"{label} must be from {lo} to {hi}.")
    return value


def merge_numbers(code: str, params: dict, changes: Mapping[str, object]) -> dict:
    """``params`` with ``changes`` applied, or :class:`EditNotApplicable` saying why not.

    Refuses: no changes, a parameter that is not a free number (names, items, choices and
    numbers the engine keeps), a value that is not a whole number or is out of range, a list
    of the wrong length, and numbers the solver's ``number_problem`` turns down.
    """
    if not changes:
        raise EditNotApplicable(OP, "No numbers were given.")
    slots = {s["key"]: s for s in number_slots(code)}
    merged = {k: (list(v) if isinstance(v, list) else v) for k, v in params.items()}
    for key, value in changes.items():
        slot = slots.get(key)
        if slot is None:
            raise EditNotApplicable(OP, f"{key!r} is not a number you can change here.")
        label, lo, hi = slot["label"], slot["minimum"], slot["maximum"]
        if slot["list"]:
            current = params[key]
            if not isinstance(value, list) or len(value) != len(current):
                raise EditNotApplicable(OP, f"{label} needs {len(current)} numbers.")
            merged[key] = [_whole(label, v, lo, hi) for v in value]
        else:
            merged[key] = _whole(label, value, lo, hi)
    problem = get_solver(code).number_problem(merged)  # type: ignore[attr-defined]
    if problem:
        raise EditNotApplicable(OP, problem)
    return merged
