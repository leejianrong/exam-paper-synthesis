# docs/

Documentation for Exam Paper Synthesis, organized so **living references** stay
at the root and **planning artifacts** are grouped **per initiative** under
`planning/` (so one planning effort never gets tangled with another).

## Living references (span all work)

| Path | What |
|------|------|
| [`ROADMAP.md`](ROADMAP.md) | Milestones → epics → stories (mirrors the Simple Kanban board) |
| [`SCHEMA.md`](SCHEMA.md) | The canonical question object, explained |
| [`DIFFICULTY.md`](DIFFICULTY.md) | The principled difficulty model |
| [`CONTEXT.md`](CONTEXT.md) | Glossary + decision register |
| [`adr/`](adr/) | Numbered architecture decision records (0001–0016) |
| [`syllabus/`](syllabus/) | The 2021 MOE P1–P6 syllabus (source PDF + LLM-readable md) |

## Planning (per initiative)

| Path | Initiative | Status |
|------|-----------|--------|
| [`planning/mvp/`](planning/mvp/) | The MVP — deterministic engine, slices **V1–V7** (PRD, SHAPING, SLICES, per-slice plans, `background/`) | shipped, tagged **v0.1.0** |
| [`planning/editor/`](planning/editor/) | The **question editor + persistent bank** — teachers author/customize questions into the canonical schema | planning |

Each initiative gets its own folder. Product descriptions, shaping, and
implementation plans for that initiative live together inside it.
