"""W1b — the document model: a paper as ProseMirror-style JSON (ADR-0021).

Pure and UI/HTTP-agnostic, like the rest of the engine. A document is a title plus a
ProseMirror ``doc`` whose block nodes are rich text and ``templatedQuestion`` atoms; each
templated question embeds a *frozen snapshot* of a canonical question object. The JSON
Schema (``schemas/document.schema.json``) gates the structure; this module adds the rules
a schema can't express (unique block ids, size limits, embedded-question validity, and the
re-solve check that keeps the "engine-proven" claim unforgeable).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .blueprints.base import validate_params
from .blueprints.registry import get_solver, load_blueprint
from .errors import UnknownBlueprint
from .schema import validate_object

# 1.15.0 (EXA-140): + coverPage.parent_signature and coverPage.even_pages.
# 1.14.0 (EXA-142): + settings.key_options.layout (full / compact answer key).
# 1.13.0 (EXA-139): + section.marks_placement (none/question/answer/both; null follows the mode).
# 1.12.0 (EXA-134): + settings.number_from (Booklet B continues Booklet A's numbering).
# 1.11.0 (P8d): + question `locked` (kept by "regenerate unlocked").
# 1.10.0 (P8a): + question `slot` (what the paper generator asked for).
# 1.9.0 (P7): + coverPage (first block only) and blankPage blocks.
# 1.8.0 (P6a): + section.marking (marking margin).
# 1.7.0 (P5): + settings.key_options, per-question in_key.
# 1.6.0 (P4): + section blocks (title, instructions, mode, marks target), settings.time_min.
# 1.5.0 (P3): + freeformPart (lettered parts of a free-form question).
# 1.4.0 (P2): + settings.marks_placement, per-question space_mm / ans_unit.
# 1.1.0 (W2a): + freeformQuestion; 1.2.0 (W2b): + image, math; 1.3.0 (W5): + question `remark`.
# Older documents stay valid (every addition is optional).
DOCUMENT_SCHEMA_VERSION = "1.15.0"

MAX_QUESTION_BLOCKS = 200
MAX_CONTENT_BYTES = 1_500_000
MAX_BLOCK_TEXT_CHARS = 20_000
MAX_IMAGES = 40
MAX_PARTS = 10
MAX_SECTIONS = 20
MAX_BLANK_PAGES = 20

QUESTION_TYPES = ("templatedQuestion", "freeformQuestion")

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "document.schema.json"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def empty_document(title: str = "Untitled paper") -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "title": title,
        "content": {"type": "doc", "content": []},
    }


def question_blocks(doc: dict) -> list[dict]:
    """The ``templatedQuestion`` nodes, in document order (top level only)."""
    return [n for n in doc["content"]["content"] if n.get("type") == "templatedQuestion"]


def questions_in_order(doc: dict) -> list[dict]:
    """The embedded canonical objects, in document order."""
    return [n["attrs"]["question"] for n in question_blocks(doc)]


def freeform_blocks(doc: dict) -> list[dict]:
    """The ``freeformQuestion`` nodes (teacher-written, unverified), in document order."""
    return [n for n in doc["content"]["content"] if n.get("type") == "freeformQuestion"]


def numbered_blocks(doc: dict) -> list[dict]:
    """Every numbered question block (templated and free-form), in document order."""
    return [n for n in doc["content"]["content"] if n.get("type") in QUESTION_TYPES]


def has_content(nodes: list[dict]) -> bool:
    """Any non-blank text, or an image / equation, anywhere in these nodes (parts included)."""
    for n in nodes:
        if n["type"] == "text" and n.get("text", "").strip():
            return True
        if n["type"] in ("image", "math"):
            return True
        if has_content(n.get("content", [])):
            return True
    return False


def is_unfilled_placeholder(node: dict) -> bool:
    """A generator placeholder (P8a: a ``freeformQuestion`` whose ``slot.placeholder`` is
    set) the teacher hasn't written yet: nothing in the stem or any part. The written answer
    doesn't count: an answer with no question still prints nothing to answer."""
    return (
        node.get("type") == "freeformQuestion"
        and bool(((node.get("attrs") or {}).get("slot") or {}).get("placeholder"))
        and not has_content(node.get("content", []))
    )


def unfilled_placeholder_numbers(doc: dict) -> list[int]:
    """The printed question numbers of the unfilled placeholders (EXA-137), in order. They
    count from the paper's ``number_from`` (Booklet B: 16 onwards, EXA-134)."""
    start = number_from(doc)
    return [
        n for n, node in enumerate(numbered_blocks(doc), start) if is_unfilled_placeholder(node)
    ]


def freeform_parts(node: dict) -> list[dict]:
    """The lettered ``freeformPart`` children of a free-form question (P3), in order."""
    return [c for c in node.get("content", []) if c.get("type") == "freeformPart"]


def freeform_body(node: dict) -> list[dict]:
    """A free-form question's body blocks (everything that is not a part)."""
    return [c for c in node.get("content", []) if c.get("type") != "freeformPart"]


def freeform_marks(node: dict) -> int:
    """Marks of a free-form question: the sum over its parts, else its own marks."""
    parts = freeform_parts(node)
    if parts:
        return sum(p["attrs"].get("marks") or 0 for p in parts)
    return node["attrs"].get("marks") or 0


def key_options(doc: dict) -> dict:
    """The answer-key print options with defaults filled in (P5). ``layout`` (EXA-142) is
    ``full`` (each question with its worked solution) or ``compact`` (a real school key: an
    answer grid for multiple choice, a two-column working table with "Ans:" for the rest)."""
    given = (doc.get("settings") or {}).get("key_options") or {}
    return {
        "show_question": given.get("show_question", True),
        "show_scheme": given.get("show_scheme", True),
        "layout": given.get("layout") or "full",
    }


def number_from(doc: dict) -> int:
    """The paper's first question number (default 1): Paper 1 Booklet B carries on from
    Booklet A, so its first question is 16, not 1 (EXA-134)."""
    return (doc.get("settings") or {}).get("number_from") or 1


def in_key(node: dict) -> bool:
    """Whether a numbered block appears in the answer key (default yes)."""
    return node["attrs"].get("in_key", True) is not False


def block_marks(node: dict) -> int:
    """Marks of one numbered block (templated or free-form)."""
    if node["type"] == "freeformQuestion":
        return freeform_marks(node)
    return node["attrs"]["question"]["question"]["total_marks"]


def section_marking(attrs: dict) -> bool:
    """Whether a section prints the marking margin: its own choice, else on for working sections."""
    chosen = attrs.get("marking")
    if isinstance(chosen, bool):
        return chosen
    return attrs.get("mode") in ("short", "structured")


MARKS_PLACEMENTS = ("none", "question", "answer", "both")


def paper_placement(doc: dict) -> str:
    """The paper-wide marks placement (P2): where [n] prints outside a section's own choice."""
    chosen = (doc.get("settings") or {}).get("marks_placement")
    return chosen if chosen in ("question", "answer", "both") else "answer"


def section_placement(attrs: dict, paper: str) -> str:
    """Where a section's per-question [n] prints (EXA-139): its own choice, else what real papers
    do: ``none`` in multiple-choice and short-answer sections (the header gives the marks),
    the paper-wide placement in structured sections and sections with no mode."""
    chosen = attrs.get("marks_placement")
    if chosen in MARKS_PLACEMENTS:
        return chosen
    return "none" if attrs.get("mode") in ("mcq", "short") else paper


def marks_groups(marks: list[int], first: int) -> list[tuple[int, int, int]]:
    """Runs of consecutive questions worth the same marks, as ``(first, last, marks)``."""
    groups: list[tuple[int, int, int]] = []
    for i, m in enumerate(marks):
        n = first + i
        if groups and groups[-1][2] == m:
            groups[-1] = (groups[-1][0], n, m)
        else:
            groups.append((n, n, m))
    return groups


def paper_outline(doc: dict) -> list[dict]:
    """The paper's sections with derived figures (P4), in order.

    Each entry: ``title``, ``instructions``, ``mode``, ``marks_target``, ``marking`` (authored or
    defaulted), and
    ``first``/``last`` question numbers (both ``None`` when empty), ``count`` and ``marks``
    (derived), ``marks_placement`` (authored or derived, EXA-139) and ``question_marks`` (each
    question's marks, in order). Questions before the first section are not in any section.
    Numbering starts at the paper's ``number_from``.
    """
    out: list[dict] = []
    number = number_from(doc) - 1
    paper = paper_placement(doc)
    for node in doc["content"]["content"]:
        if node["type"] == "section":
            a = node["attrs"]
            out.append(
                {
                    "title": a.get("title") or "",
                    "instructions": a.get("instructions"),
                    "mode": a.get("mode"),
                    "marks_target": a.get("marks_target"),
                    "marking": section_marking(a),
                    "marks_placement": section_placement(a, paper),
                    "question_marks": [],
                    "first": None,
                    "last": None,
                    "count": 0,
                    "marks": 0,
                }
            )
        elif node["type"] in QUESTION_TYPES:
            number += 1
            if out:
                sec = out[-1]
                sec["first"] = sec["first"] or number
                sec["last"] = number
                sec["count"] += 1
                sec["marks"] += block_marks(node)
                sec["question_marks"].append(block_marks(node))
    return out


def cover_page(doc: dict) -> dict | None:
    """The paper's cover block (P7), or ``None``. Validation keeps it first and unique."""
    blocks = doc["content"]["content"]
    return blocks[0] if blocks and blocks[0]["type"] == "coverPage" else None


_PART_PATTERNS = (
    ("booklet_a", re.compile(r"\bbooklet\s*a\b", re.IGNORECASE)),
    ("booklet_b", re.compile(r"\bbooklet\s*b\b", re.IGNORECASE)),
    ("paper_2", re.compile(r"\bpaper\s*(2|two|ii)\b", re.IGNORECASE)),
)


def _part_of(text: object) -> str | None:
    if not isinstance(text, str):
        return None
    return next((part for part, pat in _PART_PATTERNS if pat.search(text)), None)


def paper_part(doc: dict) -> str | None:
    """Which exam-set paper this is (O3): ``"booklet_a"``, ``"booklet_b"``, ``"paper_2"`` or
    ``None``. Read from the cover page's ``paper`` field (the templates write "Paper 1
    (Booklet A)", "Paper 2"), so renaming the paper does not change it; the title is the
    fallback for a paper without a cover, or whose cover names none of the three."""
    try:
        cover = cover_page(doc)
    except (KeyError, TypeError):
        cover = None
    from_cover = _part_of(((cover or {}).get("attrs") or {}).get("paper"))
    return from_cover or _part_of(doc.get("title"))


def total_marks(doc: dict) -> int:
    """Templated totals plus the marks teachers gave their free-form questions."""
    return sum(q["question"]["total_marks"] for q in questions_in_order(doc)) + sum(
        freeform_marks(n) for n in freeform_blocks(doc)
    )


def _walk(nodes: list[dict]):
    for n in nodes:
        yield n
        yield from _walk(n.get("content", []))
        answer = (n.get("attrs") or {}).get("answer")
        if isinstance(answer, dict):
            yield from _walk(answer.get("content", []))


def referenced_assets(doc: dict) -> list[str]:
    """Distinct ``asset_id``s the document's image nodes point at, in first-use order.

    The engine is storage-agnostic: the API checks each id exists and is the caller's.
    """
    seen: dict[str, None] = {}
    for n in _walk(doc["content"]["content"]):
        if n.get("type") == "image":
            seen.setdefault(n["attrs"]["asset_id"], None)
    return list(seen)


def _part_answer(part: dict) -> list[dict]:
    return (part["attrs"].get("answer") or {}).get("content", [])


def _check_parts(node: dict, where: str) -> list[str]:
    """Structure rules the JSON schema cannot express for a multi-part free-form question."""
    content = node["content"]
    parts = freeform_parts(node)
    if not parts:
        return []
    errors = []
    first = next(i for i, c in enumerate(content) if c.get("type") == "freeformPart")
    if first == 0:
        errors.append(f"{where}/content: a multi-part question needs a body before its parts")
    if any(c.get("type") != "freeformPart" for c in content[first:]):
        errors.append(f"{where}/content: parts must come after the body, with nothing between")
    if len(parts) > MAX_PARTS:
        errors.append(f"{where}/content: {len(parts)} parts; the limit is {MAX_PARTS}")
    if node["attrs"].get("marks") is not None:
        errors.append(f"{where}/attrs/marks: with parts, marks belong on the parts")
    return errors


def text_length(nodes: list[dict]) -> int:
    """Characters of text under ``nodes`` (recursive), for the per-block body limit."""
    total = 0
    for n in nodes:
        total += len(n.get("text", ""))
        total += text_length(n.get("content", []))
    return total


def validate_document(doc: object) -> list[str]:
    """Path-pointed errors for ``doc``; an empty list means valid and storable.

    Order matters: structure first (so later checks can trust the shape), then size and
    count limits, then unique block ids, then each embedded question through the
    canonical gate, then the re-solve check for generated snapshots.
    """
    if not isinstance(doc, dict):
        return ["<root>: a document must be an object"]

    errors: list[str] = []
    for err in sorted(_validator().iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    if errors:
        return errors

    size = len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    if size > MAX_CONTENT_BYTES:
        return [f"<root>: document is {size} bytes; the limit is {MAX_CONTENT_BYTES}"]

    blocks = doc["content"]["content"]
    errors += _check_math_and_images(blocks)
    n_sections = sum(1 for n in blocks if n["type"] == "section")
    if n_sections > MAX_SECTIONS:
        errors.append(f"content/content: {n_sections} sections; the limit is {MAX_SECTIONS}")
    for i, node in enumerate(blocks):
        if node["type"] == "coverPage" and i != 0:
            errors.append(f"content/content/{i}: a cover page must be the paper's first block")
    n_blank = sum(1 for n in blocks if n["type"] == "blankPage")
    if n_blank > MAX_BLANK_PAGES:
        errors.append(f"content/content: {n_blank} blank pages; the limit is {MAX_BLANK_PAGES}")
    seen: set[str] = set()
    n_questions = 0
    for i, node in enumerate(blocks):
        if node["type"] not in QUESTION_TYPES:
            continue
        n_questions += 1
        base = f"content/content/{i}/attrs"
        block_id = node["attrs"]["block_id"]
        if block_id in seen:
            errors.append(f"{base}/block_id: duplicate block id {block_id!r}")
        seen.add(block_id)

        if node["type"] == "freeformQuestion":
            where = f"content/content/{i}"
            errors += _check_parts(node, where)
            for label, nodes in (
                ("content", node["content"]),
                ("answer", node["attrs"].get("answer", {}).get("content", [])),
                (
                    "part answers",
                    [a for p in freeform_parts(node) for a in _part_answer(p)],
                ),
            ):
                chars = text_length(nodes)
                if chars > MAX_BLOCK_TEXT_CHARS:
                    loc = f"{where}/" + ("attrs/answer" if label != "content" else "content")
                    errors.append(
                        f"{loc}: {chars} characters of text; the limit is {MAX_BLOCK_TEXT_CHARS}"
                    )
            continue

        question = node["attrs"]["question"]
        q_errors = validate_object(question)
        if q_errors:
            errors += [f"{base}/question/{e}" for e in q_errors]
            continue
        errors += [f"{base}/question: {e}" for e in verify_snapshot(question)]

    if n_questions > MAX_QUESTION_BLOCKS:
        errors.append(
            f"content/content: {n_questions} questions; the limit is {MAX_QUESTION_BLOCKS}"
        )
    return errors


def _check_math_and_images(blocks: list[dict]) -> list[str]:
    errors: list[str] = []
    n_images = 0
    for n in _walk(blocks):
        kind = n.get("type")
        if kind == "image":
            n_images += 1
        elif kind == "math":
            latex = n["attrs"]["latex"]
            # \) would close the \( … \) delimiter the renderer wraps it in.
            if "\\)" in latex or "\\(" in latex or "\\[" in latex or "\\]" in latex:
                errors.append(f"math: {latex[:40]!r} contains a LaTeX delimiter")
    if n_images > MAX_IMAGES:
        errors.append(f"content: {n_images} images; the limit is {MAX_IMAGES}")
    return errors


def _answer_matches(actual: dict, expected: dict, *, decimals_view: bool) -> bool:
    if decimals_view:
        # change-to-decimals: money ÷ 10, shown as a 2-dp decimal (edits._change_to_decimals).
        return (
            actual.get("type") == "decimal"
            and abs(float(actual["value"]) - float(expected["value"]) / 10) < 1e-9
            and actual.get("unit") == expected.get("unit")
        )
    return all(actual.get(k) == v for k, v in expected.items())


def _verify_parts(
    code: str, spec_parts: list[dict], parts: list[dict], solution: dict, q: dict, total: int
) -> list[str]:
    """The multi-part half of :func:`verify_snapshot`: the snapshot has the blueprint's
    parts, in order, each with the re-solved answer and the blueprint's marks."""
    if len(parts) != len(spec_parts):
        return [f"a generated {code} question has exactly {len(spec_parts)} parts"]
    answers = solution.get("answers") or []
    errors = []
    for i, (part, want) in enumerate(zip(parts, spec_parts, strict=True)):
        label = want["label"]
        if part.get("label") != label:
            errors.append(f"part {i} must be labelled ({label})")
        if i >= len(answers) or not _answer_matches(
            part["answer"], answers[i], decimals_view=False
        ):
            errors.append(f"part ({label}) answer does not match the engine's solution")
        if part.get("marks") != want["marks"]:
            errors.append(f"part ({label}) marks do not match blueprint {code} ({want['marks']})")
    if q["total_marks"] != total:
        errors.append(f"marks do not match blueprint {code} ({total})")
    return errors


def verify_snapshot(obj: dict) -> list[str]:
    """Re-solve a *generated* snapshot and check it still is what the engine would produce.

    Documents are private to their owner, so the blast radius of a forged object is the
    owner's own paper — but the engine-proven badge must not be forgeable. Checks: the
    blueprint exists, ``parameters`` satisfy its schema, the solver's own validation
    passes, and the snapshot's answer and marks equal the re-derived ones. Wording is
    deliberately not compared (a tampered sentence cannot change the proven answer).
    Non-generated (sourced) objects are teacher-vouched and not verified here.
    """
    if obj.get("source_type") != "generated":
        return []

    code = obj.get("blueprint_code")
    try:
        spec = load_blueprint(code or "")
        solver = get_solver(code or "")
    except UnknownBlueprint:
        return [f"unknown blueprint {code!r}"]

    params = obj.get("parameters")
    if not isinstance(params, dict):
        return ["a generated question must carry its parameters"]
    param_errors = validate_params(params, spec.parameter_schema)
    if param_errors:
        return [f"parameters invalid for {code}: {'; '.join(param_errors)}"]

    try:
        solution = solver.solve(params)
        report = solver.validate(params, solution)
    except Exception as e:  # solver rejects structurally odd params in its own ways
        return [f"parameters not solvable for {code}: {type(e).__name__}"]
    if not report.get("ok"):
        return [f"parameters fail {code}'s own checks: {report.get('checks')}"]

    parts = obj["question"]["parts"]
    if spec.parts:  # P8c multi-part: every part's label, answer and marks are re-derived
        return _verify_parts(code or "", spec.parts, parts, solution, obj["question"], spec.marks)
    if len(parts) != 1:
        return ["a generated question has exactly one part"]
    decimals_view = obj.get("validation", {}).get("checks", {}).get("representation") == "decimals"
    actual = parts[0]["answer"]
    if actual.get("type") == "choice":
        # P8b multiple choice: the correct option must read exactly as the proven answer does,
        # and no other option may read the same.
        from .mcq import LABELS, answer_text, correct_option_text, legacy_answer_text

        options = actual.get("options", [])
        if [o.get("label") for o in options] != list(LABELS) or any(
            o.get("diagram") for o in options
        ):
            return [f"a generated multiple-choice question has text options {', '.join(LABELS)}"]
        # compared in one litre spelling, so a legacy "18 l" and a new "18 ℓ" count as the same
        texts = [" ".join(str(o.get("text") or "").split()).replace("ℓ", "l") for o in options]
        if len(set(texts)) != len(texts):
            return ["multiple-choice options must all differ"]
        proven = (answer_text(solution["answer"]), legacy_answer_text(solution["answer"]))
        if decimals_view or correct_option_text(actual) not in proven:
            return ["the correct option does not match the engine's solution for these parameters"]
    elif not _answer_matches(actual, solution["answer"], decimals_view=decimals_view):
        return ["answer does not match the engine's solution for these parameters"]
    if parts[0].get("marks") != spec.marks or obj["question"]["total_marks"] != spec.marks:
        return [f"marks do not match blueprint {code} ({spec.marks})"]
    return []
