# ADR-0005: Answer key and marking model

- Status: Accepted
- Deciders: project owner
- Related: Q-E1, Q-E1b, Q-E2, Q-E3

## Context

The answer key is a first-class product feature. We must decide what each
generated question carries for marking and worked solutions.

## Decision

Every P5–P6 question carries **all three**:

1. a **final answer** (typed, with units where relevant),
2. a **mark scheme** (ordered awardable marks), and
3. **worked solution steps**.

All three are derived deterministically from the blueprint solver's answer and
intermediate values (no LLM in the MVP).

**Marking representation (Q-E1b, decided):** store full **M/A/B** mark types on the
canonical object (future-proofs O-Level). **Render** primary P5–P6 worksheets as
simple marks-per-part `[n]`; surface the M/A/B breakdown only in a **detailed
answer-key mode**.

## Consequences

- Marks must be modelled on the canonical object (`marking_scheme`, `cognitive.marks`).
- Solver `intermediates` must be rich enough to template real worked steps and to
  justify each awarded mark.

## Resolved

- **Q-E2:** solution steps are structured `{text, expr?}`, **deterministic** in
  the MVP, held **per part**; `expr` is optional and machine-checkable.
- **Q-E3:** the answer key **embeds the aid diagram (bar model)** in the worked
  solution for ratio/fraction/percentage families (the model is the method);
  geometric-figure diagrams stay with the question and are not repeated in the key.
