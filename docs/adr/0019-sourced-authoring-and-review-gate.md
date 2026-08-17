# ADR-0019: Sourced authoring and the review gate — flag unreviewed content, never block it

- Status: Accepted
- Deciders: project owner
- Related: `docs/planning/editor/SCHEMA-FIT.md` G19, `docs/planning/editor/SHAPING.md` (R2, R5, Shape A10–A11), ADR-0011 (external material, sourced schema), ADR-0014 (schema formalization, `validation.status`/`checks`)

## Context

`SCHEMA-FIT.md`'s G19 found that **every** real answer key examined contains
errors the extractor faithfully transcribed — a statement from the wrong
question, arithmetic that doesn't add up, a wrong name in the working. This is
not incidental: it means `working_shown` (or any hand-typed answer key) cannot
be imported and trusted silently. The schema already has the fields for this
(`validation.status`, `checks.human_reviewed`, from ADR-0014) but nothing in the
MVP's flow used them as a gate — there was no editor to gate.

The open question this ADR resolves: once the editor exists, does an
unreviewed sourced object **block** use in a paper, or only get **flagged**?

## Decision

- **Every freshly authored or imported `sourced` object lands with
  `validation.status:"unverified"`.** This is automatic, not something the
  author opts into.
- **A review action is the only way to mark content trustworthy**: the reviewer
  can hand-edit any field (stem, parts, answer, marking scheme, solution steps,
  diagram) and then explicitly flips `checks.human_reviewed:true`. The object is
  re-validated against the canonical schema on this edit, same as any other
  write.
- **Unreviewed content is flagged, not blocked.** The bank's search/browse
  distinguishes reviewed from unreviewed, and assembling a paper/worksheet from
  unreviewed content surfaces a visible warning — but does not prevent it. The
  owner is the sole user and the sole reviewer; blocking would only add friction
  to the same person's own iterative workflow, without adding any safety a
  single-user, non-published tool needs. Flagging preserves the trust signal
  that matters (nothing gets handed to a student silently unreviewed) without
  turning review into a hard gate on every other action.
- This is unchanged, and reinforced, for questions imported by the external
  extraction process (`docs/planning/editor/extraction-prompt.md`): the
  extractor's explicit rule against "fixing" anything is exactly what makes G19's
  errors visible in the first place, and the review gate is where they get
  corrected — never silently, and never by an LLM.

## Consequences

- No sourced object is ever auto-promoted to trusted; the review action is the
  only path, and it's always a human edit.
- The editor's review panel (and the CLI's `bank review` in the interim, per
  `docs/planning/editor/SLICES.md` E1) is required UI/CLI surface, not optional
  polish — R5.2 is a Must-have, not a Nice-to-have.
- `source_type:"generated"` objects are unaffected — they're proven by
  construction (the engine's correctness authority) and never pass through this
  gate.
- If a future multi-user phase is ever built, this ADR's "flag don't block"
  reasoning is single-user-specific and should be revisited — a shared bank with
  multiple authors likely does need a hard gate before content is usable by
  someone other than its author.
