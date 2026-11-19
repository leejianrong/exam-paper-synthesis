"""P8a — paper templates and one-click paper generation (docs/planning/editor/P8-SHAPING.md).

A **paper template** (``content/papers/*.yaml``) is a real paper's composition: time, cover
wording and sections, each a list of **slots** of ``{marks, count}``. ``template_document``
turns one into an empty starter paper (the P4 starter templates); ``generate_paper`` fills
its slots from the blueprints and returns a document plus an honest report.

Pure and deterministic like ``pipeline.generate``: the same ``(template, level, seed)`` always
gives the same paper. The API supplies the seed (where entropy enters) and stamps
``created_at``; nothing here reads a clock or global randomness.

Rules (owner's decisions, 2026-11-15):

- Each blueprint is used at most once per paper. A slot no unused blueprint fits becomes a
  **placeholder** (a free-form question with the slot's marks and an empty body for the
  teacher to write). The paper is never padded with repeats or off-topic questions.
- Each section's marks equal its target, counting placeholders.
- A ``structured`` section first takes real **multi-part** questions (P8c blueprints with
  ``parts``), each at most once, as many as fit its marks target and slot count. The rest of
  the target is filled with single-part **stand-ins** of 2 marks or more whose marks add up to
  it; the slot count may then differ from the real paper's. Any shortfall becomes placeholders
  of 3–5 marks. Multi-part blueprints are never used in ``short`` or ``mcq`` sections.
- ``mcq`` slots take a blueprint whose answer is numeric or a fraction and turn its question
  into four-option multiple choice (P8b, ``mcq.to_mcq``); the marks stay the blueprint's. A
  blueprint that asks multiple choice itself (picture options, EXA-147) goes in as it is, and
  only in ``mcq`` slots.
- A paper of level P6 may use P5 and P6 blueprints; a P5 paper only P5 ones.
- Difficulty follows marks (EXA-146): a slot prefers blueprints whose ladder rung is at least
  :func:`min_rung` of its marks (2 marks: medium; 3 or more: hard). When none is left it takes
  the closest rung below, so the rule never adds a placeholder.
- Topics are spread: among the best-fitting rung, each slot takes the least-used topic so far,
  ties broken by the seed. A multi-part question or a stand-in never gives a topic its third
  question in the paper (:data:`TOPIC_CAP`, EXA-154): every structured section's multi-part
  questions are picked before any other question, the biggest stand-ins are chosen first, and
  marks no topic under the cap can take become placeholders.
- In an exam set (EXA-153) topics are spread over the whole set: ``generate_paper`` takes the
  topic counts of the set's papers already made (``set_topics``; :func:`generate_set` and the
  web wizard pass them on, filling Paper 2 first: :func:`set_fill_order`). "Least-used" then
  counts the set, and a topic with
  :data:`SET_TOPIC_CAP` questions in the set is **full**: a slot takes a full topic only when
  every other blueprint for it is full too, even if that means a rung below the one its marks
  ask for. Without ``set_topics`` (a paper on its own) nothing changes.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from functools import cache

import yaml

from .blueprints.registry import content_dir, load_blueprint
from .document import (
    DOCUMENT_SCHEMA_VERSION,
    _part_of,
    new_key_options,
    unfilled_placeholder_numbers,
)
from .mcq import CONVERTIBLE, to_mcq
from .pipeline import generate

LEVELS = ("P5", "P6")
KINDS = ("mcq", "short", "structured")
SUBJECT = "Mathematics"
_LEVEL_NAMES = {"P5": "Primary 5", "P6": "Primary 6"}
_STAND_IN_MIN_MARKS = 2  # a 1-mark question doesn't belong in a structured section
_PLACEHOLDER_CHUNK = (3, 5)  # stand-in shortfall is split into placeholders of this size
SET_TOPIC_CAP = 3  # EXA-153: questions of one topic in an exam set before it gives way
TOPIC_CAP = 2  # EXA-154: a stand-in or a swap never gives a topic more questions in one paper


class UnknownPaperTemplate(KeyError):
    """No paper template with that code."""


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def _papers_dir():
    return content_dir() / "papers"


@cache
def _load_all() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(_papers_dir().glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("code") != path.stem:
            raise ValueError(f"{path.name}: code {data.get('code')!r} must match the file name")
        out[data["code"]] = data
    return out


def paper_templates() -> list[dict]:
    """Every paper template (deep copies), in display order."""
    return [copy.deepcopy(t) for t in sorted(_load_all().values(), key=lambda t: t["order"])]


def paper_template(code: str) -> dict:
    try:
        return copy.deepcopy(_load_all()[code])
    except KeyError:
        raise UnknownPaperTemplate(code) from None


def slot_marks(section: dict) -> int:
    return sum(s["marks"] * s["count"] for s in section["slots"])


def _section_node(section: dict) -> dict:
    return {
        "type": "section",
        "attrs": {
            "title": section["title"],
            "instructions": section.get("instructions"),
            "mode": section["mode"],
            "marks_target": section["marks_target"],
        },
    }


def _empty_doc(title: str, settings: dict, blocks: list[dict]) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "title": title,
        "settings": settings,
        "content": {"type": "doc", "content": blocks},
    }


def _settings(t: dict) -> dict:
    """A template's paper settings: its time, where its numbering starts when that is not 1
    (Booklet B carries on from Booklet A, EXA-134), and the school key (EXA-159)."""
    start = t.get("number_from", 1)
    return {
        "time_min": t["time_min"],
        **({"number_from": start} if start != 1 else {}),
        "key_options": new_key_options(),
    }


_COVER_SWITCHES = ("examiner_table", "parent_signature", "even_pages")


def _cover_node(t: dict, level: str | None) -> dict:
    """The template's cover page (P7): subject, paper, instructions and the template's cover
    switches prefilled. The level is stated only when known (a generated paper); school, exam
    and date are the teacher's."""
    attrs = {
        "subject": t["cover"].get("subject", SUBJECT),
        "paper": t["cover"]["paper"],
        "instructions": t["cover"].get("instructions"),
        **{k: t["cover"][k] for k in _COVER_SWITCHES if k in t["cover"]},
    }
    if level is not None:
        attrs = {"level": _LEVEL_NAMES[level], **attrs}
    return {"type": "coverPage", "attrs": attrs}


def _cover_blocks(t: dict, level: str | None) -> list[dict]:
    """The cover, then a blank back of the cover when the template asks for one (EXA-140): real
    booklets are printed double-sided, so the questions start on a right-hand page."""
    back = (
        [{"type": "blankPage", "attrs": {"kind": "blank"}}] if t["cover"].get("blank_back") else []
    )
    return [_cover_node(t, level), *back]


def standard_paper_marks() -> dict[str, int]:
    """The standard marks of each exam-set paper (``document.paper_part``), from the templates'
    section targets: Booklet A 20, Booklet B 25, Paper 2 55. The cover's examiner's table uses
    them for the papers of the set that are not in the document (EXA-140)."""
    out: dict[str, int] = {}
    for t in _load_all().values():
        part = _part_of(t["cover"]["paper"])
        if part:
            out[part] = sum(s["marks_target"] for s in t["sections"])
    return out


def template_document(code: str) -> dict:
    """The empty starter paper for a template (P4): the cover page (level left for the
    teacher, as an empty template has none), its sections and time, no questions."""
    t = paper_template(code)
    return _empty_doc(
        t["title"],
        _settings(t),
        [*_cover_blocks(t, None), *(_section_node(s) for s in t["sections"])],
    )


# ---------------------------------------------------------------------------
# Blueprint pool
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    code: str
    topic: str
    level: str
    marks: int
    kind: str  # "constructed" (single-part) or "multipart" (P8c: a stem with parts)
    answer_type: str = ""
    rung: str = "easy"  # the blueprint's cognitive.difficulty: easy / medium / hard


RUNGS = ("easy", "medium", "hard")


def min_rung(marks: int) -> str:
    """The easiest rung a slot of ``marks`` should take (EXA-146): real papers spend 2 marks on
    a multi-step problem and 3–5 on a heuristic one, so a 1-mark slot takes any rung, a 2-mark
    slot medium or harder, and a slot of 3 marks or more a hard one."""
    return RUNGS[min(max(marks - 1, 0), 2)]


def rung_shortfall(rung: str, marks: int) -> int:
    """How many rungs ``rung`` falls below what a slot of ``marks`` should take (0 = it fits)."""
    return max(0, RUNGS.index(min_rung(marks)) - RUNGS.index(rung))


@cache
def _pool() -> tuple[Candidate, ...]:
    out = []
    for path in sorted((content_dir() / "blueprints").glob("*.yaml")):
        spec = load_blueprint(path.stem)
        out.append(
            Candidate(
                code=spec.code,
                topic=spec.syllabus.get("topic", spec.code),
                level=spec.syllabus.get("level", "P6"),
                marks=spec.marks,
                kind="multipart" if spec.is_multipart else "constructed",
                answer_type=str((spec.answer or {}).get("type", "")),
                rung=str(spec.cognitive.get("difficulty", "easy")),
            )
        )
    return tuple(out)


def candidates(level: str) -> list[Candidate]:
    """Blueprints a paper of ``level`` may use: its level and below."""
    allowed = LEVELS[: LEVELS.index(level) + 1]
    return [c for c in _pool() if c.level in allowed]


def _fits(c: Candidate, kind: str) -> bool:
    if kind == "mcq":  # P8b: converted to multiple choice, so the answer must be convertible
        # EXA-147: or the blueprint asks multiple choice itself (picture options)
        return c.kind == "constructed" and c.answer_type in (*CONVERTIBLE, "choice")
    if kind == "multipart":  # P8c: only structured sections ask for these
        return c.kind == "multipart"
    # short-answer and (stand-in) structured slots take constructed-response questions.
    return kind in ("short", "structured") and c.kind == "constructed" and c.answer_type != "choice"


def as_slot_question(obj: dict, kind: str, seed: int) -> dict:
    """``obj`` as an ``kind`` slot prints it: multiple choice for an ``mcq`` slot (P8b), unless
    the blueprint already asks multiple choice (EXA-147)."""
    if kind == "mcq" and obj["question"]["parts"][0]["answer"].get("type") != "choice":
        return to_mcq(obj, seed)
    return obj


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class _Filler:
    """Shared state while filling one paper: what's used, topic counts, the seeded RNG."""

    def __init__(
        self, template: dict, level: str, seed: int, set_topics: dict[str, int] | None = None
    ):
        self.rng = random.Random(f"paper|{template['code']}|{level}|{seed}")
        self.pool = candidates(level)
        self.used: set[str] = set()
        self.topics: dict[str, int] = {}  # this paper's (the report's)
        # EXA-153: None = a paper on its own; a dict (even empty) = one paper of an exam set.
        self.set_topics = None if set_topics is None else dict(set_topics)
        self.n = 0

    def topic_load(self, c: Candidate) -> int:
        """How often ``c``'s topic is already in the set: earlier papers plus this one."""
        return (self.set_topics or {}).get(c.topic, 0) + self.topics.get(c.topic, 0)

    def topic_full(self, c: Candidate) -> bool:
        """In an exam set, ``c``'s topic has reached :data:`SET_TOPIC_CAP`."""
        return self.set_topics is not None and self.topic_load(c) >= SET_TOPIC_CAP

    def block_id(self) -> str:
        self.n += 1
        return f"gq{self.n:03d}{self.rng.getrandbits(24):06x}"

    def pick(self, marks: int, kind: str, cap: int | None = None) -> Candidate | None:
        """An unused blueprint with these marks: a topic the set has not filled (EXA-153), then
        the best-fitting rung (:func:`rung_shortfall`), then the least-used topic, seeded ties.
        With ``cap`` (EXA-154), only from a topic this paper has fewer than ``cap`` questions of."""
        options = [
            c
            for c in self.pool
            if c.code not in self.used
            and c.marks == marks
            and _fits(c, kind)
            and (cap is None or self.topics.get(c.topic, 0) < cap)
        ]
        if not options:
            return None
        self.rng.shuffle(options)
        best = min(
            options,
            key=lambda c: (
                self.topic_full(c),
                rung_shortfall(c.rung, marks),
                self.topic_load(c),
            ),
        )
        self.used.add(best.code)
        self.topics[best.topic] = self.topics.get(best.topic, 0) + 1
        return best

    def pick_multipart(self, max_marks: int) -> Candidate | None:
        """An unused multi-part blueprint of at most ``max_marks``, least-used topic first
        (seeded ties), the same way :meth:`pick` chooses."""
        options = [
            c
            for c in self.pool
            if c.code not in self.used
            and c.marks <= max_marks
            and _fits(c, "multipart")
            and self.topics.get(c.topic, 0) < TOPIC_CAP
        ]
        if not options:
            return None
        self.rng.shuffle(options)
        best = min(options, key=lambda c: (self.topic_full(c), self.topic_load(c)))
        self.used.add(best.code)
        self.topics[best.topic] = self.topics.get(best.topic, 0) + 1
        return best

    def question(self, c: Candidate, slot: dict) -> dict:
        obj = generate(c.code, self.rng.randrange(1, 2**31))
        if slot["kind"] == "mcq":
            obj = as_slot_question(obj, "mcq", self.rng.randrange(1, 2**31))
        return {
            "type": "templatedQuestion",
            "attrs": {"block_id": self.block_id(), "question": obj, "slot": slot},
        }

    def placeholder(self, marks: int, kind: str) -> dict:
        return {
            "type": "freeformQuestion",
            "attrs": {
                "block_id": self.block_id(),
                "marks": marks,
                "slot": {"marks": marks, "kind": kind, "placeholder": True},
            },
            "content": [{"type": "paragraph"}],
        }


def _stand_in_plan(f: _Filler, target: int, slots: int) -> list[int]:
    """Marks of the single-part stand-ins for a structured section: an exact sum to ``target``
    if the unused pool allows, else as close below as possible. Among equal sums, prefer the
    count closest to the real paper's ``slots`` and fewer small questions. Only blueprints of
    a topic the paper has fewer than :data:`TOPIC_CAP` questions of count (EXA-154); two of one
    topic may both count, so :func:`_fill_structured` re-plans after every pick."""
    have: dict[int, int] = {}
    for c in f.pool:
        if (
            c.code not in f.used
            and c.marks >= _STAND_IN_MIN_MARKS
            and _fits(c, "structured")
            and f.topics.get(c.topic, 0) < TOPIC_CAP
        ):
            have[c.marks] = have.get(c.marks, 0) + 1
    values = sorted(have)
    # Dynamic programme over (marks so far, questions so far) -> the counts per mark value that
    # reach it with the fewest of the smallest value. Bounded by target x count x pool size, so
    # it stays fast however much content grows (an exhaustive product would not).
    states: dict[tuple[int, int], tuple[int, ...]] = {(0, 0): ()}
    for v in values:
        nxt: dict[tuple[int, int], tuple[int, ...]] = {}
        for (total, n), counts in states.items():
            for k in range(have[v] + 1):
                t = total + k * v
                if t > target:
                    break
                key = (t, n + k)
                cand = (*counts, k)
                if key not in nxt or cand[:1] < nxt[key][:1]:  # fewer of the smallest value
                    nxt[key] = cand
        states = nxt
    (total, n), counts = max(
        states.items(),
        key=lambda kv: (kv[0][0], -abs(kv[0][1] - slots), -(kv[1][0] if kv[1] else 0)),
    )
    return [v for v, k in zip(values, counts, strict=True) for _ in range(k)]


def _placeholder_chunks(shortfall: int) -> list[int]:
    """Split a shortfall into placeholders of 3–5 marks (one smaller chunk if it is tiny)."""
    if shortfall <= 0:
        return []
    lo, hi = _PLACEHOLDER_CHUNK
    if shortfall <= hi:
        return [shortfall]
    k = -(-shortfall // hi)  # ceil
    base, extra = divmod(shortfall, k)
    chunks = [base + 1] * extra + [base] * (k - extra)
    assert all(lo <= c <= hi for c in chunks), chunks
    return sorted(chunks)


def _fill_fixed(f: _Filler, section: dict, report: dict) -> list[dict]:
    """Fill the slots in print order, but choose for the higher-mark slots first: their rung
    rule leaves fewer blueprints to pick from, and the 1-mark slots then spread around the
    topics those took (EXA-146)."""
    mode = section["mode"]
    marks = [s["marks"] for s in section["slots"] for _ in range(s["count"])]
    order = sorted(range(len(marks)), key=lambda i: -marks[i])
    chosen = {i: f.pick(marks[i], mode) for i in order}
    blocks = []
    for i, m in enumerate(marks):
        c = chosen[i]
        if c is None:
            blocks.append(f.placeholder(m, mode))
            report["placeholders"] += 1
            report["placeholder_marks"] += m
        else:
            blocks.append(f.question(c, {"marks": m, "kind": mode}))
            report["filled"] += 1
            report["blueprints"].append(c.code)
    return blocks


def _pick_multiparts(f: _Filler, section: dict) -> list[dict]:
    """A structured section's real multi-part questions (P8c). :func:`generate_paper` picks
    these before any other question of the paper (EXA-154): they are scarce, so they claim
    their topics before a short question can fill one to :data:`TOPIC_CAP`."""
    target = section["marks_target"]
    n_slots = sum(s["count"] for s in section["slots"])
    blocks: list[dict] = []
    while len(blocks) < n_slots:
        mp = f.pick_multipart(target - sum(b["attrs"]["slot"]["marks"] for b in blocks))
        if mp is None:
            break
        blocks.append(f.question(mp, {"marks": mp.marks, "kind": "structured"}))
    return blocks


def _fill_structured(f: _Filler, section: dict, report: dict, multiparts: list[dict]) -> list[dict]:
    """The section's ``multiparts`` (:func:`_pick_multiparts`), then single-part stand-ins for
    the rest of the marks target, then placeholders for any shortfall. Questions are ordered by
    marks (stable), so the section reads from shorter to longer questions."""
    target = section["marks_target"]
    n_slots = sum(s["count"] for s in section["slots"])
    blocks = list(multiparts)
    for b in blocks:
        report["filled"] += 1
        report["multipart"] += 1
        report["blueprints"].append(b["attrs"]["question"]["blueprint_code"])
    rest = target - sum(b["attrs"]["slot"]["marks"] for b in blocks)
    # EXA-154: the biggest stand-in first, so it claims a topic before a 2-marker does; after
    # each pick the plan is made again, because that pick may have filled its topic
    while rest > 0:
        plan = _stand_in_plan(f, rest, n_slots - len(blocks))
        if not plan:
            break
        marks = max(plan)
        c = f.pick(marks, "structured", cap=TOPIC_CAP)
        assert c is not None  # the plan counts only unused blueprints of topics under the cap
        blocks.append(f.question(c, {"marks": marks, "kind": "structured", "stand_in": True}))
        report["filled"] += 1
        report["stand_ins"] += 1
        report["blueprints"].append(c.code)
        rest -= marks
    blocks.sort(key=lambda b: b["attrs"]["slot"]["marks"])
    for marks in _placeholder_chunks(rest):
        blocks.append(f.placeholder(marks, "structured"))
        report["placeholders"] += 1
        report["placeholder_marks"] += marks
    return blocks


def generate_paper(
    template_code: str, level: str, seed: int, set_topics: dict[str, int] | None = None
) -> tuple[dict, dict]:
    """Fill a paper template's slots for ``level`` (``P5``/``P6``). Returns ``(document,
    report)``; the document validates (``document.validate_document``) and every generated
    question is engine-proven. The report says, per section, what was filled and what is left
    for the teacher, and ``topics`` counts this paper's questions per topic.

    ``set_topics`` (EXA-153) is the topic count of the exam set's papers already made (the sum
    of their reports' ``topics``): topics are then spread over the whole set, not just this
    paper. Without it the paper is exactly what it was before."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, not {level!r}")
    t = paper_template(template_code)
    f = _Filler(t, level, seed, set_topics)

    multiparts = {
        i: _pick_multiparts(f, sec)
        for i, sec in enumerate(t["sections"])
        if sec["mode"] == "structured"
    }
    blocks: list[dict] = _cover_blocks(t, level)
    sections_report = []
    for i, section in enumerate(t["sections"]):
        rep = {
            "title": section["title"],
            "mode": section["mode"],
            "marks_target": section["marks_target"],
            "slots": sum(s["count"] for s in section["slots"]),
            "filled": 0,
            "multipart": 0,
            "stand_ins": 0,
            "placeholders": 0,
            "placeholder_marks": 0,
            "blueprints": [],
        }
        blocks.append(_section_node(section))
        if section["mode"] == "structured":
            blocks += _fill_structured(f, section, rep, multiparts[i])
        else:
            blocks += _fill_fixed(f, section, rep)
        sections_report.append(rep)

    title = f"{level} {t['title']}"
    doc = _empty_doc(title, _settings(t), blocks)
    report = {
        "template": t["code"],
        "level": level,
        "seed": seed,
        "title": title,
        "sections": sections_report,
        "filled": sum(s["filled"] for s in sections_report),
        "placeholders": sum(s["placeholders"] for s in sections_report),
        "placeholder_marks": sum(s["placeholder_marks"] for s in sections_report),
        "topics": dict(sorted(f.topics.items())),
    }
    return doc, report


def set_fill_order(template_codes: list[str]) -> list[str]:
    """The order to fill an exam set's papers in (EXA-153): the paper with the biggest slots
    first, then the most marks (Paper 2, Booklet B, Booklet A). Big slots need hard and medium
    rungs, which few blueprints have, so they choose while every topic is still free; 1-mark
    slots take any rung, so Booklet A copes best with full topics."""

    def size(code: str) -> tuple[int, int]:
        sections = paper_template(code)["sections"]
        biggest = max(s["marks"] for sec in sections for s in sec["slots"])
        return (-biggest, -sum(sec["marks_target"] for sec in sections))

    return sorted(template_codes, key=size)


def generate_set(template_codes: list[str], level: str, seed: int) -> list[tuple[dict, dict]]:
    """An exam set (EXA-153), returned in the given (printed) order. The papers are filled in
    :func:`set_fill_order`, each told the topics of those filled before it, so the set spreads
    its topics as one paper does. The web's "+ New" wizard does the same one paper per request,
    in the same order, passing the running count as ``set_topics``."""
    made: dict[str, tuple[dict, dict]] = {}
    running: dict[str, int] = {}
    for code in set_fill_order(template_codes):
        doc, report = generate_paper(code, level, seed, running)
        for topic, n in report["topics"].items():
            running[topic] = running.get(topic, 0) + n
        made[code] = (doc, report)
    return [made[code] for code in template_codes]


def unfilled_placeholders(doc: dict) -> int:
    """Placeholders the teacher hasn't written yet: nothing in the stem or any part."""
    return len(unfilled_placeholder_numbers(doc))
