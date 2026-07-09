# Summary — "SaaS Math Paper Architect" (ChatGPT conversation)

> Source: <https://chatgpt.com/share/6a4f735b-b904-83ec-b937-5f6f917bbd89>
> Model: GPT-5 Thinking · Topic: architecting a SaaS that synthesizes Singapore MOE math exam papers (PSLE + O-Level)
> Summarized: 2026-07-09

The chat has **two user prompts and two long answers**. The first designs the full technical blueprint; the second scopes a lean MVP with technical + business timelines.

---

## Turn 1 — User request: full technical blueprint

The user positions themselves as building a SaaS for teachers/tuition centres that dynamically synthesizes syllabus-compliant math questions using an **LLM agent + bespoke Python tools (MCP or CLI)**. They asked for a detailed blueprint covering five areas:

1. **Syllabus mapping & ontology** — schema/knowledge graph across P1–P6 and Sec 1–4/5; classify by *cognitive level*, not just topic.
2. **Question synthesis engine** — template vs. pure-LLM vs. verified generation; dynamic edit workflow ("make this harder with a quadratic"); correct step-by-step answer keys.
3. **Diagram/asset generation** — precise figures (PSLE geometry, cumulative frequency, 3D vectors) via Python; how the LLM specifies diagram params.
4. **Rendering/output** — Markdown vs. LaTeX vs. Typst; browser rendering + print-ready PDF/Word.
5. **Monetization/SaaS** — controlling API/token cost when generating full 100-mark papers.

## Turn 1 — Assistant answer: the blueprint

**Guiding principle:** Do **not** build "prompt → LLM writes whole paper → PDF". Build a *structured generation system*:

> Syllabus ontology → constrained generator → symbolic/numeric verifier → rubric solver → diagram renderer → human review → export.

The LLM is only an **orchestrator, wording editor, difficulty adapter, and pedagogical judge**. Mathematical truth comes from deterministic tools.

**Singapore context grounded in current docs:** MOE 2021 Primary syllabus (updated Oct 2025); Sec 1 2024-cohort onward under Full Subject-Based Banding (no more Normal/Express); O-Level Math is SEAB **4052**, organised into *Number & Algebra / Geometry & Measurement / Statistics & Probability*, with assessment objectives **AO1/AO2/AO3 ≈ 45%/40%/15%**.

### 1. Ontology
- Versioned **syllabus knowledge graph** + relational index. Start with **PostgreSQL + JSONB + pgvector** (add graph DB like Neo4j later).
- Entity chain: `SYLLABUS_VERSION → GRADE_LEVEL → STRAND → TOPIC → SUBTOPIC → LEARNING_OBJECTIVE → SKILL_NODE → QUESTION_BLUEPRINT → QUESTION_INSTANCE → SOLUTION/DIAGRAM/VALIDATION`.
- Key tables sketched in SQL: `syllabus_version`, `skill_node`, `question_blueprint` (a *parametric generator*, not a question), `question_instance`.
- **Cognitive taxonomy on multiple axes** (not just easy/hard): Assessment Objective (AO1/2/3), familiarity, representation, reasoning depth, heuristic (bar model, work-backwards, before-after, invariance…), marks, dependency breadth, answer type. Maps cleanly to SEAB's AO1/AO2/AO3.

### 2. Synthesis engine — **hybrid**
- **Templates/symbolic** own math structure, parameter sampling, answer computation, marking schemes.
- **LLM** owns wording, context, difficulty adaptation, rubric phrasing. *Never the sole source of truth for the answer.*
- Generation pipeline: intent parse → blueprint retrieve → param sample → symbolic/numeric solve → feasibility check → LLM wording → solution steps → independent verifier → diagram → render → teacher preview → export (with repair loops).
- Every question has a **canonical machine-readable JSON** (syllabus tags, cognitive metadata, parameters, constraints, answer, solution plan). Rendered English is just one *view* of that object.
- CLI contract: `mathgen generate --level --topic --cognitive --marks --seed`.
- **Dynamic edit** ("make harder with a quadratic") mutates the canonical model via a `transform_question` tool, re-solves, re-validates.
- **Answer keys layered:** Python solver → derivation tree → marking-scheme generator → LLM polish → independent verifier. Output includes final answer, M/A marks breakdown, student-facing steps, substitution check.
- **Validation gates:** numeric (Decimal/Fraction), algebra (SymPy), geometry (Shapely), diagram-consistency, syllabus rules, duplicate detection (embeddings + structural hash), answer uniqueness, mark-scheme consistency.

### 3. Diagrams — deterministic, not image models
- Generate from **structured params**, never from image-generation prompts.
- Libraries: **Matplotlib** (charts/CF curves), **svgwrite/drawsvg** (clean SVG geometry), **Shapely** (computational geometry), **SymPy** (symbolic/coordinate), **Pillow** (pixel/thumbnails), **TikZ/PGF** (publication-grade), **Manim** (animation), **CairoSVG** (conversion).
- **SVG is the canonical asset**; PNG only for compatibility/preview.
- LLM emits a **diagram spec JSON**; Python validates + renders. Renderer structured as plugins (`geometry_2d`, `graph_cartesian`, `statistics`, `vectors_3d`, `model_drawing`) + validators + exporters.

### 4. Rendering — multi-representation
- **JSON document AST** is canonical internally, with output adapters.
- Recommendation: **HTML + KaTeX + inline SVG** for browser preview; **Typst** as PDF-first export (cleaner/faster/safer than LaTeX); **python-docx** for Word; keep **LaTeX** as an advanced option. Editor: TipTap/ProseMirror with math nodes.

### 5. Paper assembly & cost
- Balanced-paper generation needs a **constraint solver** (Google OR-Tools / integer programming) driven by a paper spec (mark totals, topic %, cognitive %, no-duplicate, calculator policy). Grounded in SEAB 4052: Paper 1 & 2 each 90 marks/50%; last P2 question is a real-world application.
- **Cost control:** generate 70–85% from deterministic blueprints; tiered models (cheap for classification/tagging, strong only for hard synthesis/critique); cache aggressively by hash; pre-generate nightly pools; **70% retrieval / 20% mutation / 10% fresh LLM**; use Python (not tokens) for arithmetic; compress prompts (retrieve only relevant skill nodes, never paste full syllabus).
- **Most important decision:** the **canonical question object** is the source of truth — *not* the question text. That's the line between a toy worksheet generator and a reliable exam-synthesis platform.

**Stack:** FastAPI, PostgreSQL+JSONB, pgvector, Redis, Celery/RQ/Temporal, object storage, Docker sandbox; SymPy/NumPy/SciPy/Shapely/Matplotlib/svgwrite/Pillow/CairoSVG; React/Next.js + TipTap + KaTeX; Typst/LaTeX/python-docx.

---

## Turn 2 — User request: MVP scope + timelines

Focus the MVP **only on synthesis/generation of questions, diagrams, and step-by-step answer keys**. De-prioritize FastAPI server, auth, etc. Plan **both technical and business** timelines/milestones (including when/how to reach users and get revenue).

## Turn 2 — Assistant answer: MVP + roadmap

**First wedge:** *"Generate syllabus-aligned Singapore math questions with accurate diagrams and worked answer keys."* Prove the core engine — not a full SaaS.

**MVP target segment:** **Primary 5–6 Standard Math** (Ratio, Fractions, Percentage, Geometry, word problems) — highest willingness-to-pay for PSLE prep; secondary/O-Level comes later.

**In scope:** topic/difficulty/cognitive selection, blueprint-based synthesis, answer keys with steps, SVG/PNG diagrams for a few families, programmatic validation, HTML/PDF/Markdown export, regeneration, simple edit instructions.
**Out of scope:** production backend, auth, payments, multi-tenant SaaS, full syllabus coverage, full-paper generation, auto-marking, LMS integrations.

**MVP form:** *Python package + Streamlit demo app + PDF/HTML export* (CLI as fastest dev path). Local file-based data model (`syllabus/`, `blueprints/`, `renderers/`, `diagrams/`, `validators/`), YAML skill + blueprint files.

**Generation strategy:** blueprint-first, ~**20 strong blueprints** (not 200 weak). Each family = parameter sampler + text template + Python solver + solution-step template + validator + optional diagram. Pattern: *Python samples → solves → validates → template question → LLM wording polish → Python re-validates numbers.*

**Diagrams first:** bar models, composite/overlapping rectangles, area/perimeter — via svgwrite/drawsvg + matplotlib + shapely (defer Manim/TikZ).

### Timelines

**Technical phases:** Phase 0 product definition (1 wk) → Phase 1 core engine (2–3 wk) → Phase 2 diagram engine (2 wk) → Phase 3 Streamlit demo (1 wk) → Phase 4 quality/eval loop (2 wk) → Phase 5 paid pilot (2–4 wk).

**12-week combined timeline** (technical + business each week):
- **Wks 1–2:** discovery + 10 gold samples; list 30–50 potential users, reach out to 10, book 5 discovery calls.
- **Wks 3–4:** 5 blueprints + solvers + HTML/MD; continue calls, learn pain points.
- **Wks 5–6:** diagrams + PDF export; 3 live demos, explicit pricing questions.
- **Wks 7–8:** Streamlit prototype; give pilot users access, observe usage.
- **Wks 9–10:** quality hardening, 20 blueprints; convert pilots to paid tests (manual invoices).
- **Wks 11–12:** stabilize + package private beta; close **1–3 paid pilots**, build case studies.

**Business milestones:** M1 Problem validation (wk 2) → M2 Quality validation (wk 6, target 70–80% usable) → M3 Workflow validation (wk 8, teacher uses it in a real lesson) → M4 Revenue validation (wk 10–12).

**Go-to-market:** Stage 1 **concierge MVP** (you generate & send polished PDFs) → Stage 2 private beta → Stage 3 paid pilot (sell the *outcome* to tuition centres, not "an AI platform") → Stage 4 full SaaS only after revenue is proven.

**Pricing experiments (SGD):** individual tutor S$19–99/mo; tuition centre S$199–999/mo; topic packs S$19–299. Early on, **custom packs + centre pilots** monetize better than individual subscriptions.

**Quality metrics:** valid answer rate >95%, valid diagram rate >90%, teacher usability >4/5, manual-correction rate <20%→<10%, duplicates <10%, worksheet creation <5 min.

**Beyond MVP:** 3–6 mo (expand P3–P6, differentiated worksheets, basic login/Stripe, DOCX); 6–12 mo (O-Level E-Math, full-paper generation, diagnostics, centre subscriptions); 12+ mo (adaptive practice, auto-marking, student portal, blueprint marketplace, regional expansion).

**Key risks & mitigations:** (1) math errors destroy trust → blueprint-first + deterministic solvers + human review; (2) repetitive questions → separate math structure from context, more blueprints; (3) Word demand → start PDF, add DOCX later; (4) scope creep → stay P5/P6, 20 blueprints, topical worksheets; (5) users like but don't pay → test paid packs early, sell to centres.

**Positioning:** not "AI that generates math questions" but —
> *"We help tuition centres create differentiated PSLE math worksheets and answer keys in minutes instead of hours."*

---

## One-line takeaway
Build a **deterministic, blueprint-driven math engine** (canonical question JSON as source of truth, Python/SymPy for correctness, SVG diagrams, Typst/HTML export) with the LLM only orchestrating and polishing — start as a narrow P5/P6 PSLE tool sold to tuition centres via concierge/paid-pilot before ever building the full SaaS.
