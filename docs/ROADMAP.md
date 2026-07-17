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
| M5 | V5 | Preview + export both PDFs (completes L3 for Ratio) | done |
| M6 | V6 | Remaining ladders (Fractions/Percentage/Speed) + `shaded_fraction` | done |
| M6b | V6b | PSLE geometry figures — angle + area ladders (`geometry_figure`) | done |
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

## M5: Preview + export both PDFs (V5, shipped) - completes L3 for Ratio

Trustworthy WYSIWYG printable output. Merged via PRs #45, #46, #48-50. PDF
generation uses headless Chromium (Playwright) at the API boundary; KaTeX is
vendored self-contained (no CDN), so preview and print are the same document.

- **done** V5 slice plan doc (`docs/shaping/V5-plan.md`) - PR #45 (KAN-204)
- **done** Playwright dep + Chromium CI + vendored KaTeX assets - PR #46 (KAN-205)
- **done** A7 - pure `render_worksheet_html` / `render_answer_key_html` (vendored self-contained KaTeX + inline SVG + print CSS) - PR #48 (KAN-146)
- **done** `html_to_pdf` via headless Chromium + `POST /export/{preview,worksheet,answer-key}` - PR #49 (KAN-147)
- **done** Web: Preview + Export-worksheet/answer-key PDF buttons in WorksheetTray - PR #50 (KAN-148, rescoped)
- **todo** KAN-206 - package engine assets into the wheel (non-blocking follow-up, still open)

## M6: Remaining ladders + mandatory geometry (V6, shipped)

The remaining non-geometry topics (Fractions, Percentage, Speed) plus the
`shaded_fraction` mandatory figure. **Rescoped 2026-07-17:** Area/Geometry moved out
to **M6b** (rich figure geometry); the A10 blueprint work split per-topic. Each
ladder ships an independent seed-sweep invariant test.

- **done** KAN-149 - A10 Percentage ladder (e/m/h) + solver + goldens (no diagram)
- **done** KAN-232 - A10 Fractions ladder (e/m/h): `shaded_fraction` easy figure (D1)
- **done** KAN-234 - A10 Speed ladder (e/m/h) + goldens (no diagram; v1.3.0 speed units)
- **done** KAN-150 - A5 `shaded_fraction` diagram (Python + TS) + `edits.available_ops` aid-gating fix
- **done** KAN-151 - Web: topic selector fully live (all topics x 3 rungs) + wire new topics + e2e

## M6b: PSLE geometry figures — angle + area ladders (V6b, shipped)

Syllabus-aligned P5-P6 figure geometry via curated parametric templates. Two ladders
(`geometry_angle_{e,m,h}`, `geometry_area_{e,m,h}`) on one coherent `geometry_figure`
diagram system that **supersedes** `composite_geometry` + `area_perimeter`. Strictly
PSLE (no O-Level angle-chasing / tangents / Pythagoras). Shaped with the product owner
2026-07-17; blueprint: [`docs/shaping/V6b-geometry-plan.md`](shaping/V6b-geometry-plan.md).
Decisions G1-G7 + Q1 (2-template floor) + Q2 (schema v1.3.0).

- **done** KAN-226 - M6b geometry blueprint doc
- **done** KAN-227 - Schema v1.3.0: +`geometry_figure`, -`composite_geometry`/-`area_perimeter`, +speed units
- **done** KAN-228 - Geometry diagram system: `geometry_figure` spec + consistency check + `render_svg` (Py) + `renderGeometryFigure` (TS mirror)
- **done** KAN-229 - `geometry_angle` ladder (e/m/h) + solvers + goldens
- **done** KAN-230 - `geometry_area` ladder (e/m/h) + solvers + goldens (circles, auto-pi, inverse length)
- **done** KAN-231 - Web: geometry figures on the live card (mandatory, no toggle) + e2e
- **todo** KAN-233 - Geometry template catalogue expansion (fast-follow beyond the 2/rung floor)

### Follow-ups surfaced during V6/V6b (backlog)

- **todo** KAN-236 - Independent verification harness (formalize per-blueprint invariants; retire manual golden gate)
- **todo** KAN-237 - Graduate verification to full Hypothesis (generative strategies + shrinking)
- **done** KAN-241 - stamp `schema_version` 1.3.0 to match the schema
- **todo** KAN-242 - `geometry_figure` renderer: fill crescent/annular shaded regions
- **todo** KAN-243 - Web: drive edit-button visibility from engine `available_ops` (replace `startsWith('ratio')` heuristic)

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

11 epics (added **M6b** / EPIC-39). V6/V6b carving (2026-07-17) split A10 into
per-topic cards (KAN-149/232/234), rescoped KAN-150/151, and added the M6b epic's
7 cards (KAN-226–231, 233). Counts drift as work lands — the board is the source of
truth; run `kan list --board 8` for live status.
