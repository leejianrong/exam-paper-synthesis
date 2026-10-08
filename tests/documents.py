"""Importable helpers for document tests (not a test module)."""

from __future__ import annotations

import copy
from itertools import count

from exam_engine import generate
from exam_engine.document import DOCUMENT_SCHEMA_VERSION

_ids = count(1)


def text(value: str, *marks: str) -> dict:
    node: dict = {"type": "text", "text": value}
    if marks:
        node["marks"] = [{"type": m} for m in marks]
    return node


def para(value: str, *marks: str) -> dict:
    return {"type": "paragraph", "content": [text(value, *marks)]}


def heading(value: str, level: int = 2) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [text(value)]}


def question_block(obj: dict, block_id: str | None = None) -> dict:
    return {
        "type": "templatedQuestion",
        "attrs": {"block_id": block_id or f"blk_{next(_ids):04d}", "question": copy.deepcopy(obj)},
    }


def gen_block(code: str = "ratio_medium", seed: int = 1) -> dict:
    return question_block(generate(code, seed))


def make_doc(*blocks: dict, title: str = "Test paper") -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "title": title,
        "content": {"type": "doc", "content": list(blocks)},
    }


def freeform_block(
    body: str = "Write a question.",
    *,
    marks: int | None = 2,
    answer: str | None = None,
    block_id: str | None = None,
) -> dict:
    """A teacher-written ``freeformQuestion`` (W2a)."""
    attrs: dict = {"block_id": block_id or f"ff_{next(_ids):04d}", "marks": marks}
    if answer is not None:
        attrs["answer"] = {"type": "doc", "content": [para(answer)]}
    return {"type": "freeformQuestion", "attrs": attrs, "content": [para(body)]}


def image_node(asset_id: str = "asset_0001", *, alt: str | None = "A figure", width_pct: int = 60):
    return {"type": "image", "attrs": {"asset_id": asset_id, "alt": alt, "width_pct": width_pct}}


def math_node(latex: str = r"\frac{3}{4}") -> dict:
    return {"type": "math", "attrs": {"latex": latex}}
