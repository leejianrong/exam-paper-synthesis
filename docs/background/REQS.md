# REQS — Exam Paper Synthesis

> Raw idea capture / initial requirements. This is the seed document for the
> product-planning process (Grill → PRD → Shaping → Breadboard). It captures
> *what* we want to build and *why*, not the detailed design.
>
> Source of the idea: `docs/background/chatgpt-conversation-summary.md`.
> Scope of this doc: product requirements only (no business/GTM/pricing/timeline).

## Decisions locked

These framing decisions are settled and should be treated as fixed inputs to the
planning process (do not re-litigate them during grilling):

- **Doc scope:** full vision captured, but the **MVP is the near-term build**;
  downstream PRD/shaping stays MVP-scoped.
- **Business content:** excluded — this is a product-requirements doc only. GTM,
  pricing, and timelines live elsewhere.
- **LLM provider:** provider-agnostic for now; specific provider/model deferred.
- **Frontend:** Svelte. **Backend:** FastAPI (Python). This replaces the earlier
  Streamlit-demo suggestion.

## One-liner

A system that synthesizes syllabus-aligned Singapore math questions — each with
an accurate diagram and a correct, step-by-step answer key — that teachers and
tuition centres trust enough to use with students.

## Product vision

A deterministic, blueprint-driven math **generation engine** where the LLM
orchestrates and polishes wording, but **mathematical truth always comes from
deterministic tools** (symbolic/numeric solvers), never from the LLM alone.

The **canonical question object** (structured, machine-readable) is the single
source of truth. The rendered English question, the diagram, and the answer key
are all *views* derived from that object. This is the core design principle that
separates a reliable exam-synthesis platform from a toy worksheet generator.

Long term this becomes a SaaS for teachers and tuition centres. See
"Long-term direction (post-MVP)" — but the near-term build is the MVP below.

## MVP focus (near-term build)

Prove the core engine can reliably produce useful material, before building any
full SaaS surface.

**The MVP must answer:** *Can we generate 20–50 high-quality Singapore-style math
questions — with correct answer keys and accurate diagrams — that teachers trust
enough to use, edit, or pay for?*

**Target segment for the MVP:** Primary 5–6 Standard Math — Ratio, Fractions,
Percentage, Geometry (area/perimeter/composite), and word problems (including
PSLE Section-C-style non-routine problems). Secondary / O-Level comes later.

## MVP requirements (what it must do)

1. **Syllabus/topic selection** — choose level, topic, and subtopic for P5–P6
   Standard Math.
2. **Difficulty & cognitive-level selection** — select difficulty (e.g. easy /
   medium / hard) *and* a cognitive level (routine procedural / complex familiar
   / non-routine heuristic), not just difficulty.
3. **Blueprint-based question synthesis** — generate questions from a curated set
   of approved, parametric **blueprints** (target ~20 strong blueprints), each
   producing many varied instances via parameter sampling. Not free-form LLM
   generation.
4. **Correct step-by-step answer keys** — every question ships with a final
   answer and worked steps derived from a deterministic solver, not invented by
   the LLM. First-class product feature, not an afterthought.
5. **Accurate diagrams** — generate precise figures deterministically from
   structured parameters (not image-generation models). First diagram families:
   bar models, composite/overlapping rectangles, area/perimeter shapes.
6. **Programmatic validation** — every generated question is verified before it
   can be shown/exported: answer correctness, answer uniqueness, sane numbers,
   diagram-matches-question consistency, and within-level/syllabus fit.
7. **Regeneration & simple edits** — regenerate a variant with different numbers;
   apply simple edit instructions (e.g. "make this harder", "change to decimals",
   "add a diagram"). Edits operate on the canonical object, then re-validate.
8. **Export** — produce a printable worksheet and a matching answer key.
   Formats: HTML preview + PDF (Markdown acceptable as a debug/interchange
   format). Word/DOCX can come later.
9. **Human review gate** — a teacher can review each generated question (with its
   validation status) and approve / regenerate / discard before it goes into an
   exported worksheet. Passing automated validation is necessary but not
   sufficient; export happens from reviewed questions.

## Rock-solid, interchange-grade schema (core requirement)

The single most important non-negotiable: the **canonical question schema** and
the **diagram representation** must be rock-solid, **versioned**, and rigorously
**well-defined** — precise enough to act as an **interchange format**.

- The owner will separately (outside this project) prepare historical external
  material (past-year school papers, assessment books; ~hundreds of questions;
  **internal use only, rights held**) into our canonical form. **No IP/retrieval
  concern for the app; this project does NOT build an OCR/ingestion pipeline.**
- Consequence for this project: externally-prepared ("sourced") questions must
  load and **validate against the same schema** as engine-generated ones.
- The schema must therefore represent **both**:
  - **Generated** questions (blueprint + parameters + solver), and
  - **Sourced** questions (no blueprint/parameters/solver; answer/steps from the
    source and human-verified; diagram may be a raster/image reference rather than
    a generated SVG spec; carries `source` + `license`).
- Every canonical object carries a **schema version**; validation is enforced on
  load, not assumed.

## Quality bar (product-level targets)

- Answers are mathematically correct — very high reliability; math errors destroy
  trust and are the top risk to mitigate.
- Diagrams are clear enough for a teacher to understand without clarification.
- Most generated questions are usable with at most minor edits.
- Low rate of duplicate / near-duplicate questions.
- Creating a worksheet is fast (minutes, not hours).

## How generation should work (approach, not design)

Hybrid, deterministic-first pipeline per question:

> sample parameters (code) → solve (code) → validate (code) → fill question
> template → LLM polishes wording → re-validate the embedded numbers (code)

- **Code owns:** math structure, parameter sampling, answer computation, worked
  solution steps, marking/mark allocation, diagram geometry.
- **LLM owns:** natural wording, context/story, difficulty adaptation, ambiguity
  checking, wording variation. The LLM is *never* the source of truth for any
  answer or number.

Each blueprint provides: a parameter sampler, a question-text template, a solver,
a solution-step template, a validator, and (optionally) a diagram generator.

## Technical constraints & preferences

- **Frontend:** Svelte (the demo/app UI). Replaces the previously suggested
  Streamlit demo.
- **Backend:** FastAPI (Python).
- **Engine language:** Python — leverage deterministic math tooling (e.g. SymPy
  for algebra, Shapely for geometry validation, Decimal/Fraction for arithmetic).
- **Diagrams:** SVG as the canonical asset (crisp, scalable, embeddable,
  inspectable for validation); PNG only for compatibility/preview. Use clean-SVG
  libraries for geometry and a charting library for graphs.
- **LLM:** provider-agnostic for now — the specific provider/model is deferred.
  Assume a tiered approach later (cheaper models for classification/tagging,
  stronger models for hard synthesis/critique).
- **Data:** local file-based to start (e.g. YAML for skills and blueprints); a
  production database is not required for the MVP.

## Out of scope for the MVP

- Authentication, accounts, multi-tenancy, billing/payments.
- Production-grade infrastructure beyond what the demo needs.
- Full syllabus coverage (stay P5–P6 Standard).
- Full balanced **paper** assembly (start with topical question sets / worksheets).
- Auto-marking of student answers.
- LMS integrations, question-bank marketplace, collaborative teacher workflows.
- Polished DOCX/Word export (basic export can come later).

## Long-term direction (post-MVP)

Captured for context so early architecture doesn't paint us into a corner —
these are *not* MVP requirements:

- Expand coverage (more primary topics; then O-Level / Secondary, e.g. quadratics,
  trigonometry, statistics graphs).
- Full balanced-paper generation with topic/cognitive-distribution constraints
  (e.g. SEAB-4052-style papers) via a constraint solver.
- Versioned syllabus ontology / knowledge graph (levels → strands → topics →
  subtopics → learning objectives → skill nodes → blueprints → instances) backed
  by a real database.
- Richer diagram families (statistics graphs, circles/sectors, coordinate
  geometry, 3D solids/vectors).
- More output fidelity (DOCX, print-grade PDF templates, branded worksheets).
- Full SaaS surface: accounts, question library, teacher editing, cost controls
  (caching, retrieval-over-regeneration, pre-generated pools), analytics.

## Key risks to keep in view

1. **Math errors destroy trust** → blueprint-first, deterministic solvers,
   validation gates, human review of new blueprints.
2. **Questions feel repetitive** → separate math structure from context/wording;
   grow blueprints per topic over time.
3. **Scope creep** → hold the P5–P6 line; ~20 blueprints; topical worksheets, not
   full papers.
