# CLAUDE.md

Guidance for Claude Code sessions/agents working in this repo.

## Overview

Deterministic, blueprint-driven engine that generates syllabus-aligned Singapore
**P5–P6 Standard** math questions with correct step-by-step answer keys and
accurate diagrams. **No LLM** is involved in generation — mathematical truth
comes from deterministic Python solvers, so a printed answer key is provably the
solution to the printed question. The **canonical question object** (a plain
`dict`, gated by JSON Schema) is the single source of truth.

Currently through slice **V7** (V1 = end-to-end `ratio_medium` generation;
V2 = bar-model diagrams / worked solutions; V3 = full Ratio ladder
`ratio_easy`/`medium`/`hard` + in-place edit operations; V4 = review gate +
client-side current-worksheet tray: Approve/Discard on cards, approved questions
collect in a titled tray with total marks — the store is client-side/ephemeral,
no server state; V5 = preview + export both PDFs: pure engine HTML renderers with
vendored self-contained KaTeX + print CSS, headless-Chromium PDF generation at the
API boundary, `POST /export/{preview,worksheet,answer-key}`, and web
Preview/Export buttons — completing L3 acceptance for Ratio; V6 = the remaining
topic ladders — Fractions, Percentage, Speed — plus the `shaded_fraction`
mandatory figure and a fully live topic×difficulty selector; V6b = PSLE figure
geometry: two ladders `geometry_angle`/`geometry_area` on a general
`geometry_figure` diagram system, strictly-PSLE curated parametric templates with
auto-selected π, schema **v1.3.0**; V7 = the final MVP slice: a headless
`mathgen` CLI (`generate`/`edit`/`export`) driving the pure engine with no
web/API — proving the engine is UI/HTTP-agnostic — plus sourced-object
interchange (a hand-authored past-paper object, `source_type:"sourced"` +
`source`/`license` + `created_by:"ingested"` + a `raster` data-URI figure,
validates against the same schema and renders in a mixed worksheet/answer-key
alongside generated questions; V7 wired the `raster` renderer branch — Python +
TS mirror — that this exercises). Every blueprint now ships an independent
seed-sweep **invariant test** (the correctness authority; goldens are regression
anchors). All six topics × three rungs generate schema-valid end-to-end). See
`docs/planning/mvp/SLICES.md`.

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
| `engine/exam_engine/diagram.py` | Diagram consistency check + deterministic spec → inline SVG renderer. |
| `engine/exam_engine/errors.py` | Structured engine errors (`UnknownBlueprint`, `InfeasibleConstraints`, `DiagramInconsistent`, `EditNotApplicable`). |
| `engine/exam_engine/edits.py` | V3 edit ops as re-validated object→object transforms (`apply`, `available_ops`): regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram / toggle-bar-view (flips the before-after bar model's `view_mode`, KAN-310) / **set-cosmetic** (W1a: rename people / swap item via `param_roles`, re-solved through `pipeline.build_from_params`; not in `available_ops`). |
| `engine/exam_engine/document.py` | **W1b** document model (ProseMirror-style JSON paper, schema 1.2.0: rich text + `templatedQuestion` snapshots + teacher-written `freeformQuestion` blocks — marks, editable answer attr, unverified — + `image` (asset ref) and inline `math` (LaTeX)): `validate_document`, `verify_snapshot` (re-solves generated blocks so the engine-proven claim is unforgeable), `questions_in_order`; schema `schemas/document.schema.json`. Rendered by `render.render_document_html(title, doc, mode=student\|key\|full)`. |
| `engine/exam_engine/convert.py` | **W2c** pure canonical question → free-form pieces (body/answer blocks, marks, `figure` placeholders the API rasterises); no verification claim survives conversion. |
| `engine/exam_engine/ladder.py` | Topic difficulty ladders + `sibling(code, dir)` (drives make-harder/easier). |
| `engine/exam_engine/blueprints/` | `base.py` (solver protocol + param validation), `registry.py` (content loader + solver registry), `solvers/ratio_{easy,medium,hard}.py`. |
| `api/app/` | Thin **FastAPI** over the engine (`main.py`, `routes_generate.py` = `POST /generate`, `routes_edit.py` = `POST /edit/{op}`, `routes_export.py` = `POST /export/{preview,worksheet,answer-key}`, `export.py` = the impure Chromium `html_to_pdf`, `routes_bank.py` = owner-scoped `GET /bank` (W1d) + `POST /bank/import` (W2c: canonical load gate per item, arrives unreviewed, duplicate reported unless `replace`, ≤200 objects / 2 MB), `routes_convert.py` = `POST /convert/freeform` (W2c: engine `convert.to_freeform` text + figures rasterised to PNG assets via `export.html_to_png_many`), `routes_render.py` = `POST /render/question` (engine print markup as an embeddable fragment) + the shared `question.css`/`katex.js`, `routes_documents.py` = tenant-scoped `/documents` CRUD + preview + PDF export (W1b), `docstore.py` = `DocumentStore` protocol + SQLite impl, `assets.py` + `routes_assets.py` = W2b owner-scoped `AssetStore` (SQLite BLOBs, `EXAM_ASSETS_PATH`) + `POST/GET /assets` (raw body, PNG/JPEG by magic bytes, 2 MB / 4096 px / 50 MB per owner), `auth.py` = the identity seam (session cookie → user id; `EXAM_DEV_AUTH=1` dev stub, fails closed), `accounts.py` + `oauth.py` + `routes_auth.py` = W3a accounts/sessions + Google/Microsoft/GitHub OAuth (see `docs/AUTH.md`), `pgstores.py` + `bankstore.py` = W3b Postgres implementations of every store behind the same protocols (selected by `EXAM_DATABASE_URL`; contract tests run on both, `EXAM_TEST_DATABASE_URL`/`EXAM_TEST_BACKEND=postgres`), `usage.py` + `quota.py` = W3c per-account export allowance (rolling 24 h / 1 min ledger, 429 + Retry-After, refund on failure) and the Chromium concurrency cap, `models.py` = Pydantic envelopes only). Package `exam-api`; ASGI entry `app.main:app`. |
| `cli/mathgen/` | **V7 headless CLI** (`mathgen`) driving the engine directly — no web/API, no FastAPI import (proves engine is UI/HTTP-agnostic). `__main__.py` (argparse), `commands.py` (`generate`/`edit`/`export`, each object load-gated), `_pdf.py` (own ~15-line Chromium `html_to_pdf` mirror; Playwright lazy-imported so non-PDF cmds need no browser). Package `mathgen`; console-script `mathgen`. Deps: `exam-engine` + `playwright` only. |
| `Dockerfile`, `fly.toml`, `docs/LAUNCH.md` | **W4** production image (web build + API + Chromium, one origin, non-root), Fly config, and the launch checklist. `api/app/config.py` refuses to boot `EXAM_ENV=production` on an unsafe environment; `/ready` checks the DB. |
| `web/` | **Svelte 5 + Vite 8 + TypeScript** SPA with a hash router (`src/App.svelte`): `#/` documents list, `#/docs/:id` the **W1c WYSIWYG editor** (`src/lib/editor/`: TipTap page, `templatedQuestion` node view mounting `QuestionBlock.svelte`, `AddQuestion` picker, `AnswerKey`, `autosave.ts`, `docsApi.ts`), `#/classic` the original Generate + tray page (`src/ClassicPage.svelte`, `lib/QuestionCard.svelte`, `barModel.ts`, `api.ts`, `types.ts`). Reads API base from `VITE_API` (defaults to `http://localhost:8000`). Quality-gated by **eslint** (flat config), **svelte-check**, and **vitest** (jsdom + Testing Library). |
| `engine/exam_engine/content/blueprints/*.yaml`, `engine/exam_engine/content/syllabus/*.yaml` | Declarative blueprint/syllabus data (`ratio_{easy,medium,hard}.yaml`, `ratio.yaml`). **Package data** (KAN-258): lives under the package so it ships in the wheel; resolved package-relative (env override `EXAM_CONTENT_DIR`). |
| `engine/exam_engine/schemas/canonical-question.schema.json` | The canonical JSON Schema (currently **v1.6.0**) — single source of truth. **Package data** (KAN-258): ships in the wheel, resolved package-relative (env override `EXAM_SCHEMA_PATH`). |
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
| Run tests (~504) | `uv run pytest` (root `tests/` + `cli/tests/`) |
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
| `docs/planning/editor/` | The question-editor initiative (the next milestone; product planning lands here) |
| `docs/ROADMAP.md` | Milestones → epics → stories (mirrors the Simple Kanban board) |
| `docs/adr/` | Numbered ADRs (0001–0022) |
