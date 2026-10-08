# ADR-0021: Document-centred editor — a block document model, and three edit tiers for templated questions

- Status: Accepted
- Deciders: project owner
- Related: `docs/planning/editor/WYSIWYG.md` (reframe + slices), ADR-0004 (canonical object), ADR-0018 (paper container — amended here), ADR-0019 (review gate), ADR-0020 (schema v2), ADR-0022 (SaaS)

## Context

The form-based editor planned in E5 (author a question through web forms) does not
match how teachers work: they set papers in Word. The product is reframed as a
**WYSIWYG document editor** — a blank page with a "+" affordance — in which the engine
is a *content source*, not the editing surface.

## Decision

**1. A paper is a document: an ordered list of blocks.** Block types: rich text
(headings, paragraphs, lists, images, basic tables, equations), **templated question**,
and **free-form question**. This absorbs ADR-0018's paper → section → group container:
sections are headings, a shared-stem group is a grouped run of blocks. The canonical
question object is unchanged and stays the single source of truth *for templated
questions only*.

**2. Templated blocks embed a frozen snapshot of a canonical object** (from the bank or
freshly generated), never a live link, so a saved paper cannot change under the teacher.
In-block V3 ops (regenerate, make-harder/easier, toggle-diagram, change-to-decimals)
replace the snapshot and re-validate.

**3. Free-form blocks are a separate, looser type — not canonical objects.** Rich text +
images + an optional `marks` + a rich-text answer slot. The trust model stays honest:
templated = engine-proven, free-form = teacher-vouched. Free-form content never carries an
engine-verified badge.

**4. The answer key is derived.** A separate section at the end of the document. Templated
entries are filled from the solver/marking scheme; free-form entries are empty editable
slots. Blocks have stable ids; numbering is shared between body and key.

**5. Edits to a templated block are tiered by what they touch:**

| Tier | Edit | Guarantee |
|---|---|---|
| 1 | Cosmetic slots (names, objects) | Re-render through the same wording template; answer unaffected. Pronoun-bearing names are paired slots. |
| 2 | Numeric parameters (later slice) | Re-run validate → solve → schema-check; infeasible values rejected; key recomputed. |
| 3 | Wording / sentence structure | **Not editable.** Escape hatch: **Convert to free-form** — detaches from the engine, drops the verified badge, pre-fills the answer slot as editable text. |

Blueprints must therefore mark each parameter as cosmetic or numeric (to be specified in
the W1 plan; current YAML param schema has no such notion).

## Consequences

- E4 and E5 are superseded (see `WYSIWYG.md`); E1–E3 remain the bank/schema substrate.
- Free-form questions are not searchable/reusable by the engine; a later "promote to bank"
  action can close that gap.
- Editor technology: TipTap/ProseMirror with custom node views; PDF export stays the
  existing Chromium path using the same HTML + print CSS. `.docx` export is out of scope
  for now (PDF only while dogfooding).
