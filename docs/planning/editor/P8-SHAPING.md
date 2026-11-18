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

There are 50 blueprints: 14 topic ladders × 3 rungs, each single-part with fixed marks,
3 multi-part ones and 5 single-part 1-mark ones on no ladder. Single-part, counted by marks:
1 mark: 14, 2 marks: 13, 3 marks: 16, 4 marks: 4; 28 are P5 (1: 12, 2: 8, 3: 8). P8e batch 1
(EXA-117) added the P5 `average` ladder; P8c (EXA-116) the three P6 multi-part blueprints
(4, 5, 5 marks) for Paper 2 Section B; P8e batch 2 (EXA-121) the P5 `whole_numbers`,
`decimals` and `rate` ladders and the P6 `algebra` ladder (1/2/3 marks each); P8e batch 3
(EXA-145) five P5 1-mark blueprints for Booklet A; P8e batch 4 (EXA-149) the P6 `circles`
ladder (1/2/3 marks) (below).

| Paper part | Real composition | P6 paper today | P5 paper today |
|---|---|---|---|
| P1 Booklet A | 15 MCQ, 20 marks (10 × 1, 5 × 2) | 15 / 15 (was 13 before batch 3, 0 before P8b) | 15 / 15 (was 12 before batch 3) |
| P1 Booklet B | 15 short answer, 25 marks (5 × 1, 10 × 2) | 15 / 15, 25 / 25 (was 12 / 15) | 13 / 15, 21 / 25 (was 9 / 15) |
| P2 Section A | 5 × 2 marks | 5 / 5 | 5 / 5 |
| P2 Section B | ~12 multi-part, 45 marks | 45 / 45: 3 multi-part (4 + 5 + 5 marks) + 9 stand-ins | 30 / 45: 11 stand-ins (eight 3-mark, three 2-mark) + 3 placeholders (was 15 / 45) |

So a P6 teacher gets a complete paper set, and a P5 teacher complete Booklet A. The remaining
gaps are P5 2-mark content (Booklet B) and P5 multi-part / 3-mark content for Paper 2
Section B.

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
| **P8c** 🚧 | Multi-part blueprints | Shared stem with (a)/(b)/(c), each part solver-proven; replaces Section B stand-ins. First three built and wired into the generator (see below). | P8a, P3 |
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
  school, exam and date for the teacher). Since EXA-124, starting from an empty template adds the same cover with the
  level left blank (an empty template has none); swaps then fall back as for a paper without a
  cover: the highest level of its generated questions, else P6.

## P8b as built (2026-11-15)

- Conversion, not new blueprints: `engine/exam_engine/mcq.py` `to_mcq(obj, seed)` works on any
  generated single-part question with a numeric or fraction answer, so every new blueprint is
  usable in Booklet A for free. Options are labelled (1)–(4), shuffled by seed.
- Distractors, best first: intermediate values of the worked solution's steps (only within 8×
  of the answer: farther ones are usually another quantity, e.g. km in a time question), then
  ± one "step", ×2/÷2 and ×10/÷10; for fractions the unshaded part, shaded : unshaded,
  off-by-one numerator/denominator. Never a value equal to the answer. Known limit (fixed by EXA-122, below): an
  intermediate within 8× could be another quantity in the answer's unit.
- Proof: `verify_snapshot` re-solves the blueprint and requires the correct option's text to
  equal `mcq.answer_text` of the proven answer, and all options to differ. No schema change.
- A multiple-choice copy offers no edit ops (re-solving would turn it back into a written
  answer); P8d's swap replaces it instead.
- Booklet A's marks stay the blueprint's: 1-mark slots take 1-mark blueprints (only four
  today; eight after P8e batch 2), which is why P6 Booklet A still had 2 placeholders and P5 3;
  P8e batch 3 (13 at P6, 12 at P5) closed the gap.

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

## P8c as built so far (2026-11-15)

- **Framework.** A blueprint YAML may carry `parts:` — one entry per part, in print order, each
  `{label, text, marks, marking_scheme, solution_template, answer}` — instead of the top-level
  `marking_scheme` / `solution_template` / `answer`. Its `story_templates` then hold only the
  shared `stem`; `marks` stays the question total. The solver's `solve()` returns `"answers"`
  (one per part) instead of `"answer"`. `load_blueprint` checks the parts (labels a, b, …;
  each scheme sums to its part's marks; parts sum to `marks`). Single-part blueprints are
  untouched.
- **The marker the generator reads:** `load_blueprint(code).is_multipart` (and `.part_count`).
- **Blueprints:** `ratio_structured` (5 = 2 + 3: total from a difference; then how many were
  given, the total unchanged), `speed_structured` (4 = 1 + 3: the distance; then the
  round-trip average speed) and `volume_structured` (5 = 2 + 3: litres in tank A; then the
  water level once poured into tank B). All P6, not on any difficulty ladder.
- **Proof.** `verify_snapshot` re-solves and checks every part's label, answer and marks;
  `tests/test_invariants_structured.py` re-derives each part from the printed numbers.
- **Edits.** Multi-part questions get only `regenerate` and `set-cosmetic`; the
  representation ops (decimals, diagram toggles) rebuild one part and are not offered.
- **Generator.** `paper.py`'s pool marks a blueprint `kind="multipart"` when
  `spec.is_multipart`. A `structured` section first takes real multi-part questions (least-used
  topic first, seeded ties, each at most once, as many as fit the marks target and slot count;
  slot `{marks, kind: "structured"}` with no `stand_in` flag), then fills the rest of the target
  with single-part stand-ins through the same `_stand_in_plan` (target and slot count reduced by
  what the multi-part questions took), then placeholders for any shortfall. Questions are
  ordered by marks. Multi-part blueprints never fill `short` or `mcq` slots. The report counts
  them per section (`multipart`, apart from `stand_ins`), and the editor's banner says "Section B
  has 3 multi-part questions; 9 single-part questions stand in for the rest."
- **Keep / swap / lock (P8d).** `paper_swap` follows the same order. "Another like this" on a
  multi-part question takes another multi-part question of its topic and marks, else a new seed
  of it, else a single-part stand-in; on a stand-in it prefers a multi-part question of its
  topic. "Another topic" and placeholders try multi-part candidates first. "Regenerate unlocked"
  gives structured slots multi-part questions first, then stand-ins. Multi-part questions never
  enter `short` or `mcq` slots, and only single-part questions in structured slots carry
  `stand_in`.
- **What it fills now.** P6 Paper 2 Section B: 12 questions, 45 / 45 marks = the three
  multi-part (4 + 5 + 5) and nine single-part stand-ins (five 3-mark, four 4-mark). A P5 paper
  is unchanged (all three are P6).

## P8c polish (EXA-123, 2026-11-15)

- `speed_structured`: whole speeds 30–90 km/h, 2–6 h out, the journey back in whole or half
  hours (printed "2.5 h"), at most 480 km, a whole average speed: 105 trips (was 24),
  enumerated once (`structured.speed_trips`) so sampling is uniform over them.
- `ratio_structured`: a one-unit ratio difference says "1 unit = n" once.
- Litres print as ℓ everywhere (see `units.py`); stored codes and goldens unchanged, and a saved
  multiple-choice option in the old `l` form still verifies (`mcq.legacy_answer_text`).

## P8b follow-up: common wrong answers (EXA-122, 2026-11-15)

- Solver protocol: optional `distractors(params, solution) -> [(value, why)]`, best first, in
  the answer's own quantity and unit. `mcq.common_wrong_answers` re-solves the object's
  `parameters` and asks the solver; `distractor_candidates` takes those first, then (only for
  a solver without a hook) the worked solution's intermediates within 8×, then the generic
  near misses / doubling / place value. All 39 single-part ladder solvers have a hook; tests
  `tests/test_distractors_group_{a,b,c}.py` re-derive at least one named mistake per blueprint
  from the printed question and require the hook to supply 2 of the 3 wrong options in ≥ 90%
  of seeds (two exceptions, below).
- Plausibility is unit-aware: money ($) takes cents even for a whole-dollar answer; a
  measure (h, cm², °, …) with a whole answer takes 1-dp wrong answers; a plain count stays
  whole, except that a solver's hook may offer a unitless decimal slip up to 3 dp
  (1.984 for 19.84). A hook value more than 20× from the answer is dropped (24000 ℓ for 24 ℓ
  gives itself away). Every candidate prints at its own precision, and one that would print
  rounded is skipped, so an option always shows exactly the slip its reason names. A whole
  wrong answer prints "100 cm²", not "100.0 cm²". Bars below 90%: `speed_hard` 20% (its
  other real mistakes are recurring decimals) and `decimals_easy` 55% (its decimal-point
  slips come in ÷10 / ×10 pairs, and the give-away guard keeps only one of each).
- Give-away guard: the answer is never exactly between two options (7 / 8 / 9, or
  14 / 28 / 56) nor the odd one out (the only whole number, or the only decimal) while the
  candidates allow another choice; pinned for every convertible blueprint over 60 seeds.
- The multiple-choice marking scheme names each wrong option's reason
  ("Correct option (3). Wrong options: (1) forgot to divide; …"). No schema change; the
  correct-option proof in `verify_snapshot` is unchanged.


## P8e batch 3 as built (EXA-145, 2026-11-17)

- **Why.** Booklet A has ten 1-mark MCQ slots and only 8 (P6) / 7 (P5) blueprints fitted them
  (single-part, 1 mark, a numeric or fraction answer), so 2 / 3 placeholders printed. Real
  Booklet A papers open with number-sense and measurement 1-markers (REAL-PAPER-COMPARISON.md
  Part 2, ranked gap 3).
- **Blueprints**, all P5 (the skills are taught in P3–P5 and PSLE assumes them; P5 is the
  lowest level a paper here has), 1 mark, easy:
  - `whole_numbers_rounding` (Whole Numbers): a 4-digit number to the nearest ten, hundred
    or thousand; half the hundred / thousand items carry the double-rounding trap (7549).
  - `decimals_compare` (Decimals): the greatest / smallest of four decimals made of the same
    two digits in different places (0.15, 0.51, 0.105, 0.501).
  - `fractions_compare` (Fractions): the greatest / smallest of four proper fractions with
    different denominators (common denominator ≤ 120).
  - `measurement_conversion` (new topic Measurement): km / kg / ℓ as a decimal or in
    compound units, written in m / g / mℓ (an integer answer; ℓ via `units.printed_unit`).
  - `time_duration` (new topic Time): minutes between two 12-hour clock times that cross at
    least one hour (an integer answer in `min`; the schema has no clock-time answer type, so
    "what time did it end?" items are not covered).
- **No ladder.** Each is one 1-mark skill with no harder rung of the same skill, so
  make-harder / make-easier would only jump to an unrelated subtype; they offer `regenerate`
  only. Like the multi-part blueprints they are not in the web topic picker (it builds
  `<topic>_<difficulty>` codes), but the generator, swaps and "regenerate unlocked" use them.
- **Wrong answers.** Every solver has a `distractors` hook. For the two "which is the
  greatest" blueprints it returns exactly the other three listed numbers (with the misreading
  that picks each), so the MCQ options are the four numbers in the stem. Known limit: the
  constructed-response stem lists the numbers, so the MCQ copy shows them twice (in the stem
  and as options).
- **Topics.** Measurement and Time are new topics, so the least-used-topic rule spreads them
  first; a P5 Booklet A now draws its ten 1-mark questions from nine topics, P6 from ten.
- **Tests.** `tests/test_invariants_{rounding,compare,measurement,time}.py` (independent
  re-derivations from the printed stem), `tests/test_generate_booklet_a_one_markers.py`,
  `tests/test_distractors_group_d.py`, and `test_booklet_a_fills_every_slot_and_spreads_topics`
  in `tests/test_invariants_paper.py` (no placeholders at P5 and P6 over 40 seeds; replays
  the least-used-topic rule from the document; every eligible topic gets a 1-mark question).
- **Goldens** `tests/golden/{whole_numbers_rounding,decimals_compare,fractions_compare,
  measurement_conversion,time_duration}.jsonl`, 3 each, picked from seeds; a person checks them.

## Difficulty follows marks (EXA-146, 2026-11-17)

- **Why.** Marks were matched exactly but the rung was not, so a 2-mark Booklet A MCQ could be a
  one-step d = s × t (`speed_easy`) and a 3-mark Section B stand-in a two-step medium. Real
  2-mark items are multi-step and 3–5-mark items heuristic (REAL-PAPER-COMPARISON.md Part 2,
  ranked gap 4).
- **Signal.** The blueprint's ladder rung (`cognitive.difficulty`), not the step count: the
  printed solution steps include the answer line and do not track depth (`fractions_hard` has
  2 steps, the 1-mark `decimals_compare` 3), and the M marks are always marks − 1.
- **Rule** (`paper.min_rung`, `paper.rung_shortfall`). A slot of 1 mark takes any rung, 2 marks
  medium or harder, 3 marks or more hard. Every pick ranks candidates by how many rungs they
  fall short, then by the least-used topic, then the seed. When no fitting blueprint is left
  the closest rung below fills the slot, so the rule never adds a placeholder.
- **Order.** A fixed section chooses for its 2-mark slots before its 1-mark ones (printing
  stays in slot order): the scarcer rung picks first, and the 1-mark slots then spread around
  the topics those took. Without it a P5 Booklet A put three questions on one topic.
- **Swaps (P8d).** `like`, `topic`, placeholders and "regenerate unlocked" rank by the same
  rule first. A swap never trades a generated question for an easier rung for its slot:
  "another topic" is refused ("the ones left are easier than this one") rather than drop a
  2-mark medium to an easy rung.
- **Effect** (100 seeds per template and level; fit = share of filled slots at their rung):

  | Paper | fit before → after | placeholders | topics per paper | most per topic |
  |---|---|---|---|---|
  | P5 Booklet A | 73% → 93% | 0 → 0 | 13 → 10 | 2 → 2 |
  | P5 Booklet B | 69% → 69% | 2 → 2 | 10.8 → 10.7 | 2 → 2 |
  | P5 Paper 2 | 50% → 50% | 3 → 3 | 9 → 9 | 2 → 2 |
  | P6 Booklet A | 67% → 100% | 0 → 0 | 15 → 10 | 1 → 2 |
  | P6 Booklet B | 67% → 80% | 0 → 0 | 13.6 → 11.5 | 1.9 → 2 |
  | P6 Paper 2 | 75% → 100% | 0 → 0 | 12.1 → 13 | 2.4 → 2 |

  The P5 rows are at the content's ceiling: four 2-mark medium and four 3-mark hard P5
  blueprints. The topics lost from Booklet A are Ratio, Percentage, Speed and the two
  Geometry ladders, whose only 2-mark blueprints are easy rungs; harder 2-mark items in those
  topics (and P5 hard 3–5-markers) are content work, not a generator change.
- **Tests.** `test_difficulty_follows_marks_without_costing_a_question` and a rung check in
  `test_generated_papers_keep_every_rule` (`tests/test_invariants_paper.py`; the Booklet A
  replay now ranks rung before topic); `_check_rungs` and the no-easier-swap assertion in
  `tests/test_invariants_paper_swap.py`, plus
  `test_a_swap_never_trades_a_question_for_an_easier_rung`.

## P8e batch 4 as built: Circles (EXA-149, 2026-11-17)

- **Why.** Real papers have about 2 circle questions a set, in every school (semicircle and
  quarter-circle composites, shaded regions, "in terms of π", mostly "Take π = 3.14"); we had
  one P6 item with a semicircle, always 22/7 when whole (REAL-PAPER-COMPARISON.md Part 2,
  ranked gap 7).
- **Ladder** (topic Circles, P6, `solvers/circles.py`, all with a `geometry_figure`):
  - `circles_easy`, 1 mark: circumference or area of a circle, area of a semicircle or a
    quarter circle, from a radius or a diameter.
  - `circles_medium`, 2 marks: a square with a semicircle on one side, a rectangle with a
    semicircle cut out (perimeter or area), the perimeter of a quarter circle. The shaded
    figure is what is measured, so an inside edge is not part of the perimeter.
  - `circles_hard`, 3 marks: shaded regions in a square or rectangle: the leaf of two quarter
    circles, a quarter circle with a semicircle on a side (total shaded area, or the shaded
    part's perimeter in terms of π, an `expression` answer), the gap between two quarter
    circles in a rectangle (area or perimeter: AB counts, the other sides do not).
- **π.** The stem says "Take π = 3.14" (60% of numeric items) or "22/7" (lengths then
  multiples of 7), and the lengths are drawn so the answer is whole or has 2 decimal places.
- **Marks and rungs.** 1 / 2 / 3 marks are exactly what "difficulty follows marks" asks of
  each rung, so the easy rung fills 1-mark slots (Booklet A MCQ too), the medium 2-mark slots
  (Booklet A MCQ, Booklet B, Paper 2 Section A) and the hard one a Section B stand-in.
  "In terms of π" is only on the hard rung: the multiple-choice copy needs numeric options,
  and a 2-mark medium is a Booklet A MCQ candidate (real papers do ask 2-mark MCQs in terms of
  π; that needs expression options in `mcq.py`).
- **Effect** (100 seeds per template, P6): a circle question in every generated paper part:
  Booklet A 1.27 a paper (easy 68, medium 59 per 100, all as MCQ), Booklet B 1.44 (easy 44,
  medium 100), Paper 2 1.18 (medium 69, hard 49); about 3.9 a full set against the real 2,
  because each paper part spreads topics on its own and a new topic is the least used. Rung
  fit in P6 Booklet B rose from 80% to 87%; no placeholders added. P5 papers never draw it.
- **Tests.** `tests/test_invariants_circles.py` re-derives every answer from the printed stem
  by another decomposition and from the drawn figure (each shaded region traced from the spec
  and measured numerically with the true π; every named wrong answer is told apart),
  `tests/test_generate_circles.py`, `tests/test_distractors_circles.py`; the figure-label
  sweep picks the new figures up by itself.
- **Goldens** `tests/golden/circles_{easy,medium,hard}.jsonl`, 3 each, picked from seeds; a
  person checks them.

## Topics spread over an exam set (EXA-153, 2026-11-17)

- **Why.** Each paper spread its topics on its own, so a topic with a question in every paper
  had 4–6 in a set (a P6 set: Algebra, Average, Decimals, Rate, Charts, Volume and Whole
  numbers each up to 6; real sets average 1.3–2.3 on most of these, REAL-PAPER-COMPARISON.md
  Part 2, 2b).
- **Rule** (`paper.generate_paper(..., set_topics)`, `paper.generate_set`, `SET_TOPIC_CAP = 3`).
  One paper of a set is told the topics of the set's papers made before it. "Least-used topic"
  then counts the whole set, and a topic with 3 questions in the set is full: a slot takes a
  full topic only when every blueprint left for it is full, ranked above the rung rule. A paper
  on its own (no `set_topics`) is exactly as before.
- **Fill order** (`paper.set_fill_order`). The set is filled biggest slots first: Paper 2,
  Booklet B, then Booklet A (printed order unchanged). Paper 2's 3–5-mark slots need the scarce
  hard and medium blueprints, so they choose while every topic is free; Booklet A's 1-mark slots
  take any rung, so it copes best with full topics. Filling A first left Paper 2 at 50% fit.
- **Web.** The "+ New" wizard makes the set one paper per request, in the fill order (the
  progress list stays in printed order; retry works as before), and sends the running count
  from the reports; `POST /documents/generate` takes `set_topics`.
- **Effect** (100 seeds; fit = share of single-part questions at the rung their marks ask for):

  | Set | most per topic | fit A / B / P2 | fit of the set |
  |---|---|---|---|
  | P6 before | 6 | 100% / 80% / 100% | 94% |
  | P6, cap 3, A first | 4 | 100% / 80% / 50% | 76% |
  | **P6, cap 3, Paper 2 first** | **4** | **80% / 80% / 100%** | **87%** |
  | P6, cap 4, Paper 2 first | 5 | 100% / 80% / 100% | 94% |
  | P5 before | 6 (71% of sets) | 93% / 69% / 50% | 70% |
  | **P5, cap 3, Paper 2 first** | **5** | **93% / 69% / 50%** | **70%** |

  The trade-off left: Booklet A comes last, so its 2-mark MCQs often find the medium topics
  full and take a 2-mark easy item (about 3 of its 5; 80% overall). A cap of 4 keeps every fit
  but lets one topic reach 5 in every P6 set. P5's fit is the content's ceiling either way.
  Both ease as topics are added (EXA-143–150).
- **A failed paper in the wizard** doesn't stop the rest: they are made without its topics, and
  a retry is told the topics of every paper made by then. A retried Paper 2 still spreads its
  topics but chooses last, so it may take more easier-rung questions than usual.
- **Tests.** `test_an_exam_set_spreads_its_topics` (at most 4 of any topic in a P6 set and 5 in
  a P5 set, no set worse than its papers made apart, Paper 2 of a set at least as well fitted as
  alone) and set papers in `test_generated_papers_keep_every_rule`
  (`tests/test_invariants_paper.py`). Swaps stay per-paper.
