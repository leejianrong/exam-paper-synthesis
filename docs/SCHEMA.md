# SCHEMA — the canonical question object

The canonical question object is the **single source of truth** for a question.
Every rendered form (worksheet, answer key, diagram) is a *view* of it. The formal
spec is `schemas/canonical-question.schema.json` (JSON Schema Draft 2020-12); this
document explains it with examples.

Related decisions: ADR-0004 (object), ADR-0012 (diagram union), ADR-0013 (multi-part
+ answer union), ADR-0014 (versioning/validation/semantics).

## Guarantees

- **Versioned** — every object carries `schema_version` (semver).
- **Validated on load** — generated *and* sourced objects are JSON-Schema-validated
  when they enter the system; invalid objects are rejected with path-pointed errors.
- **Closed** — objects use `additionalProperties: false`; stray/typo'd fields fail.
- **Interchange-grade** — the *same* schema accepts engine-generated questions and
  externally-prepared ("sourced") questions.

## Shape (top level)

| Field | Notes |
|---|---|
| `schema_version` | semver, e.g. `"1.3.0"` |
| `id` | unique instance id |
| `source_type` | `generated` \| `sourced` (drives conditional requirements) |
| `blueprint_code` | required for `generated`; `null` for `sourced` |
| `seed` | reproducibility (generated) |
| `syllabus` | `{ level, strand, topic, subtopic?, skill_codes[] }` |
| `cognitive` | `{ difficulty, cognitive_level, heuristics[]?, representations[]? }` |
| `parameters` | sampled inputs (generated); validated against the blueprint's own parameter schema |
| `question` | `{ stem?, parts[], total_marks }` |
| `source` / `license` | required for `sourced` |
| `validation` | `{ status, checks{} }` |
| `provenance` | `{ created_by, llm_used, created_at?, parent_id?, version }` |

Conditional rules (JSON Schema `if/then`): `generated` ⇒ `blueprint_code` +
`parameters` required; `sourced` ⇒ `source` + `license` required.

## Multi-part

One object = one whole question. Each entry in `question.parts[]` has its own
`text`, `answer`, `marking_scheme`, `solution_steps`, and optional `diagram`.
`question.total_marks` aggregates the parts. Single-part questions are a `parts`
array of length 1.

## Discriminated unions

`answer` and `diagram` are **tagged unions** keyed by `type` — read `type`, apply
that variant's strict sub-schema.

- **answer.type** ∈ `integer | decimal | fraction | ratio | quantity | set | text`
- **diagram.type** ∈ `bar_model | bar_model_before_after | geometry_figure | shaded_fraction | raster`
  (`raster` = an image reference, used by sourced/scanned diagrams).
  - `bar_model` may carry an optional `total_bracket: { label }` (schema **1.1.0**) —
    a vertical curly brace across all bars labelling the total.
  - `bar_model_before_after` (schema **1.2.0**) is the before-after ratio aid: two
    `stages` (`Before`/`After`), each with one bar per person in a shared unit scale,
    plus `annotations` (labelled notes, e.g. the value of one unit and the amount
    spent) and an optional `total_bracket` labelling the invariant person's amount.
  - `geometry_figure` (schema **1.3.0**) is a general 2D figure — see the dedicated
    section below.

> **Removed in 1.3.0:** the never-built `composite_geometry` and `area_perimeter`
> diagram types were removed from the union (superseded by `geometry_figure`). No
> shipped or golden object used them, so no real object is affected.

Units on numeric/`quantity` answers come from a **controlled vocabulary** (see the
`unit` enum in the schema), not free text. Schema **1.3.0** adds the speed units
`km/h`, `m/s`, and `m/min` (for the Speed ladder).

## The `geometry_figure` diagram (schema 1.3.0)

`geometry_figure` is one general 2D figure type covering both PSLE geometry
families — angle figures (unknown angles) and area/perimeter figures (including
circles). It replaces the two sketched-but-never-built axis-aligned types
(`composite_geometry`, `area_perimeter`). A figure is a set of named `points` plus
the marks drawn on them; every labelled value is exact (it comes from the solved
parameters, never from measuring the drawing), so a deterministic figure built from
correct values is always consistent.

| Field | Req? | Notes |
|---|---|---|
| `type` | yes | const `"geometry_figure"` |
| `unit` | yes | controlled-vocabulary unit for length/area labels; angles are unitless degrees |
| `points` | yes | `≥2` named vertices `{ id, x, y }` in figure coordinates |
| `segments` | no | straight edges `{ from, to, label?, ticks? }` (`ticks` = equal-side marks) |
| `arcs` | no | circular arcs `{ center, radius>0, start_deg, end_deg, label? }` (whole/semi/quarter circles) |
| `angles` | no | angle marks `{ at, from, to, value_deg?, unknown?, right? }`; exactly one may set `unknown: true` (the value to solve) |
| `shaded` | no | region(s) to fill, each `{ boundary: [ids…], arcs? }` |
| `labels` | no | free text labels `{ at, text }` anchored at a named point |

## Marking

Each `marking_scheme` entry has a `type` — **M** (method) / **A** (accuracy) /
**B** (independent). Worksheets render marks-per-part as `[n]`; the M/A/B breakdown
shows only in the detailed answer-key mode (ADR-0005).

---

## Example 1 — generated, multi-part, with a bar-model aid

```json
{
  "schema_version": "1.3.0",
  "id": "qi_01H8XR",
  "source_type": "generated",
  "blueprint_code": "P6_RATIO_BEFORE_AFTER_001",
  "seed": 184922,
  "syllabus": {
    "level": "P6", "strand": "Number and Algebra",
    "topic": "Ratio", "subtopic": "Before-after ratio",
    "skill_codes": ["P6_STD_NA_RATIO_007"]
  },
  "cognitive": {
    "difficulty": "hard", "cognitive_level": "non_routine_heuristic",
    "heuristics": ["before_after", "invariance"],
    "representations": ["word_problem", "bar_model"]
  },
  "parameters": { "old_ratio": [3, 5], "change_amount": 24, "invariant": "B" },
  "question": {
    "stem": "Ali and Bala had marbles in the ratio 3 : 5.",
    "parts": [
      {
        "label": "a",
        "text": "After Ali received 24 more marbles, the ratio became 7 : 10. How many marbles did Ali have at first?",
        "marks": 3,
        "answer": { "type": "integer", "value": 144, "unit": "marbles" },
        "marking_scheme": [
          { "mark": 1, "type": "M", "description": "Equalises Bala's (invariant) units." },
          { "mark": 1, "type": "M", "description": "Finds the value of one unit (24)." },
          { "mark": 1, "type": "A", "description": "Correct answer 144." }
        ],
        "solution_steps": [
          { "text": "Bala is unchanged; make Bala's units equal: 6 : 10 → 7 : 10.", "expr": null },
          { "text": "Increase in Ali = 1 unit = 24.", "expr": "24/1" },
          { "text": "Ali at first = 6 units = 6 × 24 = 144.", "expr": "6*24" }
        ],
        "diagram": {
          "type": "bar_model",
          "bars": [ { "label": "Ali", "units": 6 }, { "label": "Bala", "units": 10 } ],
          "annotations": [ { "from_unit": 6, "to_unit": 7, "label": "24" } ],
          "total_bracket": { "label": "Total = 384" }
        }
      }
    ],
    "total_marks": 3
  },
  "validation": {
    "status": "pass",
    "checks": { "answer_verified": true, "unique": true, "diagram_consistent": true, "within_level": true }
  },
  "provenance": { "created_by": "engine", "llm_used": false, "created_at": null, "parent_id": null, "version": 1 }
}
```

## Example 2 — generated geometry (mandatory `geometry_figure`)

An unknown-angle figure: two angles of a triangle are given, the third is the
answer. The `angles[]` entry with `"unknown": true` equals the solved answer, and
every given `value_deg` equals its sampled parameter — that is what the diagram
consistency check asserts.

```json
{
  "schema_version": "1.3.0",
  "id": "qi_01H8XS",
  "source_type": "generated",
  "blueprint_code": "geometry_angle_easy",
  "seed": 5521,
  "syllabus": { "level": "P5", "strand": "Geometry and Measurement", "topic": "Geometry (Angles)", "subtopic": null, "skill_codes": ["P5_STD_GM_ANGLE_002"] },
  "cognitive": { "difficulty": "easy", "cognitive_level": "routine_procedural", "representations": ["diagram"] },
  "parameters": { "angle_a": 50, "angle_b": 60 },
  "question": {
    "parts": [
      {
        "label": "a",
        "text": "In the triangle below, find the unknown angle x.",
        "marks": 2,
        "answer": { "type": "integer", "value": 70, "unit": "degrees" },
        "marking_scheme": [
          { "mark": 1, "type": "M", "description": "Uses angle sum of a triangle = 180°." },
          { "mark": 1, "type": "A", "description": "Correct answer 70°." }
        ],
        "solution_steps": [ { "text": "x = 180° − 50° − 60° = 70°.", "expr": "180-50-60" } ],
        "diagram": {
          "type": "geometry_figure",
          "unit": "degrees",
          "points": [
            { "id": "A", "x": 0, "y": 0 },
            { "id": "B", "x": 8, "y": 0 },
            { "id": "C", "x": 3, "y": 5 }
          ],
          "segments": [
            { "from": "A", "to": "B" },
            { "from": "B", "to": "C" },
            { "from": "C", "to": "A" }
          ],
          "angles": [
            { "at": "A", "from": "B", "to": "C", "value_deg": 50 },
            { "at": "B", "from": "C", "to": "A", "value_deg": 60 },
            { "at": "C", "from": "A", "to": "B", "unknown": true }
          ],
          "labels": [ { "at": "C", "text": "x" } ]
        }
      }
    ],
    "total_marks": 2
  },
  "validation": { "status": "pass", "checks": { "answer_verified": true, "diagram_consistent": true } },
  "provenance": { "created_by": "engine", "llm_used": false, "created_at": null, "parent_id": null, "version": 1 }
}
```

## Example 3 — sourced (externally prepared), raster diagram

```json
{
  "schema_version": "1.3.0",
  "id": "qi_src_00042",
  "source_type": "sourced",
  "blueprint_code": null,
  "seed": null,
  "syllabus": { "level": "P6", "strand": "Number and Algebra", "topic": "Percentage", "subtopic": null, "skill_codes": [] },
  "cognitive": { "difficulty": "medium", "cognitive_level": "complex_familiar" },
  "parameters": null,
  "question": {
    "parts": [
      {
        "label": "a",
        "text": "A shopkeeper gave a 20% discount on a bag marked $75. How much did a customer pay?",
        "marks": 2,
        "answer": { "type": "quantity", "value": 60, "unit": "$" },
        "marking_scheme": [
          { "mark": 1, "type": "M", "description": "Computes discount or 80% of 75." },
          { "mark": 1, "type": "A", "description": "Correct answer $60." }
        ],
        "solution_steps": [ { "text": "Pay 80% × $75 = $60.", "expr": "0.8*75" } ],
        "diagram": { "type": "raster", "asset_ref": "assets/sourced/q42.png", "alt_text": "Price tag showing $75." }
      }
    ],
    "total_marks": 2
  },
  "source": { "origin": "Sample Assessment Book", "year": 2023, "paper": "Practice 4", "reference": "Q12" },
  "license": "internal-use-only",
  "validation": { "status": "unverified", "checks": { "human_reviewed": true } },
  "provenance": { "created_by": "ingested", "llm_used": false, "created_at": null, "parent_id": null, "version": 1 }
}
```
