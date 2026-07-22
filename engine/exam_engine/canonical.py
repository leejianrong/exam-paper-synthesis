"""A1 — canonical object builder + load gate.

The canonical object is a plain ``dict`` (ADR-0016). ``assemble`` builds one from
a blueprint spec + solver output; ``load`` is the validate-on-entry gate for any
object (generated or sourced).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .schema import validate_object

if TYPE_CHECKING:  # avoid an import cycle at runtime
    from .blueprints.base import BlueprintSpec

SCHEMA_VERSION = "1.4.0"


class CanonicalValidationError(Exception):
    """An object failed JSON-Schema validation (path-pointed message)."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load(obj: dict) -> dict:
    """Validate on entry; reject invalid objects (R6.1/R6.2). Returns the object."""
    errors = validate_object(obj)
    if errors:
        raise CanonicalValidationError(errors)
    return obj


def to_json(obj: dict, *, indent: int | None = None) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent)


def _fill(template: str, ctx: dict) -> str:
    """Fill ``{name}`` / ``{name[i]}`` placeholders from ``ctx`` via str.format.

    Collapses internal whitespace runs (YAML folded scalars introduce newlines)
    and trims the ends.
    """
    return " ".join(template.format(**ctx).split())


def assemble(
    spec: BlueprintSpec,
    *,
    seed: int,
    params: dict,
    solution: dict,
    report: dict,
    diagram: dict | None = None,
) -> dict:
    """Build a canonical object for a generated question, then validate it.

    Raises :class:`CanonicalValidationError` on failure — that is an *engine bug*
    (not an infeasibility), so it surfaces loudly.
    """
    ctx = {**params, **solution.get("intermediates", {})}

    template = spec.story_templates[seed % len(spec.story_templates)]
    stem = template.get("stem")
    part_text = _fill(template["text"], ctx)

    steps = []
    for step in spec.solution_template.get("steps", []):
        filled: dict[str, str | None] = {"text": _fill(step["text"], ctx)}
        filled["expr"] = _fill(step["expr"], ctx) if step.get("expr") else None
        steps.append(filled)

    marks_total = sum(m["mark"] for m in spec.marking_scheme)
    if marks_total != spec.marks:
        raise CanonicalValidationError(
            [f"<engine>: marking_scheme sums to {marks_total} but blueprint marks={spec.marks}"]
        )

    part = {
        "label": "",  # single-part (R1.7 multi-part exercised in later slices)
        "text": part_text,
        "marks": spec.marks,
        "answer": solution["answer"],
        "marking_scheme": spec.marking_scheme,
        "solution_steps": steps,
        "diagram": diagram,  # aid bar_model (A5); None when a blueprint has no diagram
    }

    obj = {
        "schema_version": SCHEMA_VERSION,
        "id": f"{spec.code}:{seed}",
        "source_type": "generated",
        "blueprint_code": spec.code,
        "seed": seed,
        "syllabus": spec.syllabus,
        "cognitive": spec.cognitive,
        "parameters": params,
        "question": {
            "stem": stem,
            "parts": [part],
            "total_marks": spec.marks,
        },
        "validation": {
            "status": "pass" if report.get("ok") else "fail",
            "checks": report.get("checks", {}),
        },
        "provenance": {
            "created_by": "engine",
            "llm_used": False,
            "created_at": None,  # stamped at the API boundary (ADR-0016)
            "parent_id": None,
            "version": 1,
        },
    }

    return load(obj)
