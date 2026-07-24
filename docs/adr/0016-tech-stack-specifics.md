# ADR-0016: Tech-stack specifics (Python, uv workspace, schema representation, id, skill codes)

- Status: Accepted
- Deciders: project owner
- Related: ADR-0006 (stack & layout), ADR-0014 (schema authority), ADR-0001
  (ephemeral state), Q-K4, Q-K5, Q-M1; surfaced while planning slice V1
  (`docs/planning/mvp/V1-plan.md`).

## Context

Slice V1 (the first end-to-end Ratio path) forced several implementation choices
that ADR-0006 and ADR-0014 left open (the deferred Q-K4/K5 items, plus the
concrete `id` and `skill_codes` conventions). Recording them here so they live in
the decision register, not only in the slice plan.

## Decision

1. **Python 3.12** across `engine/` and `api/`.
2. **uv workspace.** The root `pyproject.toml` declares `[tool.uv.workspace]`
   members `engine` and `api`, sharing one lockfile and venv. `api` takes `engine`
   as a **path dependency** (`[tool.uv.sources] exam-engine = { workspace = true }`),
   installed editable. The API and the later `mathgen` CLI both `import exam_engine`
   — **one implementation** (R7.6). Rejected alternatives: single flat package
   (blurs the engine/API boundary), published package (publish + version overhead,
   over-engineered for a single-user MVP), manual `pip -e`/PYTHONPATH (loses the
   lockfile).
3. **Schema representation — one source of truth.** The **canonical question
   object** is a plain `dict` gated by **`jsonschema`** against
   `schemas/canonical-question.schema.json` (the authoritative contract, ADR-0014).
   **Pydantic** is used **only for API request/response envelopes**
   (`GenerateRequest`, `GenerateResponse`), which wrap `list[dict]` canonical
   objects. Pydantic does **not** own or regenerate the canonical schema (its
   `if/then` conditionals, `oneOf` unions, `additionalProperties:false`, and `unit`
   enum would drift from a Pydantic-generated schema). `engine/` therefore has **no
   FastAPI/Pydantic dependency**. Typed engine-side models are deferred; if added
   they must ship a contract test asserting every instance serializes to
   jsonschema-valid output, with jsonschema still the authority.
4. **`created_at` stamped at the API boundary.** The engine emits
   `provenance.created_at = null` so `generate(blueprint_code, seed)` is a pure,
   reproducible function; `api/` sets the ISO-8601 timestamp as the object crosses
   HTTP.
5. **`id` scheme.** Generated objects: `id = f"{blueprint_code}:{seed}"`
   (deterministic — no clock/random — and its own in-session dedup key). Edits
   (V3): sibling-swap ops re-sample and get a fresh `{code}:{seed}` with
   `provenance.parent_id` set; same-sample transforms (decimals, toggle-diagram)
   get `f"{parent_id}+{op}"`; `version` bumps on every edit. Durable global
   uniqueness (content hash or run-scoped UUID) is reserved for a future saved
   library — state is ephemeral in v1 (ADR-0001).
6. **Placeholder `skill_codes`.** `syllabus.skill_codes` is a free `array of
   string` (not an enum), so provisional `TOPIC.SUBSKILL.VARIANT` codes validate.
   They live in a per-topic registry (`content/syllabus/*.yaml`) and are **carried,
   not queried** in v1 (no selection/filtering branches on their values), so
   remapping to MOE outcomes (Q-M1) is a mechanical find/replace with no data
   migration.

## Consequences

- Clean engine/API layer boundary with one shared implementation; engine is
  testable and importable without HTTP/UI deps.
- Exactly one authority for the canonical object (jsonschema), eliminating
  schema-drift risk; Pydantic still gives the API request validation + OpenAPI.
- Deterministic ids make dedup and seeded tests trivial; the edit-lineage and
  content-hash paths are pre-considered so V3 / a future library need no rework.
- Placeholder skill codes unblock blueprint authoring before the MOE syllabus doc
  arrives.

## Open

- Typed engine-side models (Pydantic/dataclass mirrors) — revisit if dict-building
  ergonomics become painful; would add a serialize-validates contract test.
- Demo deployment target (Q-K5 remainder) still deferred.
