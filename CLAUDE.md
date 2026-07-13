# CLAUDE.md

Guidance for Claude Code sessions/agents working in this repo.

## Overview

Deterministic, blueprint-driven engine that generates syllabus-aligned Singapore
**P5–P6 Standard** math questions with correct step-by-step answer keys and
accurate diagrams. **No LLM** is involved in generation — mathematical truth
comes from deterministic Python solvers, so a printed answer key is provably the
solution to the printed question. The **canonical question object** (a plain
`dict`, gated by JSON Schema) is the single source of truth.

Currently through slice **V5** (V1 = end-to-end `ratio_medium` generation;
V2 = bar-model diagrams / worked solutions; V3 = full Ratio ladder
`ratio_easy`/`medium`/`hard` + in-place edit operations; V4 = review gate +
client-side current-worksheet tray: Approve/Discard on cards, approved questions
collect in a titled tray with total marks — the store is client-side/ephemeral,
no server state; V5 = preview + export both PDFs: pure engine HTML renderers with
vendored self-contained KaTeX + print CSS, headless-Chromium PDF generation at the
API boundary, `POST /export/{preview,worksheet,answer-key}`, and web
Preview/Export buttons — completing L3 acceptance for Ratio). See
`docs/shaping/SLICES.md`.

## Repo layout

It's a **uv workspace**. Root `pyproject.toml` declares members `engine/` and
`api/`; dev deps are `pytest` + `httpx`; `testpaths = ["tests"]`.

| Path | What |
|------|------|
| `engine/exam_engine/` | **The product** — pure, deterministic question engine (UI/HTTP-agnostic; deps: `jsonschema`, `pyyaml`). Package `exam-engine`. |
| `engine/exam_engine/pipeline.py` | `generate(blueprint_code, seed)` — pure fn: sample → validate params → solve → validate → assemble → schema-validate, with bounded retry (`MAX_ATTEMPTS=20`). Also `param_hash`. |
| `engine/exam_engine/canonical.py` | Canonical object builder + load gate (`assemble`, load, validate). |
| `engine/exam_engine/schema.py` | Canonical schema loading + validation. |
| `engine/exam_engine/diagram.py` | Diagram consistency check + deterministic spec → inline SVG renderer. |
| `engine/exam_engine/errors.py` | Structured engine errors (`UnknownBlueprint`, `InfeasibleConstraints`, `DiagramInconsistent`, `EditNotApplicable`). |
| `engine/exam_engine/edits.py` | V3 edit ops as re-validated object→object transforms (`apply`, `available_ops`): regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram. |
| `engine/exam_engine/ladder.py` | Topic difficulty ladders + `sibling(code, dir)` (drives make-harder/easier). |
| `engine/exam_engine/blueprints/` | `base.py` (solver protocol + param validation), `registry.py` (content loader + solver registry), `solvers/ratio_{easy,medium,hard}.py`. |
| `api/app/` | Thin **FastAPI** over the engine (`main.py`, `routes_generate.py` = `POST /generate`, `routes_edit.py` = `POST /edit/{op}`, `models.py` = Pydantic envelopes only). Package `exam-api`; ASGI entry `app.main:app`. |
| `web/` | **Svelte 5 + Vite 8 + TypeScript** SPA: `src/App.svelte`, `src/lib/QuestionCard.svelte` (with the edit-button row), `barModel.ts`, `api.ts`, `types.ts`. Reads API base from `VITE_API` (defaults to `http://localhost:8000`). Quality-gated by **eslint** (flat config), **svelte-check**, and **vitest** (jsdom + Testing Library). |
| `content/blueprints/*.yaml`, `content/syllabus/*.yaml` | Declarative blueprint/syllabus data (`ratio_{easy,medium,hard}.yaml`, `ratio.yaml`). |
| `schemas/canonical-question.schema.json` | The canonical JSON Schema (currently **v1.2.0**) — single source of truth. |
| `tests/` | pytest suite + `tests/golden/*.jsonl` hand-verified fixtures. |
| `docs/` | `SCHEMA.md`, `DIFFICULTY.md`, `CONTEXT.md`, `PRD.md`, `shaping/`, `adr/`. |
| `site/` | Static landing page (`index.html`). |

A blueprint = declarative YAML (metadata, param schema, wording/solution
templates, marks) + a named Python solver (`sample`/`solve`/`validate`, optional
`diagram`). The solver owns the maths; YAML stays diffable (ADR-0003).

## How to run

All commands verified from repo root.

| Task | Command |
|------|---------|
| Install / sync deps | `uv sync` |
| Run tests (~118) | `uv run pytest` |
| API dev server | `uv run uvicorn app.main:app --app-dir api --reload --port 8000` |
| Health check | `curl -s http://localhost:8000/health` → `{"status":"ok"}` |
| Generate (no web) | `curl -X POST http://localhost:8000/generate -H 'content-type: application/json' -d '{"blueprint_code":"ratio_medium","count":3}'` |
| Web deps | `npm --prefix web install` |
| Web dev server | `npm --prefix web run dev` (Vite, port 5173) |
| Web build | `npm --prefix web run build` |
| Web lint | `npm --prefix web run lint` (`make web-lint`) — eslint, 0 errors |
| Web type-check | `npm --prefix web run check` (`make web-typecheck`) — svelte-check, 0 errors |
| Web unit tests | `npm --prefix web run test:unit` (`make web-test`) — vitest |
| Make: install deps | `make install` (`uv sync` + `npm --prefix web ci`) |
| Make: boot API + web | `make dev` (both together; Ctrl-C stops both) |
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
- **Every blueprint ships hand-verified golden fixtures** (never model-verified),
  in `tests/golden/*.jsonl`.
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
- **Commit messages** end with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- **Multi-level doc consistency**: if a slice's scope shifts, update
  `docs/shaping/SLICES.md` (and `SHAPING.md`).

## Where the key docs live

| Doc | What |
|-----|------|
| `docs/SCHEMA.md` | The canonical question object, explained |
| `docs/DIFFICULTY.md` | The principled difficulty model |
| `docs/CONTEXT.md` | Glossary + decision register |
| `docs/PRD.md` | Product requirements (MVP) |
| `docs/shaping/SHAPING.md` | Requirements, shape, fit check, breadboard |
| `docs/shaping/SLICES.md` | Vertical slice roadmap (V1–V7) |
| `docs/shaping/V1-plan.md`, `V2-plan.md`, `V3-plan.md` | Per-slice implementation plans |
| `docs/ROADMAP.md` | Milestones → epics → stories (mirrors the Simple Kanban board) |
| `docs/adr/` | Numbered ADRs (0001–0016) |
