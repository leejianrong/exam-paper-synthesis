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
- A ``structured`` section with no multi-part blueprints (all of today's content) is filled
  with single-part **stand-ins** of 2 marks or more whose marks add up to the target; the slot
  count may then differ from the real paper's. Any shortfall becomes placeholders of 3–5 marks.
- ``mcq`` slots take a blueprint whose answer is numeric or a fraction and turn its question
  into four-option multiple choice (P8b, ``mcq.to_mcq``); the marks stay the blueprint's.
- A paper of level P6 may use P5 and P6 blueprints; a P5 paper only P5 ones.
- Topics are spread: each slot takes the least-used topic so far, ties broken by the seed.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from functools import cache

import yaml

from .blueprints.registry import content_dir, load_blueprint
from .document import DOCUMENT_SCHEMA_VERSION
from .mcq import CONVERTIBLE, to_mcq
from .pipeline import generate

LEVELS = ("P5", "P6")
KINDS = ("mcq", "short", "structured")
SUBJECT = "Mathematics"
_LEVEL_NAMES = {"P5": "Primary 5", "P6": "Primary 6"}
_STAND_IN_MIN_MARKS = 2  # a 1-mark question doesn't belong in a structured section
_PLACEHOLDER_CHUNK = (3, 5)  # stand-in shortfall is split into placeholders of this size


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


def template_document(code: str) -> dict:
    """The empty starter paper for a template (P4): its sections and time, no questions."""
    t = paper_template(code)
    return _empty_doc(
        t["title"], {"time_min": t["time_min"]}, [_section_node(s) for s in t["sections"]]
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
    kind: str  # "constructed" today; "multipart" arrives with P8c
    answer_type: str = ""


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
                kind="constructed",
                answer_type=str((spec.answer or {}).get("type", "")),
            )
        )
    return tuple(out)


def candidates(level: str) -> list[Candidate]:
    """Blueprints a paper of ``level`` may use: its level and below."""
    allowed = LEVELS[: LEVELS.index(level) + 1]
    return [c for c in _pool() if c.level in allowed]


def _fits(c: Candidate, kind: str) -> bool:
    if kind == "mcq":  # P8b: converted to multiple choice, so the answer must be convertible
        return c.kind == "constructed" and c.answer_type in CONVERTIBLE
    # short-answer and (stand-in) structured slots take constructed-response questions.
    return kind in ("short", "structured") and c.kind == "constructed"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class _Filler:
    """Shared state while filling one paper: what's used, topic counts, the seeded RNG."""

    def __init__(self, template: dict, level: str, seed: int):
        self.rng = random.Random(f"paper|{template['code']}|{level}|{seed}")
        self.pool = candidates(level)
        self.used: set[str] = set()
        self.topics: dict[str, int] = {}
        self.n = 0

    def block_id(self) -> str:
        self.n += 1
        return f"gq{self.n:03d}{self.rng.getrandbits(24):06x}"

    def pick(self, marks: int, kind: str) -> Candidate | None:
        """An unused blueprint with these marks, from the least-used topic (seeded ties)."""
        options = [
            c for c in self.pool if c.code not in self.used and c.marks == marks and _fits(c, kind)
        ]
        if not options:
            return None
        self.rng.shuffle(options)
        best = min(options, key=lambda c: self.topics.get(c.topic, 0))
        self.used.add(best.code)
        self.topics[best.topic] = self.topics.get(best.topic, 0) + 1
        return best

    def question(self, c: Candidate, slot: dict) -> dict:
        obj = generate(c.code, self.rng.randrange(1, 2**31))
        if slot["kind"] == "mcq":
            obj = to_mcq(obj, self.rng.randrange(1, 2**31))
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
    count closest to the real paper's ``slots`` and fewer small questions."""
    have: dict[int, int] = {}
    for c in f.pool:
        if c.code not in f.used and c.marks >= _STAND_IN_MIN_MARKS and _fits(c, "structured"):
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
    blocks = []
    for slot in section["slots"]:
        for _ in range(slot["count"]):
            spec = {"marks": slot["marks"], "kind": section["mode"]}
            c = f.pick(slot["marks"], section["mode"])
            if c is None:
                blocks.append(f.placeholder(slot["marks"], section["mode"]))
                report["placeholders"] += 1
                report["placeholder_marks"] += slot["marks"]
            else:
                blocks.append(f.question(c, spec))
                report["filled"] += 1
                report["blueprints"].append(c.code)
    return blocks


def _fill_stand_ins(f: _Filler, section: dict, report: dict) -> list[dict]:
    target = section["marks_target"]
    n_slots = sum(s["count"] for s in section["slots"])
    plan = _stand_in_plan(f, target, n_slots)
    blocks = []
    for marks in sorted(plan):
        c = f.pick(marks, "structured")
        assert c is not None  # the plan only counts unused blueprints
        blocks.append(f.question(c, {"marks": marks, "kind": "structured", "stand_in": True}))
        report["filled"] += 1
        report["stand_ins"] += 1
        report["blueprints"].append(c.code)
    for marks in _placeholder_chunks(target - sum(plan)):
        blocks.append(f.placeholder(marks, "structured"))
        report["placeholders"] += 1
        report["placeholder_marks"] += marks
    return blocks


def generate_paper(template_code: str, level: str, seed: int) -> tuple[dict, dict]:
    """Fill a paper template's slots for ``level`` (``P5``/``P6``). Returns ``(document,
    report)``; the document validates (``document.validate_document``) and every generated
    question is engine-proven. The report says, per section, what was filled and what is left
    for the teacher."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, not {level!r}")
    t = paper_template(template_code)
    f = _Filler(t, level, seed)

    cover = {
        "type": "coverPage",
        "attrs": {
            "level": _LEVEL_NAMES[level],
            "subject": t["cover"].get("subject", SUBJECT),
            "paper": t["cover"]["paper"],
            "instructions": t["cover"].get("instructions"),
        },
    }
    blocks: list[dict] = [cover]
    sections_report = []
    for section in t["sections"]:
        rep = {
            "title": section["title"],
            "mode": section["mode"],
            "marks_target": section["marks_target"],
            "slots": sum(s["count"] for s in section["slots"]),
            "filled": 0,
            "stand_ins": 0,
            "placeholders": 0,
            "placeholder_marks": 0,
            "blueprints": [],
        }
        blocks.append(_section_node(section))
        # No multi-part blueprints exist yet (P8c), so structured sections take stand-ins.
        if section["mode"] == "structured":
            blocks += _fill_stand_ins(f, section, rep)
        else:
            blocks += _fill_fixed(f, section, rep)
        sections_report.append(rep)

    title = f"{level} {t['title']}"
    doc = _empty_doc(title, {"time_min": t["time_min"]}, blocks)
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


def _has_content(nodes: list[dict]) -> bool:
    """Any non-blank text, or an image / equation, anywhere in these nodes (parts included)."""
    for n in nodes:
        if n["type"] == "text" and n.get("text", "").strip():
            return True
        if n["type"] in ("image", "math"):
            return True
        if _has_content(n.get("content", [])):
            return True
    return False


def unfilled_placeholders(doc: dict) -> int:
    """Placeholders the teacher hasn't written yet: nothing in the stem or any part."""
    return sum(
        1
        for node in doc["content"]["content"]
        if node["type"] == "freeformQuestion"
        and ((node.get("attrs") or {}).get("slot") or {}).get("placeholder")
        and not _has_content(node.get("content", []))
    )
