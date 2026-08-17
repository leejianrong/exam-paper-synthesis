# ADR-0018: Paper/section/question-group structure — a container above the canonical object, not inside it

- Status: Accepted
- Deciders: project owner
- Related: `docs/planning/editor/SCHEMA-FIT.md` G15/G16, `docs/planning/editor/SHAPING.md` (R3, Shape A9, Component A9), ADR-0004 (canonical object), ADR-0013 (question structure)

## Context

`SCHEMA-FIT.md` found two structural gaps a single canonical question object
cannot hold:

- **G15** — a real paper has sections (e.g. Booklet A/MCQ, Booklet B/short
  answer, Paper 2/structured) with their own instructions and answer
  conventions; our worksheet is a flat titled list.
- **G16** — a stem and figure can be shared across two *separate numbered
  questions* (`"Use the information below to answer Question 9 and 10"`), not
  just across parts of one question (which G2/ADR-0013 already covers via
  `diagram` on `question`).

Both are demonstrated in every paper examined, not speculative. The question
this ADR resolves: does this container live **inside** the canonical object
(e.g. a `group` field with shared content copied into each member question), or
**above** it, referencing existing objects by id?

## Decision

- **The container lives above the canonical object, in the bank, and references
  questions by id. It does not change the canonical schema.**
- Shape: `Paper { title, sections[] }` → `Section { label, instructions,
  answer_convention, members[] }` → optional `QuestionGroup { shared_stem?,
  shared_diagram?, question_ids[] }`. A section's members are either bare
  question ids or question groups; a question group's shared stem/figure is
  authored once, on the group, never duplicated into the member objects.
- **Member questions are unchanged, standalone-valid canonical objects.**
  Removing a question from a group (or reusing it in a different paper) doesn't
  touch its own object.
- Rejected alternative: copying the shared stem/figure into every member
  object's own `question.diagram`/`stem`. This is exactly what G16 warned
  against — *"Duplicating the table into both objects makes them silently
  coupled — edit one and the paper becomes inconsistent."* It would also require
  a schema change (a `group_id` or shared-content field on `question`) for no
  benefit the reference approach doesn't already provide.

## Consequences

- The canonical question schema needs **no change** for paper/section/group
  support — this is purely new bank/container structure (ADR-0017's bank gains
  two new tables: sections and question groups, referencing the existing object
  table by id).
- Renderers gain a `render_*_html(Paper)` path (alongside the existing flat
  question-list path) that prints section headers/instructions and a shared
  stem/figure once per group, with paper-level numbering independent of
  internal object ids.
- Editing a shared stem or figure is now unambiguous: there is exactly one place
  it lives (the group), so an edit is visible to every member question by
  construction, not by convention.
- A question can still be authored, reviewed, and used entirely standalone —
  paper/section/group membership is optional structure layered on top, never a
  requirement for a valid object.
