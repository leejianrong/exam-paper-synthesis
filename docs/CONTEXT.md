# CONTEXT — shared language & decisions

Living glossary and decision register for the Exam Paper Synthesis project,
built during grilling (see `docs/background/QUESTIONS.md`). Terms here are the canonical
vocabulary; decisions link to `docs/adr/*.md`.

## Glossary

- **Blueprint** — a *parametric question generator*, not a question. Concretely a
  **YAML file** (metadata, parameter schema, wording/solution templates,
  constraints) plus a **named Python solver module** that owns the math. Produces
  many **question instances**. See ADR-0003.
- **Question instance** — one concrete generated question, represented as the
  **canonical question object**. See ADR-0004.
- **Canonical question object** — the single source of truth for a question:
  syllabus tags, cognitive metadata, parameters, question text, answer, marking
  scheme, worked solution steps, optional diagram spec, validation report,
  provenance. The rendered worksheet/answer-key/diagram are *views* of this.
- **Solver** — the Python plugin a blueprint references. Interface:
  `sample(schema, rng) -> params`, `solve(params) -> {answer, intermediates}`,
  `validate(params, solution) -> report`, optional `diagram(params, solution) -> spec`.
- **Golden fixture** — a hand-written, human-verified `params → expected answer/
  marks` record per blueprint; the trust anchor for correctness. Never
  LLM-verified. Lives in `tests/golden/`.
- **Parameters** — the sampled numeric/enum inputs that make one instance unique.
- **Difficulty** — enum `easy | medium | hard`.
- **Cognitive level** — enum `routine_procedural | complex_familiar |
  non_routine_heuristic`. Additional axes (heuristics, representation) are carried
  as tags. See ADR-0002.
- **Marking scheme** — ordered list of awardable marks with type (M/A/B) and
  description. Distinct from the **final answer** and the **worked solution steps**
  (all three are produced). See ADR-0005.
- **Diagram spec** — structured JSON describing a figure, produced by the
  blueprint's `diagram()` from solved values, rendered deterministically to SVG.
- **Mandatory vs aid diagram** — geometric-figure families require a diagram (the
  figure *is* the question); ratio/fraction/percentage get an optional bar-model
  *aid* (toggleable; also shown in the answer key). See ADR-0007.
- **Edit operation** — a fixed, named transform of a question (regenerate, make
  harder/easier, change to decimals, add diagram) that yields a **new** canonical
  object linked to its parent via `provenance.parent_id`. See ADR-0004, ADR-0006.
- **Engine / API / Web / CLI** — the Python generation package / the thin FastAPI
  HTTP layer over it / the Svelte + Vite SPA / the **`mathgen`** headless CLI. See
  ADR-0006.
- **`mathgen` (CLI)** — the V7 headless command-line tool (`generate` / `edit` /
  `export`) that drives the pure engine directly with no web or API server. Its own
  `cli/` workspace package, depending only on `exam-engine` (+ Playwright for the
  PDF step) — never FastAPI — which is the concrete proof that the engine is
  UI/HTTP-agnostic.
- **Generated vs sourced question** — a **generated** question comes from a
  blueprint + solver; a **sourced** question is **ingested** from external
  material and has no blueprint/parameters/solver (it carries a `source` +
  `license` and `created_by:"ingested"`, and may carry a `raster` image figure).
  Both are canonical objects validated by the same schema; V7 exercises a sourced
  object end-to-end (load → mixed worksheet → render).
- **M / A / B marks** — mark-scheme mark types (Cambridge/SEAB): **M** = method
  (correct approach, even if the number is wrong); **A** = accuracy (correct
  result, usually dependent on the method); **B** = independent (a standalone
  correct answer/statement needing no working). O-Level surfaces M/A/B; primary/
  PSLE typically surfaces only marks-per-part `[n]`. See ADR-0005, Q-E1b.
- **Difficulty ladder** — per topic, a 3-rung set of blueprints (easy/medium/hard)
  so "make harder/easier" swaps to a sibling one rung up/down. v1 = 3×5 = 15
  blueprints. See ADR-0009, ADR-0015, `docs/DIFFICULTY.md`.
- **Difficulty lever** — a named dimension along which a question is made harder or
  easier (reasoning depth, inverse/direction, hidden structure, number type, …);
  tagged per blueprint in `cognitive.difficulty_levers[]`. See ADR-0015.
- **Difficulty (two levels)** — *composition* (more/heavier interdependent parts)
  and *intrinsic* (a single part made harder via levers). See `docs/DIFFICULTY.md`.
- **Review gate** — the required human step where questions are approved /
  regenerated / discarded before export. See ADR-0010.
- **Question bank** — the persistent internal store of canonical objects produced
  by the ingestion pipeline. See ADR-0011.
- **Ingestion pipeline** — internal batch tool: PDFs → OCR/parse → segment →
  extract → human-verify → persist as canonical objects. **Out of scope for this
  project** (done externally); only the schema must accept its output. See ADR-0011.
- **Discriminated union (tagged union)** — a field that can be one of several
  shapes, with a `type` tag selecting which closed sub-schema applies. Used for
  `diagram` (ADR-0012) and `answer` (ADR-0013).
- **Multi-part question / `parts[]`** — one canonical object = a whole question
  with an optional shared `stem` and a `parts[]` array; each part has its own text,
  answer, marks, steps, and optional diagram. See ADR-0013.
- **schema_version** — semver stamped on every canonical object; the schema (JSON
  Schema) is validated on load. See ADR-0004, Q-S1.

## Decision register

| ID | Decision | Status |
|---|---|---|
| ADR-0001 | Single-user, self-serve MVP; multi-user + authn/authz later | Accepted |
| ADR-0002 | Deterministic-first generation; LLM optional/deferred; retry budget = 20 | Accepted |
| ADR-0003 | Blueprint = YAML data + named Python solver plugin; dev-time authoring | Proposed |
| ADR-0004 | Canonical question object schema; edits create new versioned objects | Proposed |
| ADR-0005 | Answer output = marks + mark scheme + final answer + worked steps | Accepted |
| ADR-0006 | Tech stack (FastAPI + Svelte/Vite, uv, pytest) & monorepo layout; fixed edit ops | Accepted (layout: Proposed) |
| ADR-0007 | Diagram policy per family (mandatory vs optional aid) | Proposed (needs gold-sample validation) |
| ADR-0008 | Export via HTML→PDF (headless Chromium/Playwright); Typst fast-follow | Proposed |
| ADR-0009 | Difficulty author-declared; edit ops = regenerate/swap-sibling/transform | Accepted |
| ADR-0010 | Human review gate (approve/regenerate/discard) before export | Accepted |
| ADR-0011 | Ingestion tooling out of scope; schema must be interchange-grade | Accepted |
| ADR-0012 | Diagram = discriminated union keyed by `type` (+ raster variant) | Accepted |
| ADR-0013 | Multi-part `parts[]`; answer = discriminated union by `type` | Accepted |
| ADR-0014 | Schema versioning/validation, param typing, diagram-consistency, uniqueness | Accepted |
| ADR-0015 | Principled difficulty: levers + 3-rung ladder × 5 topics (15 blueprints v1) | Accepted |
| ADR-0016 | Tech-stack specifics: Python 3.12, uv workspace, jsonschema-gated dict (Pydantic at API only), id scheme, placeholder skill codes | Accepted |

Formal spec: `schemas/canonical-question.schema.json` (Draft 2020-12) + `docs/SCHEMA.md`
— validated against worked examples and negative controls.

"Proposed" = recommended by the assistant, awaiting your confirmation before it
becomes Accepted.
