# ADR-0007: Diagram policy per question family

- Status: Proposed (needs validation against gold PSLE samples)
- Deciders: project owner
- Related: Q-F1, Q-F2, Q-F3

## Context

Some question families are meaningless without a figure; others merely benefit
from a supporting model. We must decide, per family, whether a diagram is required
and whether the teacher can toggle it.

## Decision (proposed)

Two tiers:

- **Mandatory diagram (the figure *is* the question; not toggleable):** composite
  / overlapping rectangles, area & perimeter of shapes, fraction of a shaded
  figure. (Later: volume/cuboids when the solid is described visually.)
- **Optional bar-model aid (toggleable; also rendered in the answer key):** ratio
  (incl. before-after), fraction of a quantity, percentage.

Diagram specs are produced by the blueprint's `diagram(params, solution)` from
solved values (deterministic; not LLM).

## Consequences

- The UI needs a per-question "include diagram" toggle only for the aid tier.
- Mandatory-diagram families cannot be generated without a working renderer for
  their figure type.

## Open / validation

- This split is a reasoned recommendation, **not yet verified**. Validate against
  ~10 gold-standard PSLE samples in Phase 0 (optional deeper sourced research pass
  available).
- Define exactly what "diagram matches the question" validation checks (Q-F3).
