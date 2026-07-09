# ADR-0014: Schema formalization — versioning, validation, parameters, semantics

- Status: Accepted
- Deciders: project owner
- Related: Q-S1, Q-S5, Q-F3, Q-G2, ADR-0004, ADR-0012, ADR-0013

## Context

The canonical schema is the top-priority, interchange-grade artifact. We fix how
it is versioned, validated, and what its runtime "rock-solid" guarantees are.

## Decision

- **Formal spec:** **JSON Schema (Draft 2020-12)**, stored in a top-level
  **`schemas/`** directory, consumed by both `engine` and `tests`. It is the
  source of truth for the canonical object, the `answer` union, and the `diagram`
  union.
- **Versioning:** every object carries a `schema_version` (**semver**, starting
  `1.0.0`). Additive changes bump minor; breaking changes bump major.
- **Validation on load:** every canonical object — **generated and sourced** — is
  JSON-Schema-validated whenever it enters the system; invalid objects are
  rejected with clear, path-pointed errors. Validation is enforced, not assumed.
- **Parameters (Q-S5):** a blueprint **declares a parameter schema** (types +
  ranges + enums); a generated object's `parameters` must validate against that
  declared schema. Not a free-form blob.
- **Diagram-consistency (Q-F3):** the blueprint's `validate` asserts that **every
  value/label in the diagram spec equals the corresponding parameter or solved
  value** (bar units = ratio units; rectangle dims = params; annotation text =
  the sampled amount). Checked per family.
- **Answer uniqueness (Q-G2):** for a word problem, "unique answer" means the
  **solver is total and deterministic** and the blueprint's constraints exclude
  ambiguous/degenerate cases (e.g. negative lengths, multiple valid readings) — a
  by-construction guarantee, not enumeration of a solution space.

## Consequences

- A shared validation utility gates every object entering the engine, API, or the
  externally-prepared question set.
- Blueprints must ship their declared parameter schema and per-family diagram
  consistency assertions.
- Schema evolution is disciplined via semver + on-load validation.
