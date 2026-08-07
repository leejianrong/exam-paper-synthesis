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

## Papers analysed

| Paper | Questions | Figures | MCQ | Notes |
|---|---:|---:|---:|---|
| Ai Tong School 2025 Prelim | 47 (100 marks) | 29 | 15 | answer key with working; 6 low-confidence items |
| CHIJ St Nicholas Girls' 2025 Prelim | 47 (100 marks) | 27 | 15 | answer key with working; 6 low-confidence items |
| Catholic High 2025 Prelim | 47 (100 marks) | 28 | 15 | answer key with working; 5 low-confidence items |
| **Total** | **141** | **84** | **45** | all P6, Paper 1 Booklets A+B and Paper 2 |

The structural uniformity is striking: **47 questions, 100 marks and exactly 15
MCQs in every paper.** Whatever we build to hold one prelim paper holds them all.

### Aggregate figure kinds (84 figures, 3 papers)

| Kind | Count | Share | In how many papers |
|---|---:|---:|:--:|
| geometric | 28 | 33% | 3 |
| **table** (incl. tables inside composite figures) | **15** | **18%** | 3 |
| context picture | 10 | 12% | 3 |
| coordinate / square grid | 9 | 11% | 3 |
| 3D solid | 8 | 10% | 3 |
| charts (line 4, bar 2+, pie 1+) | ~11 | 13% | 3 |
| net | 3 | 4% | **3** |
| number line | 1 | 1% | 1 |

**58 of 141 questions (41%) have no figure at all.**

### What the second and third papers changed

Ai Tong alone was misleading in three ways, and this is the main value of having
run more than one paper:

1. **`geometric` fell from 45% to 33%.** Ai Tong is unusually geometry-heavy, so
   `geometry_figure` covers less of the ground than one paper suggested.
2. **Tables are far bigger than they looked** — 18% of figures, the second most
   common kind, present in all three papers, and repeatedly used as the *answer
   surface*. On one paper's evidence this was ranked 7th; it belongs near the top.
3. **Construction answers are a recurring cluster, not a one-off.** Ai Tong had
   one; CHIJ has four and Catholic High four — **9 across the three papers**, and
   every single one is a drawing on a **square grid**. Ranked 14th (last) on one
   paper. That was wrong.

Also newly visible as recurring rather than incidental: **nets** (all three
papers), **symbolic π answers** (all three), and the **True/False/Not-possible-to-tell
tick matrix** (all three).

### Composition of the first paper

| | Count | Share |
|---|---:|---:|
| MCQ (Paper 1 Booklet A) | 15 | 32% |
| Short-answer | 22 | 47% |
| Structured (multi-part) | 10 | 21% |
| **Figures total** | **29** | |
| — `geometric` (candidates for `geometry_figure`) | 13 | 45% |
| — everything else (no structured home; `raster` only) | 16 | 55% |
| Figures shared across more than one part | 8 | |
| Parts with no mark allocation of their own | 4 | |

### Headline result

**17 of 47 questions (36%) cannot be represented at all** under schema v1.4.0 —
not "awkwardly", but with no valid object available: the 15 MCQs (no `options`
anywhere), plus Paper 1 Q26 and Paper 2 Q6, each of which has a part whose answer
is not a value. A further tranche is expressible only by collapsing structure into
`answer.type: "text"` or an image.

That settles the authoring-scope question the exercise was run to answer. A
parametric-only editor would not reach a third of this paper, and the topics our
blueprints cover account for roughly 18 of 47 questions — before considering
whether we can draw their figures. See
[Verdict on the authoring surface](#verdict-on-the-authoring-surface).

### What worked

Worth recording, because it means the object is sound where it does reach:

- **`stem` / `parts[]` / `total_marks` matched the paper's own structure.** The
  extractor independently recorded `figure` at *stem* level for structured
  questions, which is how the paper is laid out — that's what G2 is about.
- **`solution_steps` fits the answer key almost directly.** 40 of 47 questions
  print working, and it maps step-for-step.
- **`integer` / `decimal` / `fraction` / `quantity` / `text` covered most numeric
  answers**, and `source` + `license` + `provenance.created_by: "ingested"` carry
  the paper's identity with nothing missing.

---

## Gaps found

### G1–G3: confirmed

All three predicted gaps are demonstrated by this paper. They are no longer
predictions.

### Structural gaps identified up front

These three fell out of reading the schema before any paper arrived.

#### G1 — No multiple-choice questions — **CONFIRMED**

There is no `options`, `choices`, or equivalent anywhere in the schema. A part is
always a constructed response: `answer` is one of
`integer | decimal | fraction | ratio | quantity | set | text`.

**Evidence:** 15 of 47 questions (32%) — the whole of Paper 1 Booklet A. These
cannot be expressed at all, which makes G1 the single largest gap found.

**And it's worse than "add `options[]`."** Three of the fifteen have options that
are *themselves diagrams*, not text:

| Q | Options are… |
|---|---|
| P1 Q8 | four candidate nets of a cube (FIG-2) |
| P1 Q9 | four candidate pie charts (FIG-3) |
| P1 Q11 | four candidate isometric solids (FIG-4) |

So an option is not a string — it needs the same text-or-diagram capability a part
has. A minimal `options: [string]` would cover 12 of 15 and silently fail the rest.

One more wrinkle: P1 Q7 prints a header row spanning the options
(`Smallest … Greatest`), which is presentation attached to the option *list*
rather than to any one option.

Cost: a part-level `options[]` whose entries carry text and/or a diagram, plus
which option is correct (by label, since the paper labels them `(1)`–`(4)`), and
a renderer branch. Not cheap, but unavoidable.

#### G2 — A figure cannot attach to the stem, only to a part — **CONFIRMED**

`question` has exactly `{ stem?, parts[], total_marks }` — no `diagram`.
`diagram` lives on each part. The very common paper layout

> The figure below shows … **(a)** … **(b)** …

therefore has to duplicate the same figure into every part, or attach it to part
(a) and rely on layout. Both are wrong: the object stops being a faithful
representation of the question, and the duplicate copies can drift.

**Evidence:** 8 of 29 figures are shared across more than one part — FIG-9, 14,
22, 24, 25, 26, 27, 28. That is *every* structured question in the paper that has
a figure at all. The extractor, working only from the PDF and with no knowledge of
our schema, recorded `figure:` at stem level for each of them; the paper's own
layout is stem-level.

Cost: allow `diagram` on `question`. Low risk (additive, optional), but it
touches both renderers (Python + the TS mirror) and the diagram-consistency
check needs to know which part's answer a stem-level figure is checked against.

#### G3 — No table representation — **CONFIRMED**

No `table`/`rows`/`columns` anywhere, and `diagram` has no table variant.

**Evidence:** 4 of 29 figures involve a table — and in two of them the table is
not given data but the *answer surface*:

| Figure | Role of the table |
|---|---|
| FIG-18 (P2 Q1) | water-tariff table with a **blank cell that is the answer** |
| FIG-22 (P2 Q6b) | three statements × True / False / Not possible to tell, **answered by ticking cells** |
| FIG-3 (P1 Q9) | given data, feeding four pie-chart options |
| FIG-28 (P2 Q15) | given figure-number → rod-count table for a pattern question |

`raster` renders these but makes the content opaque. It also cannot work at all
for FIG-22, where the ticked cells *are* the answer (see G6).

### Gaps found from real questions

Numbered from G4. Each is demonstrated by at least one question in the paper.

#### G4 — The `diagram` union covers under half the figures

`diagram.type` is closed at `bar_model | bar_model_before_after |
geometry_figure | shaded_fraction | raster`. Of 29 figures, 13 (45%) are
`geometric` and so are *candidates* for `geometry_figure`; the other 16 (55%) have
no structured home and can only be `raster`:

| Kind | Count | Figures |
|---|---:|---|
| context picture | 3 | FIG-1, 13, 15 |
| 3D solid | 3 | FIG-10, 23, 26 |
| coordinate grid | 2 | FIG-14, 29 |
| net | 1 | FIG-2 |
| bar chart | 1 | FIG-9 |
| line graph | 1 | FIG-19 |
| table | 1 | FIG-18 |
| pie chart + response table | 1 | FIG-22 |
| table + pie-chart options | 1 | FIG-3 |
| orthographic views + solids | 1 | FIG-4 |
| rod pattern + table | 1 | FIG-28 |

Notably absent from our union and *recurring*: **3D solids** (cuboids, containers,
water tanks — 3 figures, and volume is a major P6 topic), **statistical charts**
(bar, line, pie — 4 figures), and **coordinate/square grids** (2 figures).

Not all 16 deserve a parametric type. But `raster` for 55% of figures means the
bank is mostly opaque blobs, which undercuts the searchable-bank goal.

#### G5 — `geometry_figure` allows only one unknown, but a shared figure needs one per part

The schema says of `angles`: *exactly one may set `unknown: true`*. That holds for
a single-part question. It breaks the moment a stem-level figure serves two parts
that each ask for a different angle.

**Evidence:** FIG-24 (P2 Q8) marks **∠LOK** unknown for part (a) *and* **∠LNM**
unknown for part (b). FIG-27 (P2 Q14) does the same with **∠DEC** and **∠DFC**.

This interacts with G2: once a figure is stem-level, the one-unknown rule is
actively wrong. The consistency check needs to bind each unknown to the part that
asks for it.

#### G6 — Answers that are not values

Three answer shapes in this paper have nowhere to live:

| Q | The answer is… | Today |
|---|---|---|
| P1 Q26b | **a construction on the figure** — complete the parallelogram and label point D. The answer key ships a completed figure (FIG-29) | cannot express |
| P2 Q6b | **a tick per row** in a 3 × 3 True/False/Not-possible-to-tell matrix | cannot express |
| P2 Q16a | **two labelled slots in one part** — "Least: ___, Most: ___" | cannot express (would need two parts, which the paper doesn't have) |

The construction answer is the deepest of the three: the answer is a *diagram*,
which means an answer key has to render a figure, not a value. That is a genuine
extension of what "answer" means, not a new variant of it.

#### G7 — No symbolic or algebraic answers

| Q | Answer as printed |
|---|---|
| P1 Q13 | `(42π + 42) m` — asked for explicitly "in terms of π" |
| P1 Q25 | `$17n` — asked for explicitly "in terms of n" |

Both would have to collapse into `answer.type: "text"`, losing any structured
checking. Note this is not exotic: "leave your answer in terms of π" is standard
PSLE phrasing, and our own geometry ladder auto-selects π, so we already care
about exact forms.

#### G8 — No compound quantities

**Evidence:** P2 Q10 instructs "Express your answer in h and min"; the answer is
`2 h 36 min`. No `answer` variant composes two units. `quantity` takes a single
`value` + `unit`.

Also relevant: P1 Q27's answer is `1.95 ℓ` where the figure's readings are in ml
— unit conversion within one question is routine, and money as dollars-and-cents
(P2 Q16c, `$10.40`) is the same shape.

#### G9 — `part` requires fields real papers don't supply

`part.required` is `label, text, marks, answer, marking_scheme, solution_steps`.
Two of those don't survive contact:

- **`marks`** — 4 parts (P1 Q21a/b, P1 Q26a/b) have **no mark allocation of their
  own**; the paper allocates 2 marks to the whole question. Forcing a per-part
  split means inventing information the paper doesn't contain.
- **`marking_scheme`** — the paper's answer key gives *working*, never an M/A/B
  breakdown. Across all 47 questions, nothing supplies a marking scheme. So every
  sourced question either fabricates one or cannot validate.

`solution_steps`, by contrast, maps cleanly from `working_shown` — 40 of 47
questions print working.

#### G10 — Multi-panel figures

Two figures are really *several* drawings that must be read together, with the
relationship between panels carrying meaning:

- **FIG-12 (P1 Q24)** — "Before folding" and "After folding", joined by a fold
  line, a curved arrow and a large right-pointing arrow. The transformation
  *between* panels is the question.
- **FIG-23 (P2 Q7)** — Figure 1 (empty container), Figure 2 (front view, filled),
  Figure 3 (same container upside down). Three panels sharing one baseline.

`geometry_figure` is a single point set. `bar_model_before_after` proves we
already accept the two-stage idea for bar models; this is the general case.

#### G11 — Figure styling primitives are missing

Recurring marks in the `geometric` figures that `geometry_figure` cannot express:

| Mark | Where |
|---|---|
| **dashed / construction segments** | FIG-5 (dashed BC), FIG-11, FIG-21 (dashed baseline), FIG-25 (dashed construction lines), FIG-26 (hidden edges) |
| **dimension arrows** (double-headed, labelled) | FIG-5, 10, 17, 20, 26 |
| **parallel-side marks** | FIG-16 (AD ∥ BC), FIG-27 (DE ∥ FC), FIG-29 |

`segments` currently carries only `label?` and `ticks?`. Dashed lines and
dimension arrows are the two most common; both are cheap additive properties.

#### G12 — Shaded regions cannot have holes

`shaded` is `{ boundary: [ids…], arcs? }` — a single closed boundary. Three
figures shade a region defined by *subtraction*:

- **FIG-6 (P1 Q14)** — the band between an outer and a middle triangle (a ring).
- **FIG-11 (P1 Q23)** — everything *except* two triangles (a complement).
- **FIG-25 (P2 Q12)** — caps between an outer boundary and inner semicircle arcs.

Needs either a hole list per shaded region or an even-odd fill rule.

#### G13 — The `unit` enum breaks immediately

The countable-noun tail (`marbles`, `items`, `people`, `units`) was already
flagged as a stand-in. This paper needs, among others: **pages** (P2 Q9),
**bags** and **mangoes** (P2 Q11), **muffins** (P1 Q25), **rods** (P2 Q15),
**coins** (P2 Q16), **students** (P1 Q9), **cubes** (P1 Q11).

The tail is unbounded — it is whatever the word problem is about. A closed
vocabulary is right for *measurement* units (where `cm` vs `cm^2` matters
mathematically) and wrong for the noun being counted. These are two different
things sharing one enum.

Minor: the paper writes litres as `ℓ`; our enum has `l`.

#### G14 — "Measure the figure" questions invert the diagram invariant

`geometry_figure`'s stated principle is that *every labelled value is exact — it
comes from the solved parameters, never from measuring the drawing*.

**Evidence:** P1 Q20 ("Measure and write down the height…", answer 2.9 cm) and
P1 Q26a ("Measure and write down the size of ∠ABC", answer 141°) require the
opposite: the drawing must be to scale, and the answer is read *off* it.

For sourced questions this is only a note. But it's also an **opportunity**: we
render SVG from exact coordinates, so we control scale precisely — meaning
measure-the-figure questions are a blueprint family we *could* generate, with the
answer derived from the coordinates we chose. Worth a separate look.

#### G16 — A stem and figure can be shared across separate *questions*

G2 is about a figure shared across parts of one question. This is a level above:
a preamble and figure shared by two **numbered questions**.

**Evidence (CHIJ):** *"Use the information below to answer Question 9 and 10"* —
FIG-4 (a bead-count table) serves Q9 and Q10. The same pattern repeats for
Q21/Q22 with FIG-9 (a line graph).

One canonical object is one whole question, so there is nowhere to put shared
context spanning two of them. Duplicating the table into both objects makes them
silently coupled — edit one and the paper becomes inconsistent.

This is the first finding that argues for something *above* the question object —
a question **group** or a paper-section container. It overlaps G15 and is probably
the same feature.

#### G17 — No time-of-day answers (distinct from durations)

Our `unit` enum has `s`, `min`, `h`, which express **durations**. Three questions
want a **clock time**:

| Q | Answer |
|---|---|
| CHIJ P1 Q27 | `3:30 pm` |
| Catholic High P2 Q12b | `11 50` |
| Catholic High P1 Q6 | options are times — `4.15 p.m.`, `9.35 p.m.` |

And the two are mixed freely: CHIJ P1 Q7 asks for a duration (`9 h 15 min`) from
two clock times. A time of day is not a quantity with a unit — it's a distinct
type, and papers write it inconsistently (`3:30 pm`, `11 50`, `4.15 p.m.`).

#### G18 — No compass directions, and figures need a north arrow

**Evidence:** CHIJ P1 Q24a answers `North-East`; Catholic High P1 Q9's options are
all compass directions. Both figures (CHIJ FIG-10, CH FIG-6) print a **north
arrow** beside the grid, which `geometry_figure` has no way to express.

Direction is a small closed vocabulary (8 compass points), so the answer side is
cheap. The north arrow is a figure annotation, and it pairs with the grid work in
G4.

#### G19 — Real answer keys contain errors, so import cannot be trusted

Not a schema gap, but it constrains the editor and is worth recording where the
evidence lives.

Every paper's answer key has defects the extractor flagged:

| Paper | Defect |
|---|---|
| Catholic High P1 Q24 | the key's response table prints **a statement from a different question** |
| Catholic High P1 Q28 | "area of triangle" where the question has no triangle |
| Catholic High P2 Q15b | working names "Mr. Lee" where the question says Mrs Sim |
| CHIJ P2 Q9a | working is arithmetically inconsistent (`45 + 28 = 73`, `73 ÷ 6.57 = 79.57`) |
| CHIJ P2 Q16 | "1 units", "5 unit" |
| Catholic High P2 Q10 | "m/mim", "Combines speed" |

So `working_shown` cannot be imported straight into `solution_steps` and trusted.
This is exactly what the schema's `validation.status: "unverified"` plus
`checks.human_reviewed` is for — and it means **the editor needs a review step on
import**, not a silent conversion. It also vindicates the extraction prompt's rule
against the extractor "fixing" anything: these defects are visible precisely
because it transcribed them verbatim.

#### G15 — A paper has section structure; a worksheet is a flat list

This paper is Paper 1 Booklet A (MCQ, no calculator), Booklet B (short answer),
and Paper 2 (long structured) — 100 marks total. Sections carry their own
instructions and answer conventions.

Our worksheet is a flat titled list of questions with total marks. Recreating a
*paper* rather than a *worksheet* needs section grouping. This is a
worksheet/editor-level gap, not a question-object one, so it belongs in the
editor's own requirements rather than the schema.

---

## Verdict on the authoring surface

The exercise was run to decide between a parametric-only editor, a free-form one,
and both. The evidence answers it:

- **Parametric-only is not viable.** It cannot reach the 36% of questions that have
  no valid object today, and our six blueprint topics cover roughly 18 of 47
  questions before asking whether we can draw their figures.
- **Free-form is required**, with `raster` as the pragmatic figure escape hatch —
  which is exactly the `sourced` / human-vouched path V7 already proved.
- **Parametric stays valuable** for the topics we do generate, because those
  questions keep the engine's correctness proof. The trust distinction
  (`source_type`, `created_by`) is already in the schema and should stay visible
  in the UI.

So: **both paths, clearly separated** — but free-form is the one that unblocks
recreating a real paper, and should come first.

> **A caveat on the 36%.** "Cannot represent" is about missing schema slots and is
> a poor proxy for what the engine could *generate*. The 15 MCQs are the largest
> unrepresentable block **and** the most generatable content in the paper. See
> [`PARAMETERIZATION.md`](PARAMETERIZATION.md), which works the same paper the
> other way round: ~60% of it is generatable with cheap additions and ~96% with a
> built-out figure vocabulary, because the obstacle is figures, not mathematics.

### Schema work, ranked — REVISED over three papers

Three papers moved three things substantially. The revised order:

| | Change | Evidence across 3 papers | Was |
|---|---|---|---|
| 1 | Part-level `options[]`, entries carrying text *and/or* diagram (G1) | 45 questions (32%), exactly 15 per paper | 1 |
| 2 | `diagram` on `question` (G2) | 28 of 84 figures shared across parts | 2 |
| 3 | `marks` / `marking_scheme` optional on `part` (G9) | 18 parts; no key supplies M/A/B | 3 |
| 4 | Unknowns bound to parts (G5) | required for #2 to be correct | 4 |
| 5 | **A `table` type** (G3) | **15 of 84 figures (18%), all 3 papers, used as answer surface** | **7** |
| 6 | **`grid` background + polygons on `geometry_figure`** (G4) | **9 grid figures, all 3 papers; the substrate for #7** | bundled |
| 7 | **`construction` answers — an answer that is a diagram** (G6) | **9 questions, all 3 papers, every one on a grid** | **14** |
| 8 | Segment styling, dimension arrows, parallel marks, north arrow (G11, G18) | 5+ figures per paper | 5 |
| 9 | Shaded regions with holes / annuli (G12) | rings recur; CHIJ FIG-6, CH FIG-26 | 6 |
| 10 | `expression` answers — π and algebra (G7) | all 3 papers; **algebra also appears inside table cells** | 9 |
| 11 | `selection` answers — tick matrices (G6) | all 3 papers | — |
| 12 | `compound` quantities, `time`, `direction` (G8, G17, G18) | all 3 papers | 10 |
| 13 | Split `unit` into closed measurement + open counted noun (G13) | pervasive | 8 |
| 14 | A question **group** / paper-section container (G15, G16) | 2 shared-stem pairs in CHIJ | — |
| 15 | Charts — bar, line, pie (G4) | ~11 figures, all 3 papers | 12 |
| 16 | `solid` type (G4) | 8 figures, but dimensions are usually in the stem | 13 |
| 17 | Multi-panel figures (G10) | 2 figures, 1 paper | 11 |

**The big movers.** `table` from 7th to 5th, `grid` promoted out of a bundle, and
`construction` answers from dead last to 7th. Those three are one cluster: nearly
every construction answer is *"draw shape X on this square grid"*, and tables are
the second most common figure kind in the paper. A one-paper reading badly
underweighted all three.

`solid` drops in practical terms even though it's 10% of figures, because the
dimensions are typically stated in the stem — the drawing is often illustrative.

### Original ranking, from the first paper only

Kept for the record, to show what one paper's evidence got wrong.

| | Change | Unblocks | Cost |
|---|---|---|---|
| 1 | Part-level `options[]` with text *and* diagram entries (G1) | 15 questions (32%) | medium |
| 2 | `diagram` on `question` (G2) | 8 figures, every structured question | low |
| 3 | `marks` and `marking_scheme` optional on `part` (G9) | 4 parts; every sourced question | low |
| 4 | Multiple unknowns bound to parts (G5) | 2 figures — and required for #2 to be correct | low |
| 5 | Segment `style: dashed` + dimension arrows + parallel marks (G11) | 5+ figures | low |
| 6 | Shaded regions with holes (G12) | 3 figures | medium |
| 7 | A `table` type (G3) | 4 figures, 2 as answer surface | medium |
| 8 | Split `unit` into measurement units (closed) + counted noun (open) (G13) | ~7 questions | low |
| 9 | Symbolic / algebraic answers (G7) | 2 questions | medium |
| 10 | Compound quantities (G8) | 2+ questions | low |
| 11 | Multi-panel figures (G10) | 2 figures | medium |
| 12 | Chart types — bar, line, pie (G4) | 4 figures | high |
| 13 | 3D solid figures (G4) | 3 figures | high |
| 14 | Construction answers (G6) | 1 question | high |

Items 12–14 are the ones to *deliberately leave* on `raster` for now: highest
cost, and the free-form path plus an image handles them at the price of opacity.
Items 1–5 are the ones that make the editor possible at all, and four of the five
are cheap.

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
