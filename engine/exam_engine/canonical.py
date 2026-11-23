"""A1 — canonical object builder + load gate.

The canonical object is a plain ``dict`` (ADR-0016). ``assemble`` builds one from
a blueprint spec + solver output; ``load`` is the validate-on-entry gate for any
object (generated or sourced).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .chart import check_chart_consistency
from .cube_stack import check_cube_stack_consistency
from .diagram import check_panels_consistency
from .expression import check_expression_consistency
from .grid import check_grid_consistency
from .net import check_net_consistency
from .number_line import check_number_line_consistency
from .schema import validate_diagram, validate_object
from .solid import check_solid_consistency

if TYPE_CHECKING:  # avoid an import cycle at runtime
    from .blueprints.base import BlueprintSpec

SCHEMA_VERSION = "1.15.0"


class CanonicalValidationError(Exception):
    """An object failed JSON-Schema validation (path-pointed message)."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load(obj: dict) -> dict:
    """Validate on entry; reject invalid objects (R6.1/R6.2). Returns the object."""
    errors = validate_object(obj) or _diagram_errors(obj) + _answer_errors(obj) + _own_errors(obj)
    if errors:
        raise CanonicalValidationError(errors)
    return obj


def _own_errors(obj: dict) -> list[str]:
    """A teacher's own question (schema 1.15.0, EXA-90): its block must be a valid one, and
    ``own-`` ids belong to such questions only (so saving one can never replace an import)."""
    from .own_question import check  # runtime import: own_question builds on this module

    return check(obj)


_ORDER_HINT = (
    " (write higher powers first, then symbols in code-point order: capitals, then"
    " lowercase, then π; constant last)"
)


def _answer_errors(obj: dict) -> list[str]:
    """Semantic gate for ``expression`` answers (schema 1.11.0)."""
    return [
        f"question.parts[{i}].answer: expression inconsistent: {name}"
        + (_ORDER_HINT if name == "terms_in_canonical_order" else "")
        for i, part in enumerate(obj["question"]["parts"])
        if (part.get("answer") or {}).get("type") == "expression"
        for name, ok in check_expression_consistency(part["answer"]).items()
        if not ok
    ]


def _diagram_errors(obj: dict) -> list[str]:
    """Semantic gate for ``chart`` (1.7.0), ``solid`` (1.8.0), ``number_line`` (1.9.0),
    ``panels`` (1.10.0), ``cube_stack`` (1.12.0), ``net`` (1.13.0) and ``grid`` (1.14.0)
    diagrams, run once the
    object is schema-valid: the numbers must agree with the figure's own axis/dims.
    Path-pointed like the schema errors."""
    q = obj["question"]
    found: list[tuple[str, dict]] = []
    if q.get("diagram"):
        found.append(("question.diagram", q["diagram"]))
    for i, part in enumerate(q["parts"]):
        if part.get("diagram"):
            found.append((f"question.parts[{i}].diagram", part["diagram"]))
        answer = part.get("answer") or {}
        for j, opt in enumerate(
            answer.get("options", []) if answer.get("type") == "choice" else []
        ):
            if opt.get("diagram"):
                found.append((f"question.parts[{i}].answer.options[{j}].diagram", opt["diagram"]))
    return _semantic_diagram_errors(found)


def load_diagram(spec: dict) -> dict:
    """Validate one diagram on its own (schema, then the semantic gate)."""
    errors = validate_diagram(spec) or _semantic_diagram_errors([("diagram", spec)])
    if errors:
        raise CanonicalValidationError(errors)
    return spec


def _semantic_diagram_errors(found: list[tuple[str, dict]]) -> list[str]:
    checkers = {
        "chart": check_chart_consistency,
        "solid": check_solid_consistency,
        "number_line": check_number_line_consistency,
        "panels": check_panels_consistency,
        "cube_stack": check_cube_stack_consistency,
        "net": check_net_consistency,
        "grid": check_grid_consistency,
    }
    errors = []
    for path, spec in found:
        check = checkers.get(str(spec.get("type")))
        if check:
            errors += [
                f"{path}: {spec['type']} inconsistent: {name}"
                for name, ok in check(spec).items()
                if not ok
            ]
    return errors


def to_json(obj: dict, *, indent: int | None = None) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent)


def _scheme(scheme: list[dict], ctx: dict) -> list[dict]:
    """The marking scheme, a description with ``{name}`` filled from ``ctx`` (EXA-154: a line
    can name what this question asks for); one without braces is left exactly as written. A
    copy, so editing a question never edits the cached blueprint."""
    return [
        {**m, "description": _fill(m["description"], ctx)} if "{" in m["description"] else {**m}
        for m in scheme
    ]


def _fill(template: str, ctx: dict) -> str:
    """Fill ``{name}`` / ``{name[i]}`` placeholders from ``ctx`` via str.format.

    Collapses internal whitespace runs (YAML folded scalars introduce newlines)
    and trims the ends.
    """
    return " ".join(template.format(**ctx).split())


def _steps(solution_template: dict, ctx: dict) -> list[dict]:
    steps = []
    for step in solution_template.get("steps", []):
        filled: dict[str, str | None] = {"text": _fill(step["text"], ctx)}
        filled["expr"] = _fill(step["expr"], ctx) if step.get("expr") else None
        steps.append(filled)
    return steps


def _multipart(
    spec: BlueprintSpec, ctx: dict, template: dict, solution: dict, diagram: dict | None
) -> tuple[str, list[dict]]:
    """The shared stem and lettered parts of a multi-part blueprint (P8c).

    Each part gets the solver's answer at its index and the YAML part's own marks,
    marking scheme and solution steps. A figure (if any) goes on the first part.
    """
    answers = solution.get("answers") or []
    if len(answers) != len(spec.parts):
        raise CanonicalValidationError(
            [f"<engine>: solver gave {len(answers)} answers for {len(spec.parts)} parts"]
        )
    parts = [
        {
            "label": p["label"],
            "text": _fill(p["text"], ctx),
            "marks": p["marks"],
            "answer": answer,
            "marking_scheme": _scheme(p["marking_scheme"], ctx),
            "solution_steps": _steps(p.get("solution_template") or {}, ctx),
            "diagram": diagram if i == 0 else None,
        }
        for i, (p, answer) in enumerate(zip(spec.parts, answers, strict=True))
    ]
    return _fill(template["stem"], ctx), parts


def assemble(
    spec: BlueprintSpec,
    *,
    seed: int,
    params: dict,
    solution: dict,
    report: dict,
    diagram: dict | None = None,
    table: dict | None = None,
) -> dict:
    """Build a canonical object for a generated question, then validate it.

    Raises :class:`CanonicalValidationError` on failure — that is an *engine bug*
    (not an infeasibility), so it surfaces loudly.
    """
    ctx = {**params, **solution.get("intermediates", {})}

    template = spec.story_templates[seed % len(spec.story_templates)]
    stem: str | None
    if spec.parts:
        stem, parts = _multipart(spec, ctx, template, solution, diagram)
    else:
        stem = template.get("stem")
        marks_total = sum(m["mark"] for m in spec.marking_scheme)
        if marks_total != spec.marks:
            raise CanonicalValidationError(
                [f"<engine>: marking_scheme sums to {marks_total} but blueprint marks={spec.marks}"]
            )
        parts = [
            {
                "label": "",  # single-part
                "text": _fill(template["text"], ctx),
                "marks": spec.marks,
                "answer": solution["answer"],
                "marking_scheme": _scheme(spec.marking_scheme, ctx),
                "solution_steps": _steps(spec.solution_template, ctx),
                "diagram": diagram,  # aid bar_model (A5); None when a blueprint has no diagram
            }
        ]

    question: dict = {"stem": stem}
    if table is not None:  # a data table printed before the parts (EXA-148)
        question["table"] = table
    obj = {
        "schema_version": SCHEMA_VERSION,
        "id": f"{spec.code}:{seed}",
        "source_type": "generated",
        "blueprint_code": spec.code,
        "seed": seed,
        "syllabus": spec.syllabus,
        "cognitive": spec.cognitive,
        "parameters": params,
        "question": {**question, "parts": parts, "total_marks": spec.marks},
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
