# ADR-0015: Principled difficulty model (levers + per-topic ladder)

- Status: Accepted
- Deciders: project owner
- Related: Q-D2, Q-D3, Q-H2, ADR-0003, ADR-0009, ADR-0013

## Context

"Make harder/easier" needs a well-defined target, and difficulty must be principled
rather than arbitrary. It also has to reconcile difficulty-via-composition (number
of parts / marks) with intrinsic per-part difficulty.

## Decision

- Difficulty operates at **two levels**: **composition** (harder = more, mutually
  dependent, higher-mark `parts[]`) and **intrinsic** (a single part made harder
  via named levers).
- Adopt a fixed set of **difficulty levers** (reasoning depth, sub-parts, number
  type, direction/inverse, extraneous info, representation translation, hidden
  structure, cross-topic, heuristic demand, answer form). Each blueprint tags the
  levers it uses in `cognitive.difficulty_levers[]`. Full detail: `docs/DIFFICULTY.md`.
- **Ladder:** 3 blueprints per topic (easy/medium/hard) × 5 MVP topics = **15
  blueprints for v1** (supersedes the earlier "5 blueprints" figure in ADR-0003).
- **Edit ops:** make harder/easier = swap to the sibling one rung up/down the same
  topic ladder; regenerate = resample within the rung (ADR-0009).
- Difficulty is **author-declared per blueprint** and partly **empirical** —
  calibrated later against gold samples / teacher feedback.

## Consequences

- v1 blueprint count rises from 5 to 15; recommend proving **one full topic ladder
  end-to-end** before building the rest.
- `cognitive.difficulty_levers[]` added to the schema (optional array).
- Sibling-swap for harder/easier is now always defined (a ladder exists per topic).

## Open

- Q-D3: a blueprint stays fixed to one profile (the ladder provides the other
  profiles), confirmed by this decision.
- Whether the swap pool may also include **sourced** questions from the internal
  bank (see ADR-0011 update).
