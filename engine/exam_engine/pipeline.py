"""A3 — deterministic generation pipeline.

``generate(blueprint_code, seed)`` is a pure function of its inputs (ADR-0002/0016):
sample -> validate params -> solve -> validate -> assemble -> schema-validate,
with a bounded retry budget.
"""

from __future__ import annotations

import hashlib
import json
import random

from .blueprints.base import BlueprintSpec, Solver, validate_params
from .blueprints.registry import get_solver, load_blueprint
from .canonical import assemble
from .diagram import check_consistency
from .errors import DiagramInconsistent, InfeasibleConstraints

MAX_ATTEMPTS = 20  # ADR-0002


def build_part_diagram(solver: Solver, params: dict, solution: dict) -> dict | None:
    """Build the aid diagram spec if the solver defines one (A5); else ``None``.

    Keeping this optional lets V1-style solvers (no ``diagram`` method) still run.
    """
    diagram_fn = getattr(solver, "diagram", None)
    if diagram_fn is None:
        return None
    return diagram_fn(params, solution)


def run_pipeline(spec: BlueprintSpec, solver: Solver, seed: int) -> dict:
    """The retry loop, decoupled from content loading so it is unit-testable."""
    rng = random.Random(seed)
    failures = 0
    last_checks: dict = {}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        params = solver.sample(spec.parameter_schema, rng)

        param_errors = validate_params(params, spec.parameter_schema)
        if param_errors:
            failures += 1
            last_checks = {"parameter_schema": "; ".join(param_errors)}
            continue

        solution = solver.solve(params)
        report = solver.validate(params, solution)
        last_checks = report.get("checks", {})
        if not report.get("ok"):
            failures += 1
            continue

        # A5: build the aid diagram (if any) and gate its consistency (R3.3).
        # A deterministic diagram from correct values is always consistent, so a
        # failure here is an engine bug, surfaced loudly rather than retried.
        diagram = build_part_diagram(solver, params, solution)
        if diagram is not None:
            dchecks = check_consistency(diagram, params, solution)
            report.setdefault("checks", {})["diagram_consistent"] = all(dchecks.values())
            if not all(dchecks.values()):
                raise DiagramInconsistent(spec.code, dchecks)

        # Success: assemble + schema-validate (a failure here is an engine bug).
        return assemble(
            spec, seed=seed, params=params, solution=solution, report=report, diagram=diagram
        )

    raise InfeasibleConstraints(spec.code, MAX_ATTEMPTS, failures, last_checks)


def generate(blueprint_code: str, seed: int) -> dict:
    """Generate one canonical question object. Pure in ``(blueprint_code, seed)``."""
    spec = load_blueprint(blueprint_code)
    solver = get_solver(blueprint_code)
    return run_pipeline(spec, solver, seed)


def param_hash(obj: dict) -> str:
    """Normalized-parameter hash for in-session dedup (ADR G4)."""
    payload = json.dumps(obj.get("parameters"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
