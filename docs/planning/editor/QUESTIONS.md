# QUESTIONS — grilling log (initiative: `editor`)

> Step A (grill + domain model) for the **question editor + persistent bank**
> initiative. Seed input: `docs/planning/editor/REQS.md`. Ground truth:
> `docs/SCHEMA.md`, `engine/exam_engine/schemas/canonical-question.schema.json`
> (**v1.4.0**), `docs/planning/mvp/PRD.md`, `docs/planning/mvp/V7-plan.md`,
> `docs/CONTEXT.md` + `docs/adr/0001…0016`.
>
> **Convention:** the owner answers **inline, directly beneath each question**,
> flipping `OPEN → ANSWERED`. Do not create a parallel answers file. Priorities:
> **P0** blocks the architecture · **P1** shapes a stage · **P2** takes a sensible
> default (marked `ASSUMED` with the default stated — correct it if wrong).
> Statuses: `OPEN` · `ANSWERED` · `DEFERRED` · `ASSUMED`.
>
> Answers distil into `docs/CONTEXT.md` (glossary + decision register) and new
> ADRs from **0017** onward.

---

## Standing conflicts this initiative creates (must be resolved, not ignored)

These are not questions yet — they are **facts** about the existing decisions of
record that this initiative contradicts. Each needs an amending/superseding ADR.

| # | Existing decision of record | What `editor` does to it |
|---|---|---|
| X1 | **ADR-0001**: single-user, **no server state**, "persistence of a per-user library is deferred (Q-A3 open)" | A durable bank **is** server state. Q-A3 must now be answered. |
| X2 | **PRD Out of Scope**: "Saved per-user library / persistence — the user-facing app is ephemeral" | Directly reversed. |
| X3 | **PRD Out of Scope**: "Hand-editing generated question text at the review gate (Q-H3) — deferred; in tension with canonical-object-as-truth and needs its own decision" | This initiative **is** that decision. See §B. |
| X4 | **CONTEXT glossary**: "**Question bank** — the persistent internal store of canonical objects produced by **the ingestion pipeline**" | The bank is now produced by **the editor**; the ingestion pipeline was dropped (ADR-0011). Definition must be rewritten. |
| X5 | **ADR-0016 §5**: "Durable global uniqueness (content hash or run-scoped UUID) is **reserved for a future saved library** — state is ephemeral in v1" | That future is now. The `id` scheme needs deciding (see C8). |
| X6 | **ADR-0011**: no ingestion tooling; the bank is "populated externally" | The editor is an *authoring* path into the bank — arguably in-project ingestion by hand. Is ADR-0011 amended, or is hand-authoring categorically different from OCR/parse tooling? |
| X7 | **CLAUDE.md convention**: "the engine stays UI/HTTP-agnostic; `generate()` is pure" | A store is I/O. Where the store lives is a P0 (see C2). |

---

## A. Scope & expressiveness — how far does "any question" go?

**A1 (P0) — Is the ceiling "anything schema v1.4.0 can already hold", or does the
schema grow in this initiative?**
REQS says text/answers/marking/multi-part "are already expressible". That is
broadly true but **not** unconditionally. Concrete gaps found in v1.4.0:
- `unit` is a **closed enum** (28 values). Missing plausible P5–P6 units: `cm/s`,
  `km/min`, `$/kg`, `l/min`, `hours` (only `h`), `days`, `weeks`, `months`,
  `years`, `km^2`, `mm^2`, `litres` spelled out, `apples`/`sweets`/`books`
  (only `marbles`, `items`, `people`, `units`).
- `answer_ratio` carries **no `unit`** field (fine) but also **no support for
  "3 : 4 : 5 in simplest form" vs unsimplified** distinction.
- **No MCQ answer type.** PSLE Paper 1 Booklet A is 15 MCQ items — there is no
  `options[]` anywhere in the schema (see A5).
- **No table / graph figure types.** PSLE uses tables, bar graphs, pie charts,
  line graphs, nets, tessellation. Only `bar_model`,
  `bar_model_before_after`, `geometry_figure`, `shaded_fraction`, `raster` exist.
- `syllabus.level` is a closed enum `P5 | P6` (see A3).
- Objects are **closed** (`additionalProperties: false`) — no escape hatch for
  anything not enumerated.
Which of these do you expect to hit in your first 50 past-paper questions?
**Status: OPEN**

**A2 (P0) — Is `raster` the only figure path for authored questions in v1, or must
the parametric types be authorable through a form?**
REQS leans raster. But a raster figure is a dead end: not re-renderable, not
editable, not consistency-checkable, and it makes `toggle-diagram` /
`toggle-bar-view` meaningless on that question. Options:
(a) **raster only** in v1 (cheapest; every authored figure is an image snip);
(b) **raster + authorable `bar_model` / `shaded_fraction`** (the two simple,
form-shaped specs) — `geometry_figure` needs a real drawing tool, so it stays
raster-or-nothing;
(c) full parametric figure editor for all types (expensive; a diagram editor is
its own product).
**Status: OPEN**

**A3 (P1) — Do you author outside P5–P6?** `syllabus.level` enum is `P5 | P6`.
Past-paper banks bleed into P4 revision and Sec 1 stretch material. If yes → a
schema change (and the MVP's "hold the P5–P6 Standard line" scope statement moves).
**Status: OPEN**

**A4 (P0) — What does the author put in `syllabus.skill_codes`, and is it queried?**
ADR-0016 §6 says skill codes are **provisional placeholders**, free strings,
"**carried, not queried** in v1 — no selection/filtering branches on their
values". A searchable bank changes that: if search filters on skill codes, they
become load-bearing data and remapping to MOE outcomes stops being "a mechanical
find/replace". Options: (a) editor requires a code from a curated per-topic list
(`content/syllabus/*.yaml`); (b) free text, best-effort; (c) optional, search uses
topic/subtopic only. Is the MOE P5–P6 syllabus doc (PRD note Q-M1) available now?
**Status: OPEN**

**A5 (P1) — MCQ: in or out?** If in, it's a new `answer` union member
(`answer_mcq` with `options[]` + `correct`) **and** a renderer branch **and** a
schema minor bump. If out, say so explicitly — it's the single most common PSLE
item type and its absence will be noticed immediately when you sit with a PDF.
**Status: OPEN**

**A6 (P1) — May an authored question be saved *incomplete*?** The schema requires
every part to carry `answer`, `marking_scheme`, `solution_steps`
(`marking_scheme: []` and `solution_steps: []` are legal — empty arrays pass).
So "text now, answer later" is *schema-legal* only if you fake an answer; there
is no null answer. Do you want (a) a draft state outside the schema that allows
incomplete objects (see C5), or (b) hard rule: nothing is saved until it validates?
**Status: OPEN**

**A7 (P2, ASSUMED) — Do you author full M/A/B mark schemes, or just marks-per-part?**
**Default assumed:** `marking_scheme` is **optional-in-practice** for authored
questions (empty array allowed, schema already permits it); the worksheet shows
`[n]` from `part.marks` regardless, and the detailed answer key simply shows
nothing extra when the scheme is empty. Authoring M/A/B for a past-paper question
you don't have the official mark scheme for would be fabrication.
**Status: ASSUMED**

**A8 (P2, ASSUMED) — `total_marks` vs the sum of `parts[].marks`.**
Verified: **nothing enforces** `total_marks == sum(parts[].marks)` — not the
schema, not `canonical.load`. The engine happens to set both from
`spec.marks`. **Default assumed:** the editor **auto-computes** `total_marks`
from the parts and makes it read-only, and an authoring lint (G3) flags any
stored object where they disagree.
**Status: ASSUMED**

**A9 (P2, ASSUMED) — Math notation in authored text.**
Verified convention (`render.py`): `\(…\)` inline / `\[…\]` display for KaTeX;
**`$` is currency, never a math delimiter** (`\$` inside math); ratios and money
are auto-wrapped by `_mathify`. **Default assumed:** the editor accepts the same
convention verbatim in `text`/`stem`/`step.text`, with a live preview so you see
mis-typed LaTeX immediately, and no new notation is invented.
**Status: ASSUMED**

---

## B. Trust model — engine-proven vs human-vouched

**B1 (P0) — What `source_type` and `created_by` does a hand-authored question get?**
This is the sharpest schema question in the initiative. Current enums:
`source_type ∈ {generated, sourced}`, `provenance.created_by ∈ {engine, ingested}`.
A question **you type in yourself** is neither generated (no blueprint/solver) nor
honestly "sourced" (a question you invented has no `origin`, `year`, `paper`, and
no `license` — yet the schema **requires** `source` + `license` when
`source_type:"sourced"`). Options:
(a) **reuse `sourced`** with `source.origin: "self-authored"` + `license:
"internal"` — zero schema change, but records a citation that is a fiction;
(b) **add `source_type: "authored"`** (+ `created_by: "authored"`) with `source`
/`license` **optional** — honest, a schema minor bump, and it makes the
three-way trust distinction (engine-proven / cited-external / self-authored)
queryable;
(c) keep two values but relax the `sourced` if-then so `source`/`license` may be
null.
Note your PDF-bank workflow is *genuinely* `sourced` (a real school paper, a real
year) — so (a) may cover your **first** use case and fail the **second**
("author any question I want").
**Status: OPEN**

**B2 (P0) — What is `validation.status` for an authored question, and what does the
UI/PDF say about it?** Enum is `pass | fail | unverified`. An authored answer is
not machine-verified; calling it `pass` launders human assertion as engine proof.
Options: `unverified` always; or `pass` with `checks: {answer_verified: false,
human_vouched: true}`. And **where does the honesty surface?** REQS says it "should
be explicit and honest in the product". Candidates: (i) a badge on the editor/bank
card only; (ii) also in the on-screen worksheet preview; (iii) also **printed on
the answer-key PDF** (e.g. a per-question marker or a footnote). Printing it on
the *student* worksheet would be noise — but the answer key is where a wrong key
does the damage.
**Status: OPEN**

**B3 (P0) — "Make similar": does it stay engine-proven, or fork to human-vouched?**
Two genuinely different products hide behind one phrase:
- **(i) Parametric re-solve** — edit the *parameters* of a generated question,
  re-run the **solver**, keep `source_type: "generated"`, keep the correctness
  guarantee. Requires a new engine entry point (today `pipeline.generate(code,
  seed)` only samples; there is **no** `solve_with_params(code, params)`), and it
  can *fail*: solver constraints (divisibility, non-degeneracy) are enforced in
  `sample()`, not fully in the declared param schema, so hand-entered params can
  produce a non-integer or degenerate answer. Behaviour on failure?
- **(ii) Fork to authored** — free-edit the text/answer/anything; the object
  **demotes** to human-vouched, keeping `provenance.parent_id` lineage.
Do we ship both, one, or one-then-the-other? (This is the deferred **Q-H3**.)
**Status: OPEN**

**B4 (P1) — When a generated question forks to authored, what happens to
`blueprint_code`, `parameters`, and `seed`?**
Verified: the schema's `if source_type == sourced then required [source, license]`
**does not forbid** a non-null `blueprint_code` — so a forked object *could* keep
its blueprint as a lineage hint and still validate. But that breaks the clean
reading "sourced ⇒ no blueprint/params" asserted in the PRD and CONTEXT. Options:
null them out (clean, loses the trail), keep them (informative, muddies the
invariant), or move them under `provenance` (schema change).
**Status: OPEN**

**B5 (P1) — Does an authored question pass through the review gate (ADR-0010)
before it can be exported?** Or does the act of authoring *imply* approval?
Argument for keeping the gate: the gate is the trust ritual, and authored
questions are the *least* trustworthy input in the system. Argument against: you
just typed it, approving your own keystrokes is theatre.
**Status: OPEN**

---

## C. Persistence — the biggest new piece

**C1 (P0) — Where does the bank physically live?**
Candidates:
(a) **SQLite single file** — canonical object as a JSON blob + extracted indexed
columns (level, topic, difficulty, source_type, total_marks, created_at) + FTS5
for text search. One file, no server, backup = copy the file, real queries.
(b) **Directory of JSON files, committed to git** — diffable, reviewable, versioned
alongside the code, trivially inspectable; no query engine (index rebuilt in
memory on load); merge conflicts are per-file.
(c) **Postgres** — real DB, needs a server, only pays off multi-user.
My recommendation is **(a) SQLite**, with a `bank export → JSONL` command so
(b)'s auditability is available on demand (G1). But note (b) has a real pull for
a repo whose whole culture is "the object is the truth and it's diffable".
**Status: OPEN**

**C2 (P0) — Which layer owns the store, given "the engine stays UI/HTTP-agnostic
and `generate()` is pure"?**
Candidates: (a) a **new workspace member `bank/` (package `exam-bank`)** depending
only on `exam-engine`, consumed by both `api/` and `cli/` — mirrors the `cli/`
precedent (V7 decision C1) and keeps the engine pure; (b) inside `engine/` as an
optional module (violates the purity convention as written); (c) inside `api/`
(then the CLI can't reach the bank without importing FastAPI — which V7 went out
of its way to avoid). I recommend **(a)**.
**Status: OPEN**

**C3 (P0) — Does the API become stateful?** ADR-0001 says "keep the API stateless
where reasonable". With a bank, either the API process owns the DB file (stateful
server; the web app is a thin client) or the **CLI** owns the bank and the web app
is read-only over it. Which? And does the answer differ local-dev vs hosted?
**Status: OPEN**

**C4 (P1) — Single-user forever, or is multi-user a near-term ambition?**
ADR-0001 defers multi-user. If the bank should not block it, the store module needs
a scoping seam (an `owner` column that is always `"local"` in v1). Cheap now,
expensive to retrofit. Worth it, or premature?
**Status: OPEN**

**C5 (P0) — Are bank records mutable, or append-only-with-lineage?**
ADR-0004 says **edits never mutate** — every edit yields a new object with
`parent_id` and a bumped `version`. But hand-authoring from a PDF is inherently
iterative: type, save, notice a typo, fix, save. Under strict ADR-0004 that's five
objects in the bank for one question. Proposal: **a `draft` is mutable and
save-over-writes; publishing to the bank freezes it; a published record is
thereafter immutable and further edits create a child.** That introduces a
draft/published lifecycle — **is that a bank-level concept or a schema field?**
(I'd argue bank-level: the canonical object should not carry workflow state.)
**Status: OPEN**

**C6 (P2, ASSUMED) — Delete semantics.** **Default assumed:** soft delete
(`archived` flag in the bank, hidden from browse, recoverable, never breaks a
`parent_id` chain). Hard delete only via an explicit `--purge`.
**Status: ASSUMED**

**C7 (P1) — Does the worksheet tray become persistent (named, saved worksheets),
or does it stay ephemeral and merely gain "pull from bank" as a source?**
REQS's success criteria only require the **bank** to be durable ("browse/search
that bank and pull questions into a worksheet and export"). Saved worksheets are a
separate, bigger feature (naming, listing, reopening, ordering). In or out?
**Status: OPEN**

**C8 (P0) — What is a bank record's identity?**
Today `id = f"{blueprint_code}:{seed}"` for generated, `f"{parent_id}+{op}"` for
same-sample edits (ADR-0016 §5), and ADR-0016 explicitly **reserves** durable
global uniqueness for "a future saved library". Authored questions have no
blueprint and no seed, so they need a different scheme entirely. Also: two
generated questions with the same `(code, seed)` collide by construction — fine
in-session, **fatal as a primary key**. Options: (a) content hash; (b) UUIDv4/v7
minted at save; (c) keep the human-readable `id` as a label and give the bank its
own surrogate key. And **who mints an authored object's `id`** — the editor UI, the
API, or the bank on insert?
**Status: OPEN**

**C9 (P0) — Raster assets: inline `data:` URIs, or a separate asset store?**
V7's decision **S1** chose a self-contained base64 `data:` URI, explicitly to keep
the object self-contained and the PDF single-file (matching the vendored-KaTeX
precedent). That does not scale to a bank: a 150 KB PDF snip becomes ~200 KB of
base64 **inside** every stored object; 300 questions ≈ 60 MB of JSON, every list
query dragging image bytes it doesn't need. Alternative: a content-addressed asset
store with `asset_ref: "asset://<sha256>"`, resolved at render time — but then the
canonical object is **no longer self-contained** and `mathgen export` of a bank
object needs a resolver, weakening the interchange property V7 just proved.
Options: (a) data URIs, accept the bloat; (b) asset store + resolver, accept the
loss of self-containment; (c) **hybrid** — asset store internally, data URIs
inlined on export/interchange. I lean (c), which costs a resolver seam but keeps
both properties.
**Status: OPEN**

---

## D. Search & browse

**D1 (P1) — What must be searchable on day one?** Proposal: **filters** on level,
topic, subtopic, difficulty, cognitive level, `source_type`, marks range, plus
**substring/FTS over question text**. Anything else (skill code, lever, "has
figure", date, tag) — needed now or later?
**Status: OPEN**

**D2 (P0) — Where do bank-only metadata (tags, folders, draft state, archived,
personal notes) live?** The canonical object is **closed**
(`additionalProperties: false`) so they cannot be stashed inside it without a
schema change. Two coherent answers: (a) **bank-side columns/tables** — keeps the
canonical object interchange-clean, but `bank export → JSONL` loses them (they'd
need a sidecar); (b) **add a schema field** (e.g. `tags[]`, or a
`workspace: {}` open sub-object) — survives export, but puts workflow state in
the interchange contract. I lean (a) with an explicit sidecar in the export format.
**Status: OPEN**

**D3 (P2, ASSUMED) — Sort order + pagination.** **Default assumed:** newest-first
by created/updated, simple offset pagination, no infinite scroll. Fine for
hundreds of records.
**Status: ASSUMED**

**D4 (P2, ASSUMED) — Duplicate detection in the bank.** The MVP does cheap
in-session dedup by `(blueprint_code, seed)` + param hash (PRD G4). **Default
assumed:** the bank warns on an exact content-hash duplicate at save time and does
nothing cleverer; embedding-based near-dup stays deferred.
**Status: ASSUMED**

---

## E. The editor itself (UX shape)

**E1 (P0) — Form-based, raw-JSON, or hybrid?**
(a) **Structured form** — a field per schema node, add/remove parts, dropdowns for
the closed enums (unit, answer type, difficulty). Guided, hard to make invalid,
slow to build for a 15-node nested schema, and it caps you at what the form
exposes.
(b) **Raw JSON/YAML editor** with live schema validation + path-pointed errors +
live preview. Maximally expressive (anything the schema allows), cheap to build,
and *you are the first user* — you already know the schema. Terrible for a
teacher who isn't you.
(c) **Hybrid** — form for the common 90% (stem, parts, text, marks, answer type +
value + unit, syllabus tags), with a "raw JSON" escape hatch for the rest
(figures, mark schemes, odd cases).
Given REQS says *you* are the first user and the goal is speed-through-a-PDF-bank,
(b) is the fastest path to value and (c) the honest destination. Which do we build
first, and does the answer change what "expressive and flexible" means?
**Status: OPEN**

**E2 (P1) — Live preview: reuse `POST /export/preview`?** That endpoint already
returns the full styled worksheet HTML from canonical objects (V5), so an
authoring preview is nearly free **via the API**. But the web app has no full
worksheet renderer in TS (only `barModel.ts` mirrors the diagram) — so preview is
a server round-trip, and the **CLI-only / offline** story loses live preview.
Accept the round-trip? And should the preview show worksheet view, answer-key
view, or both side by side?
**Status: OPEN**

**E3 (P0) — How does a figure snipped from a PDF get into the editor?**
This is the workflow's real bottleneck. Options: **paste from clipboard**
(Cmd/Ctrl-V of a screenshot → base64 in-browser — by far the fastest for your
described loop), file upload, drag-and-drop, or a path reference. Also: is any
processing needed (downscale to a max width, convert to PNG, strip EXIF) before
storing? And does `alt_text` get authored by hand (schema **requires** it on
`diagram_raster`) or auto-filled with a placeholder?
**Status: OPEN**

**E4 (P1) — Does the editor validate-as-you-type, or validate-on-save?**
Schema errors are path-pointed (`CanonicalValidationError`). Continuous validation
needs the validator in the browser (a JS JSON-Schema lib against the same schema
file — a **second implementation of the gate**, a mirror-drift risk like the
`barModel.ts`/`diagram.py` pair) or a debounced server call. Which?
**Status: OPEN**

**E5 (P2, ASSUMED) — Where does the editor live in the UI?** **Default assumed:**
inside the existing Svelte SPA as a third view alongside generate + tray (routes
or tabs), not a separate app.
**Status: ASSUMED**

**E6 (P2, ASSUMED) — Unsaved-work protection.** **Default assumed:** autosave the
in-progress draft to the bank as a `draft` record (C5) plus a beforeunload guard.
Losing a hand-typed multi-part question with a figure would be genuinely painful.
**Status: ASSUMED**

---

## F. Slicing — the smallest first useful version

**F1 (P0) — What is the thinnest end-to-end slice you'd actually use?**
My proposal for the first slice: **author a single-part, no-figure question in the
editor → it validates → save to the bank → see it in a bank list → pull it into
the existing tray → export a mixed worksheet + answer key.** That exercises every
new seam (editor, validation, store, browse, tray integration, export) with the
least new surface, exactly like V1 did for Ratio. Figures, multi-part,
make-similar, and search come after. Agree, or is a figure non-negotiable in slice
one (since "any question" mostly means "any figure")?
**Status: OPEN**

**F2 (P1) — Does the CLI get bank commands (`mathgen bank add|list|get|export`)?**
The V7 principle is that everything works headlessly. A CLI `bank add < q.json`
also gives you a bulk-import path for questions hand-written in a text editor,
and makes the bank testable without a browser. Cheap. In or out?
**Status: OPEN**

**F3 (P1) — Does this initiative have an acceptance target like the MVP's L3 demo?**
What is "done" for the editor initiative in one sentence, testable? (e.g. "20
past-paper questions authored from a real PDF, banked, searchable, and exported as
a mixed worksheet + answer key".)
**Status: OPEN**

---

## G. Non-functional, testing, risk

**G1 (P1) — Backup / portability of the bank.** With a single SQLite file, a
corrupt file or a bad migration loses hundreds of hand-typed questions.
Proposal: `bank export` → JSONL (+ asset sidecar per C9), committed to git or
backed up on a schedule; `bank import` restores. Required in the first slice or a
fast-follow?
**Status: OPEN**

**G2 (P0) — Schema evolution against a durable bank.**
Until now, schema changes were free: nothing was stored. The moment the bank
exists, every stored object is pinned at the `schema_version` it was written with,
and `canonical.load` validates against **one** current schema. Policy needed:
(a) **migrate on read** (a version→version upgrade chain in the engine/bank);
(b) **migrate in place** on upgrade (a one-shot batch, plus backup);
(c) **refuse** to load older versions (unacceptable once you've typed 200
questions);
(d) keep multiple schema versions on disk and validate each object against **its
own** version.
This deserves its own ADR — it is the durable cost of persistence, and §A implies
the schema *will* move (units, MCQ, level, `authored`).
**Status: OPEN**

**G3 (P1) — What replaces the invariant test as the correctness authority for
authored questions?** The project's verification policy is "every blueprint ships
an independent seed-sweep invariant test that re-derives the answer a different
way". For an authored question there is **nothing to re-derive** — a human
asserted the answer. So: (i) what proves the *editor* correct (schema round-trip,
store round-trip, lint rules, and a corpus of authored fixtures?), and (ii) do you
want an **authoring lint** — cheap machine checks that catch real authoring
mistakes without claiming to verify the maths? Candidates: `total_marks` == sum of
parts; every part has a non-empty answer; the final answer's unit is plausible for
the question's topic; the last solution step mentions the answer value; a
`geometry_figure` passes the existing consistency check; `marks` sum of a
mark scheme == `part.marks` when a scheme is present.
**Status: OPEN**

**G4 (P2, ASSUMED) — Concurrency.** **Default assumed:** single-user, single
process; no locking beyond SQLite's default. Multi-tab editing the same draft is
last-write-wins and not defended against.
**Status: ASSUMED**

**G5 (P2, ASSUMED) — Licensing/redistribution of banked past-paper content.**
ADR-0011 already records that you hold the rights and this is internal, no public
redistribution. **Default assumed:** unchanged — the bank is local/internal, and
`license` on each sourced record is the audit trail.
**Status: ASSUMED**

---

## H. Language (feeds the CONTEXT glossary)

**H1 (P1) — Confirm the vocabulary.** I propose these new/revised terms for
`docs/CONTEXT.md`. Correct any that read wrong to you — these words will be used
consistently in every downstream doc:
- **Authored question** — a canonical object a human typed into the editor
  (contrast **generated** = blueprint+solver, **sourced** = cited external
  material). Depends on B1.
- **Engine-proven vs human-vouched** — the two trust levels for an answer key: a
  solver computed it, vs a person asserted it.
- **Question bank (revised)** — the durable, searchable store of canonical
  objects, populated by the **editor** (and by generation), replacing the
  ingestion-pipeline definition (X4).
- **Bank record** — a stored canonical object plus bank-side metadata (state,
  tags, timestamps) that is deliberately *not* part of the canonical object.
- **Draft vs published** — a mutable in-progress record vs a frozen bank entry
  (C5).
- **Make similar** — the authoring path that starts from an existing question;
  splits into **parametric re-solve** (stays engine-proven) and **fork to
  authored** (becomes human-vouched) per B3.
- **Authoring lint** — non-authoritative machine checks on an authored object
  that catch mistakes without claiming to verify the maths (G3).
- **Asset store** — the content-addressed store for raster figure images, if C9
  goes that way.
**Status: OPEN**

---

## Answered / resolved

*(nothing yet — answers land inline above and are summarised here as they close)*
