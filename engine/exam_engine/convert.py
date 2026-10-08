"""W2c — Convert to free-form (ADR-0021 tier 3): a canonical question as editable text.

Pure and storage-agnostic. :func:`to_freeform` turns a canonical question into the pieces of
a ``freeformQuestion`` node — body blocks, a written answer, and marks — as plain text,
lists and ``figure`` placeholders. A *figure* is a diagram the caller must turn into an
image asset (the engine draws SVG; rasterising needs a browser, which lives at the API
boundary); the placeholder says where it goes. The result carries no verification of any
kind: once converted, the question is the teacher's.
"""

from __future__ import annotations

from typing import Any

Node = dict[str, Any]


def _text(value: str) -> Node:
    return {"type": "text", "text": value}


def _para(*inline: Node | str) -> Node:
    content = [_text(c) if isinstance(c, str) else c for c in inline]
    merged: list[Node] = []
    for c in content:
        if c.get("type") == "text":
            if not c["text"]:
                continue
            if merged and merged[-1].get("type") == "text":
                merged[-1] = _text(merged[-1]["text"] + c["text"])
                continue
        merged.append(c)
    content = merged
    return {"type": "paragraph", "content": content} if content else {"type": "paragraph"}


def _list(kind: str, items: list[str]) -> Node:
    return {
        "type": kind,
        "content": [{"type": "listItem", "content": [_para(i)]} for i in items],
    }


def _figure(spec: dict, label: str, alt: str | None = None) -> Node:
    return {"type": "figure", "spec": spec, "label": label, "alt": alt or "Diagram"}


def _fmt_number(value: object, *, decimal: bool, money: bool) -> str:
    if money and decimal:
        return f"{float(value):.2f}"  # type: ignore[arg-type]
    return str(value)


def answer_inline(answer: dict) -> list[Node]:
    """The typed answer as inline nodes (text; a fraction becomes a ``math`` node)."""
    atype = answer.get("type")
    if atype in ("integer", "decimal", "quantity"):
        unit = answer.get("unit") or ""
        shown = _fmt_number(answer.get("value"), decimal=atype == "decimal", money=unit == "$")
        if unit == "$":
            return [_text(f"${shown}")]
        if unit == "%":
            return [_text(f"{shown}%")]
        return [_text(f"{shown} {unit}".strip())]
    if atype == "fraction":
        latex = rf"\frac{{{answer['numerator']}}}{{{answer['denominator']}}}"
        unit = answer.get("unit") or ""
        if unit == "$":
            return [_text("$"), {"type": "math", "attrs": {"latex": latex}}]
        out: list[Node] = [{"type": "math", "attrs": {"latex": latex}}]
        if unit:
            out.append(_text(f" {unit}"))
        return out
    if atype == "ratio":
        return [_text(" : ".join(str(p) for p in answer.get("parts", [])))]
    if atype == "set":
        return [_text(", ".join(str(v) for v in answer.get("values", [])))]
    if atype == "text":
        return [_text(str(answer.get("text", "")))]
    if atype == "choice":
        correct = answer.get("correct")
        opt = next((o for o in answer.get("options", []) if o.get("label") == correct), None)
        label = f"({correct})"
        return [_text(f"{label} {opt['text']}" if opt and opt.get("text") else label)]
    return [_text(str(answer))]


def _cell(cell: object) -> str:
    if isinstance(cell, dict):  # {"answer_for": label}: the pupil fills this in
        return "______"
    return "" if cell is None else str(cell)


def _table_blocks(table: dict) -> list[Node]:
    """A plain-text grid: caption, then one paragraph per row, cells joined by `` | ``."""
    blocks: list[Node] = []
    if table.get("caption"):
        blocks.append(_para(str(table["caption"])))
    if table.get("headers"):
        blocks.append(_para(" | ".join(_cell(h) for h in table["headers"])))
    blocks.extend(_para(" | ".join(_cell(c) for c in row)) for row in table["rows"])
    return blocks


def _options_blocks(answer: dict) -> list[Node]:
    options = answer.get("options", [])
    labels = [str(o.get("label")) for o in options]
    blocks: list[Node] = []
    if labels == [str(i) for i in range(1, len(options) + 1)] and all(
        o.get("text") for o in options
    ):
        blocks.append(_list("orderedList", [str(o["text"]) for o in options]))
    else:
        blocks.extend(_para(f"({o['label']}) {o.get('text') or ''}".rstrip()) for o in options)
    for o in options:
        if o.get("diagram"):
            blocks.append(_figure(o["diagram"], f"option ({o['label']})", f"Option ({o['label']})"))
    return blocks


def to_freeform(obj: dict) -> dict:
    """Pieces of a free-form question from canonical question ``obj``.

    Returns ``{"marks", "body", "answer"}``: ``body`` and ``answer`` are lists of document
    blocks that may contain ``figure`` placeholders (``spec``, ``label``, ``alt``).
    """
    q = obj["question"]
    parts = q["parts"]
    multipart = len(parts) > 1
    body: list[Node] = []
    answer: list[Node] = []

    if q.get("stem"):
        body.append(_para(str(q["stem"])))
    if q.get("diagram"):
        body.append(_figure(q["diagram"], "figure"))
    if q.get("table"):
        body.extend(_table_blocks(q["table"]))

    for part in parts:
        label = f"({part['label']}) " if multipart and part.get("label") else ""
        marks = f" [{part['marks']}]" if multipart and part.get("marks") is not None else ""
        body.append(_para(f"{label}{part['text']}{marks}"))
        if (part.get("answer") or {}).get("type") == "choice":
            body.extend(_options_blocks(part["answer"]))
        if part.get("diagram"):
            where = f"part ({part['label']}) figure" if part.get("label") else "figure"
            body.append(_figure(part["diagram"], where))

        # The written answer: the printed answer, then how to get there.
        pa = part["answer"]
        if pa["type"] == "construction":
            answer.append(_para(f"{label}Answer: see the figure."))
            answer.append(_figure(pa["diagram"], "answer figure", "Completed construction"))
        else:
            answer.append(_para(f"{label}Answer: ", *answer_inline(pa)))
        steps = [s["text"] for s in part.get("solution_steps", []) if s.get("text")]
        if steps:
            answer.append(_list("orderedList", steps))
        scheme = [
            f"{m['type']}{m['mark']}: {m['description']}" for m in part.get("marking_scheme", [])
        ]
        if scheme:
            answer.append(_list("bulletList", scheme))

    return {"marks": q["total_marks"], "body": body, "answer": answer}


def figures(blocks: list[Node]) -> list[Node]:
    """The ``figure`` placeholders in ``blocks``, in order."""
    return [b for b in blocks if b.get("type") == "figure"]
