"""A3 retry/infeasibility behaviour (ADR-0002)."""

from __future__ import annotations

import random

import pytest

from exam_engine.blueprints.base import BlueprintSpec
from exam_engine.errors import InfeasibleConstraints
from exam_engine.pipeline import MAX_ATTEMPTS, run_pipeline


class _AlwaysFailSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        return {}

    def solve(self, params: dict) -> dict:
        return {"answer": {"type": "integer", "value": 0}, "intermediates": {}}

    def validate(self, params: dict, solution: dict) -> dict:
        return {"ok": False, "checks": {"contrived": False}}


def _stub_spec() -> BlueprintSpec:
    return BlueprintSpec(
        code="always_fail",
        syllabus={},
        cognitive={},
        marks=0,
        parameter_schema={"type": "object"},
        story_templates=[{"text": ""}],
        solution_template={"steps": []},
        marking_scheme=[],
        answer={},
    )


def test_infeasible_after_budget():
    with pytest.raises(InfeasibleConstraints) as excinfo:
        run_pipeline(_stub_spec(), _AlwaysFailSolver(), seed=1)
    err = excinfo.value
    assert err.attempts == MAX_ATTEMPTS == 20
    assert err.failures == 20
    # failure_rate > 0.5 is the author-misconfigured signal.
    assert err.failure_rate == 1.0
    assert err.last_checks == {"contrived": False}
