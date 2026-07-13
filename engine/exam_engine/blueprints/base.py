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
        """Return ``{"answer": {...}, "intermediates": {...}}``."""
        ...

    def validate(self, params: dict, solution: dict) -> dict:
        """Return ``{"ok": bool, "checks": {name: bool|str|None}}``."""
        ...

    # Optional: def diagram(self, params, solution) -> dict  (added in V2)


@dataclass
class BlueprintSpec:
    """Parsed ``content/blueprints/<code>.yaml`` (declarative data only)."""

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
    _extra: dict = field(default_factory=dict)

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
        }
        return cls(
            code=data["code"],
            syllabus=data["syllabus"],
            cognitive=data["cognitive"],
            marks=data["marks"],
            parameter_schema=data["parameter_schema"],
            story_templates=data["story_templates"],
            solution_template=data["solution_template"],
            marking_scheme=data["marking_scheme"],
            answer=data["answer"],
            diagram=data.get("diagram"),
            _extra={k: v for k, v in data.items() if k not in known},
        )


def validate_params(params: dict, parameter_schema: dict) -> list[str]:
    """Validate sampled params against the blueprint's declared schema (ADR-0014)."""
    return validate_against(params, parameter_schema)
