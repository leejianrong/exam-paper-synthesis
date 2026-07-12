"""Structured engine errors (ADR-0002 retry/infeasibility, ADR-0016)."""

from __future__ import annotations


class EngineError(Exception):
    """Base class for all engine-raised errors."""


class UnknownBlueprint(EngineError):
    """Requested a blueprint code that is not registered / has no content file."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"unknown blueprint: {code!r}")


class InfeasibleConstraints(EngineError):
    """A blueprint could not produce a valid instance within the retry budget.

    Carries ``failure_rate`` (1.0 on exhaustion) — a value > 0.5 is the
    author-misconfigured signal (ADR-0002).
    """

    def __init__(self, code: str, attempts: int, failures: int, last_checks: dict | None = None):
        self.code = code
        self.attempts = attempts
        self.failures = failures
        self.failure_rate = failures / attempts if attempts else 1.0
        self.last_checks = last_checks or {}
        super().__init__(
            f"blueprint {code!r} infeasible after {attempts} attempts "
            f"(failure_rate={self.failure_rate:.2f}); last checks={self.last_checks}"
        )


class DiagramInconsistent(EngineError):
    """A built diagram spec disagrees with the question's numbers (R3.3).

    A deterministic diagram built from correct values is always consistent, so
    this signals an engine/blueprint bug — it surfaces loudly rather than being
    retried as an infeasibility (mirrors a schema-invalid assembly).
    """

    def __init__(self, code: str, checks: dict):
        self.code = code
        self.checks = checks
        failed = [name for name, ok in checks.items() if not ok]
        super().__init__(
            f"blueprint {code!r} produced an inconsistent diagram; failed checks: {failed}"
        )


class EditNotApplicable(EngineError):
    """An edit operation was requested for an object it cannot apply to (ADR-0009).

    e.g. ``make-harder`` on the hardest rung, or an op not in ``available_ops``.
    """

    def __init__(self, op: str, reason: str):
        self.op = op
        self.reason = reason
        super().__init__(f"edit {op!r} not applicable: {reason}")


class BlueprintMisconfigured(EngineError):
    """A blueprint that succeeds but fails > 50% of sampling attempts (flaky)."""

    def __init__(self, code: str, failure_rate: float):
        self.code = code
        self.failure_rate = failure_rate
        super().__init__(
            f"blueprint {code!r} is likely misconfigured: failure_rate={failure_rate:.2f} (> 0.5)"
        )
