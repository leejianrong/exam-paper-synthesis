# ADR-0023: A teacher's own question in the bank keeps its editor block

- Status: Accepted
- Deciders: project owner
- Related: ADR-0004 (canonical question object), ADR-0019 (review gate), ADR-0021 (document model), ADR-0022 (tenancy), EXA-90

## Context

A teacher writes questions of their own in a paper: `freeformQuestion` blocks with rich text,
lettered parts, images (owner-scoped asset ids), inline maths, marks, Ans: units and written
answers. They want to keep one in their question bank and use it in other papers. The bank holds
canonical question objects, whose `question` is structured (plain stem and part text, typed
answers). Mapping a free-form block onto it loses what the teacher wrote (lists, bold, pictures
between paragraphs, the exact written answer), so a question would not come back as it went in.

## Decision

- **The block rides along verbatim.** Canonical schema 1.15.0 adds an optional top-level
  `freeform`: the `freeformQuestion` node, kept as written. It is checked at load against the
  document schema (`exam_engine.own_question.check`), and the object's `question` must agree with
  it (total marks, one part per lettered part).
- **`question` is a plain-text summary** (maths kept as `\(…\)`, a picture as `[picture]`, the
  written answer as a `text` answer) so lists, filters, pickers and the bank swap's marks and
  kind rules work on it like any other bank question.
- **Provenance: `source_type: "sourced"`, `provenance.created_by: "teacher"`** (a new enum value).
  The schema ties them: `created_by: "teacher"` requires a `freeform` block and `sourced`; any
  other object has no block. `source` says "Your own question".
- **Inserting it gives the block back** under a new block id, with a `bank_id` attribute
  (document schema 1.17.0) naming its bank copy, from "From my bank" and from "Swap from your
  bank…". Saving that block again finds the same id, so it reports "already in your bank" and
  replaces it only when asked. A block that never came from the bank saves as `own-<block_id>`;
  only an `own-` id is ever reused, so a save can't overwrite an imported or generated question.
- **It arrives unreviewed and stays unverified.** ADR-0019 says every authored or imported
  sourced object lands unreviewed and only the review action marks it; saving from the paper is
  authoring, not review. The teacher can tick it reviewed in the bank like any import.
- **Images stay the owner's.** Saving (and importing an object that has a block) refuses an image
  the caller does not own, so the question draws in any of their papers. Bank and assets are both
  owner-scoped (ADR-0022), and assets are never deleted on their own.

## Consequences

- A teacher's question round-trips exactly: the printed paper and key are the same before and
  after it goes through the bank (`tests/test_own_question.py`).
- The bank preview (`POST /render/question`) shows the plain-text summary, not the pictures.
- A bank copy and the paper's block are independent: editing one doesn't change the other.
