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

