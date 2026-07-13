# Exam Paper Synthesis

A **deterministic, blueprint-driven engine** that generates syllabus-aligned
Singapore **P5–P6 Standard** math questions with correct step-by-step answer keys
and accurate diagrams. The **canonical question object** is the single source of
truth; **no LLM** is involved — mathematical truth always comes from deterministic
Python solvers, so a printed answer key is provably the solution to the printed
question.

> **Status: slice V1** — end-to-end generation of the `ratio_medium` blueprint
> (three-term ratio sharing) through engine → API → web. See
> [`docs/shaping/SLICES.md`](docs/shaping/SLICES.md) for the full roadmap
> (V2 diagrams/worked solutions, V3 difficulty ladder + edits, … V5 PDF export).

## Repository layout

```
engine/     Python package (the product): canonical model, blueprint/solver
            framework, deterministic generation pipeline, JSON-Schema validators
api/        Thin FastAPI HTTP layer over the engine
web/        Svelte + Vite single-page app
content/    Data assets: content/blueprints/*.yaml, content/syllabus/*.yaml
schemas/    canonical-question.schema.json — the authoritative interchange contract
tests/      pytest suite + tests/golden/ hand-verified fixtures per blueprint
docs/        background/ (seed & grilling) · shaping/ (design + slice plans)
            · adr/ (decisions) · PRD, SCHEMA, DIFFICULTY, CONTEXT
```

The engine is UI/HTTP-agnostic and is imported by the API (and a future
`mathgen` CLI) as a **uv workspace path dependency** — one implementation, no
duplication (see [ADR-0016](docs/adr/0016-tech-stack-specifics.md)).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically)
- Node.js 20+ and npm (for the web app)

## Quickstart

### One-command dev (Makefile shortcut)

If you have `make`, the [`Makefile`](Makefile) wraps the steps below:

```bash
make install   # uv sync + npm --prefix web ci
make hooks     # install the pre-push hook (runs pytest + web build before every push)
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

Open http://localhost:5173 and click **Generate** to produce a fresh, validated
Ratio question. (If the API runs somewhere other than `http://localhost:8000`,
set `VITE_API` for the web app.)

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
- Every object is validated against `schemas/canonical-question.schema.json` on
  entry; invalid objects are rejected with path-pointed errors (ADR-0014).
- Correctness is regression-tested against **golden fixtures** (`params → expected
  answer/marks`), hand-verified, never model-verified.

## Documentation

| Doc | What |
|-----|------|
| [`docs/PRD.md`](docs/PRD.md) | Product requirements (MVP) |
| [`docs/shaping/SHAPING.md`](docs/shaping/SHAPING.md) | Requirements (R), shape, fit check, breadboard |
| [`docs/shaping/SLICES.md`](docs/shaping/SLICES.md) | Vertical slice roadmap (V1–V7) |
| [`docs/shaping/V1-plan.md`](docs/shaping/V1-plan.md) | This slice's implementation plan |
| [`docs/SCHEMA.md`](docs/SCHEMA.md) | The canonical question object, explained |
| [`docs/DIFFICULTY.md`](docs/DIFFICULTY.md) | The principled difficulty model |
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Glossary + decision register |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (0001–0016) |
