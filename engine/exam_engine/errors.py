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


class BlueprintMisconfigured(EngineError):
    """A blueprint that succeeds but fails > 50% of sampling attempts (flaky)."""

    def __init__(self, code: str, failure_rate: float):
        self.code = code
        self.failure_rate = failure_rate
        super().__init__(
            f"blueprint {code!r} is likely misconfigured: failure_rate={failure_rate:.2f} (> 0.5)"
        )
