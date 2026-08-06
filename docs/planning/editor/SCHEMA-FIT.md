# Schema fit — can the canonical object hold real exam questions?

A running record of an empirical exercise for the [editor initiative](README.md):
take **actual exam paper questions**, try to express each one as a canonical
question object, and record where the schema runs out of room.

The point is to decide the editor's authoring scope from evidence rather than in
the abstract. If most real questions need a hand-written answer key, the editor
must be free-form; if most fit existing blueprint shapes, it can stay
parametric and keep the engine's correctness proof. We don't know yet — so we
look at real questions first.

Current schema: **v1.4.0** (`engine/exam_engine/schemas/canonical-question.schema.json`).

## Getting a paper in

Papers arrive as text-only Markdown, extracted from a PDF by an external LLM
tool using the prompt in [`extraction-prompt.md`](extraction-prompt.md), which
asks for **structured** figure data (named points, marked angles, ticks, shading;
tables as real tables) rather than prose — a prose description would make "our
diagram types can't express this" indistinguishable from "the description didn't
carry enough detail."

Transcripts live in [`papers/`](papers/README.md), untracked: the papers are
copyrighted and this repo is public.

The prompt forbids the extractor from solving anything. Our schema requires
`answer`, `marking_scheme` and `solution_steps` on every part, so an extractor
left to its own devices will compute a missing answer — which would put
LLM-generated maths into fixtures, the one thing this project exists to avoid. A
paper with no answer key is itself a finding: it means the editor must support
authoring a key by hand.

## Method

For each question:

1. Attempt a full canonical object — stem, parts, answer, marking scheme,
   solution steps, diagram.
2. Record the verdict: **fits** / **fits awkwardly** / **cannot express**.
3. For anything short of *fits*, name the missing capability and what it would
   cost: a new enum value, a new `diagram` variant, a new `answer` variant, or a
   structural change.
4. Attempted objects go in `tests/fixtures/sourced/` so they are schema-gated
   like any other object — an object that doesn't validate is a finding, not a
   draft.

A gap only counts once it's demonstrated by a real question. Speculative
additions are how a schema rots.

## Verdict tally

| # | Source | Topic | Verdict | Gap |
|---|---|---|---|---|
| _(none yet — exercise not started)_ | | | | |

---

## Gaps found

### Structural gaps identified up front

These three fall out of reading the schema and are near-certain to be hit, but
they stay listed as *predicted* until a real question demonstrates each one.

#### G1 — No multiple-choice questions (predicted)

There is no `options`, `choices`, or equivalent anywhere in the schema. A part is
always a constructed response: `answer` is one of
`integer | decimal | fraction | ratio | quantity | set | text`.

PSLE Paper 1 Booklet A is entirely MCQ, so "author any question" cannot be met
without this. Cost: a new `answer` variant (or a part-level `options[]` plus a
key), and a renderer branch for the option list. Also raises a design question —
is the correct option identified by index or by value?

#### G2 — A figure cannot attach to the stem, only to a part (predicted)

`question` has exactly `{ stem?, parts[], total_marks }` — no `diagram`.
`diagram` lives on each part. The very common paper layout

> The figure below shows … **(a)** … **(b)** …

therefore has to duplicate the same figure into every part, or attach it to part
(a) and rely on layout. Both are wrong: the object stops being a faithful
representation of the question, and the duplicate copies can drift.

Cost: allow `diagram` on `question`. Low risk (additive, optional), but it
touches both renderers (Python + the TS mirror) and the diagram-consistency
check needs to know which part's answer a stem-level figure is checked against.

#### G3 — No table representation (predicted)

No `table`/`rows`/`columns` anywhere, and `diagram` has no table variant. Tables
appear in real papers both as *given data* (timetables, price lists, tally
tables, frequency tables) and as *the thing to complete*.

`raster` (an embedded image) is the current escape hatch, which works for
rendering but makes the content opaque — unsearchable, unstyleable, and unable
to reflow in a PDF.

### Gaps found from real questions

_(to be filled during the exercise)_

---

## Non-gaps worth recording

Things that look like gaps but aren't, so we don't re-litigate them:

- **Free-text `strand` / `topic` / `subtopic`** — only `syllabus.level` is an
  enum (`P5 | P6`). Topic naming is unconstrained, so a paper's own topic labels
  can be carried verbatim.
- **`answer.type: "text"`** — a genuine escape hatch for answers that aren't
  numeric, though anything expressed this way loses structured checking.
- **The `sourced` path already exists** — `source_type: "sourced"` with
  `source` + `license` and `provenance.created_by: "ingested"` validates on the
  same gate, joins mixed worksheets, and renders. V7 proved this end to end
  (`tests/fixtures/sourced/psle_2023_ratio.json`), so hand-authored questions
  are not starting from zero.

## Watch list

Constrained vocabularies most likely to need extending. Each is a cheap enum
addition, so these are friction, not blockers — but the *rate* at which real
papers breach them tells us whether a closed vocabulary is the right call at all.

- **`unit`** — currently `"" | cm | m | km | mm | cm^2 | m^2 | cm^3 | m^3 | ml |
  l | g | kg | $ | cents | % | degrees | s | min | h | km/h | m/s | m/min |
  marbles | items | people | units`. The countable-noun tail (`marbles`,
  `items`, `people`) is clearly a stand-in: real papers count books, sweets,
  boys, stickers, buttons.
- **Compound quantities** — "2 h 30 min", "1 m 45 cm", "$3.50" as dollars *and*
  cents. No `answer` variant composes two units.
- **`part` requires all of** `label, text, marks, answer, marking_scheme,
  solution_steps`. A question that only says "show your working", or a part with
  no marks of its own, has nothing valid to put in those fields.
- **`diagram` union is closed** at `bar_model | bar_model_before_after |
  geometry_figure | shaded_fraction | raster`. Nets, line graphs, pie charts,
  coordinate grids, clock faces, 3D solids and number lines all currently land
  in `raster`.
