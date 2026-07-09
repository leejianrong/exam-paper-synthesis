# PRD — Exam Paper Synthesis (MVP)

> **Process:** Step B (PRD) of build-plan-product. Step A (grilling + domain
> modeling) is complete. This PRD synthesizes the accepted decisions; it does
> **not** re-litigate them.
>
> **Sources of truth (read these for the "why"):** `docs/background/REQS.md`,
> `docs/CONTEXT.md` (glossary + decision register), `docs/adr/0001…0015`,
> `docs/SCHEMA.md` + `schemas/canonical-question.schema.json`,
> `docs/DIFFICULTY.md`, `docs/background/QUESTIONS.md`.
>
> **Product in one line:** a deterministic, blueprint-driven engine that
> generates syllabus-aligned Singapore P5–P6 math questions with correct
> step-by-step answer keys and accurate diagrams. The **canonical question
> object** is the single source of truth; **no LLM in v1** (fully
> deterministic). Single-user, self-serve.

---

## Problem Statement

A tuition teacher preparing Primary 5–6 Standard Math practice faces a slow,
error-prone task. Creating a topical worksheet by hand — or adapting past-paper
questions — means writing each question, drawing each bar model or geometry
figure accurately, working out every answer, and laying out a matching answer
key. It takes hours, and the part that matters most (the maths) is exactly the
part most likely to contain a silent mistake.

Existing "worksheet generator" tools don't solve this because they either
(a) recycle a fixed static bank, so questions repeat and can't be nudged
harder/easier, or (b) lean on an LLM to invent questions and answers — which
produces confident, wrong maths and mismatched diagrams. **A single wrong answer
key destroys a teacher's trust in the whole tool.**

The teacher needs to produce, in minutes, a set of 20–50 fresh, syllabus-aligned
questions that they trust enough to hand to students — each with a correct,
step-by-step answer key and a diagram that actually matches the question — while
keeping a human veto over what goes out.

## Solution

A **deterministic, blueprint-driven generation engine** with a thin FastAPI HTTP
layer and a Svelte + Vite single-page app. The teacher picks a level, topic, and
difficulty; the engine samples parameters, solves the maths **in code**, builds
worked steps and a mark scheme, and (where the family calls for it) generates an
accurate diagram — all as a **canonical question object** that is validated
against a versioned JSON Schema before it can be shown.

The teacher reviews each generated question with its validation status, and can
**regenerate**, **make harder/easier**, **change to decimals**, or **toggle a
diagram** — each edit producing a new canonical object with lineage back to its
parent. Nothing reaches a worksheet until the teacher **approves** it at the
review gate. Approved questions export to a **printable worksheet PDF** and a
**separate answer-key PDF** (HTML → headless Chromium), both rendered directly
from the canonical objects.

Because mathematical truth always comes from deterministic Python solvers (never
from a model), correctness is regression-tested against hand-verified **golden
fixtures** per blueprint. The same canonical schema also accepts **sourced**
questions (externally prepared past-paper/assessment material) as first-class
citizens, so the engine can later swap in an alternative question from the
internal bank — without this project building any ingestion tooling.

**MVP scope:** 5 topics (Ratio, Fractions, Percentage, Area/Geometry, Speed),
each as a **3-rung difficulty ladder** = **15 blueprints**. The **Ratio** ladder
is built end-to-end first as the lowest-risk proof of the whole model.

## User Stories

### Selecting and generating

1. As a tuition teacher, I want to choose a level (P5 or P6), topic, and
   difficulty, so that the questions I get fit what my class is currently
   learning.
2. As a teacher, I want to select a cognitive level (routine procedural /
   complex familiar / non-routine heuristic) as well as difficulty, so that I
   can target the *kind* of thinking a question demands, not just how "hard" it
   is.
3. As a teacher, I want to generate a question from an approved blueprint rather
   than free-form AI, so that I can trust the maths is sound by construction.
4. As a teacher, I want each generation to produce a fresh instance with
   different numbers, so that my worksheets don't repeat the same question.
5. As a teacher, I want to generate several questions for the same
   topic/difficulty in one go, so that I can build a worksheet quickly.
6. As a teacher, I want questions that are recognisably Singapore/PSLE in style
   (including non-routine, multi-step word problems), so that they prepare
   students for the real exam.
7. As a teacher, I want multi-part questions (a shared stem with parts a, b, c
   that build on each other), so that harder items mirror real exam structure.

### Answer keys, marking, and worked solutions

8. As a teacher, I want every question to come with a final answer, so that I
   never have to work it out myself.
9. As a teacher, I want typed answers with correct units (e.g. `cm²`, `$`,
   fractions, ratios), so that the answer key is unambiguous and correctly
   formatted.
10. As a teacher, I want step-by-step worked solutions for each part, so that I
    can explain the method to students and mark fairly.
11. As a teacher, I want marks shown per part as `[n]` on the worksheet, so that
    it looks like a real exam paper.
12. As a teacher, I want an optional detailed answer-key mode that shows the
    M/A/B mark breakdown, so that I can mark method vs accuracy when I want to.
13. As a teacher, I want the answer key for ratio/fraction/percentage questions
    to include the bar model in the worked solution, so that the method (not
    just the number) is visible.
14. As a teacher, I want to trust that the printed answer is the *actual*
    solution to the printed question, so that I never hand out a wrong key.

### Diagrams

15. As a teacher, I want geometry questions (composite/overlapping rectangles,
    area/perimeter, shaded fractions) to always come with an accurate figure, so
    that the question is answerable — the figure *is* the question.
16. As a teacher, I want a bar-model aid on ratio/fraction/percentage questions
    that I can turn on or off, so that I can choose whether to scaffold students.
17. As a teacher, I want every label and dimension in a diagram to match the
    question's numbers exactly, so that students are never misled by a wrong
    figure.
18. As a teacher, I want diagrams to be crisp when printed, so that worksheets
    look professional.

### Review, editing, and regeneration

19. As a teacher, I want to see each generated question's validation status
    before I use it, so that I know it passed the automated checks.
20. As a teacher, I want to approve, regenerate, or discard each question, so
    that I have the final say over what goes to students.
21. As a teacher, I want to regenerate a question with new numbers at the same
    difficulty, so that I can get a variant I prefer without changing the skill.
22. As a teacher, I want to make a question harder or easier, so that I can match
    it to a specific student or class without hunting for a new question.
23. As a teacher, I want to change a question to use decimals, so that I can
    align it with the number types my class is practising.
24. As a teacher, I want to toggle the bar-model diagram on aid-diagram
    questions, so that I control the level of scaffolding.
25. As a teacher, I want an edit to produce a new version linked to the original
    (not overwrite it), so that I can compare before/after and go back.
26. As a teacher, I want the "make harder/easier" option to be hidden when there
    is no rung to swap to, so that the UI never offers an action it can't perform.
27. As a teacher, I want the diagram toggle to appear only where a diagram is
    optional, so that I'm not offered a toggle for a figure that must stay on.
28. As a teacher, when a question can't be generated after repeated attempts, I
    want a clear message rather than a hang, so that I know to try different
    settings.

### Building and exporting a worksheet

29. As a teacher, I want to collect my approved questions into a current
    worksheet, so that I can assemble a set before exporting.
30. As a teacher, I want to preview the worksheet as it will print, so that I can
    check layout before committing.
31. As a teacher, I want to export a printable worksheet PDF with numbered
    questions, marks, and any mandatory diagrams, so that I can hand it out.
32. As a teacher, I want a separate answer-key PDF with final answers and worked
    steps, so that I can keep it apart from the student copy.
33. As a teacher, I want answer spaces and a clean header (title, name/date,
    total marks) on the worksheet, so that students can write on it directly.
34. As a teacher, I want the printed output to match the on-screen preview, so
    that there are no layout surprises.

### Trust, schema, and provenance (interchange-grade)

35. As the project owner, I want every question — generated or sourced — to
    validate against one versioned canonical schema, so that the schema is a
    reliable interchange format.
36. As the project owner, I want invalid objects rejected on load with clear,
    path-pointed errors, so that bad data can never silently enter the system.
37. As the project owner, I want externally-prepared "sourced" questions (no
    blueprint/parameters, a citation, a licence, and possibly a raster diagram)
    to load through the same schema, so that my internal bank interoperates with
    the engine.
38. As the project owner, I want the app to be able to pull an alternative
    question from the internal bank when swapping, so that I have more variety
    than blueprints alone provide (bank retrieval is permitted; ingestion is out
    of scope).
39. As the project owner, I want every object to record its provenance (created
    by engine vs ingested, whether an LLM was involved, parent lineage, version),
    so that I can audit where any question came from.

### Developer / authoring (dev-time)

40. As a blueprint author, I want to define a blueprint as YAML data plus a named
    Python solver, so that declarative content stays diffable while the maths
    stays in trustworthy code.
41. As a blueprint author, I want to declare a parameter schema for each
    blueprint, so that sampled parameters are validated, not a free blob.
42. As a blueprint author, I want to write golden fixtures (`params → expected
    answer/marks`) for each blueprint, so that correctness is regression-tested
    and never depends on a model.
43. As a developer, I want a thin `mathgen` CLI over the engine, so that I can
    generate, edit, and export headlessly for testing and golden-sample review
    without the web app.
44. As a developer, I want the engine to be an importable package that the API
    and CLI both call, so that there is one implementation of the logic.

## Implementation Decisions

> References point at the accepted ADRs, which carry the full rationale. No file
> paths or code are prescribed here beyond decision-encoding shapes.

### Architecture & modules (ADR-0006, ADR-0001)

- **Monorepo, four layers.** `engine/` (Python package: canonical model,
  parameter sampling, solvers, validators, diagram spec + SVG render, HTML
  render), `api/` (thin FastAPI HTTP layer over the engine), `web/` (Svelte +
  Vite SPA, REST/JSON to the API), `content/` (data assets: `syllabus/*.yaml`,
  `blueprints/*.yaml`). Tooling: **uv**, **pytest**.
- **The engine is the product; the API is thin.** All generation/edit/render
  logic lives in the engine so the API, and a thin **`mathgen` CLI** (confirmed
  in-scope), share one implementation.
- **Single-user, self-serve, ephemeral.** No auth/accounts/tenancy. State is a
  **session-scoped "current worksheet"** of approved objects held until export
  (ADR-0001, ADR-0010). Canonical objects are JSON-serializable so a saved
  library is a cheap later add.
- **Synchronous HTTP for v1** (ADR-0006 / Q-K2). No job queue unless later LLM /
  heavy-diagram work makes generation slow.

### The canonical question object (ADR-0004, ADR-0013, ADR-0014)

- **Single source of truth.** The rendered worksheet, answer key, and diagram
  are all *views* derived from the canonical object.
- **Formal spec is authoritative.** `schemas/canonical-question.schema.json`
  (JSON Schema Draft 2020-12) is the contract, consumed by both `engine` and
  `tests`. `docs/SCHEMA.md` explains it. **This project does not redesign the
  schema** — it is already written and validated against worked examples +
  negative controls.
- **Versioned + validated on load.** Every object carries `schema_version`
  (semver, `1.0.0`); every object — generated *and* sourced — is JSON-Schema
  validated whenever it enters the system, rejected with path-pointed errors.
  Objects are **closed** (`additionalProperties: false`).
- **`source_type` drives conditional requirements.** `generated` ⇒
  `blueprint_code` + `parameters` required; `sourced` ⇒ `source` + `license`
  required (`blueprint_code`/`parameters` null).
- **Multi-part via `parts[]`.** One object = one whole question: optional shared
  `stem`, `parts[]` each with own `text`, `answer`, `marking_scheme`,
  `solution_steps`, optional `diagram`; top-level `total_marks`. Single-part =
  `parts` of length 1.
- **`answer` and `diagram` are discriminated unions keyed by `type`.**
  `answer.type ∈ integer|decimal|fraction|ratio|quantity|set|text`;
  `diagram.type ∈ bar_model|composite_geometry|area_perimeter|shaded_fraction|raster`.
  Units come from a **controlled vocabulary** (the schema's `unit` enum), not
  free text.
- **Edits never mutate.** An edit operation yields a **new** object linked via
  `provenance.parent_id`; lineage is preserved (ADR-0004).

### Blueprints & the engine pipeline (ADR-0003, ADR-0002)

- **Blueprint = YAML data + named Python solver plugin.** YAML holds metadata,
  the declared parameter schema, wording/solution templates, constraints,
  cognitive tags, marks, and optional diagram type. The solver owns the maths via
  a small interface:
  - `sample(schema, rng) -> params`
  - `solve(params) -> {answer, intermediates}`
  - `validate(params, solution) -> report`
  - optional `diagram(params, solution) -> spec`
- **Deterministic per-question pipeline:** sample parameters → solve → validate →
  fill templates → (optional) build diagram spec → assemble + schema-validate the
  canonical object. **No LLM anywhere in v1** (ADR-0002). Generation is
  **seeded** and reproducible: `generate(blueprint_code, seed)` is a pure
  function of its inputs.
- **Retry budget:** on validation failure, resample up to **20 times**, then
  raise a structured "infeasible constraints" error; flag a blueprint that fails
  on **>50%** of attempts as author-misconfigured.
- **Parameter typing (ADR-0014):** a blueprint declares its parameter schema
  (types + ranges + enums); sampled `parameters` must validate against it.
- **Answer uniqueness is by construction (ADR-0014):** the solver is total and
  deterministic and constraints exclude ambiguous/degenerate cases — not solution
  enumeration.

### Difficulty & edit semantics (ADR-0009, ADR-0015, `docs/DIFFICULTY.md`)

- **15 blueprints = 3-rung ladder (easy/medium/hard) × 5 topics** (Ratio,
  Fractions, Percentage, Area/Geometry, Speed). **Build the Ratio ladder
  end-to-end first.**
- **Difficulty is author-declared per blueprint** — each blueprint targets one
  fixed difficulty + cognitive profile; the ladder supplies the other profiles.
  Blueprints tag the levers they pull in `cognitive.difficulty_levers[]`.
- **Difficulty operates at two levels:** composition (more, interdependent,
  higher-mark `parts[]`) and intrinsic (a single part made harder via named
  levers).
- **Fixed edit operations** (ADR-0006), each a canonical-object transform that
  re-validates and creates a new versioned object:
  - **regenerate** → resample within the same blueprint/rung (new numbers).
  - **make harder / make easier** → swap to the **sibling blueprint one rung
    up/down** the same topic ladder. Hidden when no such rung exists.
  - **change to decimals** → representation transform on the current object.
  - **toggle diagram** → only on **aid-diagram** families; hidden for
    mandatory-diagram families and families with no diagram.
  - Free-text natural-language edits are **deferred**.
- **Bank retrieval for swaps (ADR-0011, ADR-0015 open item):** the swap/harder/
  easier pool *may* include **sourced** questions from the internal bank. v1
  wiring is optional; the schema and provenance already support it.

### Answer keys, marking, and diagrams (ADR-0005, ADR-0007, ADR-0012)

- **Every question carries all three:** typed final answer, ordered mark scheme,
  and worked `solution_steps` (`{text, expr?}`, deterministic, per part), all
  derived from the solver's answer + intermediates.
- **Marking:** store full **M/A/B** on the object; **render `[n]` per part** on
  worksheets; surface M/A/B only in **detailed answer-key mode**.
- **Diagram policy per family (ADR-0007):**
  - **Mandatory** (the figure *is* the question; not toggleable): composite /
    overlapping rectangles, area & perimeter, shaded fraction.
  - **Optional bar-model aid** (toggleable; also embedded in the answer key):
    ratio (incl. before-after), fraction of a quantity, percentage.
- **Diagram spec → SVG deterministically.** Diagram specs are structured JSON
  produced by `diagram(params, solution)`; rendered to inline SVG (crisp,
  inspectable). `raster` variant carries an image reference for sourced diagrams.
- **Diagram-consistency check (ADR-0014):** `validate` asserts every value/label
  in the diagram spec equals the corresponding parameter or solved value
  (bar units = ratio units, rectangle dims = params, annotation text = sampled
  amount), per family.

### Review gate (ADR-0010)

- A **human review gate** sits between generation and export. Passing automated
  validation is **necessary but not sufficient**. Per question the UI shows the
  **validation status/badge** and offers **approve / regenerate / discard**.
- Export builds the worksheet from the **approved set only**, held in the
  session-scoped current worksheet.
- The gate is the natural place to later capture quality signals (Q-L1);
  structured ratings are **not** required in v1.

### Export & rendering (ADR-0008)

- **HTML → PDF via headless Chromium (Playwright).** One HTML/CSS pipeline feeds
  both the on-screen preview and the PDF (WYSIWYG) — inline SVG diagrams + KaTeX
  math, print CSS (`@page`, page-break rules). Typst is the designated
  fast-follow; WeasyPrint the lighter fallback. Neither is built in v1.
- **Two separate PDFs** (confirmed, resolving Q-I3): a **worksheet PDF**
  (numbered questions, `[n]` marks, answer spaces, mandatory diagrams) and a
  **separate answer-key PDF** (final answers, worked steps, embedded aid
  diagrams, optional M/A/B). The renderers are **pure functions of the approved
  canonical objects**.
- **Worksheet layout minimums (resolving Q-I2):** single-column layout (suits
  primary), sequential question numbering, per-part `[n]` marks right-aligned,
  an answer space under each part, and a header with worksheet title, name/date
  fields, and total marks.
- **Branding (resolving Q-I4):** plain in v1 — an editable worksheet **title**
  string only; centre logo/name is deferred.
- **Math rendering (resolving Q-I5):** **KaTeX**, used sparingly (fractions,
  ratios, units, simple expressions) — primary maths needs little LaTeX.

### Sourced material (ADR-0011)

- **This project builds no ingestion / OCR / parsing pipeline.** External
  material is prepared into canonical form outside the project. The load-bearing
  requirement is only that the schema is **interchange-grade** and accepts
  sourced questions (nullable blueprint/parameters, `source` + `license`,
  raster-diagram references, `provenance.created_by = "ingested"`,
  human-verified).

### Resolved open P2s (see "Further Notes" for deferrals)

- **L3 — acceptance demo:** MVP is "done" when the **full Ratio ladder** drives
  the whole flow end-to-end: generate across all 3 rungs → apply make-harder /
  make-easier / regenerate / toggle-diagram → review-gate approve → export a
  worksheet PDF **and** a separate answer-key PDF.
- **G4 — duplicate detection:** heavyweight near-duplicate detection is
  **deferred**. v1 does cheap **in-session dedup** by `(blueprint_code, seed)`
  and a normalized-parameter hash so a single worksheet never contains identical
  instances. Embedding-based near-dup is post-MVP.
- **B5 — story-template variety:** each blueprint ships **2–3 story templates**,
  selected deterministically by seed; this is an **authoring** concern, not a new
  engine feature. Richer variety grows per blueprint over time.

## Testing Decisions

**What makes a good test here:** assert on **external behaviour at the canonical
object boundary**, not solver internals. The canonical object is the interchange
contract and the single source of truth, so tests that pin its content survive
refactors of how it's produced. Seeded generation makes this exact and
reproducible. The ideal is the fewest, highest seams — confirmed direction:
**concentrate at the engine's canonical-object seam, treat renderers and edits
as pure functions of it, and keep API/web tests thin.**

- **Primary seam — `generate(blueprint_code, seed) -> canonical object`.** For a
  fixed seed, assert the returned object (a) **validates against the JSON
  Schema**, and (b) matches expected content (difficulty/cognitive tags, part
  count, answer type/value/unit, marks total). Reproducible because generation is
  pure in `(blueprint_code, seed)`. This one seam exercises sample → solve →
  validate → assemble as a unit.
- **Correctness anchor — golden fixtures per blueprint** (`tests/golden/`,
  ADR-0003). Hand-written, human-verified `params → expected answer/marks`
  records; **never LLM-verified**. These gate blueprint quality and catch
  regressions in the maths. Every blueprint ships fixtures before it is marked
  approved.
- **Schema validation utility as its own seam** (ADR-0014). Worked examples in
  `docs/SCHEMA.md` (generated multi-part, generated geometry, sourced/raster)
  **pass**; negative controls (stray field, wrong `source_type` requirements,
  bad union tag, out-of-vocab unit) **fail with path-pointed errors**. Covers
  both `generated` and `sourced` objects.
- **Diagram-consistency checks** (ADR-0014). Per family, assert every diagram
  value/label equals the corresponding parameter or solved value; assert a
  deliberately corrupted spec is rejected.
- **Edit operations as object → object transforms** (ADR-0009). Given an input
  object, assert: regenerate keeps difficulty/blueprint and changes parameters;
  make-harder/easier swaps to the correct sibling rung (and is unavailable at the
  ends of a ladder); change-to-decimals alters the answer representation;
  toggle-diagram only affects aid families; **every** edit sets
  `provenance.parent_id` and bumps `version`.
- **Retry / infeasibility behaviour** (ADR-0002). A blueprint with infeasible
  constraints raises the structured error after 20 attempts; the >50%-failure
  flag fires.
- **Renderers as pure functions of the canonical object.** `render_worksheet_html`
  and `render_answer_key_html` produce HTML containing the expected question
  text, `[n]` marks, answer spaces, and embedded SVG/aid diagrams; assert on
  structure/content, **not** styling. HTML-render golden snapshots are optional
  and can be added if layout regressions become a problem.
- **PDF export = smoke test only.** Assert the HTML → Chromium path produces a
  non-empty PDF for worksheet and answer key; do not assert on pixels.
- **API/web seam — thin.** A few FastAPI **TestClient** contract tests that
  endpoints wire to the engine and return schema-valid objects / expected HTML.
  No deep logic tests at this layer (the logic lives in the engine).
- **Acceptance test (L3).** An end-to-end test driving the **Ratio ladder**:
  generate all 3 rungs → apply each edit op → approve at the review gate →
  export both PDFs.

**Prior art:** the schema has already been validated against worked examples and
negative controls (Q-S1); the golden-fixture pattern (ADR-0003) is the
established model for every new blueprint and is the template for correctness
tests generally.

## Out of Scope

- **Authentication, accounts, multi-tenancy, billing** (ADR-0001). Single
  implicit user.
- **LLM anywhere in v1** — no API keys, no model cost, no wording polish. The
  engine is fully deterministic; a swappable LLM client is a later, separable
  phase (ADR-0002).
- **Ingestion / OCR / parsing tooling** — external material is prepared into
  canonical form outside this project; only the schema must accept its output
  (ADR-0011).
- **Redesigning the canonical schema** — it is written and validated; this build
  consumes it.
- **Free-text natural-language edits** — only the fixed edit ops ship (ADR-0006).
- **Full balanced-paper assembly** with topic/cognitive-distribution constraints
  — v1 produces **topical worksheets / question sets**, not whole exam papers.
- **Full syllabus coverage** — hold the **P5–P6 Standard** line, 5 topics, 15
  blueprints.
- **Auto-marking of student answers; LMS integrations; question-bank marketplace;
  collaborative teacher workflows.**
- **Polished DOCX/Word export; Typst/WeasyPrint pipelines; branded worksheets
  (logo)** — HTML→Chromium PDF only in v1.
- **Saved per-user library / persistence** — the user-facing app is ephemeral
  (session-scoped current worksheet); the internal sourced bank persists but is
  populated externally.
- **A job queue / async generation** — synchronous HTTP until proven necessary.
- **Embedding-based near-duplicate detection** — v1 does only cheap in-session
  dedup (G4).
- **Structured review ratings / quality-signal capture** — the review gate is
  approve/regenerate/discard only in v1 (Q-L1 deferred).
- **Hand-editing generated question text at the review gate** (Q-H3) — deferred;
  it is in tension with canonical-object-as-truth and needs its own decision.

## Further Notes

- **Deferred P2s carried forward:** Q-A2b (hosting/persistence when hosted),
  Q-E4 ("common mistake" notes), Q-F4/F5 (bar-model to-scale? SVG/charting lib
  choice — decide during build), Q-H3 (hand-editing at the gate), Q-M2 (how
  syllabus/skill data is represented and whether the app reads it), Q-K4/K5
  (Python version, how the API imports the engine, demo deployment target),
  Q-J2/J3 (LLM client interface and touch-points when introduced).
- **Diagram policy is a reasoned recommendation, not yet verified** (ADR-0007):
  validate the mandatory-vs-aid split against ~10 gold-standard PSLE samples
  during the Ratio-first build; adjust families if the samples disagree.
- **Difficulty is partly empirical** (`docs/DIFFICULTY.md`): the levers give a
  principled, consistent starting point; a "hard" blueprint may test as "medium"
  with real students. Calibration against gold samples and teacher feedback is
  tuning, not a design flaw, and is out of scope for the MVP.
- **MOE P5–P6 syllabus doc** (Q-M1): the owner will provide it; skill/syllabus
  codes in `content/syllabus/*.yaml` should follow it once available.
- **Build order (lowest risk):** prove the **Ratio ladder** end-to-end
  (generate → solve → validate → render → swap → review → export both PDFs)
  before building Fractions, Percentage, Area/Geometry, and Speed.
- **Publishing note:** the skill's final step publishes the PRD to an issue
  tracker with the `ready-for-agent` label. No issue tracker is configured for
  this project (not a git repository), so this PRD is delivered as
  `docs/PRD.md`. Run the tracker setup and re-run the publish step if an issue
  tracker is wanted.
```
