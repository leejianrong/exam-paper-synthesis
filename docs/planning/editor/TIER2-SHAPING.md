# Schema tier 2 — figure vocabulary: shaping

Follows the [re-bucket against v1.6.0](SCHEMA-FIT.md#re-bucket-against-v160)
(KAN-663). That exercise found 33 of the 51 still-awkward questions blocked by
**G4 figure vocabulary**; closing it alone lifts fit from 90 to ~117 of 141
(83%). This doc shapes *how*. It is evidence-driven: three agents (one per paper)
inventoried every non-plain-geometry figure and the fields a renderer would need.
The papers are untracked, so figures are cited by reference (`P1 Q9`), never
reproduced.

> **Scope note.** This goes past the earlier "stop at ranked item 7" decision
> (items 8+ deferred). Re-opened deliberately, on the evidence that charts and
> solids are now the two largest blockers by question count (old ranks #15, #16).

## Requirements

| | Requirement | Evidence |
|---|---|---|
| T-R1 | A teacher can put a bar, line or pie chart in a question and the figure is **structured data**, not a raster | 11 questions (AT 4, CHIJ 5, CH 2), all 3 papers |
| T-R2 | Solids with dimensions and a fill level are structured | 9 questions (AT 4, CHIJ 3, CH 2) |
| T-R3 | Unknown / hidden values in a figure **never leak** into SVG or any text alternative | CHIJ pie (unlabelled sectors), CH bar (unlabelled bars) |
| T-R4 | The drawn figure is **provably consistent** with its data (same standard as existing diagrams: `check_*_consistency`) | project invariant, ADR-0012 |
| T-R5 | Charts and solids are **reusable by the generator**, not sourced-only (statistics, volume/capacity are P5-P6 topics) | PARAMETERIZATION.md |
| T-R6 | Decorative pictures stay `raster` / omitted; no scope creep into illustration | 9 context pictures, ~all decorative or stem-redundant |
| T-R7 | One typeface (Inter) in every chart/solid label; no new fonts | CLAUDE.md, EXA-94 |

## What the evidence says (convergent across all three papers)

The three agents, working independently, arrived at the same families:

| Family | Questions | Verdict |
|---|---:|---|
| **chart** (`kind: bar \| line \| pie`) | 11 | **New type. Do first.** One renderer, strong invariants, directly generatable. |
| **solid** (`kind: cuboid \| container \| cube_stack`) | 9 (but only ~5 truly need a drawing; some are stem-sufficient) | **New type, staged.** Cuboid + fill first; unit-cube views last. |
| grid-based draw-on / nets | ~9 | **Already covered** by 1.6.0 `geometry_figure` grid+polygons and `construction` answers. Verify, then fill small gaps; no new type. |
| net | 3 (1/paper) | Express as polygons on a square grid. **No new type.** |
| number line | 1 | Tiny new type (or `geometry_figure` axis). Cheap win. |
| scale picture (graduated vessel/beaker) | 3 | Low coverage; defer. Model only the graduated vessel if it recurs. |
| pattern / tiling | 3 | `raster` + structured counts in stem/table. |
| decorative / context | ~9 | `raster` or omit. |
| multi-panel wrapper | ~2 | Option-figures already work (verified); only a `panels` wrapper is missing. |

## Shape

### S1 — `chart` diagram (one type, `kind` discriminant)

Union of fields across the 11 figures, trimmed to what a renderer and a checker
actually need:

- `kind`: `bar | line | pie`; `title?`
- axes (bar/line): `x{title, categories[] | numeric{min,max,label_step}}`,
  `y{title, min, max, label_step, minor_step?, unit}`; `gridlines`
- `series[{name, values[] | points[{x,y}], style?}]`; bar: `orientation`,
  grouped bars; line: `markers`, optional dotted `guide_lines[]`
- pie: `sectors[{label, value, show_value, marker?: right_angle}]`, `start_angle`
- **`hidden`**: per-value `visible: false`. The renderer draws a blank; the value
  stays in the object and is only used by the answer and the checker.
- no fill-pattern or colour fields: a fixed per-series style palette (stipple vs
  plain is cosmetic).

Consistency invariants (the correctness proof for the diagram):
pie shares sum to 100% (angles to 360°), and for a right-angle marker the sector
equals 25%; axis range covers every data value; `label_step` divides the axis
span; categories and series lengths agree; no hidden value appears in the SVG
string or `alt`.

### S2 — `solid` diagram, staged

- **S2a** `cuboid` + `container`: `dims{l,w,h,unit}`, labelled edges,
  `open_top`, `fill{height | fraction}`, dashed hidden edges. A **fixed oblique
  projection** (no perspective). Invariants: fill ≤ height; labelled dims equal
  params; volume claims derive from dims.
- **S2b** `cube_stack`: `heightmap[{x,y,h}]`, `projection: isometric`, views
  *derived* from the heightmap (front/side/top), never authored. This resolves
  the "hidden cubes are ambiguous" risk by construction. Deferred behind S2a
  because "could be / cannot be" questions are hard to write invariants for.
- Multi-state figures (before/after water level) are panels, not a new solid kind.

### S3 — `number_line` (small) and the grid/net/overlay delta

`number_line{start,end,divisions,tick_labels,marked_points[{label,at}]}`; fraction
and decimal tick labels. Grid, net and draw-on tasks: audit what 1.6.0 cannot do
first (per-part answer overlay styling, key-vs-student render) and add only that.

### S4 — option-figures and panels (only if the audit says E2 left a hole)

Charts and solids as MCQ *option* figures (pie-chart options are 2 questions);
a `panels[{title, figure}]` wrapper with between-panel arrows.

### S5 — `expression` answers (G7, π and algebra)

4-5 questions, all three papers, and algebra also appears in table cells. Not a
figure, but it is the next-largest non-G4 blocker and the card names it.

## Slices (proposed; each ends in a demo)

| Slice | Title | Ends in (demo) | Questions unlocked |
|---|---|---|---:|
| **T1** | `chart` (bar/line/pie): schema, renderer, consistency check, fixtures, web preview | Import one pie, one bar, one line question; unknown values blank in student view, shown in key; invariant sweep green | ~11 |
| **T2** | `solid` cuboid + container + fill | Import a tank/container question; render student + key; volume claims verified | ~4-5 |
| **T3** | `number_line` (+ confirm key distinguishes answer from givens on grid/net) | A number-line question and a net question render; key shows the completed net | ~2-3 |
| **T4** | `panels` wrapper (only if a figure needs it; option-figures already work) | A two-panel before/after figure | ~2 |
| **T5** | `expression` answers (G7) | A π-answer and an algebra-answer question validate and render | 4-5 |
| **T6** | `cube_stack` with derived views | Heightmap → three views; "which view" question | ~2 |
| **T7** | *Generation*: `blueprints` for chart-reading and cuboid-volume/fill | `mathgen generate` yields chart/volume questions with answer key + invariant test | new content |

T1 first: most questions, cleanest invariants, and the only family all three
papers agree is #1. T7 is what makes T1/T2 pay back the engine's actual promise
(deterministic, provably correct), so it should not be dropped, only sequenced
after the sourced path works.

Each slice carries: schema bump (additive, `1.7.0` onward), `diagram.py`
consistency check, deterministic SVG renderer (Inter only), server-side rendering
via the fragment endpoint (no TS mirror; see Verifications §3), a schema-gated fixture
(paraphrased, with `source`/`license`), and an invariant test.

## Verifications (done 2026-10-10)

1. **MCQ options already take any `diagram`.** `answer_choice.options[].diagram`
   is `oneOf null | $ref diagram` (the whole union), and
   `psle_2023_mcq.json` exercises it with `geometry_figure` options. So chart and
   solid option-figures come **for free** the moment those types join the union.
   One agent's claim that `answer_choice` lacked this was wrong. **T4 shrinks to
   the optional `panels` wrapper only** and is demoted until a figure needs it.
2. **`construction` answers are `geometry_figure`-only and key-only.** The key
   draws the completed figure (givens + the answer) in one diagram; there is no
   student-overlay concept and none is needed for the grid/net/draw-on cases. It
   cannot hold a chart or solid, which is fine (no "draw a chart" questions were
   found). **T3 is just `number_line` plus checking the answer is visually
   distinct from the givens in the key**; no overlay mechanism to build.
3. **The web renderer is a hand-written TS mirror with no parity test.**
   `web/src/lib/barModel.ts` (`renderDiagram`) re-implements every Python
   renderer, and returns `''` for an unknown type, so a new diagram type with no
   TS mirror **renders silently blank in the editor and tray** while the PDF is
   fine. Python and TS are never compared against each other.

   **Decision for tier 2: do not write TS mirrors for new types.** Render them
   server-side through the existing `POST /render/question` fragment endpoint
   (`routes_render.py`) or an equivalent `/render/diagram`, so one renderer is the
   truth (Inter fonts and all). `renderDiagram` should, for an unmirrored type,
   fall back to the server fragment instead of `''`. This removes a whole class of
   drift for charts and solids, at the cost of a fetch per figure (cache by spec
   hash). Existing types keep their mirrors; revisiting them is out of scope.

## Risks

- **Pie angles in sourced papers are visual estimates** (low-confidence
  transcriptions). Sourced charts must take their numbers from the key/stem, with
  the reviewer confirming, consistent with G19.
- **Protractor-style "measure the drawing" questions** need true-to-scale
  drawing, which conflicts with schematic scaling. Out of scope; they stay
  `raster` (the answer reads the picture, which our diagram invariant forbids).
- **Hidden values leaking** into SVG/alt is the one correctness bug that would
  quietly give the answer away; give it its own test.
- **Solid scope creep** (perspective, tapered containers, taps). Fixed oblique/
  isometric only; everything else raster.
- Counts are per paper and one-year; fit numbers are agent judgements, not
  validated objects (see SCHEMA-FIT caveats).

## Decisions

- **Order:** T1 charts first. **T7 generation stays in this initiative**,
  sequenced after the sourced path works.
- **Versioning:** one additive schema bump per slice (1.7.0 for T1, 1.8.0 for T2,
  ...), so each slice is independently shippable and revertable.
- **Rendering:** server-side only for new types (above).
