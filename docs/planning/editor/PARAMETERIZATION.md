# How much of a real paper can we parameterize?

Companion to [`SCHEMA-FIT.md`](SCHEMA-FIT.md), which asked whether the canonical
object can *hold* real questions. This asks the harder and more useful question:
how many of them could the engine *generate* — deterministically, with a proven
answer key?

Worked in detail against one paper — Ai Tong School 2025 Prelim, 47 questions —
then checked against two more (CHIJ St Nicholas, Catholic High; 141 questions
total). See [Checked against three papers](#checked-against-three-papers) for what
survived and what moved.

## Representation and generation are different questions

`SCHEMA-FIT.md` found that 36% of the paper cannot be *represented* today. That is
a statement about missing schema slots, and it is misleading as a proxy for
generatability — in both directions.

The 15 MCQs are the clearest case. They are the largest block of unrepresentable
questions **and** the most generatable content in the paper: arithmetic on
generated numbers, where the distractors are systematic (misplace a zero, round the
wrong way, divide instead of multiply). Fixing the MCQ gap converts the biggest
blocked bucket into the cheapest generated one.

A question is generatable when **three** things hold, and the third is the one that
usually fails:

1. A deterministic solver can compute the answer from parameters.
2. The wording is a template with the parameters substituted in.
3. **Any figure can be drawn from those same parameters.**

For this paper the maths is almost never the obstacle. The figures are.

## The three buckets

Classified by what it would take to generate each question, not whether the maths
is hard. Question numbers are `P1` = Paper 1 (Booklets A and B), `P2` = Paper 2.

| Bucket | Meaning | Count | Share |
|---|---|---:|---:|
| **A** | Generatable with existing figure support (or no figure) — needs a solver and, for MCQ, the `options` slot | 28 | 60% |
| **B** | Maths parameterizes cleanly, but needs a new figure or answer type of moderate cost | 17 | 36% |
| **C** | Resists parameterization — the insight doesn't survive changing the numbers, or the renderer cost is out of proportion | 2 | 4% |

### Bucket A — 28 questions (60%)

No figure at all, or a figure our `geometry_figure` already covers.

| Questions | Family | Status |
|---|---|---|
| P1 Q1, Q2, Q4 | place value, rounding, decimal decomposition | new family; trivial maths, systematic distractors |
| P1 Q5, Q7 | fraction comparison and ordering | new family; distractors are permutations |
| P1 Q3 | decimal ↔ percentage conversion | new family; distractors are ×/÷ 10, 100 |
| P1 Q10, P1 Q25 | algebraic substitution / expression | new family |
| P1 Q16 | order of operations | new family |
| P1 Q18 | average | new family |
| P1 Q19 | ratio part–whole | **existing** (`ratio_easy`) |
| P1 Q15, P2 Q9 | before-after / age ratio | **existing** (`ratio_hard`) |
| P1 Q12, Q30, P2 Q11, Q17 | fraction/percentage of remainder | **existing** (`fractions`, `percentage`) |
| P2 Q10 | speed, two bodies meeting | **existing** (`speed`) + compound answer |
| P1 Q17, Q28, P2 Q8, Q14 | unknown angles in a figure | **existing** (`geometry_angle`) + more templates, multi-unknown |
| P1 Q29, P2 Q4, Q5 | area/perimeter with arcs | **existing** (`geometry_area`) + more templates |
| P1 Q22, P2 Q13 | volume of a cuboid, tanks with flow rate | new family; figure is *decorative* — the stem states every dimension |
| P2 Q2 | measurement conversion | new family |
| P2 Q16 | money / coin mixes | new family |

Two things stand out. Roughly a third of this bucket is reachable by our **existing
six families** plus extra templates. And the volume questions (P1 Q22, P2 Q13) only
*look* like they need a 3D renderer — every dimension is given in the stem, so the
drawing is illustrative. A generated version can ship without it.

### Bucket B — 17 questions (36%)

The maths parameterizes cleanly; a new figure or answer type is the blocker.

| Questions | What's needed |
|---|---|
| P1 Q9, Q21, P2 Q3, Q6 | **charts** — pie, horizontal bar, line. One data-driven type covers all four |
| P2 Q1, P2 Q15 | **tables** — a tariff table with a blank cell; a pattern table |
| P1 Q26a, P2 Q15 | **square/coordinate grid** — points and segments on a grid background |
| P1 Q8 | **nets** — 11 valid cube nets, distractors from invalid hexominoes. Cleanly enumerable |
| P1 Q13, Q25 | **symbolic answers** — "in terms of π", "in terms of n" |
| P1 Q14, Q23, P2 Q12 | **shaded regions with holes** — rings and complements |
| P1 Q20, Q26a | **to-scale figures** — measure-the-drawing questions |
| P1 Q6, Q27 | **scale/context figures** — object icons, beaker scales |
| P2 Q7 | **multi-panel 3D** — same container upright and inverted |

The scoring pattern here is worth noting: **charts are the single best-value
addition.** One `chart` type with `kind: bar | line | pie` unblocks four questions
across two papers' worth of topics, and the underlying maths (read a value, compute
a difference or a percentage change) is trivially generatable.

### Bucket C — 2 questions (4%)

- **P1 Q11** — top and side views, pick the matching solid. Enumerable in principle
  (generate a polycube, compute its projections, render candidates) but needs an
  isometric renderer *and* a projection solver for one question.
- **P1 Q24** — a folded triangle. The fold is a reflection whose figure needs two
  panels and a transformed copy; the angle chase is generatable, the drawing isn't
  worth it yet.

Both are "expensive, not impossible." Neither should block anything.

### So: realistically

**~60% generatable with cheap additions, ~96% if we build out the figure
vocabulary, ~4% not worth it.** The 36% in bucket B is not blocked by mathematics
— it is blocked by roughly five new figure capabilities.

Caveat on all of the above: this is one paper and my classification is a judgement
call. Bucket boundaries should be re-checked against a second and third paper
before anything is committed to on the strength of them.

## Checked against three papers

The three papers are structurally identical — 47 questions, 100 marks, exactly 15
MCQs each — and **41% of all 141 questions (58) carry no figure at all**, which is
the floor under bucket A regardless of any renderer work.

### What held

- **MCQ is the top priority, unchanged.** 45 questions, precisely 15 per paper.
- **The maths is almost never the obstacle.** Across all three papers, the blocker
  is a figure or an answer shape, not a solver.
- **Bucket C stays tiny** — isometric-solid questions (3 across the three papers)
  and one folding question. Nothing else genuinely resists.
- **3D solids stay mostly decorative.** Where dimensions matter they are usually
  stated in the stem, so a generated version can ship without the drawing.

### What moved

| | One paper said | Three papers say |
|---|---|---|
| `geometry_figure` coverage | 45% of figures | **33%** — Ai Tong is unusually geometry-heavy |
| Tables | 4 figures, rank 7 | **15 of 84 figures (18%), rank 5** — 2nd most common kind, in every paper |
| Construction answers | 1 question, rank 14 (skip) | **9 questions, rank 7** — every one a drawing on a square grid |
| Coordinate grids | folded into "cheap additions" | **9 figures, all 3 papers** — and the substrate for construction answers |
| Nets | 1 question, one-off | **3 figures, one in every paper** |

The correction that matters: **tables, grids and construction answers are one
cluster**, and a single paper underweighted all three. Nearly every construction
answer is *"draw shape X on this square grid"* — so grid rendering plus an answer
that can hold a diagram unlocks 9 questions at once, and the same grid work also
covers nets and pattern figures.

Bucket-A-versus-B proportions are carried forward from the Ai Tong classification;
I have not re-bucketed all 141 questions individually. The 41%-no-figure floor and
the movements above are measured, but the precise 60/36/4 split is still one
paper's number.

### One more finding, from the answer keys

Every paper's answer key contains errors — a statement copied from the wrong
question, working that doesn't add up, the wrong person named. Recorded as G19 in
`SCHEMA-FIT.md`.

For parameterization this is an argument *for* generating rather than sourcing
wherever a family is reachable: an engine-generated answer key is proven by
construction, whereas an imported one needs human review and sometimes correction.
It also means the editor's import path needs a review step, not a silent
conversion.

## The real constraint is families, not questions

The binding cost is not schema expressiveness. It is that every blueprint family
ships a hand-written solver plus **an independently authored invariant test** — the
project's correctness authority (`tests/test_invariants_*.py`). Today: 6 families,
18 blueprints (3 difficulty rungs each), 6 invariant test files, ~190 lines per
solver.

So the unit of work is a **family**, not a question. And 47 questions collapse into
far fewer families — roughly 22, of which we have 6:

| | Families |
|---|---|
| **Have** (6) | ratio, fractions, percentage, speed, geometry_angle, geometry_area |
| **Need, no new figure work** (9) | place value & rounding, fraction comparison, percentage conversion, order of operations, average, algebraic expression, measurement conversion, volume & flow rate, money/coins |
| **Need, with figure work** (5) | charts, tables, grids & patterns, scale reading, nets |
| **Deliberately skip** (2) | orthographic→solid, folding |

That is the number that matters for planning: **about 14 new families** to cover a
whole prelim paper, 9 of which need no renderer work at all. And families are
reusable across papers — the same 22 will cover most P6 prelim papers, not just
this one. That is where the leverage is.

## What the schema should become

The instinct to "add a diagram type per figure kind" would produce eight or nine
new types and still miss the next paper. Two generalizations do more work.

### 1. `panels[]` — a wrapper, not a type

Any figure can be a sequence of labelled panels sharing a coordinate convention.
This handles before/after folding, Figure 1 / 2 / 3 containers, and side-by-side
tanks **once**, for every figure type, rather than per type.

`bar_model_before_after` is already this idea hard-coded for one case. Generalizing
it lets that type collapse into `bar_model` + panels later.

### 2. Grow `geometry_figure` into a general 2D scene

It is already a small declarative DSL — `points`, `segments`, `arcs`, `angles`,
`shaded`, `labels`. The additions found in this paper are mostly cheap, and
together they absorb several would-be new types:

| Addition | Absorbs |
|---|---|
| `style: solid \| dashed` on segments | construction lines, hidden edges (5 figures) |
| dimension arrows (double-headed, labelled) | 5 figures |
| parallel marks (alongside existing `ticks`) | 3 figures |
| `holes[]` on a shaded region, or even-odd fill | rings and complements (3 figures) |
| unknowns bound to a part, not one per figure | shared stem-level figures (2 figures) |
| an optional `grid` background | coordinate grids, nets, rod patterns |
| `polygons[]` as first-class regions | nets, tessellations |

With a grid background and polygons, coordinate grids, cube nets and rod patterns
stop needing bespoke types — they are points and unit squares on a grid.

### 3. Three genuinely new types

- **`chart`** — `kind: bar | line | pie`, plus categories, values, axis config.
  One type, four figures, and charts are pure data so they are the easiest thing
  here to generate and verify.
- **`solid`** — a small vocabulary (cuboid, cylinder, composite of cuboids) with
  dimension labels and an optional fill level. All three 3D figures in this paper
  are boxes with a water level.
- **`table`** — arguably not a diagram at all but *content*, with cells that may be
  blank and answerable. Belongs alongside `stem`, not inside `diagram`.

Net effect: **a wrapper, seven cheap `geometry_figure` additions, and three new
types** — versus eight or nine special-case types, with better coverage of whatever
the next paper contains.

### 4. The answer union needs the same treatment

| New variant | Covers |
|---|---|
| `choice` | MCQ — options carrying text *and/or* a diagram |
| `expression` | "in terms of π", "in terms of n" |
| `compound` | `2 h 36 min`, dollars-and-cents |
| `multi` | labelled slots in one part ("Least: …, Most: …") |
| `selection` | tick-per-row matrices |

Plus splitting `unit` into a **closed** measurement vocabulary (where `cm` vs
`cm²` matters mathematically) and an **open** counted noun (pages, bags, rods —
unbounded, because it is whatever the word problem is about).

`construction` — an answer that is a drawing — stays out. One question needs it and
it would mean answer keys render figures.

## Recommended order

Revised after the second and third papers.

1. **MCQ (`choice`) + `options` with diagram-capable entries.** 45 questions, and
   MCQ arithmetic is the cheapest generation in the paper.
2. **`diagram` on `question`, with per-part unknowns.** Cheap, and required for
   stem-level figures to be *correct* rather than merely allowed.
3. **Optional `marks` / `marking_scheme` on `part`.** Cheap; without it no sourced
   question validates.
4. **`table`.** Promoted from 6th: the second most common figure kind, in every
   paper, and sometimes the answer surface.
5. **`grid` background + polygons on `geometry_figure`.** Promoted, because it is
   the substrate for construction answers, nets and pattern figures — one piece of
   renderer work serving three clusters.
6. **`construction` answers** — an answer that carries a diagram. Promoted from
   "deliberately skip": 9 questions, one in every paper, all on grids from step 5.
7. **The cheap `geometry_figure` additions** — dashed segments, dimension arrows,
   parallel marks, north arrow, holes.
8. **`chart`.** Still good value, but behind the table/grid cluster now.
9. The nine no-figure families, in whatever order suits the syllabus.

`solid` and multi-panel figures stay on `raster`. Bucket C — isometric-view
questions and folding — stays out.

The one-paper version of this list had `table` 6th, `grid` bundled into step 5,
and construction answers dropped entirely. Two more papers were enough to correct
all three, which is a reasonable argument for running a fourth before committing to
build order below step 3.
