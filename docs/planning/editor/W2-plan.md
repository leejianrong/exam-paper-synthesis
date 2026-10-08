---
shaping: true
---

# W2 Slice Plan — Free-form blocks, images, equations, import

> **Slice W2 of `WYSIWYG.md`.** Where W1 let a teacher assemble a paper from engine questions,
> W2 lets them *write their own*: a free-form question typed straight onto the page, with
> images and equations, an answer they write themselves, and marks — plus the bank import
> screen deferred from W1d. Decisions: ADR-0021 (document model; free-form is a separate,
> teacher-vouched type), ADR-0022 (tenancy, private content). Document schema **1.0.0 → 1.1.0**
> (additive).
>
> | Sub-slice | Title | Ends in (demo) |
> |---|---|---|
> | **W2a** | Free-form question block | Type a question on the page, give it marks, write its answer in the key region, export student / key / full PDFs |
> | **W2b** | Images + equations | Paste a PNG diagram and a fraction into a free-form question; both survive reload and appear in the PDF |
> | **W2c** | Convert to free-form + bank import screen | Click **Convert to free-form** on an engine question and edit it freely; import canonical JSON into the bank from the editor |
>
> **Demo goal for W2:** write a two-line word problem with a PNG figure and an equation, set
> 3 marks, type the worked answer in the key, and export student + key PDFs that agree.

---

## Status

W2a (#139), W2b (#140) and W2c are built. Deviations from the plan as written: `POST /assets`
takes the image as the raw request body (`X-Filename` header) rather than multipart, to avoid a new
dependency; the document schema ended at **1.2.0** (1.1.0 = free-form, 1.2.0 = image + math); the
bank import request is `{ "objects": [...], "replace": bool }` (the editor flattens files and
pasted JSON, batching at 200 objects / 1.5 MB).

## Scope

**In:** the `freeformQuestion` node; `image` and equation nodes (usable anywhere in a document);
an owner-scoped asset store + upload API; per-block marks; an editable answer per free-form
question; renderer support (student / key / full, one numbering); **Convert to free-form**
(ADR-0021 tier 3); the bank **import** screen (canonical JSON → bank, review-gated).

**Out (later):** tables inside free-form text (until a real paper needs them), drawing tools,
`.docx`, object storage + CDN (W3/W4 swap behind the same interface), promote-free-form-to-bank
(a free-form question is not a canonical object — see Decision 3), real accounts (W3), the
inspector side panel and typography pass (cards EXA-93 / EXA-94, separate from W2).

---

## Document model (schema 1.1.0, additive)

New node types (allowed nowhere else — the schema stays a whitelist):

| Node | Where | Shape |
|---|---|---|
| `freeformQuestion` | top level | `attrs: { block_id, marks?: int ≥ 0, answer: AnswerDoc }`, `content: (paragraph \| heading? \| bulletList \| orderedList \| image)+` — **editable content**, typed on the page |
| `image` | free-form body, answer, and plain document body | atom, `attrs: { asset_id, alt, width_pct (10–100) }` |
| `math` | inline atom, anywhere text is | `attrs: { latex }` (≤ 500 chars) |

- **`answer`** is stored as an attribute: a restricted sub-document (`paragraph`, lists, text with
  `bold/italic/underline`, `math`, `image`), empty by default. It is *not* in the page flow — it
  is edited in the answer-key region (below) and written back to the node.
- **Marks** are optional (`null` = unmarked, no bracket printed); they add to `total_marks`
  alongside templated questions. `total_marks(doc)` = templated totals + free-form marks.
- **Question numbering** stays one continuous CSS counter across templated and free-form blocks.
- **Trust:** free-form blocks carry no verification of any kind and the renderer never prints
  an engine-verified claim for them (there is none on the page anyway — EXA-93).
- **Limits (validated):** ≤ 200 questions of any kind (templated + free-form combined), body
  ≤ 20 000 chars of text per block, ≤ 40 images per document, `latex` ≤ 500 chars; the existing
  1.5 MB content cap applies (images are *referenced*, never embedded in the JSON).
- `validate_document` also returns `referenced_assets(doc)`; the API checks every `asset_id`
  exists and belongs to the caller (the engine stays pure and storage-agnostic).

## Assets (W2b)

`AssetStore` protocol beside `DocumentStore` (owner first on every method): `put(owner, bytes,
mime, filename) -> asset`, `get(owner, id)`, `delete`, `usage(owner)`. W2 ships a SQLite BLOB
implementation (path `EXAM_ASSETS_PATH`, backed up with the rest); W3/W4 move bytes to object
storage behind the same protocol and run the same contract tests.

- `POST /assets` (multipart): **PNG or JPEG only** — verified by magic bytes, never the filename or
  client MIME; **SVG and GIF rejected** (script / animation risk); ≤ 2 MB per file, ≤ 4096 px per
  side (read from the header, no new dependency), ≤ 50 MB per owner. Returns `{ id, mime, width,
  height, bytes }`.
- `GET /assets/{id}`: owner-scoped (foreign id → 404), fixed `Content-Type` from the verified mime,
  `X-Content-Type-Options: nosniff`, long `Cache-Control` (ids are content-addressed UUIDs).
- **Export:** headless Chromium renders from `set_content` (no origin), so the renderer is given a
  resolver and inlines each image as a `data:` URI. `render_document_html(..., assets=resolver)`
  keeps the engine pure — the API supplies the bytes.
- Dev note: `<img src>` cannot send the dev identity header, so in dev the editor fetches assets
  through the same default `local` owner; W3's session cookie makes this a non-issue.

## Equations (W2b)

- **Input:** a toolbar **Equation** button and a click-to-edit popover: a LaTeX field with live
  KaTeX preview (the editor already loads KaTeX from `/render/katex.js`). No visual equation
  editor in W2 — teachers type LaTeX, with a small cheat-sheet of the 8 forms P5–P6 papers need
  (fraction, mixed number, ratio, percent, ×, ÷, square, π).
- **Render:** `math` serialises to `\(latex\)` (HTML-escaped; `\)` inside the source is rejected)
  and is typeset by the existing KaTeX bootstrap in the PDF. KaTeX's `trust` stays off, so
  `\href` / `\includegraphics` are inert; `throwOnError: false` shows a bad formula in red
  instead of breaking the page.

## Rendering (engine, pure)

- **student:** body (rich text, images, math), `[marks]` right-aligned, answer space sized by
  marks (the existing `.answer-space`).
- **key:** the question body again, then the *teacher-written answer* — or a quiet
  "No answer written yet" placeholder when empty (visible in the key only, so a blank is never
  mistaken for a verified answer).
- Shared numbering and marks totals with templated questions; page breaks unchanged.

## Editor (W2a/W2b)

- **+ Add question → Free-form** (the tab W1 greyed out) inserts an empty free-form block with the
  caret in it; the teacher just types. Images: toolbar **Image** (file picker), drag-drop, and
  paste from the clipboard (uploads, then inserts an `image` node). Width handle (10–100 %) and
  alt-text field in the node's popover.
- **Marks:** a small number field in the block's own toolbar (not on the page); the `[n]` appears
  on the page exactly as it prints.
- **Answer key region:** each free-form entry shows its question body read-only and an editable
  answer (a compact TipTap instance per entry, restricted to the answer schema) — this is the
  "blank space for the user to manually fill in the answer key". Edits write back to the node's
  `answer` attribute through a transaction, so autosave, undo/redo and conflict handling are
  unchanged. Templated entries stay generated and read-only.
- No status badges or tags on the page (EXA-93); free-form blocks have none to show anyway.

## Convert to free-form (W2c)

The ADR-0021 tier-3 escape hatch, available on any templated or bank block:

1. Body ← the stem and part text as paragraphs; MCQ options become a list; a table becomes a
   plain-text grid in W2c (a real table node waits for tables-in-free-form).
2. **Figures:** a bar-model / geometry / grid diagram is rendered to PNG by the same headless
   Chromium used for PDFs (`html_to_png` helper, ≤ 1 call per figure), stored as an asset and
   inserted as an `image` node. If rendering fails the conversion still succeeds and says
   which figure was dropped.
3. Answer ← the printed answer plus the worked steps as text; marks ← the question's marks.
4. The original block is replaced (undo restores it); the new block is plainly *not* engine-proven.

## Bank import screen (W2c)

- **Bank tab → Import…**: choose one or more `.json` files (a single canonical object or an array)
  or paste JSON. `POST /bank/import` runs every object through the canonical load gate; items
  import **unreviewed** (ADR-0019), a duplicate id reports instead of overwriting unless the
  user ticks **Replace existing**, and per-item path-pointed errors are shown (one bad item never
  blocks the rest). Owner-scoped like everything else; capped at 200 objects / 2 MB per request.
- Review stays a deliberate act (`mathgen bank review` today); an in-app review toggle is a later
  card, not W2.

## Tests

| Area | Asserts |
|---|---|
| `test_document` (schema 1.1.0) | accepts free-form / image / math; rejects: image outside whitelist positions, `latex` > 500 or containing `\)`, negative marks, body over the limit, > 40 images, unknown nodes; v1.0.0 documents still validate unchanged |
| render | numbering is one counter across templated + free-form; student has no answer text; key shows the answer or the "No answer written yet" placeholder; marks totals; math escaped; images inlined as `data:` URIs; a missing asset renders a visible placeholder, never a broken page |
| `test_assets` (contract, parametrised) | put/get/delete/usage; owner isolation; per-owner quota; magic-byte validation (PNG/JPEG accepted; GIF, SVG, `.png`-named HTML, truncated and oversize files rejected); `nosniff` + fixed content type |
| `test_api_documents` | save rejects an `asset_id` that does not exist or belongs to another owner; free-form content round-trips |
| convert | templated → free-form for every blueprint family (seed sweep): text preserved, marks preserved, figure becomes an asset, answer carried; MCQ options listed; the result validates |
| import | valid / invalid / duplicate / array / oversize; unreviewed on arrival; owner-scoped |
| web (vitest) | free-form node view; marks field; image upload + paste + failure; equation popover preview and bad-LaTeX state; answer editor writes back to the node; Convert action; import dialog |
| e2e | write a free-form question with an image and an equation, set marks, fill the answer, reload, student vs key previews, PDF export |

## Decisions to confirm

1. **Answer lives on the node** (edited in the key region), not as a second editable region on
   the page — keeps the page WYSIWYG and the key where you described it.
2. **PNG/JPEG only, 2 MB each**; SVG is rejected on security grounds. Diagrams come in as PNG, as
   you planned.
3. **A free-form question is not a bank object.** The bank holds canonical questions only, so
   "promote free-form to bank" stays deferred; W2c adds *import into* the bank, not *export from*
   free-form.
4. **Equations are typed LaTeX with live preview** for now; a visual editor is a later card.
5. **Assets in SQLite for now**, behind a protocol, so the October launch does not wait on object
   storage.

## Risks

- **Pasting images from Word/Google Docs** often arrives as HTML with `data:` or blob images; the
  paste handler must upload clipboard files first and drop foreign `<img>` sources.
- **Per-entry answer editors** (one TipTap instance each) — fine at 200 questions only if they are
  created lazily (on focus/scroll into view); built that way from the start.
- **Rendering a figure to PNG** reuses Chromium (cost + concurrency cap already exist) — conversion
  is a deliberate user action, rate-limited by the existing export slot.
- **October date:** W2a alone already gives teachers free-form questions; W2b/W2c can follow W3's
  tenancy work if time is short.

## Acceptance (W2 done when)

1. `uv run pytest`, web lint/check/unit/build, and the Playwright suite are green.
2. Manually: a paper mixing generated, bank and free-form questions (one with a PNG and an
   equation) survives a reload; the student PDF has continuous numbering, images and typeset math,
   no answers; the key PDF shows generated solutions, bank solutions and the teacher-written
   answers (placeholder where blank).
3. Uploading a renamed HTML/SVG file as `x.png` is refused; another owner's asset id is a 404.
4. Convert-to-free-form on a ratio question yields an editable block with its bar model as an image.
