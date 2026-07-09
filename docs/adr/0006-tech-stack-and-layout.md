# ADR-0006: Tech stack, repo layout, and edit operations

- Status: Accepted (stack & edit-ops); Proposed (exact layout)
- Deciders: project owner
- Related: Q-K1, Q-H1

## Context

We need to fix the implementation stack, the repository shape, and the editing
model for the MVP.

## Decision

- **Stack (Accepted):** Python **engine**, **FastAPI** backend, **Svelte + Vite**
  frontend. Tooling: **uv** for env/deps, **pytest** for tests.
- **Repo layout (Proposed):** single monorepo

  ```
  engine/    # Python pkg: canonical model, sampling, solvers, validators, diagrams, HTML render
  api/       # FastAPI — thin HTTP layer over engine
  web/       # Svelte + Vite SPA (REST/JSON to the API)
  content/   # data assets: syllabus/*.yaml, blueprints/*.yaml
  tests/     # incl. tests/golden/ fixtures per blueprint
  docs/      # REQS, PRD, adr/, ...
  ```

  `engine` is an installable package the API imports; the API stays thin (so a
  `mathgen` CLI can be added later without duplicating logic).
- **Edit operations (Accepted):** the MVP exposes **fixed, named operations**:
  regenerate, make harder, make easier, change to decimals, and **toggle diagram**.
  **Free-text natural-language edits are a future phase.**
  - **toggle diagram** is available **only on aid-diagram families** (ratio /
    fraction / percentage); it is **hidden** for mandatory-diagram families (the
    figure is always on) and for families with no diagram (ADR-0007).
  - make harder/easier swap along the topic difficulty ladder (ADR-0015).

## Consequences

- Clear separation of concerns; the engine is testable and reusable independent of
  HTTP or UI.
- Fixed ops are simple to validate deterministically and map cleanly to canonical-
  object transforms; they define the initial UI affordance set.

## Open

- Sync vs async generation, questions-per-request, latency (Q-K2).
- Whether to ship a CLI in the MVP (Q-K3).
- "Make harder/easier" semantics — resample vs blueprint-swap (Q-H2, Q-D2).
