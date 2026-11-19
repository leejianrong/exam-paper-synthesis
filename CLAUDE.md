# CLAUDE.md

Guidance for Claude Code sessions/agents working in this repo. Agent working rules (subagent
limits) are in [AGENTS.md](AGENTS.md).

## Overview

Deterministic, blueprint-driven engine that generates syllabus-aligned Singapore
**P5–P6 Standard** math questions with correct step-by-step answer keys and
accurate diagrams. **No LLM** is involved in generation — mathematical truth
comes from deterministic Python solvers, so a printed answer key is provably the
solution to the printed question. The **canonical question object** (a plain
`dict`, gated by JSON Schema) is the single source of truth.

**Status:** the MVP slices **V1–V7** are shipped (Ratio/Fractions/Percentage/Speed
ladders, PSLE geometry, bar-model and `geometry_figure` diagrams, review gate,
preview + PDF export, headless `mathgen` CLI, sourced-object interchange incl. the
`raster` figure; see `docs/planning/mvp/SLICES.md`). Every blueprint ships an
independent seed-sweep **invariant test** (the correctness authority; goldens are
regression anchors). Beyond the MVP: the **editor + SaaS** (W1–W4: WYSIWYG
document editor, bank, accounts/OAuth, Postgres, Fly deploy), the **T-series**
server-drawn diagrams and answer types (chart, solid, number_line, cube_stack,
expression, `panels`; ladders `statistics_chart` and `volume`; the web fetches
these figures from `POST /render/diagram`), and the current **paper-format
initiative (EXA-E15)**: P1–P3 shipped (icon toolbar, working space / `Ans:` lines /
marks placement, multi-part free-form questions) and P4 (sections with a marks target,
derived question ranges and totals, paper time, starter templates) and P5 (answer-key
options: hide the question text, omit the M/A breakdown, leave questions out; document
schema 1.7.0), and P6a (marking margin per section, the tally-box component; schema 1.8.0) and P6b–d (a paginator script, `assets/paginate.js`, prints a per-page tally box, multi-part questions may break between parts, the editor's Preview shows the pages and tallies; since EXA-138 it paginates every paper: footer with page number and "Go on", end marker, stretched working space, one marking strip per page, structured questions a page each), and P7 (cover page and blank pages; schema 1.9.0), and P8a (one-click paper generation from paper templates; schema 1.10.0) and P8b (multiple choice for Booklet A by converting generated questions), and P8d (keep / swap / lock and "regenerate unlocked" on a generated paper; schema 1.11.0); the rest of P8 (multi-part blueprints, coverage) is planned in `docs/planning/editor/P8-SHAPING.md`. Live status is
the Pandan board (EXA, board 8) and `docs/ROADMAP.md`.

## Repo layout

It's a **uv workspace**. Root `pyproject.toml` declares members `engine/`,
`api/`, and `cli/`; dev deps are `pytest` + `httpx`; `testpaths = ["tests",
"cli/tests"]`.

| Path | What |
|------|------|
| `engine/exam_engine/` | **The product** — pure, deterministic question engine (UI/HTTP-agnostic; deps: `jsonschema`, `pyyaml`). Package `exam-engine`. |
| `engine/exam_engine/pipeline.py` | `generate(blueprint_code, seed)` — pure fn: sample → validate params → solve → validate → assemble → schema-validate, with bounded retry (`MAX_ATTEMPTS=20`). Also `param_hash`. |
| `engine/exam_engine/canonical.py` | Canonical object builder + load gate (`assemble`, load, validate). |
| `engine/exam_engine/schema.py` | Canonical schema loading + validation. |
| `engine/exam_engine/diagram.py` | Diagram consistency check + deterministic spec → inline SVG renderer; `is_worked_model` (bar models are worked solutions: printed in the answer key only, never on the student paper, EXA-132) (incl. the **T4** `panels` wrapper, schema 1.10.0). |
| `engine/exam_engine/label_layout.py` | **EXA-136** figure text placement: a renderer records its strokes, then places each label at the first candidate clear of every stroke and earlier label (estimated text boxes). Used by `geometry_figure`; `tests/svg_labels.py` is the independent SVG-reading check (`tests/test_figure_labels.py` sweeps every figure). |
| `engine/exam_engine/chart.py` | **T1** (schema 1.7.0) `chart` diagram — bar/line/pie: `check_chart_consistency` (also run by the `canonical.load` gate), `render_chart_svg`, and `leaked_hidden_values` (a `show_value:false` number never reaches the SVG text). Rendered server-side only — no TS mirror (see `docs/planning/editor/TIER2-SHAPING.md`). |
| `engine/exam_engine/solid.py` | **T2** (schema 1.8.0) `solid` diagram — cuboid/container + fill level: `check_solid_consistency` (also run by the `canonical.load` gate), `render_solid_svg` (fixed oblique projection, dashed hidden edges), `leaked_hidden_values`, `solid_volume`/`fill_volume`. Server-side only, like `chart`. |
| `engine/exam_engine/number_line.py` | **T3** (schema 1.9.0) `number_line` diagram — `check_number_line_consistency` (load gate), `render_number_line_svg` (decimal / stacked-fraction labels, lettered marked points), `tick_value`. Server-side only. |
| `engine/exam_engine/cube_stack.py` | **T6** (schema 1.12.0) `cube_stack` diagram — heightmap of unit cubes; `iso` / `front` / `side` / `top` pictures all derived from it (`front_view`, `side_view`, `top_view`, `view_key`, `cube_count`); `check_cube_stack_consistency` (load gate); `readable` / `visible_cubes` (what the iso picture shows); `show_front` "Front" arrow (1.13.0). Server-side only. |
| `engine/exam_engine/net.py` | **EXA-147** (schema 1.13.0) `net` diagram — six squares of a cube net on a grid: `check_net_consistency` (load gate: distinct, joined, unique labels; folding is not required), `fold` (rolls a cube over the net), `opposite`, `render_net_svg`. Server-side only. |
| `engine/exam_engine/grid.py` | **EXA-144** (schema 1.14.0) `grid` diagram — square grid (lines or dots) with shaded/lettered cells, polygons, segments, lettered points and a compass rose; `check_grid_consistency` (load gate), `render_grid_svg` (letters placed off the grid lines via `label_layout`). Server-side only. Blueprints: `solvers/square_grid.py` (`grid_area`, and the letter-choice `grid_lines`, `grid_compass`, `grid_symmetry`, MCQ slots only); invariants in `tests/test_invariants_grid.py`. |
| `engine/exam_engine/expression.py` | **T5** (schema 1.11.0) `expression` answer ("in terms of π / n"): `check_expression_consistency` (load gate; collected form + canonical order), `to_latex`, `evaluate`, `expressions_equal`. |
| `engine/exam_engine/units.py` | How a unit code prints (`printed_unit`): `l`/`ml` print as ℓ/mℓ (PSLE) in the paper, key, Ans: line and MCQ options; codes stay ASCII. The ℓ glyph is a one-glyph Inter face (`assets/fonts/inter-ell-*.woff2`, also in `web/src/assets/fonts/`). Likewise π (`inter-pi-*`, from Inter's greek subset) and ∠ (`katex-angle.woff2`, from KaTeX_Main); `render.FONT_FACES` lists every face (EXA-130). |
| `engine/exam_engine/palette.py` | **EXA-135** the print palette: the only colours a server-drawn figure uses, all neutral greys (black line art on white, as on a photocopied paper); `assets/print.css` mirrors it, `tests/test_monochrome_print.py` enforces r = g = b on every paper, key, fragment and figure. |
| `engine/exam_engine/errors.py` | Structured engine errors (`UnknownBlueprint`, `InfeasibleConstraints`, `DiagramInconsistent`, `EditNotApplicable`). |
| `engine/exam_engine/edits.py` | V3 edit ops as re-validated object→object transforms (`apply`, `available_ops`): regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram / toggle-bar-view (flips the before-after bar model's `view_mode`, KAN-310) / **set-cosmetic** (W1a: rename people / swap item via `param_roles`, re-solved through `pipeline.build_from_params`; not in `available_ops`). |
| `engine/exam_engine/document.py` | **W1b** document model (ProseMirror-style JSON paper, schema 1.10.0: rich text + `templatedQuestion` snapshots + teacher-written `freeformQuestion` blocks — marks, editable answer attr, unverified — + `image` (asset ref) and inline `math` (LaTeX), + per-question private `remark` that never prints, + **P2** paper layout: per-block `space_mm` working space and `ans_unit` for the `Ans: ____ unit [marks]` line, and paper `settings.marks_placement` question/answer/both, default answer, + **P3** multi-part free-form questions: a `freeformQuestion` body followed by lettered `freeformPart` children, each with its own marks, space, Ans: line and answer; labels are positions, marks are the parts' sum, + **P4** paper structure: top-level `section` divider blocks (title, instructions, mode, authored marks target) — the question range and marks of each are derived by `paper_outline`, numbering continues across sections — and `settings.time_min`; printed as section headers and a header "Time:" field, omitted from the answer key, + **P5** answer-key options: `settings.key_options` (`show_question`, `show_scheme`, both default true; `layout` full/compact; since EXA-159, schema 1.16.0, new papers write the school key explicitly via `new_key_options`/`with_key_style`, with `show_marks` and `one_mark_working`; an absent option keeps a saved paper's old behaviour) and per-question `in_key` (false leaves it out; the key keeps the paper's numbers via an explicit counter), applied by `render.render_document_html` to `key` and the key section of `full`, + **P6a** marking margin: `section.marking` (null = on for `short`/`structured` sections via `section_marking`); the student paper gives those questions the `marked` class (a ruled right strip captioned "Do not write in this space") and `data-marks`, and `render.render_tally_box(total)` is the per-page tally component the P6b paginator will place, + **P7** a `coverPage` block (first block only, at most one; school/exam/level/subject/paper/date/instructions authored, time, total and the "For examiner's use" table derived; replaces the student paper's header) and `blankPage` blocks (`blank`/`rough`, a page of their own; the paginator honours `break-before: page`), both left out of the key): `validate_document`, `verify_snapshot` (re-solves generated blocks so the engine-proven claim is unforgeable), `questions_in_order`; schema `schemas/document.schema.json`. Rendered by `render.render_document_html(title, doc, mode=student\|key\|full)`. |
| `engine/exam_engine/paper.py` | **P8a** paper templates (`content/papers/*.yaml`: real slot layouts of Paper 1 Booklet A/B and Paper 2) and one-click generation: `template_document(code)` (the P4 starter papers, with the same prefilled cover page as a generated paper, level left blank), pure seeded `generate_paper(template, level, seed, set_topics=None) -> (document, report)` (each blueprint once per paper; `set_topics` and `generate_set` spread topics over an exam set, EXA-153; least-used topic first, sections exactly at their targets, single-part stand-ins for structured sections, placeholders = free-form questions with `slot.placeholder`), `unfilled_placeholders`. Invariants in `tests/test_invariants_paper.py`. API: `GET /papers` (`routes_papers.py`), `POST /documents` with `template`, `POST /documents/generate`. |
| `engine/exam_engine/mcq.py` | **P8b** `to_mcq(obj, seed)`: a generated numeric/fraction question, or one answered in terms of π (EXA-155: a 2 × 2 grid of two π parts × two numbers from the solver's expression slips, so no option shares a part with all the others; listed by coefficient; `tests/test_invariants_pi_mcq.py`), → four-option multiple choice (distractors: intermediate step values, near misses, slips); `answer_text` is the shared option format that `document.verify_snapshot` checks the correct option against. **EXA-122**: a solver's optional `distractors(params, solution)` hook supplies common wrong answers with reasons (every ladder solver has one; reasons go in the MCQ marking scheme); a guard keeps the answer from being guessable from the options (`tests/test_distractors_group_{a,b,c}.py`). Used by `paper.generate_paper` for `mcq` slots. Invariants in `tests/test_invariants_mcq.py`. |
| `engine/exam_engine/paper_swap.py` | **P8d** keep / swap / lock as pure document transforms: `swap_question(doc, block_id, mode, seed, level)` (`like` = same slot and topic, a sibling blueprint or a new seed; `topic` = same marks, another topic the paper uses less; `own` = an empty placeholder keeping the slot's marks), `regenerate_unlocked(doc, level, seed)` (refills unlocked generated questions and empty placeholders; locked, bank and teacher-written blocks untouched), `paper_level`, `SwapNotPossible`. Every P8a rule still holds (invariants in `tests/test_invariants_paper_swap.py`). API: `POST /documents/{id}/swap`, `POST /documents/{id}/regenerate` (owner-scoped, 409 on a stale `base_version`). Web: `web/src/lib/editor/paperOps.ts` + the swap/lock buttons on question blocks and "Regenerate unlocked" in the editor's side panel (EXA-160). |
| `engine/exam_engine/convert.py` | **W2c** pure canonical question → free-form pieces (body/answer blocks, marks, `figure` placeholders the API rasterises); no verification claim survives conversion. |
| `engine/exam_engine/ladder.py` | Topic difficulty ladders + `sibling(code, dir)` (drives make-harder/easier). |
| `engine/exam_engine/blueprints/` | `base.py` (solver protocol + param validation), `registry.py` (content loader + solver registry), `solvers/ratio_{easy,medium,hard}.py`, and the T7 `solvers/statistics_chart.py` + `solvers/volume.py` (three rungs each; independent invariants in `tests/test_invariants_statistics_volume.py` re-derive answers from the drawn figure + the stem's numbers), and the P8e `solvers/average.py` (P5 Average ladder, 1/2/3 marks; `tests/test_invariants_average.py` re-derives each answer as the mean of the numbers printed in the stem), and the P8e batch 2 ladders `solvers/whole_numbers.py`, `decimals.py`, `rate.py` (P5) and `algebra.py` (P6), each 1/2/3 marks with `tests/test_invariants_<topic>.py`, and the P8e batch 3 1-mark Booklet A blueprints on no ladder (EXA-145): `solvers/number_sense.py` (`whole_numbers_rounding`, `decimals_compare`, `fractions_compare`) and `solvers/measurement.py` (`measurement_conversion`, `time_duration`; topics Measurement and Time), invariants in `tests/test_invariants_{rounding,compare,measurement,time}.py`, and the EXA-147 `solvers/solids.py` (`cubes_count`, `cubes_complete` P5; `cubes_view`, `net_opposite` P6, which ask multiple choice themselves and go only in MCQ slots; invariants in `tests/test_invariants_solids.py`), and the P8e batch 4 `solvers/circles.py` (EXA-149: P6 `circles_{easy,medium,hard}`, 1/2/3 marks, π = 3.14 or 22/7 stated, some medium and hard answers in terms of π as an `expression`; `tests/test_invariants_circles.py` re-derives each answer from the stem and by measuring the figure's traced shaded region), and the EXA-154 2-mark medium rungs `solvers/{ratio_difference,percentage_remainder,speed_minutes,geometry_angle_opposite,geometry_area_perimeter}.py` (each the second rung of a 4-rung ladder; invariants in `tests/test_invariants_two_mark_medium.py`), and the **P8c** multi-part `solvers/structured.py` (`ratio_structured`, `speed_structured`, `volume_structured`: a YAML `parts:` list, `solve()` returns `answers` one per part, `BlueprintSpec.is_multipart`/`part_count`; not on any ladder; invariants in `tests/test_invariants_structured.py`, framework/verify/edit tests in `tests/test_multipart_blueprints.py`), and the EXA-143 heuristic multi-part `solvers/heuristics.py` (`supposition_structured`, `fraction_remainder_structured`, `lcm_packs_structured`, `age_difference_structured`, `equal_number_amount_structured`; invariants in `tests/test_invariants_heuristics.py`), and the EXA-150 `solvers/geometry_angle_p6.py` (`geometry_angle_{folded,composite,reflex,structured}`, P6, on no ladder; figures drawn to scale, so `tests/test_invariants_geometry_angle_p6.py` measures each answer off the figure), and the EXA-148 data-table blueprints `solvers/tables.py` (`postage_table`, `rental_table`, multi-part `tariff_gst`; the solver's optional `table()` hook fills `question.table`; invariants in `tests/test_invariants_tables.py`). |
| `api/app/` | Thin **FastAPI** over the engine (`main.py`, `routes_generate.py` = `POST /generate`, `routes_edit.py` = `POST /edit/{op}`, `routes_export.py` = `POST /export/{preview,worksheet,answer-key}`, `export.py` = the impure Chromium `html_to_pdf`, `routes_bank.py` = owner-scoped `GET /bank` (W1d) + `PUT /bank/{id}/review` (W5: the in-app ADR-0019 review toggle, sourced only, confirmation required in the UI) + `POST /bank/import` (W2c: canonical load gate per item, arrives unreviewed, duplicate reported unless `replace`, ≤200 objects / 2 MB), `routes_convert.py` = `POST /convert/freeform` (W2c: engine `convert.to_freeform` text + figures rasterised to PNG assets via `export.html_to_png_many`), `routes_render.py` = `POST /render/question` (engine print markup as an embeddable fragment) + the shared `question.css`/`katex.js`, `routes_documents.py` = tenant-scoped `/documents` CRUD + preview + PDF export (W1b), `docstore.py` = `DocumentStore` protocol + SQLite impl (also **O2 folders**: a `folders` table + nullable `documents.folder_id`, added idempotently on both backends; deleting a folder unfiles its papers), `routes_folders.py` = O2 owner-scoped `GET/POST /folders` + `PATCH/DELETE /folders/{id}` (papers move with `PATCH /documents/{id}` `{folder_id}`, which is not an edit: no new version; `POST /documents` and `/documents/generate` take `folder_id`; a foreign folder is a 404), `assets.py` + `routes_assets.py` = W2b owner-scoped `AssetStore` (SQLite BLOBs, `EXAM_ASSETS_PATH`) + `POST/GET /assets` (raw body, PNG/JPEG by magic bytes, 2 MB / 4096 px / 50 MB per owner), `auth.py` = the identity seam (session cookie → user id; `EXAM_DEV_AUTH=1` dev stub, fails closed), `accounts.py` + `oauth.py` + `routes_auth.py` = W3a accounts/sessions + Google/Microsoft/GitHub OAuth (see `docs/AUTH.md`), `pgstores.py` + `bankstore.py` = W3b Postgres implementations of every store behind the same protocols (selected by `EXAM_DATABASE_URL`; contract tests run on both, `EXAM_TEST_DATABASE_URL`/`EXAM_TEST_BACKEND=postgres`), `usage.py` + `quota.py` = W3c per-account export allowance (rolling 24 h / 1 min ledger, 429 + Retry-After, refund on failure) and the Chromium concurrency cap, `settings.py` + `routes_settings.py` = **O1** per-account settings (`GET/PUT /settings`, known keys only, defaults merged on read; `classic_generator` off by default; `answer_key_style` school/worked, the key new papers start with, EXA-159), `models.py` = Pydantic envelopes only). Package `exam-api`; ASGI entry `app.main:app`. |
| `cli/mathgen/` | **V7 headless CLI** (`mathgen`) driving the engine directly — no web/API, no FastAPI import (proves engine is UI/HTTP-agnostic). `__main__.py` (argparse), `commands.py` (`generate`/`edit`/`export`, each object load-gated), `_pdf.py` (own ~15-line Chromium `html_to_pdf` mirror; Playwright lazy-imported so non-PDF cmds need no browser). Package `mathgen`; console-script `mathgen`. Deps: `exam-engine` + `playwright` only. |
| `Dockerfile`, `fly.toml`, `docs/LAUNCH.md` | **W4** production image (web build + API + Chromium, one origin, non-root), Fly config, and the launch checklist. `api/app/config.py` refuses to boot `EXAM_ENV=production` on an unsafe environment; `/ready` checks the DB. |
| `web/` | **Svelte 5 + Vite 8 + TypeScript** SPA with a hash router (`src/App.svelte`; every route but the editor sits under one app header, `src/lib/AppHeader.svelte`: Papers, Question bank, Classic when on, the `AccountMenu` avatar, EXA-167): `#/` documents list, `#/docs/:id` the **W1c WYSIWYG editor** (`src/lib/editor/`: TipTap page; since EXA-160 a two-row sticky header, `EditorBar.svelte` (breadcrumb, save state, marks total, Preview, the Export ▾ menu, the `AccountMenu` avatar) over the formatting toolbar, and a right `SidePanel.svelte` with Paper and Question tabs; the reusable WAI-ARIA `lib/Menu.svelte`, `lib/Icon.svelte` and `lib/ConfirmDialog.svelte`; `templatedQuestion` node view mounting `QuestionBlock.svelte`; since EXA-161 every question's controls are the shared `QuestionBar.svelte` (a pill when selected, a ⋯ menu whose rows come from `questionMenu.ts`) and its block shortcuts live in `shortcuts.ts` (the place for S5's global ones); `AddQuestion` picker, `autosave.ts`, `docsApi.ts`; since EXA-162 the answer key is a view, `KeyView.svelte`: the server's printed key (`GET /documents/{id}/preview/key`) in an iframe under an options strip, `keyRows.ts` finds a question in that markup, and an own question's answer is written in `AnswerDialog.svelte`), (the header's Paper / Insert / View / Help menus are `src/lib/MenuBar.svelte` over `Menu.svelte`; the editor-wide shortcuts, Ctrl+K palette `CommandPalette.svelte` and shortcut sheet are driven from `src/lib/editor/shortcuts.ts`, labels via `src/lib/keys.ts`, EXA-163), `#/bank` the question bank page (EXA-167: `src/lib/BankPage.svelte`, filters in `src/lib/bank.ts`, reusing `BankImport` and `ReviewControl`), `#/settings` the account settings (O1), `#/classic` the original Generate + tray page (hidden unless *Show the Classic generator* is on) (`src/ClassicPage.svelte`, `lib/QuestionCard.svelte`, `api.ts`, `types.ts`). Every API failure is worded by `src/lib/errors.ts` (`ApiError` with a plain-language message, `fail(res)`, `errorText(e, action)`, `canRetry`; `http.ts` makes an unreachable server `ApiError(0)`) and shown with `lib/ErrorNote.svelte` (Try again when it can help); a paper that won't open is `editor/PaperUnavailable.svelte`, first loads show skeletons (`.skel` in `app.css`, `editor/EditorSkeleton.svelte`) (EXA-165). Every figure the web shows but a raster comes from the engine via `POST /render/diagram` (`lib/DiagramView.svelte` → `ServerDiagram.svelte`, cached per spec; `lib/diagram.ts` holds only the spec types), so the editor, the Classic page and the PDF share one renderer and one label test (EXA-151). Reads API base from `VITE_API` (defaults to `http://localhost:8000`). Quality-gated by **eslint** (flat config), **svelte-check**, and **vitest** (jsdom + Testing Library). |
| `engine/exam_engine/content/blueprints/*.yaml`, `engine/exam_engine/content/syllabus/*.yaml` | Declarative blueprint/syllabus data (`ratio_{easy,medium,hard}.yaml`, `ratio.yaml`). **Package data** (KAN-258): lives under the package so it ships in the wheel; resolved package-relative (env override `EXAM_CONTENT_DIR`). |
| `engine/exam_engine/schemas/canonical-question.schema.json` | The canonical JSON Schema (currently **v1.14.0**) — single source of truth. **Package data** (KAN-258): ships in the wheel, resolved package-relative (env override `EXAM_SCHEMA_PATH`). |
| `tests/` | pytest suite: per-blueprint `test_invariants_*.py` seed-sweeps (correctness authority) + shared `tests/invariants.py` helper + `tests/golden/*.jsonl` hand-verified regression anchors. |
| `docs/` | Living refs at root (`SCHEMA.md`, `DIFFICULTY.md`, `CONTEXT.md`, `ROADMAP.md`) + `adr/` + `syllabus/`; `planning/` holds per-initiative planning (`mvp/` = V1–V7 design + slice plans + `PRD.md` + `background/`, `editor/` = the question-editor initiative). |
| `site/` | Static landing page (`index.html`). |

A blueprint = declarative YAML (metadata, param schema, wording/solution
templates, marks) + a named Python solver (`sample`/`solve`/`validate`, optional
`diagram`). The solver owns the maths; YAML stays diffable (ADR-0003).

## How to run

All commands verified from repo root.

| Task | Command |
|------|---------|
| Install / sync deps | `uv sync` |
| Run tests (~1300, ~4 min) | `uv run pytest` (root `tests/` + `cli/tests/`) |
| API dev server | `uv run uvicorn app.main:app --app-dir api --reload --port 8000` |
| Health check | `curl -s http://localhost:8000/health` → `{"status":"ok"}` |
| Generate (no web) | `curl -X POST http://localhost:8000/generate -H 'content-type: application/json' -d '{"blueprint_code":"ratio_medium","count":3}'` |
| CLI: generate (no web/API) | `uv run mathgen generate ratio_medium --seed 7 --out q.json` |
| CLI: edit | `uv run mathgen edit make-harder q.json --out q2.json` |
| CLI: export PDFs | `uv run mathgen export worksheet q.json --title "Review" --out ws.pdf` (also `answer-key`; `preview` → HTML) |
| Web deps | `npm --prefix web install` |
| Web dev server | `npm --prefix web run dev` (Vite, port 5173) |
| Web build | `npm --prefix web run build` |
| Web lint | `npm --prefix web run lint` (`make web-lint`) — eslint, 0 errors |
| Web type-check | `npm --prefix web run check` (`make web-typecheck`) — svelte-check, 0 errors |
| Web unit tests | `npm --prefix web run test:unit` (`make web-test`) — vitest |
| Make: install deps | `make install` (`uv sync` + `npm --prefix web ci`) |
| Make: boot API + web | `make dev` (both together; Ctrl-C stops both) |
| Make: stop dev servers | `make stop` (graceful TERM→KILL on ports 8000/5173; works from any shell, e.g. when `make dev` was backgrounded or orphaned) |
| Make: run tests | `make test` |
| Make: show goldens for the human check | `make goldens G="decimals rate"` (prints each golden as the printed question, steps and answer; `G` filters by blueprint prefix) |
| Make: lint Python | `make py-lint` (`uv run ruff check .`) |
| Make: format Python | `make py-fmt` (`uv run ruff format .`) |
| Make: type-check Python | `make py-typecheck` (`uv run mypy`) |
| Make: web build | `make build` |
| Make: install hooks | `make hooks` (sets `core.hooksPath` → `.githooks`) |

OpenAPI docs at `/docs`. The API stamps `provenance.created_at` and dedups within
a request; entropy (random seed) enters only here.

## Conventions (team rules)

- **JSON Schema is the single source of truth** (ADR-0016). Every canonical
  object is schema-validated; invalid objects rejected with path-pointed errors.
- **Engine stays UI/HTTP-agnostic** — no FastAPI/Pydantic in `engine/`.
  `generate()` is pure and deterministic (no clock/RNG leaking in); `created_at`
  is stamped only at the API boundary.
- **Correctness is proved by an independent invariant test per blueprint; goldens
  are regression anchors.** Every blueprint ships an independently-authored
  seed-sweep **invariant test** (`tests/test_invariants_*.py`, reviewed once) that
  re-derives the answer's *defining relationship* a different way from `solve()` —
  the correctness authority. Each blueprint also ships **hand-verified golden
  fixtures** (`tests/golden/*.jsonl`, never model-verified) as stability/regression
  anchors. Shared sweep boilerplate lives in `tests/invariants.py` (not a test
  module — an importable helper).
- **Workflow**: branch → PR → **merge once CI is green** (never push to `main`
  directly — it is **branch-protected**). **Standing instruction for agents: after
  you open a PR, watch its checks and merge it as soon as CI is green and it has
  been reviewed — do not leave a green, reviewed PR sitting or let PRs pile up.**
  `main` requires **all 7 status checks** to pass before merge: `Python tests`,
  `Web build`, `e2e`, `Secret scan`, `Dependency audit`, `Python quality`,
  `Web quality` (CI lives in `ci.yml` — `uv run pytest`, `npm --prefix web run
  build`, the `Python quality` job = ruff + mypy, the `Web quality` job = `lint` +
  `check` + `test:unit`; the browser e2e runs via `e2e.yml`). To merge: confirm with
  `gh pr checks <n>`, then `gh pr merge <n> --merge --delete-branch`. **Never merge a
  red or pending PR, and never merge unreviewed work.** (Run the checks locally first
  via the pre-push hook.)
- **Pre-push hook** (install with `make hooks`, i.e.
  `git config core.hooksPath .githooks`): the `.githooks/pre-push` hook mirrors
  the cheap CI jobs locally — Python (`uv run ruff check`, `ruff format --check`,
  `mypy`, `pytest -q`) then the web quality gates (`npm --prefix web run lint`,
  `check`, `test:unit`) and the web build — and blocks the push if any step
  fails. Bypass with `git push --no-verify` (escape hatch).
  `web/node_modules` self-heals: `scripts/ensure-web-deps.sh` (called by pre-push,
  post-merge, post-checkout and the `make web-*` targets) re-runs `npm ci` whenever
  `web/package-lock.json` differs from the last install, so a pull that adds a
  dependency never leaves stale "Cannot find module" type errors.
- **Ruff + mypy gate Python** (enforced in CI's `Python quality` job and in the
  pre-push hook). Lint/format with ruff (rules `E,F,I,UP,B,SIM`, line length 100)
  and type-check with mypy (Python 3.12, over `exam_engine` + `app`). Run locally
  with `make py-lint` / `make py-fmt` / `make py-typecheck`; all three must be
  green (as must `uv run pytest`) before pushing.
- **Commit messages** carry no `Co-Authored-By` trailer (or any other AI attribution line).
- **One typeface (EXA-94)**: Inter (OFL, bundled under `engine/exam_engine/assets/fonts/` and `web/src/assets/fonts/`) for the app, editor, diagrams and PDFs; the `--serif/--sans/--mono` tokens all resolve to it, PDFs embed it as data URIs. Only real maths (fractions, authored `\(…\)`, equations) uses KaTeX's own face; ratios and money are plain text. Don't add font families.
- **Multi-level doc consistency**: if a slice's scope shifts, update
  `docs/planning/mvp/SLICES.md` (and `SHAPING.md`).

## Where the key docs live

| Doc | What |
|-----|------|
| `docs/SCHEMA.md` | The canonical question object, explained |
| `docs/DIFFICULTY.md` | The principled difficulty model |
| `docs/CONTEXT.md` | Glossary + decision register |
| `docs/planning/mvp/PRD.md` | Product requirements (MVP) |
| `docs/planning/mvp/SHAPING.md` | Requirements, shape, fit check, breadboard |
| `docs/planning/mvp/SLICES.md` | Vertical slice roadmap (V1–V7) |
| `docs/planning/mvp/V1-plan.md`, `V2-plan.md`, `V3-plan.md` | Per-slice implementation plans |
| `docs/planning/editor/` | The editor + paper-format initiative (shaping, slices, `PAPER-FORMAT.md` = P1–P8) |
| `docs/ROADMAP.md` | Milestones → epics → stories (mirrors the Simple Kanban board) |
| `docs/adr/` | Numbered ADRs (0001–0022) |
