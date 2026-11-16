# Organise and create: settings, folders, the + New wizard (shaping)

Owner feedback from the P7–P8 acceptance run (2026-11-16):

1. Hide the Classic generator. Add a **Settings** page; "Show the Classic generator" is off by
   default.
2. **Folders** to organise papers. An exam session is typically one Paper 1 Booklet A, one
   Booklet B and one Paper 2; a folder keeps such a set together, alongside drafts.
3. A **+ New wizard**: a new folder, a set of all three papers in the current folder, a single
   paper, a template, and (last) a completely blank paper. Use the project's design system with
   Material Design 3 **chips** for the choices.
4. Compare the generated PDFs with real papers (waiting on the owner's sample papers: none are
   in the repo, and SCHEMA-FIT.md's three 2025 prelims were never committed).

## Decisions (owner, 2026-11-16)

- **Free folders with an exam-set helper.** A folder holds any papers (drafts, practice, old
  copies). Nothing blocks a second Booklet A. The wizard's *Exam set* makes one of each paper
  in a folder, and a folder shows which of the three it has (a chip per paper part).
- **Exam set asks generated or empty.** Generate at P5 / P6 (today's one-click papers, with
  placeholders where content runs out), or empty starters (cover and sections only).
- **Settings live on the account**, server-side per owner, so they follow the teacher across
  devices. Unknown keys are refused; defaults apply when nothing is stored.
- **"Folders"**, not workspaces: the word teachers already use for files.
- **Design**: extend the existing token layer in `web/src/app.css` (one typeface, Inter,
  EXA-94). M3 is used for the chip *component* (assist / filter / suggestion chips: shape,
  height, state layers, selected state) mapped onto our tokens, not as a second theme.

## Shape

**Settings (O1).** `GET /settings` → `{classic_generator: false}` (defaults merged with what is
stored); `PUT /settings` with a partial object, validated against a fixed key set (booleans
only for now). Stored per owner in a `settings` table (SQLite + Postgres, same protocol as the
other stores), erased with the account and included in *Download my data*. Web: `#/settings`
page (one switch today), a Settings link in the masthead; the *Classic generator* link shows
only when the setting is on, and `#/classic` while it is off says so with a button to turn it
on.

**Folders (O2).** `folders` table `(id, owner_id, name, created_at, updated_at)`; documents gain
a nullable `folder_id` (idempotent `ADD COLUMN` on both stores; existing papers are unfiled).
API: `GET/POST /folders`, `PATCH /folders/{id}` (rename), `DELETE /folders/{id}` (its papers
become unfiled, never deleted), `PATCH /documents/{id}` `{folder_id}` to move; `POST
/documents` and `POST /documents/generate` accept `folder_id`. Owner-scoped like documents
(a foreign folder is a 404). The paper list shows folders (with the exam-set chips: *Booklet
A · Booklet B · Paper 2*, filled when the folder has one) and *Unfiled*; a paper can be moved
between folders.

**+ New wizard (O3).** One dialog from **+ New**, choices as M3 chips / option cards, in this
order: *New folder*; *Exam set* (all three papers into the current or a new folder; then
*Generate at P5 / P6* or *Empty starters*); *Single paper* (pick the paper, then generate at a
level or start it empty); *Template* (the starter templates); and last, *Blank paper*. Keyboard
operable, Escape closes, the result opens in the editor (one paper) or the folder (a set).

**Real-paper comparison (O4, blocked).** When the owner adds sample PDFs (git-ignored, e.g.
`samples/real-papers/`), compare page by page: cover, instructions, numbering, marks
placement, Ans: lines, working space, margins and tally boxes, options layout, and file the
gaps as cards.

## Slices

| # | Slice | Depends on |
|---|---|---|
| **O1** | Account settings API + store + Settings page; Classic generator off by default and hidden | — |
| **O2** | Folders: store, API, moving papers, the folder view on the paper list | — |
| **O3** | + New wizard with M3 chips (folder, exam set, single paper, template, blank) | O2 |
| **O4** | Compare generated PDFs with real papers | owner's samples |



## O2 as built (API)

- **Store.** Folders live in the `DocumentStore` (same database as the papers), on both
  backends behind the one protocol: `create_folder`, `list_folders` (each with its `papers`
  count, ordered by name case-insensitively then age), `rename_folder`, `delete_folder`,
  `move(owner, doc_id, folder_id | None)`, and `create(..., folder_id=None)`. Document records
  (get, list, save, move) carry `folder_id`. `erase_owner` erases folders too.
- **Schema, no migration tool.** `CREATE TABLE IF NOT EXISTS folders (id, owner_id, name,
  created_at, updated_at)`; the nullable `documents.folder_id` is added idempotently — Postgres
  `ALTER TABLE documents ADD COLUMN IF NOT EXISTS folder_id TEXT` in the boot DDL (under the
  existing advisory lock), SQLite checks `PRAGMA table_info(documents)` and adds the column
  when missing. Inserts now name their columns, so an old file (column appended last) and a new
  one behave alike. Existing papers are unfiled (NULL). No foreign key: deleting a folder
  unfiles its papers in the same transaction.
- **Rules.** Names are trimmed, 1–80 characters (else 422); duplicates are allowed. A foreign or
  unknown folder is `FolderNotFound` → 404, for rename, delete, move and create/generate with
  `folder_id`. Filing a paper locks the folder row for the write (SQLite `BEGIN IMMEDIATE`,
  Postgres `FOR SHARE`), so a concurrent delete cannot leave a paper in a vanished folder.
- **Moving is not an edit.** `PATCH /documents/{id}` `{folder_id: string | null}` changes only
  the folder: content, `version` and `updated_at` stay, so an editor open on the paper keeps
  saving without a 409. It returns the paper's summary record (no content).
- **API.** `GET /folders` → `{folders: [{id, name, created_at, updated_at, papers}]}`;
  `POST /folders {name}` → 201; `PATCH /folders/{id} {name}` → 200; `DELETE /folders/{id}` →
  204. Router `routes_folders.py`; envelopes `FolderRequest`, `MoveDocumentRequest` in
  `models.py`.
- **Account.** *Download my data* adds `folders.json` (and a `folders` count in
  `account.json`); `DELETE /account` erases folders through `erase_owner`.
- **Tests.** Store contract tests in `tests/test_docstore.py` (SQLite, and Postgres when
  `EXAM_TEST_DATABASE_URL` is set), including an old-schema SQLite file gaining the column;
  API tests in `tests/test_api_folders.py` (also run on Postgres with
  `EXAM_TEST_BACKEND=postgres`).

## O2 as built (web)

- **List.** `DocumentList.svelte` loads papers and folders together and groups them with
  `folders.ts` `groupByFolder` (folders in the API's order, papers in list order; a paper whose
  folder is gone counts as unfiled). Each folder is a `FolderSection.svelte` region; then an
  *Unfiled* heading (only when folders exist, so a teacher without folders sees the old list).
  Loading, empty-folder and every-paper-is-filed states; API errors go to the page's alert.
- **Exam-set chips.** M3 filter chips on our tokens (32 px, 8 px corners, outline when off,
  `--verify-soft` fill and a leading check when on). They report state, so they are not
  buttons. **The part comes from the paper's title** (`paperPart`: "Booklet A", "Booklet B",
  "Paper 2"), because the list response carries no content: the templates and the generator
  title papers "Paper 1 Booklet A" / "P6 Paper 2", so a teacher's set lights up, but a paper
  renamed without those words counts as none. The reliable signal is the cover page's `paper`
  field ("Paper 1 (Booklet A)"); the smallest fix is a derived `paper_part` on each listed
  summary, computed server-side from the cover (title as fallback) when the store lists papers
  (it already reads the whole row). Not built: it touches both stores.
- **Folder actions.** *+ New folder* opens an inline name field (Enter creates, Escape
  cancels); *Rename* edits the name in place (stays open on a 422); *Delete* shows an inline
  confirmation saying how many papers move to Unfiled and that none is deleted. Focus returns
  to the button that opened each field; a polite status line announces what happened.
- **Move.** `MoveMenu.svelte` on each paper row (only when folders exist): a menu button with
  `menuitemradio` items (the folders, then Unfiled; the current place is checked). Arrow keys,
  Home/End, Escape (back to the button) and Tab; clicking outside closes it. No drag-and-drop.
  New papers inside a folder wait for the + New wizard (O3).
- **Tests.** `folders.test.ts` (part detection, grouping), `DocumentList.test.ts` (grouping,
  chips, keyboard move, move to Unfiled, rename incl. failure, delete with confirm, loading),
  and `tests/e2e/folders.spec.js` (create a folder, move a paper in, chip fills, delete the
  folder, the paper is unfiled and its version unchanged).

## O3 as built (EXA-127)

- **One entry point.** *+ New* on "Your papers" opens `NewWizard.svelte` (a modal dialog). It
  replaces the list's *+ New paper* button, the template buttons, the *Generate a paper* form and
  the inline *+ New folder* field. Choices, as M3 option cards (outlined, 12 px corners, a
  leading icon on `--verify-soft`, the 8 % / 12 % state layer), in order: *New folder*, *Exam
  set*, *Single paper*, *Template*, *Blank paper*. Single choices inside a step (where the exam
  set goes) are M3 filter chips over native radios; levels are compact cards ("Generate at P5",
  "Generate at P6", "Empty starters" / "Start it empty").
- **Steps.** New folder: name → create → the dialog closes and the folder's heading is scrolled
  to and focused. Exam set: *Put them in* a new folder (default name "P6 exam set", editable) or
  an existing one → *Next* → *Generate at P5 / P6* (`POST /documents/generate` per template with
  `folder_id`) or *Empty starters* (`POST /documents` with `template` + `folder_id`). The folder
  is created first; if that fails nothing else is tried. The three papers are made **one at a
  time** (each generation is a full solve; three at once would only contend for the server) with
  a row each (waiting / making / made / failed). Each made paper is added to the list as it
  arrives. If all three succeed the folder is shown; if any fails the dialog stays, says which
  part failed and why, names the parts that were kept, and offers *Try … again* (only the failed
  parts, into the same folder) and *Show the folder*. Single paper: pick Booklet A / B / Paper 2
  → optional folder (a select, "No folder" by default) → generate at a level (the fill report
  goes to the editor's banner as before) or start it empty; opens in the editor. Template: the
  templates from `GET /papers` (today the same three starters, shown with sections, questions,
  marks and time) → opens in the editor. Blank paper: opens in the editor.
- **Current folder.** There is no "current folder" on the list (all folders are shown expanded),
  so none was invented. Instead each folder has **+ New in folder**, which opens the same wizard
  with that folder as its home: the dialog says "Papers go in X", the exam set preselects it,
  the single-paper folder select defaults to it, and Template / Blank paper file into it. From
  the top *+ New* nothing is assumed: the exam set defaults to a new folder and the rest are
  unfiled unless the teacher picks a folder.
- **Keyboard and focus.** Arrow keys (and Home / End) move between the option cards of a group,
  wrapping; Enter / Space picks. Escape steps back (or closes on the first step; while a set is
  being made it does nothing). A back arrow is shown from the second step on. Tab and Shift+Tab
  wrap inside the dialog. Closing returns focus to the button that opened it (*+ New* or the
  folder's *+ New in folder*); after a folder or set is made, focus goes to that folder's heading
  instead, so the teacher lands on the result. Cards are named by their title, with the
  description as `aria-describedby`; progress changes are announced in a polite status line.
  At phone width the dialog fills the screen less a 16 px gutter and the cards stack.
- **`paper_part` (from #210's review).** `exam_engine.document.paper_part(doc)` returns
  `booklet_a` / `booklet_b` / `paper_2` / `None` from the cover page's `paper` field ("Paper 1
  (Booklet A)", "Paper 2"), falling back to the title when there is no cover or it names none.
  Both stores add it to every document record (`_record` / `_doc_record`), so `GET /documents`,
  the `PATCH` move summary and the full records all carry it. The cheapest correct place: the
  list query already selects the whole row (`SELECT *`), so this costs one JSON parse per paper
  on SQLite (Postgres hands back the decoded JSONB) and no extra query or column; the route
  layer could not do it because the list records it gets have no content. A stored column
  would need a migration and a backfill for no measurable gain at today's list sizes.
  `folders.ts` `partOf` prefers `paper_part` and falls back to the title regex only when a
  summary lacks the field.
- **Tests.** `tests/test_paper_part.py` (engine), a store contract test in
  `tests/test_docstore.py` (SQLite and Postgres), an API test in `tests/test_api_folders.py`;
  `NewWizard.test.ts` (each choice, both exam-set branches, existing vs new folder, partial
  failure and retry, folder failure, keyboard, Escape / Back, Tab wrap), `DocumentList.test.ts`
  (opening, focus return, *+ New in folder*, the exam set filling the chips), `folders.test.ts`
  (`partOf`); e2e `folders.spec.js` (+ New → Exam set → new folder → Empty starters → three
  papers, three chips filled, survives a reload). The specs that used the old list controls go
  through the wizard with `helpers.js` `newBlankPaper` / `newFromTemplate` /
  `generateSinglePaper`.
- **Open question.** *Template* and *Single paper → Start it empty* make the same paper today,
  because the only templates are the three exam papers. Template becomes distinct when other
  starters (a worksheet, a topic test) are added; until then the owner may prefer to drop one.

## Not in this round

Nested folders, sharing folders between teachers, drag-and-drop, bulk export of a whole exam
set (a natural follow-up once folders exist).

## O1 as built (2026-11-16)

- `api/app/settings.py`: `DEFAULTS = {classic_generator: False}`, `merged` (stored known keys
  over the defaults), `check_patch` (unknown key or wrong type → `UnknownSetting`, 422 at the
  API); `SqliteSettingsStore` (a `settings` table in the documents database) and
  `pgstores.PgSettingsStore` pass the same contract tests (`tests/test_settings.py`).
- `GET /settings`, `PUT /settings` (partial); `settings.json` in the account export; erased with
  the account.
- Web: `settings.ts` store loaded once a session exists; `SettingsPage.svelte` (an M3-style
  switch on our tokens); the paper list's masthead shows *Settings* always and *Classic
  generator* only when on; `#/classic` while off renders `ClassicOff.svelte`. The e2e specs that
  use the Classic page turn the setting on first (`helpers.openClassic`);
  `tests/e2e/settings.spec.js` covers the flow.

