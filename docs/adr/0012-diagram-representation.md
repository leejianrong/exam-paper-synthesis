# ADR-0012: Diagram representation (discriminated union)

- Status: Accepted
- Deciders: project owner
- Related: Q-S2, Q-F2, Q-F5, ADR-0007 (policy), ADR-0004 (schema)

## Context

Diagrams must be rock-solid and validatable. Different families share almost no
fields (a bar model vs a rectangle figure), and sourced/scanned diagrams have no
math spec at all — only an image. We need a representation that validates each
kind strictly.

## Decision

The `diagram` field is a **discriminated union keyed by `type`**. Each variant has
its own closed schema (`additionalProperties: false`, `type` pinned via `const`):

- `bar_model` — bars (label, units) + annotations (braces/labels).
- `composite_geometry` — shapes (rectangles etc. with coords) + shaded region ops.
- `area_perimeter` — a shape with labelled dimensions.
- `shaded_fraction` — a figure partitioned into equal parts with some shaded.
- `raster` — `{ asset_ref, alt_text }` for sourced/scanned diagrams (no math spec).

Generated questions emit a typed spec; sourced questions use `raster`. Both live
in the same `diagram` field under the same schema. Rendering switches on `type`.
The formal spec will be JSON Schema (`oneOf` + `discriminator: {propertyName: type}`).

## Consequences

- Precise validation: a variant missing required fields, or with stray/typo'd
  fields, fails on load.
- Extensible: new families (e.g. `cumulative_frequency`, `number_line`) add one
  `$def` + one `oneOf` entry without touching existing variants.
- Clean renderer/validator dispatch on `type`.

## Open

- Exact per-family field sets (esp. bar-model annotations/scale — Q-F4) to be
  fixed when the formal schema is written.
- SVG/charting library choice (Q-F5) is an implementation detail, not schema.
- What "diagram matches the question" validation asserts (Q-F3).
