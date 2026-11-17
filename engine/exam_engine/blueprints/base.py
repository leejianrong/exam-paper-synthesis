"""A2 — solver interface + blueprint spec + parameter validation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..schema import validate_against


@runtime_checkable
class Solver(Protocol):
    """The maths lives here (ADR-0003). Deterministic given its inputs."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        """Draw a valid, non-degenerate parameter set (constraints by construction)."""
        ...

    def solve(self, params: dict) -> dict:
        """Return ``{"answer": {...}, "intermediates": {...}}``.

        A multi-part blueprint (P8c, ``BlueprintSpec.parts``) returns ``"answers"`` instead:
        one answer per part, in the order of the YAML ``parts`` list.
        """
        ...

    def validate(self, params: dict, solution: dict) -> dict:
        """Return ``{"ok": bool, "checks": {name: bool|str|None}}``."""
        ...

    # Optional: def diagram(self, params, solution) -> dict  (added in V2)
    # Optional: def table(self, params, solution) -> dict  (EXA-148) the data table printed
    #   before the parts (``question.table``: caption, headers, rows of display strings).
    # Optional: def distractors(self, params, solution) -> list[tuple[number, str]]
    #   (EXA-122) the "common wrong answers" for a multiple-choice copy (mcq.to_mcq): values
    #   in the answer's own quantity and unit, each with the reason a pupil gives it, best
    #   first. mcq filters out the answer itself and anything implausible, then falls back
    #   to its generic candidates; the correct option is still proven by verify_snapshot.
    # Optional: mcq_ascending = False  (EXA-141) the multiple-choice copy keeps a seeded option
    #   order instead of ascending order, for a question whose answer is an extreme of the
    #   options ("which is the greatest?"), where ascending order would give it away.


@dataclass
class BlueprintSpec:
    """Parsed ``exam_engine/content/blueprints/<code>.yaml`` (declarative data only)."""

    code: str
    syllabus: dict
    cognitive: dict
    marks: int
    parameter_schema: dict
    story_templates: list[dict]
    solution_template: dict
    marking_scheme: list[dict]
    answer: dict
    diagram: object = None
    param_roles: dict = field(default_factory=dict)
    # P8c multi-part blueprints: one entry per part, in print order, each
    # ``{label, text, marks, marking_scheme, solution_template, answer}``. Empty for a
    # single-part blueprint (the top-level ``marking_scheme``/``solution_template``/
    # ``answer`` describe its only part). ``marks`` is always the question total.
    parts: list[dict] = field(default_factory=list)
    _extra: dict = field(default_factory=dict)

    @property
    def is_multipart(self) -> bool:
        return bool(self.parts)

    @property
    def part_count(self) -> int:
        """How many parts every question of this blueprint has (1 for single-part)."""
        return len(self.parts) or 1

    @classmethod
    def from_dict(cls, data: dict) -> BlueprintSpec:
        known = {
            "code",
            "syllabus",
            "cognitive",
            "marks",
            "parameter_schema",
            "story_templates",
            "solution_template",
            "marking_scheme",
            "answer",
            "diagram",
            "param_roles",
            "parts",
        }
        parts = data.get("parts") or []
        return cls(
            code=data["code"],
            syllabus=data["syllabus"],
            cognitive=data["cognitive"],
            marks=data["marks"],
            parameter_schema=data["parameter_schema"],
            story_templates=data["story_templates"],
            # A multi-part blueprint describes these per part, so they are optional there.
            solution_template=data["solution_template"] if not parts else {},
            marking_scheme=data["marking_scheme"] if not parts else [],
            answer=data["answer"] if not parts else {},
            diagram=data.get("diagram"),
            param_roles=data.get("param_roles") or {},
            parts=parts,
            _extra={k: v for k, v in data.items() if k not in known},
        )


def check_parts(code: str, spec: BlueprintSpec) -> list[str]:
    """Problems with a multi-part blueprint's ``parts`` (empty when consistent, P8c).

    At least two parts, labels a, b, c… in order, each part's marking scheme sums to
    its marks, and the parts' marks sum to the blueprint's ``marks``.
    """
    if not spec.parts:
        return []
    errors = []
    if len(spec.parts) < 2:
        errors.append(f"{code}: a multi-part blueprint needs at least two parts")
    for i, part in enumerate(spec.parts):
        want = "abcdefgh"[i]
        if part.get("label") != want:
            errors.append(f"{code}: part {i} is labelled {part.get('label')!r}, not {want!r}")
        scheme = sum(m["mark"] for m in part.get("marking_scheme") or [])
        if scheme != part.get("marks"):
            errors.append(
                f"{code}: part ({want}) marking_scheme sums to {scheme}, marks={part.get('marks')}"
            )
    total = sum(p.get("marks") or 0 for p in spec.parts)
    if total != spec.marks:
        errors.append(f"{code}: parts' marks sum to {total} but blueprint marks={spec.marks}")
    return errors


def validate_params(params: dict, parameter_schema: dict) -> list[str]:
    """Validate sampled params against the blueprint's declared schema (ADR-0014)."""
    return validate_against(params, parameter_schema)


PARAM_ROLES = frozenset({"name", "item", "number", "choice"})
# Roles a teacher may change without touching the maths (ADR-0021 tier 1).
COSMETIC_ROLES = frozenset({"name", "item"})


def check_param_roles(code: str, spec: BlueprintSpec) -> list[str]:
    """Problems with a blueprint's ``param_roles`` (empty when complete and valid).

    Every ``parameter_schema`` property needs exactly one declared role, so a new
    blueprint can never ship with an unclassified parameter (W1a).
    """
    props = set((spec.parameter_schema.get("properties") or {}).keys())
    roles = spec.param_roles
    errors = [
        f"{code}: parameter {k!r} has no param_roles entry" for k in sorted(props - set(roles))
    ]
    errors += [
        f"{code}: param_roles names unknown parameter {k!r}" for k in sorted(set(roles) - props)
    ]
    for key, entry in roles.items():
        role = entry.get("role") if isinstance(entry, dict) else None
        if role not in PARAM_ROLES:
            errors.append(f"{code}: parameter {key!r} has invalid role {role!r}")
    return errors
