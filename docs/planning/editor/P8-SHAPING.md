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

There are 27 blueprints, 9 topics × 3 rungs. Each has fixed marks, one part and a
constructed-response answer. Counted by marks: 1 mark: 4, 2 marks: 8, 3 marks: 11, 4 marks: 4.
14 are P5 (1: 4, 2: 5, 3: 5). P8e batch 1 (EXA-117) added the P5 `average` ladder (1/2/3 marks).

| Paper part | Real composition | P6 paper today | P5 paper today |
|---|---|---|---|
| P1 Booklet A | 15 MCQ, 20 marks (10 × 1, 5 × 2) | 9 / 15 (was 0 before P8b, 8 before P8e) | 9 / 15 (was 7 before P8e) |
| P1 Booklet B | 15 short answer, 25 marks (5 × 1, 10 × 2) | 12 / 15 slots, 20 / 25 marks | 9 / 15, 14 / 25 |
| P2 Section A | 5 × 2 marks | 5 / 5 | 5 / 5 |
| P2 Section B | ~12 multi-part, 45 marks | 45 / 45 with 14 stand-ins (eleven 3-mark, three 4-mark) | 15 / 45 (five 3-mark) |

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
| **P8a** ✅ | Paper generator | Paper-template YAML (P4 templates move to it), `generate_paper` + placeholders + stand-ins + report, `slot` attr (schema 1.10.0), `POST /documents/generate`, the generate dialog, invariant test. | P4, P7 |
| **P8b** ✅ | MCQ for Booklet A | Turn constructed-response blueprints into MCQ with deterministic distractors from common wrong answers (per-solver "wrong turn" hooks), or write MCQ blueprints; `choice` answers already exist in the canonical schema. Fills `mcq` slots. | P8a |
| **P8d** ✅ | Keep / swap / lock | Per-question "another like this" (same slot: new seed or sibling blueprint), "another topic", "write my own" (turns it into a free-form question keeping the slot's marks and Ans: line), lock; "regenerate paper" refills unlocked slots only. | P8a |
| **P8c** | Multi-part blueprints | Shared stem with (a)/(b)/(c), each part solver-proven; replaces Section B stand-ins. | P8a, P3 |
| **P8e** | Coverage growth | More topics (whole numbers, decimals, average, algebra, rate, circles, data tables, …) and more 1-/2-mark and P5 blueprints, ordered by the report's placeholder counts. | — |

## Not in P8

Two-column answer keys. Exam-wide topic balance (decision 1). Difficulty targets beyond what a
slot's marks imply. Marks and rung mostly track each other in today's content, but not
always: `geometry_angle` and `speed` give 3 marks at both the medium and hard rungs. An LLM anywhere
in generation (the engine stays deterministic).

## P8a as built (2026-11-15)

- `engine/exam_engine/paper.py` (`paper_templates`, `template_document`, `generate_paper`,
  `unfilled_placeholders`) over `engine/exam_engine/content/papers/*.yaml`; `GET /papers`,
  `POST /documents` with `template`, `POST /documents/generate`. Generation takes well under a
  second. The fill counts are exactly the coverage table above (pinned by
  `tests/test_invariants_paper.py::test_what_todays_content_fills`, which must be updated
  whenever content grows).
- The P4 starter templates are the same YAML (the TypeScript copy is gone), so "start from a
  template" and "generate" can't drift.
- Differences from the shape above: the generator is an inline form on the papers list, not a
  modal dialog; unfilled placeholders show as a "N placeholders to write" count in the editor's
  top bar (and a hint on each placeholder) rather than an export warning. A placeholder stops
  counting as soon as its body has text, so nothing is stored to clear.
- Generated papers start with a cover page (level, subject, paper and instructions prefilled;
  school, exam and date for the teacher). Starting from an empty template doesn't add one.

## P8b as built (2026-11-15)

- Conversion, not new blueprints: `engine/exam_engine/mcq.py` `to_mcq(obj, seed)` works on any
  generated single-part question with a numeric or fraction answer, so every new blueprint is
  usable in Booklet A for free. Options are labelled (1)–(4), shuffled by seed.
- Distractors, best first: intermediate values of the worked solution's steps (only within 8×
  of the answer: farther ones are usually another quantity, e.g. km in a time question), then
  ± one "step", ×2/÷2 and ×10/÷10; for fractions the unshaded part, shaded : unshaded,
  off-by-one numerator/denominator. Never a value equal to the answer. Known limit: an
  intermediate within 8× can still be another quantity in the answer's unit; per-solver
  distractor hooks are the fix if teachers find these weak.
- Proof: `verify_snapshot` re-solves the blueprint and requires the correct option's text to
  equal `mcq.answer_text` of the proven answer, and all options to differ. No schema change.
- A multiple-choice copy offers no edit ops (re-solving would turn it back into a written
  answer); P8d's swap replaces it instead.
- Booklet A's marks stay the blueprint's: 1-mark slots take 1-mark blueprints (only four
  today), which is why P5/P6 Booklet A still has 6 placeholders; more 1-mark content (P8e)
  closes the gap.

## P8d as built (2026-11-15)

- `engine/exam_engine/paper_swap.py`, pure document → document transforms beside the generator
  (kept out of `paper.py` so P8b/P8c can change the generator independently; it reuses
  `paper.candidates` and `paper._fits`, so MCQ and multi-part candidates arrive here for free).
  - `swap_question(doc, block_id, mode, seed, level)`: `like` takes an unused blueprint of the
    same topic and marks, else a new seed of the same blueprint (a visibly different question);
    on a placeholder it *fills* it with any unused blueprint of those marks, least-used topic
    first. `topic` takes an unused blueprint with the same marks from another topic,
    preferring topics the paper doesn't use yet. `own` leaves an empty placeholder with the
    slot's marks (`slot.placeholder`, stand-in flag dropped). A swap keeps the block id and
    the position's attributes (working space, in-key, remark, lock) but drops `ans_unit`,
    which belonged to the old answer.
  - A question without a `slot` (added by hand) is swapped by its marks and its section's mode,
    and stays slot-less. Refused, with a message for the teacher (`SwapNotPossible` → 422): a
    locked question, a bank (sourced) question, a free-form question that isn't a placeholder, a placeholder the teacher
    has started writing, `own` on a placeholder, and any swap the content can't make without
    repeating a blueprint.
  - `regenerate_unlocked(doc, level, seed)` refills unlocked *generated* questions and *empty*
    placeholders, least-used topic first, never repeating a blueprint the kept blocks use. It
    never touches locked questions, bank (sourced) questions, free-form questions or
    placeholders with anything written in them. A slot nothing fits becomes a placeholder.
  - The level is the cover page's ("Primary 6") when the paper states one, else the request's,
    else the highest level of the paper's questions, else P6. Only a missing block is a 404
    (`BlockNotFound`); other engine errors surface as errors.
- `locked` (boolean, only `true` stored) on both question kinds: document schema 1.11.0.
- `POST /documents/{id}/swap {block_id, mode, base_version}` and
  `POST /documents/{id}/regenerate {base_version}`: owner-scoped (foreign = 404), computed on
  `base_version` only (409 otherwise, like PUT), seed chosen at the boundary, `created_at`
  stamped on new snapshots, re-validated, saved, and returned like GET plus the `report`.
- Web: every generated question (with or without a slot — "Regenerate unlocked" refills both)
  shows "Another like this", "Another topic", "Write my own" and a Lock toggle (swaps disabled
  while locked); a bank question shows none. A placeholder shows "Fill with a question",
  "Another topic" and Lock; "Regenerate unlocked" sits in the top bar when the paper has
  anything it would refill.
- No lost updates around an op: the editor saves pending edits first and snapshots what the
  server will work on; the page is `inert` while the request is out, and any change that gets
  through anyway is not saved until the op is done (then saved on the server's version).
  Autosave `rebase(version)` drops any snapshot scheduled before it, ignores a save in flight
  across it and lifts a conflict. The editor replaces only the question blocks the server
  changed (matched by block id against the snapshot, one undo step), so a change made
  meanwhile elsewhere survives.
- Multiple choice (P8b): candidates are `paper._fits` for the slot's kind, so an `mcq` slot only
  takes convertible blueprints, and a swapped or refilled Booklet A question is converted with
  `mcq.to_mcq` exactly as the generator does — it stays four-option multiple choice and
  engine-proven (pinned by `test_booklet_a_stays_multiple_choice_through_swaps_and_regenerate`).
- A placeholder offers "Another topic" too (fills it from a topic the paper lacks).
  "Regenerate unlocked" also refills generated questions added by hand (so they show Lock too);
  its tooltip says locked questions and the teacher's own writing are kept.
- Not done: a preview of the candidate before swapping.
