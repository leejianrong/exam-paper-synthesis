---
shaping: true
---

# Diagram & figure roadmap (forward-looking notes)

> **Status: notes, not scope.** This does **not** change the MVP (P5–P6 Standard:
> Ratio, Fractions, Percentage, Area/Geometry, Speed). It records diagram/figure
> types the full MOE P1–P6 syllabus will eventually demand, so the **schema**
> (diagram discriminated union, ADR-0012) and the **engine renderer** stay
> *expressive enough* to grow into them without a redesign. Grounded in
> `docs/syllabus/` (2021 syllabus, read in full).

## Where we are

Shipped diagram types (`diagram.type`): `bar_model`, `composite_geometry`,
`area_perimeter`, `shaded_fraction`, `raster`. These cover Number-&-Algebra aids
and 2D rectangle/square area well. The union is **designed to be extended**
(ADR-0012), which is the whole point of this note.

## The critical principle: "not drawn to scale" (anti-measurement)

Real PSLE geometry items carry the standard rubric **"All diagrams are not drawn
to scale."** This is deliberate and load-bearing: the figure must look plausible
and be **structurally** correct, but must **not** be measurement-accurate — a
student must **not** be able to get the answer by laying a protractor on an angle
or a ruler on a length. They have to *calculate* it from the given values and
geometric properties, as the question intends.

This splits our diagram families into two rendering contracts:

| Contract | Families | Consistency rule (extends R3.3) |
|---|---|---|
| **To-scale** | `bar_model`, `area_perimeter`, `composite_geometry`, `shaded_fraction` | Every drawn dimension/label **equals** the corresponding parameter or solved value (current check). Bar widths ∝ units is *desirable* here. |
| **Schematic / not-to-scale** | angles & geometry-properties figures (future) | Labelled **givens** must match; the **unknown must be recoverable only from givens + properties**. The renderer must **not** draw the unknown at its true measure — angles/lengths are approximate on purpose, so measuring fails. |

> Implication: the current diagram-consistency check (assert *everything* drawn
> equals a solved value) is correct for to-scale families but must be **inverted**
> for schematic families — there we assert the givens match **and** that the
> figure is intentionally not-to-scale (e.g. the drawn unknown angle ≠ its answer).
> Worth an ADR when we build the first geometry-properties blueprint.

## The figures you mean (angles & shape properties)

Yes — these are the composite "find the unknown angle / length" figures:
triangles, circles, and quadrilaterals (parallelogram, rhombus, trapezium)
**intersecting, adjacent, or encapsulated within each other**, with given values
labelled and one or more unknowns to solve. They require a small **annotation
vocabulary** drawn *on* the shapes and lines:

| Marker | Meaning | Typical render |
|---|---|---|
| **Parallel marks** | Two+ lines are parallel | Matching arrowheads / chevrons (›, ››) on each line of a parallel set |
| **Equal-length ticks** | Sides of equal length (isosceles / equilateral) | Small tick strokes across a side; matching tick-counts (`/`, `//`) mark equal groups |
| **Angle arc + label** | A named/known/unknown angle | Small arc at the vertex with a number (`52°`) or letter (`∠x`) |
| **Right-angle square** | A 90° angle | Small square at the intersection (not an arc) |
| **Vertex / point labels** | Name points | `A`, `B`, `C` at vertices; `∠ABC` naming |

These map directly onto syllabus content: P3 angles & right angles; P4 angle
measure, rectangle/square properties, line symmetry, nets; **P5** angles on a
line / at a point / vertically opposite, triangle properties + angle sum,
parallelogram/rhombus/trapezium; **P6** unknown angles in composite figures of
square/rectangle/triangle/parallelogram/rhombus/trapezium.

## Future diagram-type backlog (with syllabus anchors)

Not built; listed so the union and renderer can absorb them later.

| Prospective `type` | Covers | Syllabus (level) | Rendering notes |
|---|---|---|---|
| `geometry_figure` | Angles & shape-property figures above | P3–P6 Geometry | **Schematic / not-to-scale**; needs the marker vocabulary above (points, segments, parallel-groups, tick-groups, angle arcs, right-angle squares) |
| `area_perimeter` **(extend)** | Triangles; circle / semicircle / quarter-circle; composites of these | P5 triangle area; **P6** circle area & circumference, composite figures | To-scale; add triangle + circular primitives to the existing type |
| `solid_3d` / `isometric` | Cube / cuboid, liquid in a rectangular tank | P5–P6 Volume | Isometric grid drawing; labelled edges |
| `net` | 2D nets of cube/cuboid/prism/pyramid | P4 Nets | Unfolded-faces layout |
| `clock` | Analog clock faces, elapsed time | P1–P3 Time | Clock face + hour/minute hands |
| `symmetry` | Symmetric figures + line(s) of symmetry on a grid | P4 Line Symmetry | Grid + shape + dashed symmetry axis |
| `pictograph` | Picture graphs (with scale) | P1–P2 Statistics | Repeated icons, scale key |
| `bar_chart` | Bar graphs | P3 Statistics | Categorical bars, axis scale |
| `line_graph` | Line graphs | P4 Statistics | Points + connecting lines |
| `pie_chart` | Pie charts | P4 & P6 Statistics | Sectors by proportion |
| `data_table` | Tables for data interpretation | P4–P6 Statistics | Row/column grid |

For statistics families note the same to-scale caveat *inverts* again: there the
chart often **is** the data and *must* be accurate (a pie sector must be its true
proportion), unlike the anti-measurement geometry figures.

## Schema & engine implications (when we act on this)

- **Schema** (`schemas/canonical-question.schema.json`): each new family is an
  additive member of the `diagram` `oneOf`, keyed by `type`, gated by version
  bumps (we already do minor bumps for additive changes — see the `bar_model`
  `total_bracket` addition in 1.1.0). The `unit` enum already anticipates some of
  this (`cm^3`, `m^3`, `degrees` are present) — the *figure* side is what's missing.
- **Engine renderer** (`engine/exam_engine/diagram.py`): grows a builder + SVG
  renderer per family, and the **two rendering contracts** above (to-scale vs
  schematic-not-to-scale). Geometry primitives (points, segments, arcs, ticks,
  parallel/right-angle marks) are reusable across `geometry_figure`, `symmetry`,
  and extended `area_perimeter`.
- **Consistency check**: bifurcates as described — value-equality for to-scale
  families; givens-match-plus-intentionally-not-to-scale for schematic families.

None of this is scheduled; it is the map for when we push past the P5–P6-Standard
MVP line.
