# ADR-0020: Schema v2 for the editor — grow through the confirmed cluster (MCQ, stem diagram, table, grid, construction), stop there

- Status: Accepted
- Deciders: project owner
- Related: `docs/planning/editor/SCHEMA-FIT.md` (G1–G9, ranked schema work), `docs/planning/editor/PARAMETERIZATION.md`, `docs/planning/editor/SHAPING.md` (R7, Shape A3–A8), ADR-0004, ADR-0012 (diagram union), ADR-0013 (question structure/answer union), ADR-0014 (schema formalization)

## Context

`SCHEMA-FIT.md` ranked 17 schema changes against evidence from three real P6
prelim papers (141 questions). Three papers, not one, moved the ranking
substantially: tables went from 4 figures/rank-7 to 15 figures (18%)/rank-5,
grid backgrounds were promoted out of a bundle, and construction answers went
from a one-off skip to a confirmed 9-question cluster — every single one a
drawing on a square grid. This ADR fixes how far the schema grows *this*
milestone and records why the line is drawn where it is.

## Decision

**Schema v2 includes ranked items 1–7, all additive (no breaking change to
existing v1.4.0 objects, no data migration — only a version bump):**

1. `answer.type:"choice"` — `options[]`, each entry carrying text and/or a
   diagram, plus the correct label. Unblocks 45 questions (32% of every paper
   examined) — the single largest gap.
2. `diagram` allowed on `question` (stem-level), with each figure's unknowns
   bound to a specific `part.label` rather than the figure as a whole. Required
   for #1's structured MCQs and every shared-figure structured question to be
   *correct*, not just representable.
3. `marks`/`marking_scheme` become optional on `part` — real answer keys never
   supply an M/A/B breakdown, and some parts carry no mark allocation of their
   own; forcing either fabricates information the source paper doesn't contain.
4. A `table` type, content-level (a sibling of `stem`, not a `diagram` variant)
   — the second most common figure kind across all three papers, and
   repeatedly the answer surface itself (a blank/answerable cell).
5. `grid` background + `polygons[]` on `geometry_figure` — the substrate for
   coordinate grids, cube nets, and rod-pattern figures, all of which currently
   have no structured home.
6. `construction` answer — an answer whose value is itself a diagram, built on
   #5's grid. Every construction answer found (9 across three papers) is a
   drawing on a square grid, so this and #5 are one cluster, not two unrelated
   additions.
7. Segment/figure styling primitives strictly needed to make #5/#6 legible
   (dashed/construction-line style, since grid constructions routinely include
   them) ship as part of the same `geometry_figure` growth, not a separate item.

**Ranked items 8+ are explicitly deferred**, not included in v2: symbolic/
algebraic answers (`"in terms of π"`, `"in terms of n"`), compound quantities
(`2 h 36 min`), time-of-day, compass direction, tick-matrix `selection`
answers, chart types, `solid` figures, and multi-panel figures. Each is real
(confirmed across all three papers) but individually lower-value or
higher-cost than the items above, and none of them block the milestone's
acceptance question (`docs/planning/editor/SHAPING.md` R8.5) — the one real
paper chosen for acceptance can be fully recreated using items 1–7 plus the
existing `raster`/`text` escape hatches for anything in items 8+.

## Consequences

- The schema bumps to a new minor/major version (additive-only, so minor per
  semver discipline already established for `total_bracket`, `view_mode`, and
  `geometry_figure` itself); every existing v1.4.0 object — generated or
  sourced, including all golden fixtures — remains valid without edits.
- Both renderers (Python + the TS mirror, per the established dual-renderer
  discipline) need a branch for each new type: MCQ options, a real `<table>`,
  and a construction-answer figure in the answer key.
- The diagram-consistency check gains a per-part resolution step (item #2) —
  it can no longer assume a figure's unknown belongs to "the" part, since a
  stem-level figure now serves several.
- Items 8+ stay explicitly on the watch list in `SCHEMA-FIT.md`; a fourth real
  paper is the trigger to revisit this ranking, per that document's own
  observation that two additional papers already corrected the first paper's
  reading three times.
