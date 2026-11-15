# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Summary of work since 0.1.0 (see `docs/ROADMAP.md` and git history for detail).

### Added

- **Editor + SaaS (W1–W4)** — WYSIWYG document editor (ProseMirror-style document
  model, schema `1.5.0`), templated and free-form question blocks, question bank,
  assets, owner-scoped accounts with Google/Microsoft/GitHub OAuth, Postgres
  stores, per-account export quotas, production image and Fly launch config.
- **Server-drawn diagrams and answer types (T1–T7)** — `chart`, `solid`,
  `number_line`, `panels`, `expression` answers, `cube_stack`, and the
  `statistics_chart` and `volume` ladders (canonical schema now `1.12.0`).
- **Paper format (P1–P7)** — icon toolbar, working space and `Ans: ____ unit`
  lines, marks placement, multi-part free-form questions, and paper structure:
  section blocks with derived question ranges / marks and an authored target, paper
  time, and Paper 1 Booklet A/B and Paper 2 starter templates; and answer-key options: hide the question text, omit the M/A
  breakdown, leave chosen questions out (numbers kept), mirrored in the editor's key
  view (document schema `1.7.0`); and the marking margin ("Do not write in this space")
  per section, on by default for short-answer and structured sections, plus the tally-box
  component (document schema `1.8.0`); and a tally box on every printed page of a paper
  with a marking section, summing the marks of the questions on that page (an inline paginator
  measures the paper and prints explicit pages, so the PDF and the Preview agree; a question
  taller than a page has its blank working space trimmed rather than clipped; a multi-part
  question may break between its parts); the editor's Preview shows the page count, each
  page's questions and tally, and any trimmed-space warning; and a cover page (school, exam,
  level, subject, paper, date, instructions to candidates, Name / Class / Register No. lines,
  and a "For examiner's use" table derived from the sections; it replaces the paper's header)
  and blank pages ("This page is intentionally left blank." or rough work), each on a page of
  its own and left out of the answer key (document schema `1.9.0`).
- **One-click paper generation (P8a)** — paper templates as engine content
  (`content/papers/*.yaml`: Paper 1 Booklet A/B, Paper 2, with their real slot layouts;
  the P4 starter templates now come from them via `GET /papers`), a pure, seeded
  `paper.generate_paper(template, level, seed)` (each blueprint once per paper, topics
  spread, every section exactly at its marks target, single-part stand-ins for Paper 2
  Section B, placeholders for what the content can't fill yet, an honest report),
  `POST /documents/generate`, the "Generate a whole paper" form on the papers list, the
  report banner and a placeholders-to-write count in the editor (document schema `1.10.0`:
  a question's `slot`). Also fixed: a paper opening on a cover or section block started
  with that block selected, so the first click and keystroke could replace it.
- **Multiple choice for Booklet A (P8b)** — `mcq.to_mcq` turns a generated question with a
  numeric or fraction answer into four-option multiple choice: the correct option is the
  engine's answer, the distractors are the worked solution's intermediate values (stopping a
  step early), near misses, halving/doubling and place-value slips (fractions: the unshaded
  part, shaded : unshaded, off-by-one). The paper generator fills Booklet A's slots this way
  (P6: 8 of 15, P5: 7 of 15 with today's content); `verify_snapshot` checks the correct option
  reads exactly as the re-solved answer, so these stay engine-proven. Options now print as a
  (1)–(4) grid after the figure, with real units (cm², °); edit ops are not offered on a
  multiple-choice copy.
- **Keep / swap / lock (P8d)** — per-question actions on a generated paper: "Another like
  this" (same slot and marks, same topic: a sibling blueprint or a new seed), "Another
  topic" (same marks, a topic the paper uses less), "Write my own" (an empty placeholder
  keeping the slot's marks), "Fill with a question" / "Another topic" on a placeholder, a
  lock toggle (Booklet A questions stay multiple choice through swaps), and
  "Regenerate unlocked" in the editor's top bar, which refills every unlocked generated
  question and empty placeholder and never touches locked questions, bank questions or
  anything the teacher wrote. Pure engine transforms (`paper_swap.swap_question`,
  `regenerate_unlocked`) that keep every P8a rule; `POST /documents/{id}/swap` and
  `POST /documents/{id}/regenerate` (owner-scoped, optimistic concurrency like PUT)
  (document schema `1.11.0`: a question's `locked`).

## [0.1.0] — 2026-07-25

First tagged checkpoint: the **MVP is complete**. A deterministic,
blueprint-driven engine generates syllabus-aligned Singapore **P5–P6 Standard**
math questions with provably-correct step-by-step answer keys and accurate
diagrams — no LLM in the generation path. The schema-gated canonical question
object is the single source of truth. Delivered across vertical slices V1–V7
(see `docs/planning/mvp/SLICES.md`), plus a post-MVP polish wave.

### Added

- **Engine (V1–V3)** — pure, deterministic `generate(blueprint_code, seed)`
  pipeline (sample → validate → solve → validate → assemble → schema-validate,
  bounded retry); canonical object builder + JSON-Schema load gate; structured
  engine errors. Full **Ratio** ladder (`ratio_easy` / `medium` / `hard`).
- **Answer keys & diagrams (V2)** — typed answers, ordered M/A/B marking schemes,
  and `solution_steps` from solver intermediates; `bar_model` spec builder +
  consistency check + deterministic spec→SVG renderer.
- **Edit operations (V3)** — object→object, re-validated transforms:
  regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram,
  driven by topic difficulty ladders.
- **Review gate + worksheet tray (V4)** — client-side (Svelte), ephemeral
  current-worksheet store with approve/discard, reorder, dedup, and total marks.
  No server state.
- **Preview + PDF export (V5)** — pure `render_worksheet_html` /
  `render_answer_key_html` (vendored self-contained KaTeX + inline SVG + print
  CSS); headless-Chromium `html_to_pdf` at the API boundary;
  `POST /export/{preview,worksheet,answer-key}`. Completes **L3 acceptance for
  Ratio**. Engine assets and content/schema data ship as package data (wheel).
- **Remaining topic ladders (V6)** — Fractions, Percentage, and Speed ladders
  (easy/medium/hard) with goldens; `shaded_fraction` mandatory figure; fully live
  topic × difficulty selector.
- **PSLE figure geometry (V6b)** — `geometry_angle` and `geometry_area` ladders on
  a general `geometry_figure` diagram system with strictly-PSLE curated parametric
  templates and auto-selected π (schema **v1.3.0**).
- **Headless CLI (V7)** — `mathgen generate/edit/export` driving the pure engine
  with no web/API (proves the engine is UI/HTTP-agnostic); own ~15-line Chromium
  PDF boundary with lazily-imported Playwright.
- **Sourced-object interchange (V7)** — hand-authored past-paper objects
  (`source_type:"sourced"`, `created_by:"ingested"`, `source`/`license`, `raster`
  data-URI figure) validate against the same schema and render in a mixed
  worksheet/answer-key alongside generated questions; wired the `raster` renderer
  branch (Python + TS mirror).
- **Verification** — every blueprint ships an independent seed-sweep invariant
  test (the correctness authority); hand-verified goldens are regression anchors.
  Verification graduated to Hypothesis (generative strategies + shrinking).
- **Foundation & CI/CD** — GitHub Actions merge gate (7 required checks),
  branch protection on `main`, secret scan + dependency audit + Dependabot,
  pre-push hook mirroring CI, ruff + mypy (Python) and eslint + svelte-check +
  vitest (web) quality gates, browser e2e.
- **Schema v1.4.0** — before/after bar-model `view_mode` + `parts`, and a
  `toggle-bar-view` edit op.

### Changed (post-MVP polish)

- Unified the crafting UI and print output with the landing-page design system
  (shared tokens, type roles, dark mode).
- `change-to-decimals` renders monetary/decimal values at 2 dp.
- Geometry figures label vertices with letters; running-track figure draws the
  semicircle radius as a dotted dimension line; rebalanced `geometry_area`
  difficulty rungs.
- `shaded_fraction` uses distinct outline vs fill colours so segment borders stay
  visible.

[0.1.0]: https://github.com/leejianrong/exam-paper-synthesis/releases/tag/v0.1.0
