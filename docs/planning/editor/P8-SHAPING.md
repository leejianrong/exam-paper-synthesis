# P8 — one-click paper generation (shaping)

Shaping for P8 of [`PAPER-FORMAT.md`](PAPER-FORMAT.md) (EXA-114). That doc states the owner's
workflow: one button makes a whole paper in the real composition, then the teacher keeps,
swaps or replaces questions. This doc fixes the decisions, the model and the order of the
sub-slices.

## Decisions (owner, 2026-11-15)

1. **One paper per click.** The generate dialog makes one document from one paper template
   (Paper 1 Booklet A, Paper 1 Booklet B, Paper 2), the same unit as the P4 starter templates.
   A full exam takes three clicks. Spreading topics across a whole exam is out of scope.
2. **Each blueprint at most once per paper, then a placeholder.** A slot that no unused blueprint
   can fill becomes a clearly marked placeholder for the teacher. The paper is never padded with
   repeats or with off-topic questions, and the gap shrinks as content grows (P8e).
3. **Single-part stand-ins for Paper 2 Section B until multi-part blueprints exist (P8c).** Section
   B is filled with single-part questions whose marks add up to the section's 45. The slot count
   may differ from the real ~12, and each stand-in is flagged so P8c can replace it later.
4. **P8a (the generator) comes first.** Then P8b (MCQ), P8d (keep/swap/lock), P8c (multi-part)
   and P8e (coverage).

## What the content can fill today (computed, not estimated)

There are 24 blueprints, 8 topics × 3 rungs. Each has fixed marks, one part and a
constructed-response answer. Counted by marks: 1 mark: 3, 2 marks: 7, 3 marks: 10, 4 marks: 4.
Only 11 are P5 (1: 3, 2: 4, 3: 4).

| Paper part | Real composition | P6 paper today | P5 paper today |
|---|---|---|---|
| P1 Booklet A | 15 MCQ, 20 marks (10 × 1, 5 × 2) | **0 / 15**: no MCQ (P8b) | 0 / 15 |
| P1 Booklet B | 15 short answer, 25 marks (5 × 1, 10 × 2) | 10 / 15 slots, 17 / 25 marks | 7 / 15, 11 / 25 |
| P2 Section A | 5 × 2 marks | 5 / 5 | 4 / 5 |
| P2 Section B | ~12 multi-part, 45 marks | 45 / 45 with 14 stand-ins (one 2-mark, nine 3-mark, four 4-mark) | 12 / 45 (four 3-mark; no 2-mark left after Section A) |

So for a P6 teacher, P8a alone makes a complete Paper 2 and two thirds of Booklet B. P8b (MCQ) is
the single largest content unlock after that. A P5 paper stays thin until P8e.

## Shape

**Paper templates are engine content.** Add `engine/exam_engine/content/papers/*.yaml`, package
data like the blueprints. Each template holds the title, time, an optional cover (level, subject
and paper prefilled) and its sections (title, mode, instructions, marks target). Each section
lists **slots** of `{marks, kind}`, where `kind` is `mcq`, `short` or `structured`. The P4 starter
templates in `web/src/lib/editor/templates.ts` become the same YAML with the slots left unfilled,
served by the API, so there is one source of truth.

**`generate_paper(template_code, level, seed) -> (document, report)`** is pure and deterministic,
like `generate()`. The same inputs give the same paper. The API supplies the seed, which is where
entropy enters, as with `/generate`.
- **Candidates.** The blueprints of the paper's level and below (a P6 paper may use P5 topics,
  a P5 paper only P5 ones) whose marks match the slot and whose kind fits. `short` and
  `structured` slots take constructed-response blueprints; `mcq` slots need P8b.
- **Fill.** A small seeded constraint search. No blueprint is used twice in the paper. Topics are
  spread by preferring the least-used topic, with ties broken by the seed. Each slot's question is
  generated with a seed derived from the paper seed and the slot index.
- **Exact totals.** Each section's marks must equal its target, counting placeholders. In a
  section with fixed slots (Booklet A, Booklet B, Section A), every slot that can't be filled
  becomes a placeholder with that slot's marks. A paper is never silently short.
- **Stand-ins.** For a `structured` section with no multi-part candidates, the search may change
  the slot count and choose single-part questions of 2 marks or more (1-mark questions don't
  belong in a structured section) whose marks sum to the target. Each one is flagged
  `stand_in`. Any shortfall is split into placeholders of 3–5 marks, the size of a real
  Section B question.
- **Report.** Per section: slots filled, placeholders, stand-ins, and the topics used. The dialog
  shows it honestly, e.g. "Filled 10 of 15 questions; 5 placeholders (8 marks) for you to write".

**Document model (schema 1.10.0, additive).**
- An optional `slot` attr on `templatedQuestion` / `freeformQuestion`:
  `{marks, kind, stand_in?, placeholder?}`, recording what the generator asked for. P8d's
  "another like this" needs it.
- An optional `locked` attr (P8d).
- A placeholder is a `freeformQuestion` with `slot.placeholder: true` and the slot's marks. The
  editor shows it as "Write a 2-mark question here, or pick one", and the Preview/PDF export warns
  while placeholders remain (a warning, not a block).

**API.** `POST /documents/generate {template, level}` creates the document and returns it with the
report. It is owner-scoped like `POST /documents`. P8d adds `POST /documents/{id}/swap` and a
"regenerate unlocked" call, both re-validated through `validate_document`.

**UI.** A "Generate paper" dialog on the documents list, beside the starter-template buttons:
pick the template and the level (P5/P6). It creates the document, opens the ordinary editor, and
shows the report as a dismissable banner.

## Correctness

Following the project rule, an independent seed-sweep **invariant test** checks every generated
paper over many seeds:
- each section's marks equal its target (a placeholder carries any shortfall);
- no blueprint appears twice;
- every templated block passes `verify_snapshot`, so it is engine-proven;
- every block's level is at or below the paper's;
- the same seed gives the same paper.

A golden paper per template anchors regressions.

## Sub-slices

| # | Slice | What | Depends on |
|---|---|---|---|
| **P8a** | Paper generator | Paper-template YAML (P4 templates move to it), `generate_paper` + placeholders + stand-ins + report, `slot` attr (schema 1.10.0), `POST /documents/generate`, the generate dialog, invariant test. | P4, P7 |
| **P8b** | MCQ for Booklet A | Turn constructed-response blueprints into MCQ with deterministic distractors from common wrong answers (per-solver "wrong turn" hooks), or write MCQ blueprints; `choice` answers already exist in the canonical schema. Fills `mcq` slots. | P8a |
| **P8d** | Keep / swap / lock | Per-question "another like this" (same slot: new seed or sibling blueprint), "another topic", "write my own" (turns it into a free-form question keeping the slot's marks and Ans: line), lock; "regenerate paper" refills unlocked slots only. | P8a |
| **P8c** | Multi-part blueprints | Shared stem with (a)/(b)/(c), each part solver-proven; replaces Section B stand-ins. | P8a, P3 |
| **P8e** | Coverage growth | More topics (whole numbers, decimals, average, algebra, rate, circles, data tables, …) and more 1-/2-mark and P5 blueprints, ordered by the report's placeholder counts. | — |

## Not in P8

Two-column answer keys. Exam-wide topic balance (decision 1). Difficulty targets beyond what a
slot's marks imply. Marks and rung mostly track each other in today's content, but not
always: `geometry_angle` and `speed` give 3 marks at both the medium and hard rungs. An LLM anywhere
in generation (the engine stays deterministic).
