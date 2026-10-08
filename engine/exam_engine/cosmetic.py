"""W1a — cosmetic (tier-1) edit slots: person names and item nouns.

A blueprint's ``param_roles`` classifies every parameter (``name | item | number |
choice``). Only ``name`` and ``item`` may be changed without touching the maths:
they never enter ``solve()``. This module describes those slots and validates a
proposed change; the actual edit lives in :func:`exam_engine.edits.apply`
(``set-cosmetic``), which re-solves through the normal pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from .blueprints.base import COSMETIC_ROLES
from .blueprints.registry import get_solver, load_blueprint
from .errors import EditNotApplicable

OP = "set-cosmetic"

NAME_MAX_LEN = 24
# Unicode letters, joined by single spaces / hyphens / apostrophes ("Nurul Aini",
# "Mary-Anne", "O'Brien"). No digits, no markup characters (names are untrusted
# input that ends up in HTML and SVG).
_NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '’\-][^\W\d_]+)*$")


def editable_slots(code: str) -> list[dict]:
    """The cosmetic slots of blueprint ``code``, for building an edit form.

    One entry per ``name``/``item`` parameter: ``{key, role, count, ...}`` where
    ``count`` is the number of values (1 for scalars, the array length for arrays),
    ``max_length`` bounds names, and ``pool`` lists the allowed values for items.
    """
    spec = load_blueprint(code)
    props = spec.parameter_schema.get("properties") or {}
    slots: list[dict] = []
    for key, entry in spec.param_roles.items():
        role = entry["role"]
        if role not in COSMETIC_ROLES:
            continue
        prop = props.get(key, {})
        slot: dict = {
            "key": key,
            "role": role,
            "count": prop.get("minItems", 1) if prop.get("type") == "array" else 1,
        }
        if role == "name":
            slot["max_length"] = NAME_MAX_LEN
        else:
            slot["pool"] = list(getattr(get_solver(code), "ITEM_POOL", []))
        slots.append(slot)
    return slots


def _normalise_name(value: object) -> str:
    if not isinstance(value, str):
        raise EditNotApplicable(OP, f"a name must be text, got {type(value).__name__}")
    name = " ".join(value.split())
    if not name:
        raise EditNotApplicable(OP, "a name must not be empty")
    if len(name) > NAME_MAX_LEN:
        raise EditNotApplicable(OP, f"name {name!r} is longer than {NAME_MAX_LEN} characters")
    if not _NAME_RE.match(name):
        raise EditNotApplicable(
            OP, f"name {name!r} may only contain letters, spaces, hyphens and apostrophes"
        )
    return name


def merge_changes(code: str, params: dict, changes: Mapping[str, object]) -> dict:
    """Return a copy of ``params`` with ``changes`` applied, or raise
    :class:`EditNotApplicable` explaining why a change is refused.

    Refuses: unknown keys, ``number``/``choice`` parameters (they change the maths —
    use regenerate / make-harder instead), wrong shapes, invalid names, items outside
    the curated pool, and duplicate names across the question's name slots.
    """
    if not changes:
        raise EditNotApplicable(OP, "no changes given")
    spec = load_blueprint(code)
    merged = {k: (list(v) if isinstance(v, list) else v) for k, v in params.items()}

    for key, value in changes.items():
        entry = spec.param_roles.get(key)
        if entry is None:
            raise EditNotApplicable(OP, f"unknown parameter {key!r}")
        role = entry["role"]
        if role not in COSMETIC_ROLES:
            raise EditNotApplicable(
                OP,
                f"parameter {key!r} is a {role!r} parameter — it changes the maths, so it "
                "cannot be edited cosmetically (use regenerate / make-harder / make-easier)",
            )
        current = params[key]
        if isinstance(current, list):
            if not isinstance(value, list) or len(value) != len(current):
                raise EditNotApplicable(OP, f"{key!r} needs a list of {len(current)} values")
            new_values: object = [_check_value(code, role, v) for v in value]
        else:
            if isinstance(value, list):
                raise EditNotApplicable(OP, f"{key!r} takes a single value")
            new_values = _check_value(code, role, value)
        merged[key] = new_values

    _check_distinct_names(spec.param_roles, merged)
    return merged


def _check_value(code: str, role: str, value: object) -> str:
    if role == "name":
        return _normalise_name(value)
    pool = list(getattr(get_solver(code), "ITEM_POOL", []))
    if value not in pool:
        raise EditNotApplicable(OP, f"item {value!r} is not in the allowed list: {pool}")
    assert isinstance(value, str)
    return value


def _check_distinct_names(roles: dict, params: dict) -> None:
    names: list[str] = []
    for key, entry in roles.items():
        if entry["role"] != "name":
            continue
        value = params[key]
        names.extend(value if isinstance(value, list) else [value])
    folded = [n.casefold() for n in names]
    if len(set(folded)) != len(folded):
        raise EditNotApplicable(OP, "names must be different from each other")
