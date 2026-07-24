# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-07-25

First tagged checkpoint: the **MVP is complete**. A deterministic,
blueprint-driven engine generates syllabus-aligned Singapore **P5–P6 Standard**
math questions with provably-correct step-by-step answer keys and accurate
diagrams — no LLM in the generation path. The schema-gated canonical question
object is the single source of truth. Delivered across vertical slices V1–V7
(see `docs/shaping/SLICES.md`), plus a post-MVP polish wave.

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
