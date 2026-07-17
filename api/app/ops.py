"""KAN-243 — API-boundary handling of the ``available_ops`` UI hint.

The engine is the single source of truth for which edit ops apply to an object
(:func:`exam_engine.edits.available_ops`). The API surfaces that set on every
returned question so the web can drive edit-button visibility from it, instead of
re-deriving it with a brittle client-side heuristic.

``available_ops`` is *not* part of the canonical JSON Schema (a UI hint, not
mathematical truth). To keep the engine pure and objects round-trippable, the API
attaches it only on the way **out** and strips it on the way **in**, before the
strict :func:`exam_engine.canonical.load` gate ever sees the object.
"""

from __future__ import annotations

from exam_engine import edits

# UI-only keys the API attaches to responses; never part of the canonical schema.
_UI_HINT_KEYS = ("available_ops",)


def with_available_ops(obj: dict) -> dict:
    """Return a shallow copy of ``obj`` with the sorted ``available_ops`` UI hint.

    A sorted list (not a set) is JSON-friendly and stable across requests.
    """
    return {**obj, "available_ops": sorted(edits.available_ops(obj))}


def strip_ui_hints(obj: dict) -> dict:
    """Return ``obj`` without UI-only hint keys, so it can round-trip the schema gate.

    Returns the object unchanged when it carries no hints (the common case), so
    freshly-sourced/tampered objects are untouched before validation.
    """
    if not any(k in obj for k in _UI_HINT_KEYS):
        return obj
    return {k: v for k, v in obj.items() if k not in _UI_HINT_KEYS}
