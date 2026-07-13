# Roadmap

This document maps the project's **milestones -> epics -> key stories** as tracked on
the Simple Kanban board **"Exam Paper Synthesis Roadmap"** (board id `8`). Milestones are a
naming convention only: slice-backed epics are prefixed `M<n>:` and map 1:1 to the slices in
[`docs/shaping/SLICES.md`](shaping/SLICES.md); cross-cutting/ongoing epics carry no prefix.

Status is evidence-based (git history, open PRs via `gh`, and the code on `main`):
**done** = merged to `main`; **in_progress** = open PR / active; **todo** = planned.

## Milestone backbone (slices V1-V7)

| Milestone | Slice | Epic | Status |
|-----------|-------|------|--------|
| M1 | V1 | Generate one Ratio question | done |
| M2 | V2 | Worked solution + marks + bar model | done |
| M3 | V3 | Ratio ladder + edit operations | done |
| M4 | V4 | Review gate + current worksheet | done |
| M5 | V5 | Preview + export both PDFs (completes L3 for Ratio) | todo |
| M6 | V6 | Remaining ladders + mandatory geometry | todo |
| M7 | V7 | CLI + sourced-object interchange | todo |

Ongoing (un-prefixed) epics: **Foundation & CI/CD**, **Product shaping & docs**, **Marketing site**.

---

## M1: Generate one Ratio question (V1, shipped)

Thinnest full-stack path: `generate("ratio_medium", seed)` -> API -> Svelte, schema-valid with a validation badge.

- **done** A1 - Canonical question object + JSON-Schema validator + provenance stamping
- **done** A2 - Blueprint loader + param-schema validation + `ratio_medium` solver + golden fixtures
- **done** A3 - `generate(blueprint_code, seed)` pipeline (retry <=20, structured error, in-session dedup)
- **done** A9 - `POST /generate` + minimal Svelte Generate page with validation badge

## M2: Worked solution + marks + bar model (V2, shipped)

Make the answer explainable: worked steps, per-part M/A/B marks, and an accurate bar-model SVG.

- **done** A6 - Typed answer + ordered M/A/B `marking_scheme` + `solution_steps` from solver intermediates
- **done** A5 - `bar_model` spec builder + consistency check + spec-to-SVG renderer
- **done** Web - render worked steps, `[n]` marks, bar-model SVG, M/A/B key toggle
- **done** Bar-model refinements - canvas-width fit + vertical Total brace (schema 1.1.0)

## M3: Ratio ladder + edit operations (V3, shipped)

Full Ratio ladder plus edit transforms. Merged via PRs #11-14.

- **done** V3 slice plan doc (`docs/shaping/V3-plan.md`) - PR #11 (KAN-139)
- **done** Ratio ladder: `ratio_easy` + `ratio_hard` + `bar_model_before_after` diagram (schema 1.2.0) - PR #12 (KAN-140)
- **done** Edit-ops backend: object-to-object transforms + `POST /edit/{op}` - PR #13 (KAN-141)
- **done** Web: edit buttons on QuestionCard (harder/easier hidden at ladder ends) - PR #14 (KAN-142)

## M4: Review gate + current worksheet (V4, shipped)

The human veto plus the collection surface. Merged via PRs #40-43; the store is
client-side (Svelte) and ephemeral — no server state.

- **done** A8 - Client-side (Svelte) current-worksheet store: dedup by id, up/down reorder, total-marks - PR #40 (KAN-143)
- **done** `question.total_marks` in web types (marks sum per ADR-0005) - PR #40 (KAN-188)
- **done** Approve/discard gate + "Added" state on each QuestionCard - PR #41 (KAN-144)
- **done** Worksheet tray UI: editable title, approved list (remove/reorder), total-marks - PR #42 (KAN-145)
- **done** App.svelte wiring: approve/discard handlers + tray mount - PR #43 (KAN-189)
- **done** vitest + e2e coverage for the worksheet flow - PR #43 (KAN-190)

## M5: Preview + export both PDFs (V5, planned) - completes L3 for Ratio

Trustworthy WYSIWYG printable output.

- **todo** A7 - `render_worksheet_html` / `render_answer_key_html` (KaTeX + inline SVG + print CSS)
- **todo** HTML -> Chromium (Playwright) -> two PDFs; `POST /export/*`
- **todo** Worksheet preview (`GET /worksheet/preview`) matching print

## M6: Remaining ladders + mandatory geometry (V6, planned)

The other four topics (all 5 topics x 3 rungs) plus mandatory, non-toggleable geometry figures.

- **todo** A10 - 12 more blueprints (Fractions, Percentage, Area/Geometry, Speed) + solvers + goldens
- **todo** A5 - `composite_geometry` / `area_perimeter` / `shaded_fraction` spec builders + consistency checks
- **todo** Topic selector fully live (5x3) + mandatory non-toggleable geometry figures

## M7: CLI + sourced-object interchange (V7, planned)

Headless engine access plus interchange-grade schema proof.

- **todo** A9 - `mathgen generate/edit/export` CLI over the engine
- **todo** A1 - sourced-object load path (`source`+`license`, raster diagram, `created_by="ingested"`)

---

## Ongoing: Foundation & CI/CD (in progress)

Cross-cutting engineering foundation. Open PRs #8-10.

- **in_progress** CI: GitHub Actions to gate merges (`ci.yml`) - PR #8
- **in_progress** Root `CLAUDE.md` repo guide - PR #9
- **in_progress** Playwright browser e2e for the Generate flow (`e2e.yml`) - PR #10

## Ongoing: Product shaping & docs (done-history record)

- **done** Shaping: R set, breadboard, slices, V1 plan (+ADR-0016)
- **done** ADRs 0001-0015 (architecture decisions)
- **done** PRD + canonical schema (`SCHEMA.md`) + difficulty model (`DIFFICULTY.md`)
- **done** V2 slice plan doc

## Ongoing: Marketing site (done-history record)

- **done** Static GitHub Pages landing page + `pages.yml`
- **done** Humanise landing copy; mark V2 shipped

## Backlog / deferred (no milestone, no epic)

- **todo** Deferred: pull alternative from internal bank on swap (R6.4) - Nice-to-have, not sliced
  (ADR-0015 open item). Promote to a slice V8 if it becomes Must-have.

---

## Board summary

10 epics, 36 cards: **done 24**, **in_progress 3**, **todo 9**.
