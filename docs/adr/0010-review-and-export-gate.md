# ADR-0010: Human review gate before export

- Status: Accepted
- Deciders: project owner
- Related: Q-G3, Q-L1, Q-H3

## Context

Automated validation guarantees mathematical correctness but not pedagogical
quality, wording clarity, or fit for a particular class. The owner wants a human
in the loop before questions reach an exported worksheet.

## Decision

- The MVP includes a **human review gate**. Passing automated validation is
  **necessary but not sufficient** to export.
- In the review step the user sees each generated question with its **validation
  status/badge** and can **approve / regenerate / discard**.
- Export produces a worksheet from the **approved** set only.

## Consequences

- The UI needs a review surface (per-question status + approve/regenerate/discard
  actions) between generation and export.
- Even in the ephemeral v1 (ADR-0001), a **session-scoped "current worksheet"**
  collection of approved questions must be held until export.
- Review actions are a natural place to capture quality signals (ties to Q-L1).

## Open

- Whether the review gate captures structured feedback/ratings (Q-L1).
- Whether a teacher may hand-edit question text at the gate, and how that
  interacts with the canonical-object-as-truth principle (Q-H3).
