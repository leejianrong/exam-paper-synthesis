---
shaping: true
---

# W1 Slice Plan — Document model + editor shell (rest of W1)

> **Slice W1 of `WYSIWYG.md`**, building on **W1a** (param roles + `set-cosmetic`, merged).
> Decisions: ADR-0021 (document model, edit tiers), ADR-0022 (Fly + Neon, tenant-scoped,
> social login). This plan covers everything in W1 *except* W1a, split into three
> sub-slices so each ends in a demo and the risky UI work sits on a proven backend:
>
> | Sub-slice | Title | Ends in (demo) |
> |---|---|---|
> | **W1b** | Document model, store, API, document PDF (no UI) | `curl` creates a document, saves blocks, exports **student**, **key** and **full** PDFs |
> | **W1c** | Editor shell (web) | Blank A4 page → **+** → pick topic/difficulty → templated question lands in the page; ops, rename-names popover, autosave, answer key at the bottom, PDF export |
> | **W1d** | "From my bank" in the picker | Bank question (sourced/hand-authored) inserted as a templated-style block |
>
> **Demo goal for W1 overall:** open the editor, type a title and an instruction line, add
> three generated questions (one made harder, one with renamed people), reload the page and
> everything is still there, then export a student PDF and an answer-key PDF that agree.

---

## Scope

**In:** the `document` model and schema (engine, pure); a tenant-scoped document store behind
an interface with a SQLite implementation; document CRUD + export API with a **stub auth
seam**; a document→HTML renderer (reusing the question renderers, one numbering across the
whole document, answer-key section); the web editor shell (TipTap/ProseMirror, A4 page,
**+** picker for *generated* questions, in-block ops, "Edit names" popover, autosave, key
region, export); the bank tab (W1d).

**Out (later slices):** free-form blocks, images, equations, tables in rich text (**W2**);
real login, Postgres, export quotas (**W3**); hardening (**W4**); numeric-parameter editing,
grouped shared-stem blocks, `.docx` (deferred cards); live browser pagination (the page is an
A4-width column with page-break markers; true pagination comes from Chromium at export).

---

## Document model (engine, pure)

A document is ProseMirror-style JSON stored as-is, so the editor and the renderer share one
structure. New module `engine/exam_engine/document.py` + `schemas/document.schema.json`
(JSON Schema stays the source of truth, ADR-0016).

```jsonc
{
  "schema_version": "1.0.0",
  "title": "P6 Ratio Review",
  "content": {                              // ProseMirror doc
    "type": "doc",
    "content": [
      { "type": "heading", "attrs": { "level": 2 }, "content": [{ "type": "text", "text": "Section A" }] },
      { "type": "paragraph", "content": [{ "type": "text", "text": "Answer all questions.", "marks": [{ "type": "bold" }] }] },
      { "type": "templatedQuestion",
        "attrs": { "block_id": "b_7f3a…", "question": { /* frozen canonical object */ } } }
    ]
  }
}
```

- **Allowed nodes in W1:** `doc`, `heading` (levels 1–3), `paragraph`, `bulletList`,
  `orderedList`, `listItem`, `text` (marks: `bold`, `italic`, `underline`), `hardBreak`,
  `pageBreak` (atom), and **`templatedQuestion`** (atom). Anything else is rejected, so W2's
  new node types are an explicit schema bump, not silent drift.
- **`templatedQuestion.attrs.question`** is a *frozen snapshot* of a canonical object
  (ADR-0021), validated through the existing `canonical.load` gate. `block_id` is a stable
  id (client-generated, server-validated unique per document) that links the block to its
  answer-key entry.
- **Helpers:** `validate_document(doc) -> list[str]` (path-pointed errors, same style as
  `schema.validate_object`), `questions_in_order(doc) -> list[dict]`,
  `total_marks(doc) -> int`, `empty_document(title)`.
- **Limits** (validated, so the server never stores unbounded input): ≤ 200 question blocks,
  ≤ 1.5 MB serialised content, ≤ 20 000 text characters per text node.

### Server-side verification of generated snapshots

A client could submit a hand-crafted object claiming `source_type: "generated"` with a wrong
answer. Documents are private to their owner in W1–W3, so the blast radius is the owner's own
paper, but the "engine-proven" badge must not be forgeable. `document.verify_snapshot(obj)`
(run on every save, for `source_type == "generated"` blocks): blueprint exists; `parameters`
pass the blueprint's parameter schema; `solver.validate` is ok; `solver.solve(parameters)`
answer equals the snapshot's answer (dividing by 10 for the decimals view); `marks` match the
blueprint. It deliberately does **not** compare wording (cheap, and a tampered sentence can't
change the proven answer). A failing block is rejected with a path-pointed 422.

---

## Rendering (engine, pure)

`render.py` gains:

```python
def render_document_html(title: str, doc: dict, *, mode: Literal["student", "key", "full"]) -> str
```

- **`student`** — the paper only: title, `Name: ____` / total-marks header, rich text, and the
  questions with answer space. **No solutions anywhere** (tested by absence of every answer
  string — the existing leak-guard idiom).
- **`key`** — the answer key only: a keyed list in document order, each entry
  `n. Answer: … / steps / marking scheme`, reusing `_render_solution`.
- **`full`** — student paper, a page break, then the **Answer Key** section. This is what the
  editor shows at the bottom and what "Export full copy (teacher)" produces.
- One continuous question number across the whole document. `print.css` already numbers
  `.question` with a CSS counter, so interleaved headings/paragraphs don't reset it; the
  renderer stops wrapping questions in a single `<ol class="questions">` and emits
  `<section class="question" data-block="…">` in place.
- A small ProseMirror→HTML serialiser for the allowed nodes (escaped text, whitelisted tags and
  marks; `pageBreak` → `<div class="page-break">`). Text goes through the same `_esc`/`_mathify`
  path as question text.

> **Why three modes, not "key at the bottom of the one PDF":** you will want to hand students
> a paper *without* the key. The key still lives at the bottom of the document in the editor
> (your design); export just lets you choose.

The existing flat `render_worksheet_html` / `render_answer_key_html` stay unchanged (the
classic Generate page and CLI still use them).

---

## W1b — Store + API (no UI)

> **Status: implemented** (branch `feat/w1b-documents`).

### Tenancy seam (stub auth)

`api/app/auth.py`: `current_owner(request) -> str` is a FastAPI dependency and the **only**
place identity enters.

- W1 stub: if `EXAM_DEV_AUTH=1`, the owner is the `X-Dev-Owner` header (default `dev`);
  otherwise **401**. The stub therefore cannot serve a public deployment by accident — a
  missing env var fails closed.
- W3 replaces the body with session-cookie → user id (Google/Microsoft/GitHub, ADR-0022);
  every route and the store already take `owner_id`, so nothing else changes.

### Store

`api/app/docstore.py`: `DocumentStore` protocol, every method taking `owner_id` first:
`create`, `get`, `list`, `save(…, base_version)`, `delete`. W1 ships `SqliteDocumentStore`
(stdlib `sqlite3`, path `EXAM_DOCS_PATH`, default `~/.exam_engine/documents.sqlite3`);
W3 adds a Postgres implementation behind the same protocol.

```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,            -- uuid4
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,          -- ProseMirror JSON
  total_marks INTEGER NOT NULL,
  version INTEGER NOT NULL,       -- optimistic concurrency
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX documents_owner ON documents(owner_id, updated_at DESC);
```

Every query filters on `owner_id`; a document owned by someone else is a **404** (never 403,
so ids can't be probed). Store-contract tests are written once and parametrised over
implementations, so W3's Postgres store must pass the identical suite.

### Routes (`api/app/routes_documents.py`)

| Route | Behaviour |
|---|---|
| `POST /documents` `{title?}` | new empty document (201) |
| `GET /documents` | list: `id, title, total_marks, updated_at` (no content) |
| `GET /documents/{id}` | full document + `version` |
| `PUT /documents/{id}` `{title, content, base_version}` | validate (`validate_document` + `verify_snapshot` + limits) → save; **409** if `base_version` ≠ stored (autosave from a stale tab never silently overwrites); returns new `version` |
| `DELETE /documents/{id}` | 204 |
| `POST /documents/{id}/export/{student\|key\|full}` | PDF (`html_to_pdf`); `Content-Disposition` slugged title + mode |
| `GET /documents/{id}/preview/{mode}` | the same HTML (for the in-editor true-print preview) |

`/generate`, `/edit/{op}` and `/blueprints/{code}/params` are reused unchanged for block
operations — they stay stateless and owner-agnostic. Export is wrapped in a `check_export_quota`
no-op hook (W3 fills it) and a process-wide semaphore (default 2 concurrent Chromium renders)
so a burst can't exhaust the Fly machine.

### Tests (W1b)

| Test | Asserts |
|---|---|
| `test_document_schema` | accepts valid docs; rejects unknown node types, bad heading level, duplicate `block_id`, > 200 questions, oversize content, invalid embedded canonical object (path-pointed) |
| `test_verify_snapshot` | genuine generated objects pass (seed sweep × all blueprints); a tampered answer, tampered `parameters` or fake `source_type: generated` is rejected; decimals view passes |
| `test_render_document` | one continuous numbering across interleaved headings; student mode contains **no** answer string / solution / marking scheme; key mode lists every question in order; full = student + page break + key; rich-text marks serialised, HTML in text escaped |
| `test_docstore_contract` (parametrised) | create/get/list/save/delete; **owner isolation** (owner B cannot get/list/save/delete A's doc → not-found); version increments; stale `base_version` → conflict |
| `test_api_documents` | CRUD happy path; 401 without `EXAM_DEV_AUTH`; cross-owner → 404; 409 on stale save; 422 on invalid content/tampered snapshot; 413/422 on oversize |
| `test_api_document_export` | preview HTML per mode; PDF smoke (skips without Chromium, same guard as export tests); semaphore limits concurrency |

---

## W1c — Editor shell (web)

> **Status: implemented** (branch `feat/w1c-editor`). The Svelte 5 node-view spike worked (no fallback needed). Findings: the API's `available_ops` hint is stripped from stored snapshots on save and re-attached on read (`ops.strip_document_hints` / `with_document_hints`), mirroring KAN-243; the `e2e` job runs the API with `EXAM_DEV_AUTH=1` and a temp `EXAM_DOCS_PATH`; classic e2e specs now start at `#/classic`.

**Stack:** `@tiptap/core` + `@tiptap/starter-kit` (headings, lists, bold/italic, history) +
`@tiptap/extension-underline`, used directly from a Svelte 5 component (no wrapper library
needed). The `templatedQuestion` node uses a custom node view that `mount()`s a Svelte
component into the node's DOM. **Risk and spike:** Svelte 5 `mount`/`unmount` inside a
ProseMirror node view (lifecycle on node updates/destroy) is the one unproven integration; the
first task of W1c is a throwaway spike proving it, before any other UI work.

### Screens / structure

- **Routes** (hash-based, no router dependency): `#/` documents list (new, open, delete,
  rename); `#/docs/:id` the editor; `#/classic` the existing Generate + tray page (kept until
  W1 is done, then removed in a cleanup card).
- **Page canvas:** grey desk, white A4-width page (210 mm at 96 dpi, centred), with the same
  typographic tokens as `print.css`. Title field above the first line. Page-break markers shown
  as dashed rules.
- **The "+" block:** a large dashed **+ Add question** area under the last block, and a smaller
  hover "+" between blocks. Click opens the **picker**: tabs **Templated** (W1) / **From my
  bank** (W1d) / **Free-form** (disabled, "coming soon", W2).
- **Templated picker:** topic × difficulty (reusing `topics.ts`), `Generate` produces three
  candidates via `POST /generate`; clicking one inserts it at the cursor/end. Candidates the
  teacher doesn't pick are simply dropped (no server state).
- **Question block (node view):** renders the question body (extracted from `QuestionCard` into
  a presentational `QuestionBody.svelte`, reusing `barModel.ts` for diagrams) plus a block
  toolbar: Regenerate · Make harder · Make easier · Decimals · Toggle diagram · Toggle bar view
  (driven by `available_ops`, as today), **Edit names** (popover built from
  `GET /blueprints/{code}/params`, saved via `POST /edit/set-cosmetic`), move up/down, delete.
  Every op replaces the block's `question` attr with the returned child (new snapshot, lineage
  intact).
- **Answer-key region:** below the page, a read-only "Answer key" section rendered from the
  current document (a Svelte component over `questions_in_order`), updating live. Shared numbers
  match the body because both use the same ordering.
- **Persistence:** debounced autosave (1 s) via `PUT` with `base_version`; status chip
  (Saved / Saving… / Conflict). On 409 the editor shows "This document changed in another tab"
  with *Reload* (no silent merge in W1). The document id lives in the URL, so reload restores
  everything from the server.
- **Export menu:** Student PDF · Answer key PDF · Full copy PDF, plus **Preview** (iframe of
  `GET /preview/{mode}` — the *true* print rendering, since the on-screen page is an
  approximation of it).

### Tests (W1c)

- **Vitest + Testing Library:** `QuestionBody` renders a ratio, a geometry and a shaded-fraction
  question; picker flow with a mocked API; block ops replace the snapshot; names popover builds
  fields from slot metadata and posts `changes`; autosave debounces and sends `base_version`;
  409 shows the conflict banner; document list actions; answer-key region order matches the
  body.
- **Playwright e2e (`tests/e2e/editor.spec.ts`)**, run in the existing `e2e` job (with
  `EXAM_DEV_AUTH=1` and a temp `EXAM_DOCS_PATH`): create a document → add a ratio question →
  make it harder → rename people → reload (still there) → export student PDF (200,
  `application/pdf`) and confirm the student preview contains no "Answer:" text while the full
  preview does.

---

## W1d — "From my bank" in the picker

The bank (E1–E3) holds sourced / hand-authored objects. For SaaS those are **private per
owner**, so:

- `bank.py` gains an `owner_id` column (migration adds it with default `'local'`, which the CLI
  keeps using — no behaviour change for `mathgen bank`); `Bank` methods take an optional
  `owner_id`. API: `GET /bank` (search, owner-scoped) using the same `owner_id` seam.
- Inserted bank items are frozen snapshots like generated ones, but render as
  **teacher-vouched** (a subtle "from my bank" tag, no engine-verified badge) and are *not*
  re-verified by `verify_snapshot` (they are `sourced`). The ops toolbar hides regenerate /
  harder / easier / decimals for them (none apply — `available_ops` is blueprint-driven).
- This slice is separable: if October runs short it moves after W3 without blocking anything.

---

## Decisions to confirm

1. **Export modes:** `student` / `key` / `full`, with the key always shown at the bottom of the
   editor page. (Alternative: a single full PDF only — rejected, you can't hand that to students.)
2. **Classic page stays** at `#/classic` until W1c ships, then is removed.
3. **Snapshot verification** checks the answer, not the wording (above).
4. **W1d separable:** bank tab can slip behind W3.
5. **No collaborative editing / merge** in W1: a stale save is a conflict the user resolves by
   reloading.

## Risks

- **Svelte 5 node views in ProseMirror** (spike first; fallback: render the block body with
  plain DOM from a small renderer and keep Svelte only for the toolbar/popover).
- **Screen vs print drift:** mitigated by the server-rendered Preview and by sharing CSS tokens;
  the PDF is always the authority.
- **Autosave conflicts** on a second tab: handled by `base_version` + banner, not merged.
- **October date:** W1b is the foundation for W3 (tenancy, store interface) and carries no UI
  risk; if W1c slips, W1b still unblocks W3 work in parallel.

## Acceptance (W1 done when)

1. `uv run pytest` green including all W1b tests; `npm` lint/check/unit/build green incl. W1c.
2. The e2e flow above passes in CI.
3. Manually: a three-question paper with a heading and an instruction paragraph survives a
   reload; student PDF has continuous numbering and no answers; key PDF lists all three with
   steps and marking schemes; a tampered `PUT` (wrong answer on a generated block) is rejected.
4. Every API call and store query is owner-scoped; a second `X-Dev-Owner` cannot see the first's
   document.
