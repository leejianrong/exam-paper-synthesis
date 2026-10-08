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


def strip_document_hints(document: object) -> object:
    """Strip UI-only hints from every embedded question of a document (W1b/W1c).

    The editor keeps ``available_ops`` on each question (it drives the block toolbar), but
    stored snapshots are canonical objects, so hints are removed on the way in and
    re-attached on the way out. Non-conforming input is returned untouched for the
    validator to reject with a proper error.
    """
    try:
        blocks = document["content"]["content"]  # type: ignore[index]
        if not isinstance(blocks, list):
            return document
    except (KeyError, TypeError):
        return document
    new_blocks = []
    for node in blocks:
        question = node.get("attrs", {}).get("question") if isinstance(node, dict) else None
        if (
            isinstance(node, dict)
            and node.get("type") == "templatedQuestion"
            and isinstance(question, dict)
        ):
            node = {**node, "attrs": {**node["attrs"], "question": strip_ui_hints(question)}}
        new_blocks.append(node)
    return {**document, "content": {**document["content"], "content": new_blocks}}  # type: ignore[index,dict-item]


def with_document_hints(record: dict) -> dict:
    """Attach ``available_ops`` to each generated question of a stored document record."""
    document = record["document"]
    blocks = []
    for node in document["content"]["content"]:
        if node.get("type") == "templatedQuestion" and node["attrs"]["question"].get(
            "blueprint_code"
        ):
            question = with_available_ops(node["attrs"]["question"])
            node = {**node, "attrs": {**node["attrs"], "question": question}}
        blocks.append(node)
    return {
        **record,
        "document": {**document, "content": {**document["content"], "content": blocks}},
    }
