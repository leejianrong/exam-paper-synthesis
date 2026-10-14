# Exam Paper Synthesis

A **deterministic, blueprint-driven engine** that generates syllabus-aligned
Singapore **P5–P6 Standard** math questions with correct step-by-step answer keys
and accurate diagrams. The **canonical question object** is the single source of
truth; **no LLM** is involved — mathematical truth always comes from deterministic
Python solvers, so a printed answer key is provably the solution to the printed
question.

> **Status:** the **MVP (v0.1.0)** is complete: six topics × three difficulty
> rungs generate end-to-end through engine → API → web with worked solutions,
> accurate diagrams and PDF export, plus a headless `mathgen` CLI. Since then the
> project has grown into a **hosted Word-like paper editor** (accounts, a question
> bank, templated and free-form questions, working space and `Ans:` lines,
> multi-part questions) and extra server-drawn diagrams (charts, solids, number
> lines, cube stacks). The current initiative is making the editor produce a real
> P5/P6 maths paper (sections, answer-key options, marking margin, one-click paper
> generation) — see [`docs/planning/editor/PAPER-FORMAT.md`](docs/planning/editor/PAPER-FORMAT.md).
> History: [`docs/ROADMAP.md`](docs/ROADMAP.md), [`CHANGELOG.md`](CHANGELOG.md).

## Repository layout

```
engine/     Python package (the product): canonical model, blueprints/solvers,
            deterministic pipeline, diagram renderers, document model, HTML
            renderers. Its content/ (blueprint + syllabus YAML) and schemas/
            (canonical-question + document JSON Schemas) ship as package data
            under engine/exam_engine/
api/        FastAPI layer over the engine: generate/edit/export, documents,
            bank, assets, accounts + OAuth, Postgres/SQLite stores
cli/        `mathgen` headless CLI (generate / edit / export) — no web/API
web/        Svelte 5 + Vite SPA: document editor, classic generate page
tests/      pytest suite + tests/golden/ hand-verified fixtures per blueprint
docs/       Living refs (ROADMAP, SCHEMA, DIFFICULTY, CONTEXT, AUTH, LAUNCH)
            · adr/ (decisions) · syllabus/ · planning/<initiative>/
            (mvp/ = V1–V7; editor/ = the editor + paper-format initiative)
site/       Static landing page
```

The engine is UI/HTTP-agnostic and is imported by the API and the `mathgen` CLI
as a **uv workspace path dependency** — one implementation, no duplication (see
[ADR-0016](docs/adr/0016-tech-stack-specifics.md)). Production hosting (Docker
image, Fly + Neon) is described in [`docs/LAUNCH.md`](docs/LAUNCH.md); sign-in
in [`docs/AUTH.md`](docs/AUTH.md).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python automatically)
- Node.js 24 and npm (what CI uses) for the web app

## Quickstart

### One-command dev (Makefile shortcut)

If you have `make`, the [`Makefile`](Makefile) wraps the steps below:

```bash
make install   # uv sync + npm --prefix web ci
make hooks     # install the pre-push hook (ruff, mypy, pytest, web quality gates + build)
make dev       # boot API (:8000) and Vite (:5173) together; Ctrl-C stops both
```

Run `make` (or `make help`) to see all targets (`test`, `build`, `api`, `web`,
`e2e`, `health`). The manual steps below do the same thing without `make`.

### Manual steps

```bash
# 1. Install the Python workspace (engine + api + dev tools)
uv sync

# 2. Run the tests
uv run pytest

# 3. Run the API (http://localhost:8000, OpenAPI docs at /docs)
uv run uvicorn app.main:app --reload

# 4. In another terminal, run the web app (http://localhost:5173)
cd web
npm install
npm run dev
```

Open http://localhost:5173 for the document editor (sign-in uses the dev stub
when `EXAM_DEV_AUTH=1`; see [`docs/AUTH.md`](docs/AUTH.md)), or
http://localhost:5173/#/classic for the original Generate + worksheet-tray page.
(If the API runs somewhere other than `http://localhost:8000`, set `VITE_API`
for the web app.)

### Headless CLI

```bash
uv run mathgen generate ratio_medium --seed 7 --out q.json
uv run mathgen export worksheet q.json --title "Review" --out ws.pdf
```

### Generate without the web app

```bash
curl -X POST http://localhost:8000/generate \
  -H 'content-type: application/json' \
  -d '{"blueprint_code": "ratio_medium", "count": 3}'
```

## How it works

- A **blueprint** = declarative YAML (metadata, parameter schema, wording/solution
  templates, marks) + a named Python **solver** (`sample` / `solve` / `validate`).
  The solver owns the maths; the YAML stays diffable and reviewable (ADR-0003).
- `generate(blueprint_code, seed)` is a **pure function**: sample → validate params
  → solve → validate → fill templates → assemble → JSON-Schema-validate. It is
  seeded and reproducible, with a bounded retry budget (ADR-0002).
- Every object is validated against `engine/exam_engine/schemas/canonical-question.schema.json`
  on entry; invalid objects are rejected with path-pointed errors (ADR-0014).
- Correctness is regression-tested against **golden fixtures** (`params → expected
  answer/marks`), hand-verified, never model-verified.

## Documentation

| Doc | What |
|-----|------|
| [`docs/planning/mvp/PRD.md`](docs/planning/mvp/PRD.md) | Product requirements (MVP) |
| [`docs/planning/mvp/SHAPING.md`](docs/planning/mvp/SHAPING.md) | Requirements (R), shape, fit check, breadboard |
| [`docs/planning/mvp/SLICES.md`](docs/planning/mvp/SLICES.md) | Vertical slice roadmap (V1–V7) |
| [`docs/planning/editor/`](docs/planning/editor/) | Editor + paper-format initiative (shaping, slices, `PAPER-FORMAT.md`) |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Milestones → epics → stories |
| [`docs/AUTH.md`](docs/AUTH.md), [`docs/LAUNCH.md`](docs/LAUNCH.md) | Sign-in and production launch checklist |
| [`docs/SCHEMA.md`](docs/SCHEMA.md) | The canonical question object, explained |
| [`docs/DIFFICULTY.md`](docs/DIFFICULTY.md) | The principled difficulty model |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Glossary + decision register |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (0001–0022) |
