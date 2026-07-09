# QUESTIONS — grilling log

Interrogation of `docs/REQS.md` to sharpen the plan before PRD/shaping.
As answers settle they migrate into `CONTEXT.md` (shared terms) and
`docs/adr/*.md` (decisions). Status: 🔴 open · 🟡 partial · 🟢 answered.

Priority: **[P0]** blocks everything · **[P1]** shapes core design · **[P2]** deferrable.

---

## A. Users, deployment & the "who"

- 🟢 **Q-A1 [P0]** → **Self-serve**. → ADR-0001.
- 🟢 **Q-A2 [P0]** → **Single-user MVP**; multi-user + authn/authz later. → ADR-0001.
- 🟢 **Q-A3 [P1]** Saved library vs ephemeral? → **Ephemeral for v1** (generate →
  preview → export); canonical objects are JSON-serializable so a library is a
  small later add. → ADR-0001.
- 🔴 **Q-A2b [P2]** If/when hosted: who hosts, what data persists between sessions?

## B. Blueprints

- 🟢 **Q-B1 [P0]** → **Hybrid: YAML data + named Python solver plugin.** → ADR-0003 (Proposed).
- 🟢 **Q-B2 [P0]** → **Dev-time, human-curated, LLM-assisted, golden-fixture-gated.** → ADR-0003.
- 🟢 **Q-B3 [P1]** → **v1 = 15 blueprints (3-rung difficulty ladder × 5 topics)**;
  build one full topic ladder end-to-end first. → ADR-0003, ADR-0015.
- 🟢 **Q-B4 [P1]** → `diagram` optional; other five required. → ADR-0003.
- 🔴 **Q-B5 [P2]** Variety beyond number-swapping — how many story templates each?

## C. Canonical question object

- 🟡 **Q-C1 [P0]** Schema proposed (CONTEXT.md / ADR-0004, Proposed). Confirm.
  *Now must also accommodate ingested/sourced questions (see section N).*
- 🟡 **Q-C2 [P1]** → *Proposed:* JSON-serializable; user-facing persistence
  ephemeral (Q-A3), but the ingested bank persists (section N).
- 🟢 **Q-C3 [P1]** → Edit = **new object with `provenance.parent_id`** lineage. → ADR-0004.

## D. Difficulty & cognitive levels

- 🟢 **Q-D1 [P0]** → `difficulty ∈ {easy,medium,hard}`;
  `cognitive_level ∈ {routine_procedural, complex_familiar, non_routine_heuristic}`;
  extra axes carried as tags. → ADR-0002.
- 🟢 **Q-D2 [P1]** Assigned vs computed? → **Author-declared per blueprint** (each
  blueprint targets one difficulty/cognitive profile). → ADR-0009.
- 🟢 **Q-D3 [P2]** → **Fixed to one profile**; the topic ladder supplies the other
  profiles. → ADR-0015.

## E. Answer keys, solutions & marking

- 🟢 **Q-E1 [P0]** → Marks + mark scheme **and** final answer **and** worked steps. → ADR-0005.
- 🟢 **Q-E1b [P1]** → **Model M/A/B internally; render primary as `[n]`; M/A/B in
  detailed answer-key mode.** → ADR-0005.
- 🟢 **Q-E2 [P1]** → Structured steps `{text, expr?}`, deterministic, **per part**. → ADR-0005.
- 🟢 **Q-E3 [P1]** → Answer key **embeds the aid diagram** (ratio/fraction/%);
  geometric figures stay with the question. → ADR-0005.
- 🔴 **Q-E4 [P2]** "Common mistake" notes per question in v1, or defer?

## F. Diagrams

- 🟡 **Q-F1 [P0]** → *Recommendation:* geometric-figure families **mandatory**;
  ratio/fraction/percentage **optional bar-model aid** (toggleable, also in answer
  key). Needs gold-sample validation. → ADR-0007 (Proposed).
- 🟡 **Q-F2 [P1]** → *Proposed:* spec derived by blueprint `diagram(params,
  solution)` (deterministic). Confirm.
- 🟢 **Q-F3 [P1]** → Blueprint `validate` asserts every diagram value/label equals
  the corresponding parameter/solved value (per family). → ADR-0014.
- 🔴 **Q-F4 [P2]** Bar-model: drawn to scale? annotations/braces model?
- 🔴 **Q-F5 [P2]** SVG lib + charting lib — decide now or during build?

## G. Validation & failure handling

- 🟢 **Q-G1 [P0]** → **20 resample attempts**, then structured error; flag
  blueprint if >50% fail. → ADR-0002.
- 🟢 **Q-G2 [P1]** → Uniqueness = solver is total & deterministic + constraints
  exclude ambiguous/degenerate cases (by construction). → ADR-0014.
- 🟢 **Q-G3 [P1]** Review gate before export? → **Yes — human review gate**
  (approve / regenerate / discard); automated validation is necessary but not
  sufficient. → ADR-0010.
- 🔴 **Q-G4 [P2]** Duplicate detection in v1 or deferred? Hash, embeddings, both?

## H. Editing & regeneration

- 🟢 **Q-H1 [P0]** → **Fixed operations for MVP**; free-text NL later. → ADR-0006.
- 🟢 **Q-H2 [P1]** Make harder/easier semantics? → **Swap to a sibling blueprint**
  in the same topic tagged one profile up/down; **regenerate** resamples within
  the same blueprint. → ADR-0009.
- 🔴 **Q-H3 [P2]** Can a teacher hand-edit generated text directly? Does that
  bypass validation? *(Tension with canonical-object-as-truth; interacts with the
  review gate G3.)*

## I. Export & rendering

- 🟢 **Q-I1 [P0]** → **HTML→PDF via headless Chromium (Playwright)**; Typst
  fast-follow. → ADR-0008 (Proposed).
- 🔴 **Q-I2 [P1]** Worksheet layout minimum: columns, answer spaces, header, numbering?
- 🔴 **Q-I3 [P1]** Worksheet + answer key = two documents or one with answer section?
- 🔴 **Q-I4 [P2]** Branding (centre logo/name) in v1, or plain?
- 🔴 **Q-I5 [P2]** Math renderer (KaTeX/MathJax) — how much LaTeX-style math in primary?

## J. LLM integration

- 🟢 **Q-J1 [P0]** → **No — v1 fully deterministic**; LLM polish deferred/optional. → ADR-0002.
- 🟡 **Q-J2 [P1]** *(deferred)* Swappable `LLMClient` when added; interface TBD.
  *(Note: the ingestion pipeline (section N) may use an LLM/vision model even
  though the generation engine does not — keep these separable.)*
- 🔴 **Q-J3 [P2]** *(deferred)* Exact LLM touch-points when introduced.

## K. Architecture & tech

- 🟢 **Q-K1 [P0]** → Monorepo `engine/`+`api/`(FastAPI)+`web/`(Svelte+Vite)+
  `content/`+`tests/`+`docs/`; engine importable pkg; uv + pytest. → ADR-0006.
- 🟢 **Q-K2 [P1]** Sync vs async? → **Synchronous HTTP for v1**; add a job queue
  only if LLM/heavy diagrams make it slow. → ADR-0006.
- 🔴 **Q-K3 [P1]** Ship a CLI in the MVP, or API-only? *(Layout makes it cheap.)*
- 🔴 **Q-K4 [P2]** Python version + tooling specifics; how the API imports engine.
- 🔴 **Q-K5 [P2]** Demo deployment target (local only, Docker, single VM)?

## L. Quality, testing & success

- 🔴 **Q-L1 [P1]** How to *measure* "usable with minor edits" in the MVP — review
  spreadsheet, in-app rating (ties to the G3 review gate), or not-in-software yet?
- 🟡 **Q-L2 [P1]** → *Proposed:* golden `params→answer` fixtures per blueprint +
  property checks. Confirm scope.
- 🔴 **Q-L3 [P2]** Single acceptance demo that means "MVP done"?

## M. Content / syllabus fidelity

- 🟡 **Q-M1 [P1]** MOE P5–P6 syllabus doc? → **User will provide it shortly.**
- 🔴 **Q-M2 [P2]** How is syllabus/skill data represented (`syllabus/*.yaml`), and
  does the app read it or is it author reference only?

## N. External material — TOOLING OUT OF SCOPE (see ADR-0011)

Resolved: the owner prepares external material into canonical form **outside this
project**; we build no OCR/ingestion pipeline. What matters here is the
interchange-grade schema (see section C / ADR-0004).

- 🟢 **Q-N1** → Bank is **internal**; owner holds rights. **App MAY retrieve from
  it for swapping** questions (updated — permissions confirmed). No public
  redistribution. → ADR-0011.
- 🟢 **Q-N6** → Owner **holds rights/licence** to ingest and reuse.
- 🟢 **Q-N5** → ~**hundreds** of questions.
- 🟢 **Q-N2/N3/N4/N7/N8/N9** → **N/A** (external to this project).
- 🟢 **Q-N10** → **Confirmed requirement:** the canonical schema must represent
  **sourced** questions (nullable blueprint/parameters, `source`, `license`,
  raster-diagram references, human-verified provenance). → ADR-0004, ADR-0011.

## Schema hardening (elevated — now the top priority)

- 🟢 **Q-S1 [P0]** → `schema_version` **semver** (`1.0.0`); **JSON Schema Draft
  2020-12** in top-level **`schemas/`**; validated on every load. → ADR-0014.
  *(Formal spec written + validated: `schemas/canonical-question.schema.json`.)*
- 🟢 **Q-S2 [P0]** Diagram representation → **discriminated union keyed by `type`**
  (bar_model, composite_geometry, area_perimeter, shaded_fraction + `raster`). → ADR-0012.
- 🟢 **Q-S3 [P1]** → Closed set `integer|decimal|fraction|ratio|quantity|set|text`;
  units via **controlled vocabulary**. → ADR-0013.
- 🟢 **Q-S4 [P1]** Multi-part → **one object with `parts[]`** (shared stem; per-part
  text/answer/marks/steps/diagram; top-level `total_marks`). → ADR-0013.
- 🟢 **Q-S5 [P1]** → Blueprint **declares a parameter schema**; sampled
  `parameters` must validate against it (not a free blob). → ADR-0014.
