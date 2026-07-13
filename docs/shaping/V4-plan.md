---
shaping: true
---

# V4 Slice Plan — Review gate + current worksheet

> **Slice V4 of `docs/shaping/SLICES.md`.** The human veto plus the collection
> surface. Ground truth for R and Shape A: `docs/shaping/SHAPING.md` (part **A8**;
> requirements **R4.1–R4.2**, **R5.1**). Review-gate policy: **ADR-0010**; marking:
> **ADR-0005**; single-user/ephemeral stance: **ADR-0001**. Schema contract:
> `schemas/canonical-question.schema.json` (v1.2.0 — **no schema change in V4**).
>
> **Demo goal:** each question card gains **Approve** and **Discard**. Approving a
> card adds it to a **Worksheet tray** (editable title, approved-question list with
> remove + up/down reorder, running total marks) and flips the card to an "Added"
> state with its Approve + edit buttons disabled. Discard removes a card from the
> review list only. Reload clears the tray — it is ephemeral.

---

## The shaping decisions this slice locks in

1. **Worksheet store is client-side** — a Svelte store in `web/`, not a server
   session. No new API route, no persistence (honors ADR-0001: single-user,
   ephemeral, stateless-where-reasonable). V5 export will POST the approved objects.
2. **Discard = remove from the review list only** (client-only). "Give me another"
   is the existing V3 **Regenerate**; Discard is not overloaded to regenerate.
3. **After approve, the card shows an "Added" state** with its Approve + edit actions
   disabled — no desync between the card and the tray copy, and it sidesteps ADR-0010's
   open hand-edit-at-the-gate question (Q-H3).
4. **Editable worksheet title lives in the V4 tray** (defaults to "Untitled
   worksheet"); it's consumed by V5 export.

Settled defaults: **total marks = sum of `question.total_marks`**; **reorder = up/down
buttons**; **dedup by `id`** (a question already in the worksheet can't be re-added).

---

## Scope

**In — pure frontend (`web/`), no API/engine/schema change:**

- **`web/src/lib/worksheet.ts`** — a `writable` worksheet store `{ title: string;
  items: Question[] }` plus actions: `add(q)` (dedup by `id`), `remove(id)`,
  `move(id, 'up'|'down')` (clamped at ends), `setTitle(s)`, `has(id)`, `clear()`; and
  a `derived` `totalMarks` = `sum(items[].question.total_marks)`.
- **`web/src/lib/types.ts`** — add `total_marks: number` to the `question` object type
  (currently omitted; needed to read marks cleanly per ADR-0005).
- **`web/src/lib/QuestionCard.svelte`** — add **Approve** + **Discard** controls to the
  gate-action row (`~line 66`), dispatching `approve` / `discard` events. Accept an
  `added: boolean` prop; when true, render an "✓ Added to worksheet" state and disable
  Approve + all edit buttons.
- **`web/src/lib/WorksheetTray.svelte`** *(new)* — subscribes to the store: editable
  title input, ordered approved-item list (index · short label · `[marks]` · remove ·
  up/down), total-marks line, and an empty state. No Preview/Export buttons yet (V5).
- **`web/src/App.svelte`** — import the store; wire `onApprove` (`worksheet.add` then
  mark the card added — derived from `worksheet.has(id)`) and `onDiscard`
  (`questions = questions.filter(q => q.id !== id)`); render `WorksheetTray` in `<main>`.

**Explicitly deferred (do NOT build here):**
- Preview + both PDF exports, and any `/export/*` route → **V5**.
- Any server-side worksheet route or persistence — the store is client-only and
  ephemeral. Saving/loading worksheets remains a deferred, still-open question (Q-A3).
- Remaining topic ladders + geometry → **V6**; CLI + sourced objects → **V7**.

---

## Schema / API impact

**None.** No canonical-schema change (the closed object already carries
`question.total_marks`; approval is client-side view state, never stamped on the
object). No new API endpoint — `generate` and `edit/{op}` are unchanged, and the
engine/API stay stateless/pure.

---

## Implementation order

1. **`types.ts`** — add `total_marks` (unblocks the marks sum + its test).
2. **`worksheet.ts`** store + unit tests (add/dedup, remove, move at boundaries,
   totalMarks, setTitle, has, clear). Pure logic — fastest to TDD.
3. **`QuestionCard.svelte`** — Approve/Discard events + `added` state; component tests.
4. **`WorksheetTray.svelte`** — render/reorder/remove/title/empty; component tests.
5. **`App.svelte`** — wire handlers + mount tray; the pieces come together.

---

## Tests (all gates must stay green: eslint + svelte-check + vitest + build + e2e)

- **`worksheet.test.ts`** (vitest): `add` dedups by id; `remove`; `move` up/down and
  clamped at both ends; `totalMarks` sums `total_marks` (incl. empty = 0); `setTitle`;
  `has`; `clear`.
- **`QuestionCard.test.ts`** (extend): Approve/Discard dispatch their events; with
  `added=true`, the "Added" state renders and Approve + edit buttons are disabled.
- **`WorksheetTray.test.ts`** (new): renders items + running total; remove and up/down
  mutate the store; title edit updates the store; empty state when no items.
- **e2e** (`tests/e2e/`, extend or add `worksheet.spec.js`): generate → **Approve** →
  item appears in the tray with correct total marks and the card shows "Added";
  **Discard** removes a different card; (optional) reload shows the tray empty.

---

## Acceptance (from SLICES V4)

Approve several Ratio questions across rungs → they appear in the tray with the
correct total marks; discard removes a card without persisting; the tray is ephemeral
(a reload clears it). No server state introduced; V5 export can read the approved set
straight from the client store.
