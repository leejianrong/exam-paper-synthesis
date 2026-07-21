# KAN-310 — Hard-ratio bar model: two view modes + toggle (Phase 3, not yet started)

> **Status (2026-07-22):** shaped + approved, agent **NOT yet spawned**. Card KAN-310
> is in `in_progress` on board 8 with a leased treehouse worktree reserved. This doc is
> the ready-to-run brief; resume by spawning one solo agent with the brief below.

## Context
Last card of EPIC-51 ("M8: Post-MVP diagram & difficulty polish"). The other six
(KAN-309/311/312/313/314/315) are merged to `main`. This is the headline fix.

**Problem:** for `ratio_hard` before/after bar models, coprime-ish ratio terms blow up the
common-unit count (before 7:1, after 8:9 → 63 tiny segments, unreadable).

**Approved design (PO, 2026-07-22):** implement BOTH options with a toggle.
- **"grouped" (DEFAULT, Option 3)** — draw at ORIGINAL ratio granularity + a brace/label
  giving a segment's unit-worth (e.g. "= 9u"). Always legible.
- **"sliced" (Option 1)** — common-unit grid with a HEAVY divider on the original ratio
  boundaries and a LIGHT divider (current weight) on sub-units.

**Mechanism:** a `view_mode` field (enum `["grouped","sliced"]`, default `"grouped"`) on the
`bar_model_before_after` diagram spec, flipped by a new `toggle-bar-view` edit-op (mirrors
`toggle-diagram`, gated by `available_ops`). Because the mode lives on the object, it carries
through preview + PDF export for free.

**Schema → 1.4.0:** additive minor bump covering BOTH the new `view_mode` AND the
already-merged `dashed` segment field (KAN-314). Update `SCHEMA_VERSION` in
`engine/exam_engine/canonical.py` and every pinned assertion (see below).

## Files in scope
- `engine/exam_engine/schemas/canonical-question.schema.json` — add optional `view_mode`
  to `bar_model_before_after`; version-history `$comment`.
- `engine/exam_engine/canonical.py` — `SCHEMA_VERSION = "1.4.0"`.
- `engine/exam_engine/diagram.py` — `_render_bar_model_before_after` (branch on view_mode) +
  keep `check_bar_model_before_after_consistency` passing for both modes.
- `web/src/lib/barModel.ts` — `renderBarModelBeforeAfter` (lock-step mirror of both modes).
- `engine/exam_engine/edits.py` — `toggle-bar-view` op + `available_ops` gating (only when the
  diagram is `bar_model_before_after`, i.e. ratio_hard).
- `web/src/lib/QuestionCard.svelte` — toggle button, shown when `available_ops` includes
  `toggle-bar-view` (KAN-243 pattern; no hardcoded blueprint check).
- ratio_hard solver diagram builder — set/allow the default view_mode.
- **Version pins to flip 1.3.0 → 1.4.0** (10 files + fixture): all
  `tests/test_generate_*_*.py` asserting `obj["schema_version"] == "1.3.0"`,
  `tests/fixtures/sourced/psle_2023_ratio.json`, and any `1.3.0`/`v1.3.0` ref in
  `tests/test_sourced_interchange.py`. (`grep -rn '1\.3\.0' tests/ engine/`; leave the schema's
  historical "geometry_figure added in schema 1.3.0" `$comment` as fact.)
- Tests: `tests/test_invariants_ratio.py` (both modes valid + consistent; answer is
  mode-independent), `tests/test_diagram_before_after.py` (grouped ≠ exploded cell count;
  sliced has heavy vs light divider strokes), `tests/test_edits.py` (toggle round-trip),
  `web/src/lib/barModel.test.ts` + `QuestionCard.test.ts`.

## Gates (all must pass)
`uv sync`; `npm --prefix web ci`; ruff check + format --check; mypy; `uv run pytest -q`;
`npm --prefix web run lint`/`check`/`test:unit`/`build`;
`HYPOTHESIS_PROFILE=nightly uv run pytest tests/test_invariants_ratio.py -q`. Sanity-generate a
7:1 → 8:9 ratio_hard question and confirm grouped is legible + toggle flips to sliced.

## How to resume
Spawn ONE `general-purpose` agent (solo — undivided attention) in a treehouse worktree, branch
`feat/kan-310-bar-model-view-modes` off fresh `origin/main`. The full agent brief was drafted in
the session on 2026-07-22 (worktree discipline, scope, mechanism, schema bump, tests, gates,
PR). Land policy: auto-merge on green + reviewed. Remember the branch-protection "BEHIND" +
`gh pr update-branch` step if anything else lands first.
