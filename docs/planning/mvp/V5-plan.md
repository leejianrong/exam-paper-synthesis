---
shaping: true
---

# V5 Slice Plan — Preview + export both PDFs

> **Slice V5 of `docs/planning/mvp/SLICES.md`.** Trustworthy printable output, WYSIWYG —
> the last rung that closes **L3 acceptance for Ratio**. Ground truth for R and
> Shape A: `docs/planning/mvp/SHAPING.md` (part **A7**; requirements **R5.2–R5.5**,
> **R8.6**). PDF engine: **ADR-0008** (HTML → headless Chromium / Playwright; this
> slice resolves its open Q-I2/Q-I3/Q-I5). Review/export gate: **ADR-0010**.
> Single-user/ephemeral/stateless-where-reasonable stance: **ADR-0001**. Engine
> purity + JSON-Schema-as-truth: **ADR-0016**. Schema contract:
> `schemas/canonical-question.schema.json` (v1.2.0 — **no schema change in V5**).
>
> **Demo goal:** the Worksheet tray (from V4) gains three actions — **Preview**,
> **Export worksheet PDF**, **Export answer-key PDF**. Preview renders the approved
> set as a printable HTML sheet (numbered questions, `[n]` marks, answer spaces,
> inline bar-model SVGs, KaTeX-typeset math). Export downloads two files: a
> **worksheet PDF** (questions + blank working space, no answers) and a **separate
> answer-key PDF** (the same questions with worked `solution_steps`, the typed final
> answer, and the M/A/B `marking_scheme`). **Preview matches print byte-for-layout**
> because both are produced from the *same* HTML/CSS/KaTeX document.

---

## The shaping decisions this slice locks in

1. **PDF engine = headless Chromium via Python Playwright** (ADR-0008), not
   WeasyPrint. `playwright` becomes a Python dependency of **`api/`** (not the
   engine); CI installs the Chromium browser. HTML → Chromium → PDF is the single
   print path, so preview and print cannot diverge.
2. **Renderers are pure functions in the engine.** `engine/exam_engine/render.py`
   exposes `render_worksheet_html(title, questions) -> str` and
   `render_answer_key_html(title, questions) -> str`. No browser, no network, no
   clock/RNG — same inputs give byte-identical HTML. The **impure** HTML→PDF
   (Chromium) step lives at the **API boundary** (`api/app/export.py`), keeping the
   engine UI/HTTP-agnostic (ADR-0016). The renderers read their vendored KaTeX/CSS
   assets **once at module import** (packaged data), so each `render_*` call itself
   does no per-call I/O and stays deterministic.
3. **Math = full KaTeX now, vendored self-contained.** KaTeX CSS + JS +
   auto-render + WOFF2 fonts are **committed into the repo**, never loaded from a
   CDN — deterministic, offline, and consistent with the no-LLM ethos. The renderer
   emits KaTeX-delimited math (`\(…\)` inline, `\[…\]` display); a small inline
   bootstrap script runs KaTeX auto-render on load, so **both** the preview (in an
   iframe/new tab) **and** Chromium (before the PDF snapshot) execute the *same*
   typesetting. Resolves ADR-0008 Q-I5.
4. **Worksheet and answer key are two separate documents** (resolves ADR-0008
   Q-I3): different routes, different PDFs, from two renderer functions sharing one
   markup/CSS core.
5. **New `POST /export/{preview|worksheet|answer-key}` routes, each receiving
   `{ title, questions }` from the client worksheet store.** This **supersedes the
   old `GET /worksheet/preview` idea** — after V4 the worksheet lives **client-side**
   (a Svelte store, ADR-0001), so there is no server session to `GET`; the client
   POSTs the approved set to be rendered. The API/engine stay stateless.

Settled defaults: **question order = the tray order**; **numbering = 1…N**;
**total marks on the sheet header = sum of `question.total_marks`**; **`$` is
currency, never a KaTeX delimiter** (dollar amounts inside math are written `\$`);
**A4, single column**.

---

## Scope

**In:**

**Engine — `engine/exam_engine/render.py` *(new, pure)*:**
- `render_worksheet_html(title, questions) -> str` and
  `render_answer_key_html(title, questions) -> str` — each returns a **complete,
  self-contained** HTML document (`<!doctype html>` … inlined `<style>`/`<script>`
  … body), sharing one markup/CSS core (see **The render contract** below).
- Reuse existing engine output verbatim: inline diagrams via
  `diagram.render_svg(part["diagram"])` (do **not** re-render or re-implement bar
  models); marks from `part["marks"]` / `question["total_marks"]`; worked steps from
  `part["solution_steps"]`; the typed final answer from `part["answer"]`; the M/A/B
  rows from `part["marking_scheme"]`.

**Vendored assets *(new, committed)* — `engine/exam_engine/assets/`:**
- `katex/katex.min.css`, `katex/katex.min.js`, `katex/auto-render.min.js`,
  `katex/fonts/*.woff2` (the KaTeX distribution), plus `print.css` (the worksheet /
  answer-key print stylesheet). Packaged into the wheel (hatch `force-include`).
  WOFF2 fonts are inlined as `data:` URIs into the emitted CSS so the document is
  truly host-free (works offline and inside a cross-origin iframe).

**Dependency + CI — (KAN-205):**
- Add `playwright` to `api/pyproject.toml` dependencies.
- CI installs Chromium for the PDF smoke tests: add a `uv run playwright install
  --with-deps chromium` step to the **Python tests** job in `ci.yml` (the `e2e.yml`
  job already installs Chromium).

**API — `api/app/` (thin, impure boundary only):**
- `api/app/export.py` — `html_to_pdf(html: str) -> bytes`: launch headless
  Chromium (Playwright), `set_content(html)`, wait for the KaTeX bootstrap to
  finish, `page.pdf(format="A4", print_background=True)`. This is the one place the
  browser/subprocess lives.
- `api/app/routes_export.py` — the three routes (see **API contract**).
- `api/app/models.py` — add `ExportRequest { title: str; questions: list[dict] }`.
- `api/app/main.py` — include the export router.

**Web — `web/src/` (KAN-148, rescoped):**
- `web/src/lib/api.ts` — `previewWorksheet(title, questions)` (→ HTML string) and
  `exportPdf(kind, title, questions)` (→ `Blob`), mirroring the existing
  `generate`/`editQuestion` error handling.
- `web/src/lib/WorksheetTray.svelte` — a **Preview / Export worksheet / Export
  answer-key** action row (disabled while the tray is empty). Preview opens the
  returned HTML in a new tab (or `<iframe srcdoc>`); export triggers a browser
  download of the PDF blob.

**Explicitly deferred (do NOT build here):**
- Remaining topic ladders + mandatory geometry figures → **V6**; `mathgen` CLI +
  sourced-object interchange → **V7** (the CLI's `export` subcommand reuses these
  same pure renderers + a local `html_to_pdf`).
- Any server-side worksheet persistence / saved-worksheet route — the store stays
  client-side and ephemeral (ADR-0001; still-open Q-A3).
- Multi-column / Typst layout, per-question answer-space sizing heuristics beyond a
  marks-scaled minimum, combined single-document export, and hand-edit-at-the-gate
  (ADR-0010 Q-H3).

---

## The render contract (HTML / CSS / KaTeX)

Implementers **must** emit exactly these class names so the CSS, tests, and e2e
selectors line up — do not invent divergent markup.

**Document shell (both renderers).** A full standalone doc: `<head>` inlines the
vendored KaTeX CSS (fonts as `data:` URIs) + `print.css`; a trailing `<script>`
inlines `katex.min.js` + `auto-render.min.js` and a bootstrap that runs
`renderMathInElement(document.body, { delimiters: [ {left:"\\(", right:"\\)",
display:false}, {left:"\\[", right:"\\]", display:true} ] })` on load. `$` is **not**
a delimiter (it is currency). Root element: `<main class="sheet worksheet">` or
`<main class="sheet answer-key">`.

**Shared structure:** `<header class="sheet-header">` → `<h1 class="sheet-title">`
(the title; answer key appends " — Answer Key") + `<p class="sheet-meta">` (e.g.
`<span class="field-name">` name/date line on the worksheet, `<span
class="field-marks">` total marks). Questions in `<ol class="questions">`; each is
`<li class="question">` (numbered via a CSS counter). Within a question, each part
is `<div class="part">` with `<span class="part-label">` (rendered only for
multi-part, e.g. `(a)`), `<div class="part-text">` (the question text, math
KaTeX-delimited), and a right-aligned `<span class="marks">[n]</span>`. A diagram,
when present, is `<figure class="diagram">` wrapping the inline `<svg>` from
`diagram.render_svg`.

**Worksheet-only:** after each part, `<div class="answer-space" aria-hidden="true">`
— a bordered blank working area whose `min-height` scales with the part's marks. No
solutions, answers, or marking scheme appear.

**Answer-key-only:** after each part, `<div class="solution">` containing
`<ol class="solution-steps"><li class="step">…</li></ol>`, a
`<p class="final-answer">` (label "Answer:" + the typed answer, math-delimited), and
`<ul class="marking-scheme">` whose rows are `<li class="mark">` with `<span
class="mark-type mark-{M|A|B}">M1</span>` (type + mark count) and `<span
class="mark-desc">`. No `answer-space`.

### Worksheet skeleton

```html
<!doctype html>
<!-- <head>: inlined KaTeX CSS (data-URI fonts) + print.css -->
<main class="sheet worksheet">
  <header class="sheet-header">
    <h1 class="sheet-title">Ratio Practice</h1>
    <p class="sheet-meta">
      <span class="field-name">Name: ______________</span>
      <span class="field-marks">Total: 18 marks</span>
    </p>
  </header>

  <ol class="questions">
    <li class="question">
      <div class="part">
        <div class="part-text">Aisha and Ben share \(\$100\) in the ratio \(2 : 3\). How much does Ben receive?</div>
        <span class="marks">[3]</span>
      </div>
      <figure class="diagram"><svg …>…</svg></figure>
      <div class="answer-space" aria-hidden="true"></div>
    </li>
    <!-- … one <li class="question"> per approved question, in tray order … -->
  </ol>
</main>
<!-- <script>: inlined katex.min.js + auto-render.min.js + renderMathInElement bootstrap -->
```

### Answer-key skeleton

```html
<!doctype html>
<!-- same <head> shell -->
<main class="sheet answer-key">
  <header class="sheet-header">
    <h1 class="sheet-title">Ratio Practice — Answer Key</h1>
    <p class="sheet-meta"><span class="field-marks">Total: 18 marks</span></p>
  </header>

  <ol class="questions">
    <li class="question">
      <div class="part">
        <div class="part-text">Aisha and Ben share \(\$100\) in the ratio \(2 : 3\). How much does Ben receive?</div>
        <span class="marks">[3]</span>
      </div>
      <div class="solution">
        <ol class="solution-steps">
          <li class="step">\(1 \text{ unit} = \$100 \div 5 = \$20\)</li>
          <li class="step">Ben \(= 3 \times \$20 = \$60\)</li>
        </ol>
        <p class="final-answer">Answer: \(\$60\)</p>
        <ul class="marking-scheme">
          <li class="mark"><span class="mark-type mark-M">M1</span><span class="mark-desc">Finds value of one unit</span></li>
          <li class="mark"><span class="mark-type mark-A">A1</span><span class="mark-desc">Correct amount with \$</span></li>
        </ul>
      </div>
    </li>
  </ol>
</main>
```

### Diagram embedding

The canonical object stores the diagram **spec** on `part["diagram"]` (or `null`).
The renderer calls the existing `engine.diagram.render_svg(spec)` and drops its
output verbatim inside `<figure class="diagram">`. The SVG is already self-contained
(explicit `viewBox`, integer coords, no external refs — see `diagram.py`), so it
prints and previews identically. No re-rendering, no `barModel.ts` involvement on
the export path.

### Print CSS (`assets/print.css`)

- `@page { size: A4; margin: 18mm 16mm; }`; base font `system-ui, sans-serif`, ~11pt.
- **Single column:** `.questions` is a plain vertical list (no `column-count`).
- **Numbered questions:** `.questions { counter-reset: q; list-style: none; }`;
  `.question::before { counter-increment: q; content: counter(q) ". "; font-weight: 700; }`.
- **Right-aligned marks:** `.part { display: flex; }` with `.marks { margin-left: auto; }`.
- **Answer space:** `.answer-space { border: 1px solid …; min-height: calc(<per-mark> * marks); }`
  (marks-scaled blank box; worksheet only).
- **Page-break behaviour:** `.question { break-inside: avoid; }` so a question is
  not split across pages where it fits; `page-break` between questions is natural.
- Rely on Chromium `print_background=True` for the diagram/answer-space fills.

Because preview and PDF are the **same document** (same inlined CSS + KaTeX),
"preview matches print" is structural, not a claim to re-verify per change.

---

## API contract

All three are `POST`, body `ExportRequest { title: string, questions: Question[] }`
(the approved set straight from the client worksheet store — engine/API hold no
session). Each route first `canonical.load`s every question (reject a
tampered/invalid object → **422**, mirroring `/edit/{op}`); an empty `questions`
list → **422** ("no questions to export"). No `created_at` stamping — export is a
read-only view of already-built objects.

| Route | Calls | Returns | Content-Type |
|---|---|---|---|
| `POST /export/preview` | `render_worksheet_html` | worksheet HTML | `text/html; charset=utf-8` |
| `POST /export/worksheet` | `render_worksheet_html` → `html_to_pdf` | worksheet PDF bytes | `application/pdf` + `Content-Disposition: attachment; filename="<slug>.pdf"` |
| `POST /export/answer-key` | `render_answer_key_html` → `html_to_pdf` | answer-key PDF bytes | `application/pdf` + `Content-Disposition: attachment; filename="<slug>-answers.pdf"` |

`<slug>` is a filesystem-safe slug of `title` (default "worksheet"). The engine
does the HTML; `html_to_pdf` (the only impure, browser-touching code) does the PDF —
the route just marshals, guards, and sets headers.

---

## Web affordances (KAN-148, rescoped)

`web/src/lib/api.ts` gains `previewWorksheet(title, questions)` (POST
`/export/preview`, returns the HTML text) and `exportPdf(kind: 'worksheet' |
'answer-key', title, questions)` (POST the matching route, returns a `Blob`).

`web/src/lib/WorksheetTray.svelte` gains an action row (hidden/disabled when
`items.length === 0`):
- **Preview** → fetch the HTML and open it in a new tab / `<iframe srcdoc>` so the
  document's inlined KaTeX bootstrap runs and the preview is the exact print doc.
- **Export worksheet** / **Export answer-key** → fetch the `Blob`, create an object
  URL, click a synthetic `<a download="<slug>[-answers].pdf">`, and revoke the URL.

No new store fields — it reads `$worksheet.title` and `$worksheet.items` and posts
them. **This is the rescope of the old `GET /worksheet/preview`:** the client owns
the worksheet, so it POSTs `{ title, questions }` to `/export/preview`.

---

## Schema / API impact

**No canonical-schema change** (v1.2.0 unchanged) — rendering is a *view* of the
closed object; nothing new is stamped on it. **New API surface:** three
`/export/*` routes + one Pydantic envelope. **New Python dep:** `playwright` in
`api/` only (the engine's deps stay `jsonschema` + `pyyaml`). **New committed
assets:** vendored KaTeX + `print.css` under `engine/exam_engine/assets/` (data,
not code deps). CI installs Chromium (see KAN-205).

---

## Implementation order

Cards map one-to-one to the pieces; build in this order (each depends on the prior):

1. **KAN-205 — Playwright dep + Chromium CI + vendored KaTeX assets.** Add
   `playwright` to `api/pyproject.toml`; add the Chromium install step to the
   `ci.yml` Python job; commit the KaTeX distribution + `print.css` under
   `engine/exam_engine/assets/` and wire hatch `force-include`. Unblocks everything.
2. **KAN-146 — Renderers.** `engine/exam_engine/render.py`
   (`render_worksheet_html` / `render_answer_key_html`), inlining the vendored
   assets (fonts as data URIs) and reusing `diagram.render_svg`. Pure — fastest to
   TDD against structure/content asserts. Depends on KAN-205's assets.
3. **KAN-147 — `html_to_pdf` + routes.** `api/app/export.py` (Chromium),
   `api/app/routes_export.py`, `ExportRequest` in `models.py`, router wired in
   `main.py`. Depends on the renderers + Playwright.
4. **KAN-148 — Web preview/export buttons (rescoped).** `api.ts` helpers +
   `WorksheetTray.svelte` action row + browser download. Depends on the routes.

---

## Tests

**Engine renderers — `tests/test_render.py` (pytest, pure, fast; no browser):**
- Returns a full doc (`<!doctype html>`), title in `.sheet-title`, one
  `.question` per input question in tray order, `[n]` marks present.
- Embeds the inline `<svg` for a question whose part carries a diagram; omits
  `<figure class="diagram">` when `part["diagram"]` is `null`.
- Math is KaTeX-delimited (`\(` appears); the KaTeX CSS/JS is inlined
  (`.katex` rule + `renderMathInElement` present); no `http`/CDN reference.
- **Worksheet** has `.answer-space` and **no** `.marking-scheme` / `.final-answer`;
  **answer key** has `.solution-steps`, `.final-answer`, `.marking-scheme` and
  **no** `.answer-space`.
- **Deterministic:** same `(title, questions)` → byte-identical HTML.

**API / PDF smoke — `tests/test_export_api.py` (httpx `TestClient`; Chromium):**
- `POST /export/preview` → 200, `text/html`, body contains `.sheet-title`.
- `POST /export/worksheet` and `/export/answer-key` → 200, `application/pdf`,
  non-empty body starting `%PDF`, `Content-Disposition: attachment`.
- Tampered/invalid question → 422; empty `questions` → 422.
- Chromium-dependent cases carry a marker so they skip cleanly when the browser is
  absent locally (CI always has it).

**e2e — `tests/e2e/export.spec.js` (Playwright):**
- Generate → **Approve** → tray shows the item → **Preview** renders the sheet
  surface (`.sheet-title`, a `.question`) → **Export worksheet** yields a non-empty
  `.pdf` download → **Export answer-key** yields a separate non-empty `.pdf`.

All existing gates stay green (pytest, ruff, mypy, eslint, svelte-check, vitest,
web build, e2e).

---

## Acceptance (from SLICES V5 — **completes L3 for Ratio**)

Full Ratio ladder → **generate across all 3 rungs** (easy/medium/hard) → **apply
each edit op** (regenerate / make-harder / make-easier / change-to-decimals /
toggle-diagram) → **approve at the gate** → **export a worksheet PDF *and* a
separate answer-key PDF**; the on-screen **preview matches print** (same document).
PDF export is smoke-tested (non-empty, `application/pdf`); the renderers are
asserted on structure and content. On merge, the site roadmap flips V5 → Shipped.
