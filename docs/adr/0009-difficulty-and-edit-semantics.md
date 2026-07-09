# ADR-0009: Difficulty model and edit-operation semantics

- Status: Accepted
- Deciders: project owner
- Related: Q-D2, Q-H2, Q-D3

## Context

We need to define where difficulty comes from and what the fixed edit operations
(from ADR-0006) actually do to a question.

## Decision

- **Difficulty is author-declared per blueprint.** Each blueprint targets a single
  difficulty + cognitive profile; difficulty is not computed from parameters.
- **Edit-operation semantics:**
  - **Regenerate** → resample parameters within the *same* blueprint (same
    difficulty, new numbers).
  - **Make harder / make easier** → swap to a **sibling blueprint** in the same
    topic tagged one profile up/down. (Not merely larger numbers.)
  - **Change to decimals / add diagram** → transform the current canonical object
    (representation change / toggle the optional diagram), re-validated.

## Consequences

- Requires blueprints to be organised into **topic families with an ordered
  difficulty ladder** so "harder/easier" has a defined sibling to swap to.
- If a topic lacks a sibling one step up/down, that edit is unavailable (UI must
  reflect this).
- Each edit yields a new canonical object with lineage (ADR-0004).

## Open

- Q-D3: whether a blueprint may ever span multiple profiles via parameters
  (current decision implies **fixed to one**; confirm).
