# Roadmap

This document maps the project's **milestones -> epics -> key stories** as tracked on
the Simple Kanban board **"Exam Paper Synthesis Roadmap"** (board id `8`). Milestones are a
naming convention only: slice-backed epics are prefixed `M<n>:` and map 1:1 to the slices in
[`docs/planning/mvp/SLICES.md`](planning/mvp/SLICES.md); cross-cutting/ongoing epics carry no prefix.

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
| M7 | V7 | CLI + sourced-object interchange | done |

Ongoing (un-prefixed) epics: **Foundation & CI/CD**, **Product shaping & docs**, **Marketing site**.

Post-MVP epics on the board (not yet itemised below; the board is the live source):
**M8** diagram & difficulty polish (E12, done), **Editor: bank + schema v2** (E13, done),
**Editor: WYSIWYG document editor + SaaS** (E14, deferred stories remain: EXA-33, 89, 90),
and **Paper format** (E15, P1–P5, P6a–d, P7, P8a, P8b and P8d done (P6d = a page summary in the Preview; live frames on the editing surface not built); P8c first three multi-part blueprints done (generator and swap wiring), then five heuristic ones (supposition, fraction of a remainder, LCM packs, ages, equal number vs amount) so Section B has 8 multi-part questions (EXA-143); starter templates carry the generated paper's cover (level left blank); P8e in progress: the P5 `average` ladder (EXA-117), then `whole_numbers`, `decimals`, `rate` (P5) and `algebra` (P6) (EXA-121), then five 1-mark Booklet A blueprints so Booklet A has no placeholders (EXA-145), then the P6 `circles` ladder (EXA-149), then five 2-mark medium rungs (ratio, percentage, speed, both geometry ladders) so Booklet B's 2-mark slots take medium questions (EXA-154) — see
[`planning/editor/PAPER-FORMAT.md`](planning/editor/PAPER-FORMAT.md) and [`planning/editor/P8-SHAPING.md`](planning/editor/P8-SHAPING.md)).
A comparison of generated papers with four real 2025 P6 prelims (O4, EXA-128) is in
[`planning/editor/REAL-PAPER-COMPARISON.md`](planning/editor/REAL-PAPER-COMPARISON.md): its layout gaps are EXA-134–142 (done: EXA-134, Booklet B numbers on from 16; EXA-137, a paper with empty placeholders asks before it prints; EXA-135, papers print monochrome; EXA-136, figure labels clear of lines; EXA-139, real section headers, per-section marks placement and a short right-aligned Ans: line, shown per section on the editing page too (EXA-152); EXA-151, the editor shows the engine's figures too; EXA-138, page numbers, "Go on" and end markers, pages filled with working space, one marking strip per page; EXA-140, real cover pages with the set's examiner's table, the page-count line and a blank back of the cover; EXA-141, MCQ options in one column, numbers in ascending order, the OAS sentence in the Booklet A header; EXA-142, a compact school-style answer key and cm²/×/− in key text, the default for new papers since EXA-159) and its content gaps EXA-143–150 (done: EXA-146, the generator matches the rung to the slot's marks; EXA-153, an exam set spreads its topics over the whole set; EXA-156, an MCQ's answer is no longer mostly the smallest or largest option; EXA-149, a Circles ladder; EXA-154, 2-mark medium rungs for five more topics; EXA-150, folded-paper, composite, reflex and two-part angle questions; EXA-147, cube-stack and net questions; EXA-148, data-table blueprints: postage, rental, tariff with GST; tick tables still to do; EXA-144, square-grid questions on a new `grid` figure; EXA-155, π-terms multiple choice).
From the P7–P8 acceptance run: **Organise and create** (O1 settings, O2 folders, O3 the + New wizard, O4 a comparison with real papers — done, see above; O1 done; O2 folders built: API and the folder view on "Your papers"; O3 the + New wizard built, with a server-derived `paper_part` for the exam-set chips) — see
[`planning/editor/ORGANIZE-SHAPING.md`](planning/editor/ORGANIZE-SHAPING.md).
The editor and app UI redesign (EXA-159–170) is planned in
[`planning/editor/UI-REDESIGN.md`](planning/editor/UI-REDESIGN.md) (approved 2026-11-19; done: S2,
EXA-159, the school key by default with an account setting for the key style; S1, EXA-160, an
editor header that fits: two rows, one Export menu, an avatar menu, and Time / first question /
marks shown / Regenerate unlocked in a Paper / Question side panel; S3, EXA-161, the question
bar: nothing at rest, a pill when a question is selected, one ⋯ menu, block shortcuts and undo
on delete; S5, EXA-163, the Paper / Insert / View / Help menus, a Ctrl+K command palette, a
shortcut sheet and the editor-wide shortcuts, and a side panel you can hide).

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

- **done** V3 slice plan doc (`docs/planning/mvp/V3-plan.md`) - PR #11 (KAN-139)
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

- **done** V5 slice plan doc (`docs/planning/mvp/V5-plan.md`) - PR #45 (KAN-204)
- **done** Playwright dep + Chromium CI + vendored KaTeX assets - PR #46 (KAN-205)
- **done** A7 - pure `render_worksheet_html` / `render_answer_key_html` (vendored self-contained KaTeX + inline SVG + print CSS) - PR #48 (KAN-146)
- **done** `html_to_pdf` via headless Chromium + `POST /export/{preview,worksheet,answer-key}` - PR #49 (KAN-147)
- **done** Web: Preview + Export-worksheet/answer-key PDF buttons in WorksheetTray - PR #50 (KAN-148, rescoped)
- **done** KAN-206 - package engine assets (KaTeX + print.css) into the wheel - PR #74
- **done** KAN-258 - ship content/** + schemas/** as package data so `generate()` works from a wheel - PR #77

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
2026-07-17; blueprint: [`docs/planning/mvp/V6b-geometry-plan.md`](planning/mvp/V6b-geometry-plan.md).
Decisions G1-G7 + Q1 (2-template floor) + Q2 (schema v1.3.0).

- **done** KAN-226 - M6b geometry blueprint doc
- **done** KAN-227 - Schema v1.3.0: +`geometry_figure`, -`composite_geometry`/-`area_perimeter`, +speed units
- **done** KAN-228 - Geometry diagram system: `geometry_figure` spec + consistency check + `render_svg` (Py) + `renderGeometryFigure` (TS mirror)
- **done** KAN-229 - `geometry_angle` ladder (e/m/h) + solvers + goldens
- **done** KAN-230 - `geometry_area` ladder (e/m/h) + solvers + goldens (circles, auto-pi, inverse length)
- **done** KAN-231 - Web: geometry figures on the live card (mandatory, no toggle) + e2e
- **done** KAN-233 - Geometry template catalogue expansion (fast-follow beyond the 2/rung floor) - PR #79

### Follow-ups surfaced during V6/V6b (backlog)

- **done** KAN-236 - Independent verification harness (formalize per-blueprint invariants; retire manual golden gate) - PR #76
- **in_progress** KAN-237 - Graduate verification to full Hypothesis (generative strategies + shrinking)
- **done** KAN-241 - stamp `schema_version` 1.3.0 to match the schema
- **done** KAN-242 - `geometry_figure` renderer: fill polygon-minus-arc shaded regions (square minus circle) - PR #78
- **done** KAN-243 - Web: drive edit-button visibility from engine `available_ops` (replace `startsWith('ratio')` heuristic) - PR #75

## M7: CLI + sourced-object interchange (V7, shipped)

Headless engine access plus interchange-grade schema proof. The final MVP slice,
shipped 2026-07-17. Plan: [`docs/planning/mvp/V7-plan.md`](planning/mvp/V7-plan.md). Both
cards built in parallel in treehouse worktrees, landed serially on green CI.

- **done** KAN-152 - A9 `mathgen generate/edit/export` CLI over the engine (new `cli/`
  workspace package; own `_pdf.py` Chromium boundary; depends only on `exam-engine`,
  no FastAPI — proven by an import-guard test) - PR #69
- **done** KAN-153 - A1 sourced-object load path (`source`+`license`, `raster`
  data-URI diagram, `created_by="ingested"`): validates against the same schema and
  renders in a mixed worksheet/answer-key. Wired the `raster` `<img>` renderer branch
  (Python + TS mirror) — the load/validate/join path was unchanged but raster
  *rendering* was not; also fixed a silently-dropped `question.stem` - PR #70

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
