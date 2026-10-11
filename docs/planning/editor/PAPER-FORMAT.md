# Paper format — making the editor produce a real P5/P6 maths paper

Shaping for the owner's feedback of 2026-10-11 (after trying the editor). Goal: the editor
becomes the main surface teachers use, and its WYSIWYG page and exported PDFs look like a
real Singapore P5/P6 maths paper, with the working space, answer lines, marks, sections and
marking furniture a teacher expects.

## Where we are today (checked in the code)

| Feedback item | Today |
|---|---|
| Formatting toolbar | Text buttons only (B, I, U, lists, break, equation, image). The top bar is sticky, the formatting toolbar under it is not. |
| Working space | One bordered box under each question, height `18px + 16px × marks` (`.answer-space` in `print.css`), not adjustable and not drawn in the editor. |
| Answer line (`Ans: ____ unit`) | None. A free-form question has one `answer` doc (key only); a templated question prints no line. |
| Multi-part questions | Templated snapshots keep canonical `parts[]` and render them. A **free-form** question is a single body with one marks value and one answer, so a teacher cannot author (a)/(b). |
| Paper structure | Headings and page breaks only. No sections, booklets, time, section totals or auto-numbering rules. |
| Marking margin and per-page tally box | None. |
| Marks display | Beside the question only. |
| Answer key | Re-renders each question, then the worked solution and the M/A/B scheme (`mode=key`/`full`). Not optional. |

## The paper being modelled (owner's observations)

- **Paper 1** (45 marks, 1 hour): **Booklet A** MCQ, 15 questions, 20 marks; **Booklet B** short
  answer, 15 questions, 25 marks.
- **Paper 2**: **Section A** (about Q1–5, 2 marks each, 10 marks) then **Section B** (about
  Q6–17, multi-part, 45 marks).
- Working sections (Booklet B, Paper 2) have a right margin headed **"Do not write in this
  space"** for marker notes, and a **tally box** bottom-right of each page: a square split by a
  bottom-left to top-right diagonal, blank upper-left triangle (marks awarded), the page's
  total available marks in the lower-right.
- Each question: text and figures, blank working space, then `Ans: ____ unit [marks]`; each
  part of a multi-part question has its own space and answer line `Ans: (a) ____ [2]`.
- Answer keys do not repeat the question, usually omit the M/A breakdown, and are
  space-efficient (two columns is a later nicety).

## Slices (recommended order)

| # | Slice | What | Size |
|---|---|---|---|
| **P1** | Editor chrome | Icon toolbar (Word/Docs-style icons with tooltips and aria-labels, text kept only for B/I/U) and a formatting toolbar that stays visible while scrolling (it is currently scrolled away; the top bar alone is sticky). | S |
| **P2** | Working space + answer line + marks placement | Per-question **space** (presets S/M/L/XL, default larger than today, plus a drag handle in the editor; drawn in the editor and the PDF). Per-question **answer line** with a unit (`$`, `°`, cm, m, cm², l, …; derived from the answer unit for templated questions, picked for free-form). **Marks placement** document setting: beside the question / beside the answer line / both, default answer line. | M |
| **P3** | Multi-part free-form questions | A `freeformQuestion` can hold parts (a), (b)… each with text, marks, space, answer line and answer. Templated parts already exist; they gain the same space and answer line. Schema `document` 1.4.0. | M |
| **P4** | Paper structure | `section` blocks (title, instructions, marks target, mode MCQ / short answer / structured), continuing question numbers, running and target totals, paper time. Starter templates: Paper 1 Booklet A, Paper 1 Booklet B, Paper 2 (editable, not hard-coded). | M |
| **P5** | Answer-key options | Key export options: hide question text (steps and answer only), include or omit the M/A marks breakdown, include or exclude chosen questions; the editor's answer-key view mirrors them. Two-column is deferred. | S–M |
| **P6** | Marking page furniture | Right margin with "Do not write in this space" and the per-page tally box with total available marks, per section toggle. | L, spike first |

**Why this order.** P1 is independent and cheap. P2 precedes P3 because part-level answer lines
reuse its space and answer-line model. P4 needs P3 for numbering and totals to be meaningful.
P5 is small once P2–P4 settle the model. P6 last: it depends on stable question sizes and is
the one real technical risk.

## The risk: per-page mark totals (P6)

The tally box needs the marks of the questions that sit on each page, so it depends on real
pagination, which only the print engine knows. Plan: render the paper in headless Chromium
(already used for PDFs), measure each question's page from its position, sum marks per page,
then inject the boxes in a second pass. Questions are kept whole (`break-inside: avoid`);
a multi-part question that cannot fit splits between parts, never inside one. A part's marks
count on the page where its answer line falls. The editor can only approximate pagination, so
the WYSIWYG view shows the margin and an indicative box; the PDF is authoritative. Spike this
before committing to the slice.

## Decisions (confirmed by the owner, 2026-10-11)

1. Space unit: presets (S/M/L/XL) plus a drag handle in the editor, stored as millimetres.
2. Default marks placement: beside the answer line, switchable per paper (question / answer line / both).
3. Tally box and margin: on by default for sections marked "working", off for MCQ.
4. Pagination in the editor: indicative page frames; the PDF is the source of truth.
5. Starter paper templates ship as editable presets; mark totals are targets that warn, not hard limits.

## Added later the same day

| # | Slice | What | Size |
|---|---|---|---|
| **P7** | Cover, title and blank pages | A title/cover page block (school, paper, level, time, candidate name/class/date fields, instructions) and an explicit blank page (e.g. "This page is intentionally left blank", or rough-work space). To be discussed and shaped separately; captured here so it is not lost. | S–M, later |
| **P8** | One-click full paper generation | See below. | L, its own shaping |

### P8 — generate an entire paper with one click

**Workflow (owner).** A teacher presses one button and gets a whole paper, built to the real
composition: **Paper 1** (Booklet A: 15 MCQ, 20 marks; Booklet B: 15 short-answer, 25 marks;
45 marks, 1 hour) and **Paper 2** (calculator allowed: Section A short answer, about Q1–5 at 2 marks
each = 10 marks; Section B multi-part questions, about Q6–17 = 45 marks). Roughly 50 questions
across the exam, which is too slow to add one at a time. Sensible default mixes of question types
per section, and the totals per paper and per section are respected. Then the teacher reviews:
**keep** the questions they like, **swap** the ones they do not for another from the templated
blueprints, or **replace with their own** free-form question.

**Shape.**
- A **paper template** (the P4 starter, now with a composition: per section, a list of slots of
  `{marks, kind, topic weights, difficulty}`) plus `generate_paper(template, seed)` — pure and
  deterministic like `generate()`, so the same seed gives the same paper; a different seed is a
  different paper.
- Slot filling is a small constraint solve: choose, per slot, a blueprint whose marks and kind
  match, spread topics (no topic over-represented, no repeated question within a paper), and hit
  each section's mark total exactly. Failure to fill a slot falls back to a placeholder the teacher
  fills (never a silent short paper).
- **Swap** is per-question: "another like this" (same slot, new seed or sibling blueprint),
  "another topic" and "write my own" (a free-form question that keeps the slot's marks and answer
  line). Keep/lock a question so a later "regenerate paper" leaves it alone.
- The UI is a generate-paper dialog (choose paper, level, calculator or not, total/section marks,
  optionally topic emphasis), which creates a document; everything after that is the ordinary
  editor.

**Hard dependency — content coverage.** The engine today has 8 ladders of constructed-response
questions (ratio, fractions, percentage, speed, geometry angle and area, chart reading, volume).
A real paper needs far more:
- **MCQ for Booklet A**: none of our blueprints produce multiple choice yet. The schema supports
  `choice` answers, so this needs a way to turn a constructed-response question into an MCQ
  (deterministic distractors from common wrong answers) or new MCQ blueprints.
- **Multi-part structured questions for Paper 2 Section B**: blueprints emit a single part.
  Needs multi-part blueprints (a shared stem with (a)/(b)/(c)), which also depends on P3.
- **Topic breadth**: P5/P6 syllabus topics beyond the eight we have (whole numbers, decimals,
  area and perimeter of composite figures, average, algebra, rate, circles, data tables, and so on).
  Until coverage grows, generation must honestly report which slots it could fill from blueprints
  and which are left for the teacher, rather than padding with irrelevant questions.

So P8 is a programme, not one slice: P8a paper templates + generator on the existing blueprints,
P8b MCQ conversion, P8c multi-part blueprints, P8d keep/swap/lock UI, P8e coverage growth. It sits
after P2–P4, because a paper needs sections, answer lines and multi-part questions to land in.
