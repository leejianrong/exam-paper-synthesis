"""EXA-90 — a teacher's own question in their question bank.

A ``freeformQuestion`` block (body, lettered parts, images by asset id, inline maths, marks,
Ans: units, written answers) is saved as a canonical *sourced* object written by the teacher
(``provenance.created_by: "teacher"``). The block itself rides along verbatim in the object's
``freeform`` field, so inserting it into another paper gives back exactly the same question;
``question`` holds a plain-text summary of it for the bank's lists and pickers. Nothing here
claims the question is right: like every free-form block it stays unverified.

Pure and storage-agnostic. Whether the images belong to the caller is the API's check.
"""

from __future__ import annotations

import copy
from functools import cache

import yaml

from .blueprints.registry import content_dir
from .document import (
    DOCUMENT_SCHEMA_VERSION,
    freeform_body,
    freeform_marks,
    freeform_parts,
    has_content,
    validate_document,
)

LEVELS = ("P5", "P6")
DIFFICULTIES = ("easy", "medium", "hard")
# The schema needs a cognitive level; a teacher picks only the difficulty, which it follows.
_COGNITIVE = {
    "easy": "routine_procedural",
    "medium": "complex_familiar",
    "hard": "non_routine_heuristic",
}
# What belongs to a question's place in one paper, not to the question.
_PAPER_ONLY = ("slot", "locked", "in_key", "bank_id")
PICTURE = "[picture]"
OWN_PREFIX = "own-"


class NotSavable(ValueError):
    """The block can't be saved as it is (the message says why, in the teacher's words)."""


@cache
def topics() -> tuple[dict, ...]:
    """The topics a bank question can be filed under: the blueprints' own (so a saved question
    sits with the generated ones), each with its strand, sorted by name."""
    found: dict[str, str] = {}
    for path in sorted((content_dir() / "blueprints").glob("*.yaml")):
        syllabus = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("syllabus") or {}
        if syllabus.get("topic"):
            found.setdefault(syllabus["topic"], syllabus.get("strand") or syllabus["topic"])
    return tuple({"topic": t, "strand": found[t]} for t in sorted(found))


def _inline_text(nodes: list[dict]) -> str:
    out: list[str] = []
    for n in nodes:
        if n["type"] == "text":
            out.append(n.get("text", ""))
        elif n["type"] == "math":
            out.append(f"\\({n['attrs']['latex']}\\)")
        elif n["type"] == "hardBreak":
            out.append(" ")
    return "".join(out)


def plain_text(blocks: list[dict]) -> str:
    """Rich-text blocks as one line of plain text (maths kept as ``\\(…\\)``, a picture as
    ``[picture]``), for the bank's summary of the question."""
    out: list[str] = []
    for b in blocks:
        if b["type"] == "image":
            out.append(PICTURE)
        elif b["type"] in ("paragraph", "heading"):
            out.append(_inline_text(b.get("content", [])))
        elif b["type"] in ("bulletList", "orderedList"):
            out.extend(plain_text(li.get("content", [])) for li in b.get("content", []))
    return " ".join(" ".join(s.split()) for s in out if s.strip())


def _answer_text(attrs: dict) -> str:
    return plain_text((attrs.get("answer") or {}).get("content", []))


def _summary(node: dict) -> dict:
    """The canonical ``question``: the block as plain text, one part per lettered part."""
    parts = freeform_parts(node)
    body = plain_text(freeform_body(node))
    if not parts:
        part = {
            "label": "",
            "text": body or "…",
            "marks": node["attrs"]["marks"],
            "answer": {"type": "text", "text": _answer_text(node["attrs"])},
            "solution_steps": [],
        }
        return {"stem": None, "parts": [part], "total_marks": node["attrs"]["marks"]}
    out: list[dict] = [
        {
            "label": chr(ord("a") + i),
            "text": plain_text(p["content"]) or "…",
            "marks": p["attrs"].get("marks") or 0,
            "answer": {"type": "text", "text": _answer_text(p["attrs"])},
            "solution_steps": [],
        }
        for i, p in enumerate(parts)
    ]
    return {"stem": body or None, "parts": out, "total_marks": freeform_marks(node)}


def bank_id(node: dict) -> str:
    """The bank id a block saves as: the one it came from, else one of its own. Saving the same
    block again finds the same id, so it reports "already in your bank" (or replaces it). Only
    an own question's id is reused: replacing never overwrites an imported or generated one."""
    came_from = node["attrs"].get("bank_id") or ""
    return came_from if came_from.startswith(OWN_PREFIX) else OWN_PREFIX + node["attrs"]["block_id"]


def to_canonical(
    node: dict, *, topic: str, level: str, difficulty: str, marks: int | None = None
) -> dict:
    """The bank's canonical object for the teacher's block ``node``.

    ``marks`` sets a single-part question's marks (a multi-part question's marks are its
    parts'). Raises :class:`NotSavable` for an empty or unmarked question or an unknown topic;
    the result has passed the canonical load gate.
    """
    from . import canonical  # canonical's load gate calls back into this module

    if node.get("type") != "freeformQuestion":
        raise NotSavable("Only a question you wrote can be saved to your bank.")
    strands = {t["topic"]: t["strand"] for t in topics()}
    if topic not in strands:
        raise NotSavable(f"Unknown topic {topic!r}.")
    if level not in LEVELS:
        raise NotSavable(f"The level must be one of {', '.join(LEVELS)}.")
    if difficulty not in DIFFICULTIES:
        raise NotSavable(f"The difficulty must be one of {', '.join(DIFFICULTIES)}.")
    if not has_content(node.get("content", [])):
        raise NotSavable("Write the question before saving it to your bank.")
    block = copy.deepcopy(node)
    attrs = block["attrs"]
    for key in _PAPER_ONLY:
        attrs.pop(key, None)
    if not freeform_parts(block):
        if marks is not None:
            attrs["marks"] = marks
        if attrs.get("marks") is None:
            raise NotSavable("Give the question its marks before saving it.")
    obj = {
        "schema_version": canonical.SCHEMA_VERSION,
        "id": bank_id(node),
        "source_type": "sourced",
        "blueprint_code": None,
        "seed": None,
        "parameters": None,
        "syllabus": {
            "level": level,
            "strand": strands[topic],
            "topic": topic,
            "subtopic": None,
            "skill_codes": [],
        },
        "cognitive": {"difficulty": difficulty, "cognitive_level": _COGNITIVE[difficulty]},
        "question": _summary(block),
        "source": {"origin": "Your own question", "year": None, "paper": None, "reference": None},
        "license": "Written by the bank's owner",
        "validation": {"status": "unverified", "checks": {"human_reviewed": False}},
        "provenance": {
            "created_by": "teacher",
            "llm_used": False,
            "created_at": None,
            "parent_id": None,
            "version": 1,
        },
        "freeform": block,
    }
    return canonical.load(obj)


def to_block(obj: dict, block_id: str) -> dict:
    """The bank question ``obj`` as a block for a paper, under ``block_id``: the saved block,
    unchanged but for its id, remembering which bank question it is."""
    block = copy.deepcopy(obj["freeform"])
    block["attrs"] = {**block["attrs"], "block_id": block_id, "bank_id": obj["id"]}
    return block


def check(obj: dict) -> list[str]:
    """The load gate's rules for a teacher's question the schemas can't express: the block is a
    valid document block, and the summary's marks and parts agree with it."""
    node = obj.get("freeform")
    if not node:
        return []
    doc = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "title": "bank",
        "content": {"type": "doc", "content": [node]},
    }
    errors = [
        "freeform: " + e.removeprefix("content/content/0").lstrip("/: ")
        for e in validate_document(doc)
    ]
    if errors:
        return errors
    if node["type"] != "freeformQuestion":
        return ["freeform: must be a freeformQuestion block"]
    q = obj["question"]
    if q["total_marks"] != freeform_marks(node):
        errors.append("question.total_marks: must equal the block's marks")
    n_parts = len(freeform_parts(node))
    if len(q["parts"]) != max(n_parts, 1):
        errors.append("question.parts: must have one part per lettered part of the block")
    return errors
