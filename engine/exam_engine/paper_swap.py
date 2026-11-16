"""P8d — keep / swap / lock on a paper (docs/planning/editor/P8-SHAPING.md).

Per-question actions on a (generated) paper and "regenerate unlocked", as pure
document → document transforms. They keep every P8a rule (``paper.generate_paper``):

- no blueprint twice in the paper;
- every question at or below the paper's level;
- each question keeps its slot's marks, so each section's total stays at its target.

``swap_question(doc, block_id, mode, seed, level)`` replaces one question:

- ``like``  — another question for the same slot: an unused blueprint of the same topic and
  marks, else a new seed of the same blueprint (a placeholder takes any unused blueprint that
  fits, least-used topic first — it is *filled*);
- ``topic`` — an unused blueprint with the same marks from another topic, preferring topics
  the paper doesn't use yet (on a placeholder: fills it from a topic the paper lacks);
- ``own``   — a free-form placeholder with the slot's marks and an empty body, for the
  teacher to write.

``regenerate_unlocked(doc, level, seed)`` refills every generated question and every
still-empty placeholder whose ``locked`` is not true. Locked questions, bank (sourced)
questions and anything the teacher wrote — free-form questions, placeholders with something
in them — are kept exactly as they are.

Every choice follows the generator's rung rule first (EXA-146, ``paper.rung_shortfall``): a
candidate whose rung fits the slot's marks beats one that falls short, whatever the order of
preference below, so a swap or a regenerate never makes a slot easier than the content allows.

Candidates are ``paper._fits`` for the slot's kind, so an ``mcq`` slot only takes blueprints
``mcq.to_mcq`` can convert, and its new question is converted like the generator's (P8b).

Multi-part questions (P8c) only ever fill ``structured`` slots, and there they come first, as
in ``generate_paper``: ``like`` on a multi-part question takes another multi-part question of
the same topic and marks, else a new seed of it, else a single-part one (a stand-in); ``like``
on a stand-in prefers a multi-part question of its topic; ``topic`` and placeholders try the
multi-part candidates before the single-part ones; ``regenerate_unlocked`` fills structured
slots with multi-part questions first, then stand-ins. A single-part question in a structured
slot is flagged ``stand_in``; a multi-part one is not.

Pure and deterministic: the API chooses the seed and stamps ``created_at``.
"""

from __future__ import annotations

import copy
import random

from .document import QUESTION_TYPES, has_content, is_unfilled_placeholder
from .mcq import to_mcq
from .paper import KINDS, LEVELS, Candidate, _fits, candidates, rung_shortfall
from .pipeline import generate

MODES = ("like", "topic", "own")
_LEVEL_BY_NAME = {"primary 5": "P5", "primary 6": "P6", "p5": "P5", "p6": "P6"}
_RESEED_TRIES = 12  # new seeds of the same blueprint tried for a visibly different question
# Attributes that belong to the position, not the question, and survive a swap.
_KEPT_ATTRS = ("block_id", "space_mm", "in_key", "remark", "locked")


class SwapNotPossible(ValueError):
    """The requested swap can't be made (the message says why, for the teacher)."""


class BlockNotFound(KeyError):
    """No question block with that id in the paper."""


# ---------------------------------------------------------------------------
# Reading the paper
# ---------------------------------------------------------------------------


def cover_level(doc: dict) -> str | None:
    """The level the paper's cover page states ("Primary 6" -> P6), if it has one."""
    blocks = doc["content"]["content"]
    if blocks and blocks[0]["type"] == "coverPage":
        name = str((blocks[0].get("attrs") or {}).get("level") or "").strip().lower()
        return _LEVEL_BY_NAME.get(name)
    return None


def paper_level(doc: dict, requested: str | None = None) -> str:
    """The level to fill for: the cover page's ("Primary 6") when the paper states one, else
    ``requested``, else the highest level of its generated questions, else P6."""
    stated = cover_level(doc) or requested
    if stated:
        if stated not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}, not {stated!r}")
        return stated
    blocks = doc["content"]["content"]
    seen = [
        n["attrs"]["question"].get("syllabus", {}).get("level")
        for n in blocks
        if n["type"] == "templatedQuestion"
    ]
    return max((lv for lv in seen if lv in LEVELS), key=LEVELS.index, default="P6")


def _blueprint(node: dict) -> str | None:
    if node["type"] != "templatedQuestion":
        return None
    return node["attrs"]["question"].get("blueprint_code")


def _topic(node: dict) -> str | None:
    if node["type"] != "templatedQuestion":
        return None
    return node["attrs"]["question"].get("syllabus", {}).get("topic")


def _marks(node: dict) -> int:
    if node["type"] == "templatedQuestion":
        return int(node["attrs"]["question"]["question"]["total_marks"])
    return int(node["attrs"].get("marks") or 0)


def _is_placeholder(node: dict) -> bool:
    return node["type"] == "freeformQuestion" and bool(
        ((node.get("attrs") or {}).get("slot") or {}).get("placeholder")
    )


def _is_generated(node: dict) -> bool:
    return (
        node["type"] == "templatedQuestion"
        and node["attrs"]["question"].get("source_type") == "generated"
        and bool(_blueprint(node))
    )


def _section_modes(blocks: list[dict]) -> list[str | None]:
    """The mode of the section each block sits in (``None`` outside any section)."""
    out, mode = [], None
    for n in blocks:
        if n["type"] == "section":
            mode = (n.get("attrs") or {}).get("mode")
        out.append(mode)
    return out


def _slot_of(node: dict, section_mode: str | None) -> dict:
    """What this position asks for: the generator's slot, or (for a hand-added question) its
    marks and the kind of its section (short answer outside any section)."""
    slot = (node.get("attrs") or {}).get("slot")
    if slot:
        return dict(slot)
    kind = section_mode if section_mode in KINDS else "short"
    return {"marks": _marks(node), "kind": kind}


class _Paper:
    """What a paper already uses, besides the blocks being replaced."""

    def __init__(self, blocks: list[dict], level: str, skip: set[int]):
        self.pool = candidates(level)
        self.used: set[str] = set()
        self.topics: dict[str, int] = {}
        for i, n in enumerate(blocks):
            if i in skip:
                continue
            code, topic = _blueprint(n), _topic(n)
            if code:
                self.used.add(code)
            if topic:
                self.topics[topic] = self.topics.get(topic, 0) + 1

    def options(self, slot: dict) -> list[Candidate]:
        return [
            c
            for c in self.pool
            if c.code not in self.used and c.marks == slot["marks"] and _slot_takes(c, slot)
        ]

    def take(self, c: Candidate) -> None:
        self.used.add(c.code)
        self.topics[c.topic] = self.topics.get(c.topic, 0) + 1


def _slot_takes(c: Candidate, slot: dict) -> bool:
    """``paper._fits``, plus multi-part blueprints for a structured slot (P8c)."""
    if slot["kind"] == "structured" and _fits(c, "multipart"):
        return True
    return _fits(c, slot["kind"])


def _tiers(options: list[Candidate]) -> list[list[Candidate]]:
    """The candidates in the generator's order of preference: multi-part, then the rest."""
    multi = [c for c in options if c.kind == "multipart"]
    return [multi, [c for c in options if c.kind != "multipart"]]


def _first(
    tiers: list[list[Candidate]], topics: dict[str, int], rng: random.Random, marks: int
) -> Candidate | None:
    """The least-used-topic candidate of the first tier that has any, among the candidates of
    the best-fitting rung for ``marks`` (EXA-146): the rung rule outranks the tiers."""
    shortfalls = [rung_shortfall(c.rung, marks) for tier in tiers for c in tier]
    if not shortfalls:
        return None
    best = min(shortfalls)
    for tier in tiers:
        choice = _least_used(
            [c for c in tier if rung_shortfall(c.rung, marks) == best], topics, rng, marks
        )
        if choice is not None:
            return choice
    return None


def _least_used(
    options: list[Candidate], topics: dict[str, int], rng: random.Random, marks: int
) -> Candidate | None:
    """The best-fitting rung for ``marks``, then the least-used topic (seeded ties)."""
    if not options:
        return None
    options = list(options)
    rng.shuffle(options)
    return min(options, key=lambda c: (rung_shortfall(c.rung, marks), topics.get(c.topic, 0)))


# ---------------------------------------------------------------------------
# Building replacement blocks
# ---------------------------------------------------------------------------


def _kept(node: dict) -> dict:
    return {k: node["attrs"][k] for k in _KEPT_ATTRS if node["attrs"].get(k) is not None}


def _filled_slot(slot: dict, multipart: bool) -> dict:
    out = {"marks": slot["marks"], "kind": slot["kind"]}
    # a single-part question in a structured section stands in for a multi-part one (P8a);
    # a real multi-part question (P8c) does not
    if not multipart and (slot["kind"] == "structured" or slot.get("stand_in")):
        out["stand_in"] = True
    return out


def _question_block(node: dict, obj: dict, slot: dict | None) -> dict:
    attrs = {**_kept(node), "question": obj}
    if slot is not None:
        attrs["slot"] = slot
    return {"type": "templatedQuestion", "attrs": attrs}


def _placeholder_block(node: dict, slot: dict) -> dict:
    attrs = _kept(node)
    attrs["marks"] = slot["marks"]
    attrs["slot"] = {"marks": slot["marks"], "kind": slot["kind"], "placeholder": True}
    return {"type": "freeformQuestion", "attrs": attrs, "content": [{"type": "paragraph"}]}


def _new_slot(node: dict, slot: dict, c: Candidate) -> dict | None:
    """The slot a filled block records: a generated position keeps (and fills) its slot; a
    hand-added question without one stays without one."""
    if not (node.get("attrs") or {}).get("slot"):
        return None
    return _filled_slot(slot, c.kind == "multipart")


def _fresh(code: str, kind: str, rng: random.Random, avoid: dict | None = None) -> dict:
    """A question from ``code`` for a slot of ``kind`` (multiple choice for an ``mcq`` slot,
    converted exactly as ``paper._Filler.question`` does); with ``avoid``, one whose
    parameters differ from it."""
    obj = generate(code, rng.randrange(1, 2**31))
    for _ in range(_RESEED_TRIES):
        if avoid is None or obj.get("parameters") != avoid.get("parameters"):
            break
        obj = generate(code, rng.randrange(1, 2**31))
    if kind == "mcq":
        obj = to_mcq(obj, rng.randrange(1, 2**31))
    return obj


def _describe(c: Candidate) -> dict:
    return {"blueprint": c.code, "topic": c.topic, "marks": c.marks}


# ---------------------------------------------------------------------------
# Swap
# ---------------------------------------------------------------------------


def swap_question(
    doc: dict, block_id: str, mode: str, seed: int, level: str | None = None
) -> tuple[dict, dict]:
    """Replace the question ``block_id`` (see the module docstring). Returns ``(document,
    report)``; ``doc`` itself is not changed. Raises ``SwapNotPossible`` with a message for
    the teacher when the paper's rules leave nothing to swap in, and ``KeyError`` when no
    question has that id (``BlockNotFound``). Bank (sourced) questions and teacher-written
    free-form questions are never swapped."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    level = paper_level(doc, level)
    out = copy.deepcopy(doc)
    blocks = out["content"]["content"]
    idx = next(
        (
            i
            for i, n in enumerate(blocks)
            if n["type"] in QUESTION_TYPES and (n.get("attrs") or {}).get("block_id") == block_id
        ),
        None,
    )
    if idx is None:
        raise BlockNotFound(block_id)
    node = blocks[idx]
    if node["attrs"].get("locked"):
        raise SwapNotPossible("This question is locked. Unlock it to swap it.")
    if node["type"] == "templatedQuestion" and not _is_generated(node):
        raise SwapNotPossible(
            "A question from your bank is kept as it is; delete it to replace it."
        )
    if node["type"] == "freeformQuestion":
        if not _is_placeholder(node):
            raise SwapNotPossible("Only generated questions and placeholders can be swapped.")
        if has_content(node.get("content", [])):
            raise SwapNotPossible("You have started writing this question, so it is kept.")
        if mode == "own":
            raise SwapNotPossible("This is already a question for you to write.")

    slot = _slot_of(node, _section_modes(blocks)[idx])
    rng = random.Random(f"swap|{block_id}|{mode}|{level}|{seed}")
    paper = _Paper(blocks, level, skip={idx})
    report: dict = {"block_id": block_id, "mode": mode, "marks": slot["marks"]}

    if mode == "own":
        blocks[idx] = _placeholder_block(node, slot)
        return out, {**report, "placeholder": True}

    current, topic = _blueprint(node), _topic(node)
    options = paper.options(slot)
    easier = False
    if node["type"] == "templatedQuestion":  # never swap in an easier rung than the slot had
        floor = rung_shortfall(node["attrs"]["question"]["cognitive"]["difficulty"], slot["marks"])
        kept = [c for c in options if rung_shortfall(c.rung, slot["marks"]) <= floor]
        easier, options = len(kept) < len(options), kept
    choice: Candidate | None
    if mode == "like":
        if node["type"] == "freeformQuestion":  # filling a placeholder
            choice = _first(_tiers(options), paper.topics, rng, slot["marks"])
        else:
            multi, single = _tiers([c for c in options if c.topic == topic])
            itself = [c for c in options if c.code == current]  # a new seed of it
            multi = [c for c in multi if c.code != current]
            single = [c for c in single if c.code != current]
            order: list[list[Candidate]]
            if itself and itself[0].kind == "multipart":  # keep it multi-part if at all possible
                order = [multi, itself, single]
            else:
                order = [multi, single, itself]
            choice = _first(order, {}, rng, slot["marks"])
    else:  # topic
        others = [c for c in options if c.topic != topic]
        order = []
        for tier in _tiers(others):
            fresh = [c for c in tier if not paper.topics.get(c.topic)]
            order += [fresh, tier]
        choice = _first(order, paper.topics, rng, slot["marks"])

    if choice is None:
        what = "another topic" if mode == "topic" else "this topic"
        why = (
            "the ones left are easier than this one"
            if easier
            else "each question is used once per paper"
        )
        raise SwapNotPossible(
            f"No other {slot['marks']}-mark question from {what} fits this paper ({why})."
        )
    avoid = node["attrs"]["question"] if choice.code == current else None
    obj = _fresh(choice.code, slot["kind"], rng, avoid)
    blocks[idx] = _question_block(node, obj, _new_slot(node, slot, choice))
    return out, {**report, **_describe(choice), "placeholder": False}


# ---------------------------------------------------------------------------
# Regenerate unlocked
# ---------------------------------------------------------------------------


def _refillable(node: dict) -> bool:
    if node["type"] not in QUESTION_TYPES or node["attrs"].get("locked"):
        return False
    return _is_generated(node) or is_unfilled_placeholder(node)


def regenerate_unlocked(doc: dict, level: str | None, seed: int) -> tuple[dict, dict]:
    """Refill every unlocked generated question and empty placeholder (see the module
    docstring). Returns ``(document, report)``; ``doc`` itself is not changed."""
    level = paper_level(doc, level)
    out = copy.deepcopy(doc)
    blocks = out["content"]["content"]
    modes = _section_modes(blocks)
    targets = [i for i, n in enumerate(blocks) if _refillable(n)]
    paper = _Paper(blocks, level, skip=set(targets))
    rng = random.Random(f"regenerate|{level}|{seed}")
    report = {"replaced": 0, "placeholders": 0, "kept": 0}
    report["kept"] = sum(1 for n in blocks if n["type"] in QUESTION_TYPES) - len(targets)
    # P8c: like generate_paper, structured slots take multi-part questions first, so a later
    # stand-in slot can't use up a multi-part blueprint an earlier slot could have had.
    chosen: dict[int, Candidate] = {}
    for i in targets:
        slot = _slot_of(blocks[i], modes[i])
        if slot["kind"] == "structured":
            c = _least_used(_tiers(paper.options(slot))[0], paper.topics, rng, slot["marks"])
            if c is not None:
                paper.take(c)
                chosen[i] = c
    for i in targets:
        node = blocks[i]
        slot = _slot_of(node, modes[i])
        c = chosen.get(i) or _least_used(paper.options(slot), paper.topics, rng, slot["marks"])
        if c is None:
            if node["type"] == "templatedQuestion":
                blocks[i] = _placeholder_block(node, slot)
            report["placeholders"] += 1
            continue
        if i not in chosen:
            paper.take(c)
        avoid = node["attrs"]["question"] if _blueprint(node) == c.code else None
        blocks[i] = _question_block(
            node, _fresh(c.code, slot["kind"], rng, avoid), _new_slot(node, slot, c)
        )
        report["replaced"] += 1
    return out, report
