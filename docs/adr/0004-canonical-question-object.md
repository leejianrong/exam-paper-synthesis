# ADR-0004: Canonical question object schema

- Status: Proposed
- Deciders: project owner
- Related: Q-C1, Q-C2, Q-C3

## Context

The canonical question object is the single source of truth; all rendered forms
are views of it. We need an agreed field set and an edit/versioning model.

## Decision (proposed)

Fields (see `CONTEXT.md` for the worked example):

- `id`, `blueprint_code`, `seed`
- `syllabus`: level, strand, topic, subtopic, skill_codes
- `cognitive`: difficulty, cognitive_level, heuristics[], marks
- `parameters`: the sampled inputs
- `question`: text, representations[]
- `answer`: type, value, units
- `marking_scheme`: [{mark, type (M/A/B), description}]
- `solution_steps`: [{text, expr?}]  (`expr` optional, machine-checkable)
- `diagram`: spec | null
- `validation`: status + checks{}
- `provenance`: created_by, llm_used, created_at, parent_id, version
- `schema_version`: semver of the schema this object conforms to (validated on load)

**Multi-part questions:** one canonical object represents a whole question. It has
an optional shared `stem`, and a `parts[]` array; **each part** carries its own
`text`, `answer`, `marking_scheme`, `solution_steps`, and optional `diagram`. The
top level aggregates `total_marks`. Single-part questions are just one part (or a
degenerate parts array of length 1). See ADR-0013.

**Answer typing:** `answer` is itself a **discriminated union keyed by `type`**
(integer, fraction, decimal, ratio, quantity-with-units, set/list, text) — closed
set pending Q-S3. See ADR-0013.

**Diagram:** the `diagram` field is a discriminated union keyed by `type`
(per-family specs + a `raster` variant for sourced diagrams). See ADR-0012.

Edit model: an edit operation produces a **new** canonical object linked to its
source via `provenance.parent_id` (lineage tracked); objects are **not** mutated
in place. Objects are JSON-serializable and JSON-Schema-validated on load.

## Consequences

- Stable contract between engine, API, renderers, and (later) the LLM layer.
- Edit lineage enables "before/after" views and undo without losing history.
- `solution_steps[].expr` lets the verifier re-substitute and check steps.

## Sourced (ingested) questions

The schema must also represent questions **ingested from external material**
(ADR-0011), not just blueprint-generated ones. For sourced questions:
`blueprint_code = null`, `parameters = null`; `diagram` may hold a **raster asset
reference** rather than a spec; `provenance.created_by = "ingested"` with human
verification (not solver-based). Add `source` (citation) and `license` fields.

## Open

- Persistence scope (in-memory vs stored library) depends on Q-A3 (ephemeral for
  the user-facing app; the ingested bank persists, ADR-0011).
- M/A/B granularity for primary marking depends on Q-E1b.
- Exact `source`/`license` shape for sourced questions depends on section N.
