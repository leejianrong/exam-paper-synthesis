# ADR-0003: Blueprint representation and authoring

- Status: Proposed
- Deciders: project owner
- Related: Q-B1, Q-B2, Q-B4

## Context

A blueprint is the core engine primitive (a parametric generator). We must decide
its representation (data vs code) and how blueprints are authored and trusted.

## Decision (proposed)

- A blueprint = **one YAML file + one named Python solver module**.
  - YAML holds declarative data: metadata, parameter schema, wording/solution
    templates, constraints, cognitive tags, marks, optional `diagram` type.
  - The Python solver owns the math via a small interface: `sample`, `solve`,
    `validate`, and optional `diagram`.
- Of the six components, `diagram` is **optional**; the other five are required.
- **Authoring is a dev-time activity**, not an in-app MVP feature. Blueprints are
  curated, version-controlled, human-reviewed assets.
- Authoring workflow: draft YAML+solver (LLM may scaffold) → hand-write
  **golden fixtures** (`params → expected answer/marks`, human-verified) → generate
  N samples → human review → mark `approved`.

## Consequences

- Data stays reviewable/diffable and can feed a future authoring UI; math stays in
  trustworthy code.
- Every blueprint carries golden fixtures — correctness is regression-tested.
- Slightly more moving parts per blueprint (a YAML + a module + fixtures) than a
  single-file approach, accepted for safety and clarity.

## v1 blueprint set (Q-B3, resolved)

- **15 blueprints = a 3-rung difficulty ladder (easy/medium/hard) × 5 topics**
  (Ratio, Fractions, Percentage, Area/Geometry, Speed). See ADR-0015 and
  `docs/DIFFICULTY.md`. Build **one full topic ladder end-to-end first**.
  (Supersedes the earlier "5 blueprints" figure.)

## Open

- Story-template variety per blueprint (Q-B5).
