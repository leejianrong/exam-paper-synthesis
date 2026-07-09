# ADR-0002: Deterministic-first generation (LLM optional) + taxonomy + retry budget

- Status: Accepted
- Deciders: project owner
- Related: Q-J1, Q-D1, Q-G1

## Context

The core risk is that math errors destroy trust. The product principle is that
mathematical truth comes from deterministic tools, with the LLM only polishing.
We need to decide whether the MVP depends on an LLM at all, fix the difficulty/
cognitive vocabulary, and bound the generation retry loop.

## Decision

- **The MVP runs fully deterministically.** Question wording, answers, steps, and
  diagrams are produced by code (parameter sampling + Python solvers + templates).
  An **LLM is not required** for the MVP to function.
- **LLM wording polish is a deferred, optional enhancement** — introduced only
  after the deterministic engine is proven, behind a swappable client. No API keys
  or LLM cost are needed on day one.
- **Taxonomy:** `difficulty ∈ {easy, medium, hard}`;
  `cognitive_level ∈ {routine_procedural, complex_familiar, non_routine_heuristic}`.
  Additional axes (heuristics used, representation, answer type) are carried as
  tags on the canonical object.
- **Retry budget:** on validation failure (bad numbers, non-unique answer,
  infeasible geometry), resample parameters up to **20 times** per requested
  instance, then raise a structured "infeasible constraints" error. If a blueprint
  fails on **>50%** of attempts across a run, flag it as author-misconfigured.

## Consequences

- Trust and reproducibility come from code + golden fixtures, not model behaviour.
- A clean seam is needed so the LLM can be added later without reworking the core.
- The retry cap prevents infinite loops and turns constraint bugs into visible
  signals rather than silent slowness.
