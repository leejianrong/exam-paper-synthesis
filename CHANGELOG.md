# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Summary of work since 0.1.0 (see `docs/ROADMAP.md` and git history for detail).

### Changed

- **Section headers, marks and the Ans: line print as on real papers (EXA-139).** A section header
  is now a sentence built from its questions ("Questions 16 to 20 carry 1 mark each.", or for a
  structured section "The number of marks available is shown in brackets [ ] …"), then the
  instructions and "(5 marks)" at the right, then a rule; the "Section A" label and the grey
  "Questions 1–15 · 20 marks · Multiple choice" line are gone (a teacher's own title still prints).
  Booklet B is two sections, Q16–20 at 1 mark and Q21–30 at 2 marks. Each section chooses where
  its [n] marks print (new `marks_placement`, document schema 1.13.0): by default nowhere in
  multiple-choice and short-answer sections (the header gives them) and after the Ans: line in
  structured ones; the editor's section bar has a "Marks shown" choice. The Ans: line is short
  (55 mm) and right-aligned.
- **Papers print black on white, like a photocopied school paper (EXA-135).** Figures were blue
  line art with pale-blue fills, pie sectors differed only by blue/grey tone, marks were red,
  question numbers grey, working space a grey box and answer-key panels green. Now every figure
  (geometry, bar models, fractions, charts, solids, number lines, cube stacks) uses black lines
  and white or light-grey fills from one grey palette (`exam_engine/palette.py`, mirrored in
  `print.css`); pie sectors are white, outlined and labelled; bar series differ by grey tone and
  line series by dash pattern; numbers and marks print in black; the working space is plain
  white space; the key's panels are light grey with a black rule. The editor shows the same.

### Fixed

- **Paper 1 Booklet B numbers on from Booklet A (EXA-134)**: Q16–30, as in every real P6 paper,
  instead of starting again at 1. A new paper setting, the first question number
  (`settings.number_from`, document schema 1.12.0, a "First Q" field in the editor), moves the
  section ranges, the student paper, the answer key and the editor's numbering; the Booklet B
  template sets it to 16. Older papers still number from 1.
- **Figure labels sit clear of the lines (EXA-136).** Side lengths printed over a rectangle's
  edge, a height's length over the height, and vertex letters over right-angle marks, angle arcs
  and their own corner. Geometry figures now put side lengths outside the edge (a height that has
  no room gets its length turned to run beside it), angle values inside the angle past the arc,
  and vertex letters outside the corner; the canvas grows to keep every label on it. A test reads
  every generated and hand-built figure and fails if any label touches a line or another label.
- **An empty placeholder never prints by accident (EXA-137).** A generated Booklet A printed
  two unwritten placeholders as grey boxes with `Ans:` lines. Exporting a paper with
  placeholders nobody has written is now refused with the question numbers; the editor lists
  them and offers *Fill them* (goes to the first) or *Print anyway*. Printed anyway, an empty
  placeholder in a multiple-choice section is a numbered blank gap with no `Ans:` line.
- **A fraction option never reads "4/1" (EXA-133)**, and **working steps typeset their maths**
  in the editor's answer key and on the Classic page (algebra showed raw `\\(3x\\)`, EXA-131).

- **The student paper no longer prints worked bar models (EXA-132).** A `bar_model` /
  `bar_model_before_after` figure is the worked solution: it showed units and values such as
  "1 unit = $36" and, on before–after ratio questions, the answer itself ("Devi = $216"). Found
  by comparing generated papers with real P6 prelims. Bar models now print only in the answer
  key (also when the key hides the question text); *Convert to free-form* puts them in the
  answer, not the question; the editor labels them "printed in the answer key only".
- **A selected block is never replaced (EXA-129).** One click on the cover selects the whole
  block; the toolbar's Section / Blank page / Page break then replaced it, and so did the first
  keystroke — after *Write my own* the selection could be left on the cover, so typing into the
  new placeholder wiped the cover. Toolbar inserts now go after a selected block, typing or
  Enter starts a paragraph after it, and a swap leaves the caret in the block it changed.
- **Maths prints in KaTeX's fonts again; ∠ and π in the paper's own faces (EXA-130).** Every
  inlined KaTeX `@font-face` carried `format("woff2")` twice, so the browser dropped its src
  and all maths (fractions, algebra) printed in the host's Times. ∠ and π are outside Inter's
  latin subset and fell back to the host's Noto fonts (boxes where none is installed). Now: the
  KaTeX faces load, π is a one-glyph face cut from Inter's greek subset and ∠ one from
  KaTeX_Main, all declared under the Inter family; a real-Chromium test asserts a PDF embeds
  only Inter and KaTeX fonts.

### Added

- **Booklet A fills all fifteen questions (P8e batch 3, EXA-145)** — five new 1-mark P5
  questions of the kinds real Booklet A papers open with: round a 4-digit number to the
  nearest ten, hundred or thousand; the greatest or smallest of four decimals; the greatest or
  smallest of four fractions; a km / kg / ℓ measurement in m / g / mℓ; and how many minutes
  between two clock times. Each has its own wrong-answer reasons, and in multiple choice the
  "which is the greatest" options are the four listed numbers. A generated P5 or P6 Paper 1
  Booklet A now has no placeholders (was 3 and 2). Two new topics, Measurement and Time. The
  five are not on a harder / easier ladder.
- **The + New wizard has four choices**: the *Template* choice made the same papers as *Single
  paper → Start it empty*, so it was dropped until other starters exist.
- **The + New wizard (O3, EXA-127)** — *+ New* on "Your papers" opens one dialog in place of
  the old *+ New paper* button, template buttons, generate form and *+ New folder* field. Pick
  *New folder*, *Exam set* (Booklet A, Booklet B and Paper 2 into a new or existing folder,
  generated at P5 / P6 or as empty starters, with progress for each paper; if one fails it says
  which, keeps the others and offers to try it again), *Single paper* (generated or empty,
  optionally in a folder), *Template* or *Blank paper*. Each folder has *+ New in folder*, which
  opens the wizard with that folder as the home for what it makes. Keyboard operable (arrow keys
  between options, Escape steps back or closes, focus stays in the dialog). Each listed paper now
  carries a `paper_part` read from its cover page, so the exam-set chips stay right after a
  rename.
- **Folders on "Your papers" (O2, web, EXA-126)** — the paper list is grouped by folder, then
  *Unfiled*. Each folder shows its papers and an exam-set chip for *Booklet A · Booklet B ·
  Paper 2*, filled when the folder holds that paper (read from the paper's title). Make a
  folder with *+ New folder*, rename it, or delete it (it asks first; its papers move to
  Unfiled, none is deleted). A paper's *Move* menu files it in a folder or back in Unfiled,
  by mouse or keyboard.
- **Folders (O2, API)** — papers can be kept in folders (one exam set, drafts, practice).
  `GET/POST /folders`, `PATCH /folders/{id}` (rename), `DELETE /folders/{id}` (its papers
  become unfiled, never deleted), `PATCH /documents/{id}` `{folder_id}` to move a paper (not an
  edit: content and version unchanged), and `folder_id` on `POST /documents`,
  `POST /documents/generate` and every listed paper. Owner-scoped (a foreign folder is a 404),
  names 1–80 characters, duplicates allowed. Stored in the document store on SQLite and
  Postgres; the `folder_id` column is added idempotently, so existing papers are unfiled.
  *Download my data* includes `folders.json`; deleting the account erases folders. The web UI
  follows.
  The SQLite upgrade (adding `documents.folder_id`) works going forward only: code from before
  O2 inserts 8 positional values and cannot create papers in an upgraded file; Postgres is
  unaffected.
- **Editor + SaaS (W1–W4)** — WYSIWYG document editor (ProseMirror-style document
  model, schema `1.5.0`), templated and free-form question blocks, question bank,
  assets, owner-scoped accounts with Google/Microsoft/GitHub OAuth, Postgres
  stores, per-account export quotas, production image and Fly launch config.
- **Server-drawn diagrams and answer types (T1–T7)** — `chart`, `solid`,
  `number_line`, `panels`, `expression` answers, `cube_stack`, and the
  `statistics_chart` and `volume` ladders (canonical schema now `1.12.0`).
- **Litres print as ℓ** (and millilitres as mℓ), as on PSLE papers: question text, working,
  answer key, Ans: line units, multiple-choice options and the editor's unit picker. The stored
  unit codes stay `l`/`ml` (no schema change; goldens unchanged); a paper saved with the old
  `18 l` option still verifies (and keeps printing `18 l` until that question is swapped or
  the paper regenerated: option text is stored). The glyph is a one-glyph Inter face cut from Inter's latin-ext
  subset (`inter-ell-*.woff2`), so the one-typeface rule holds.
- **Multi-part polish (P8c review)** — `speed_structured` asks about ~100 different trips
  (was 24): whole speeds 30–90 km/h, the journey back in whole or half hours; the
  `ratio_structured` working no longer repeats "1 unit = n" when the ratio difference is one unit.
- **Starter templates get a cover page** — starting a paper from an empty template
  (Paper 1 Booklet A/B, Paper 2) now adds the same prefilled cover a generated paper gets
  (subject, paper and instructions); the level is left blank for the teacher, since an empty
  template has none. A starter paper's student print therefore shows the cover in place of
  the sheet header, and the Preview counts the cover as page 1; its page list names cover,
  blank and rough-work pages.
- **Settings, and the Classic generator hidden by default (O1)** — a Settings page
  (`#/settings`, linked from Your papers) saved on the account (`GET/PUT /settings`, SQLite and
  Postgres, included in *Download my data* and erased with the account). Its first switch,
  *Show the Classic generator*, is off by default: the link is hidden and `#/classic` says the
  page is turned off, with a button to turn it on.
- **Better multiple-choice distractors (P8b follow-up)** — a solver may give its own
  "common wrong answers" (`distractors(params, solution)`: values in the answer's own
  quantity and unit, each with the reason pupils give it), and every one of the 39 ladder
  solvers does: forgot to divide, the mean of the two speeds, the capacity of the whole
  tank, worked left to right, the change instead of the total... The answer key's marking
  scheme says why each wrong option is tempting. The answer is never left guessable from
  the options (between two others evenly or by a factor, or the odd one out); money
  distractors keep their cents and whole wrong answers print without ".0".
- **Coverage growth (P8e, batch 2: 1-mark content)** — four new ladders, 1 / 2 / 3 marks
  each: `whole_numbers` (P5: order of operations; a remainder to interpret; excess and
  shortage), `decimals` (P5: × / ÷ by a whole number; unit cost; change from shopping),
  `rate` (P5: rate × time; unitary rate; tiered car-park / bicycle charges) and `algebra`
  (P6: evaluate an expression; a story expression in $; solve a simple equation from a
  story). Every answer is numeric, so all twelve convert to multiple choice. P6 Booklet B
  and Paper 2 now fill completely; Booklet A fills 13 / 15 (P6) and 12 / 15 (P5).
- **Coverage growth (P8e, batch 1)** — an `average` ladder at P5 (1 / 2 / 3 marks):
  the average of a set of numbers; a missing score or the money left from an average;
  the average when a child joins or leaves a group. Also in the web topic picker.
- **Paper format (P1–P7)** — icon toolbar, working space and `Ans: ____ unit`
  lines, marks placement, multi-part free-form questions, and paper structure:
  section blocks with derived question ranges / marks and an authored target, paper
  time, and Paper 1 Booklet A/B and Paper 2 starter templates; and answer-key options: hide the question text, omit the M/A
  breakdown, leave chosen questions out (numbers kept), mirrored in the editor's key
  view (document schema `1.7.0`); and the marking margin ("Do not write in this space")
  per section, on by default for short-answer and structured sections, plus the tally-box
  component (document schema `1.8.0`); and a tally box on every printed page of a paper
  with a marking section, summing the marks of the questions on that page (an inline paginator
  measures the paper and prints explicit pages, so the PDF and the Preview agree; a question
  taller than a page has its blank working space trimmed rather than clipped; a multi-part
  question may break between its parts); the editor's Preview shows the page count, each
  page's questions and tally, and any trimmed-space warning; and a cover page (school, exam,
  level, subject, paper, date, instructions to candidates, Name / Class / Register No. lines,
  and a "For examiner's use" table derived from the sections; it replaces the paper's header)
  and blank pages ("This page is intentionally left blank." or rough work), each on a page of
  its own and left out of the answer key (document schema `1.9.0`).
- **One-click paper generation (P8a)** — paper templates as engine content
  (`content/papers/*.yaml`: Paper 1 Booklet A/B, Paper 2, with their real slot layouts;
  the P4 starter templates now come from them via `GET /papers`), a pure, seeded
  `paper.generate_paper(template, level, seed)` (each blueprint once per paper, topics
  spread, every section exactly at its marks target, single-part stand-ins for Paper 2
  Section B, placeholders for what the content can't fill yet, an honest report),
  `POST /documents/generate`, the "Generate a whole paper" form on the papers list, the
  report banner and a placeholders-to-write count in the editor (document schema `1.10.0`:
  a question's `slot`). Also fixed: a paper opening on a cover or section block started
  with that block selected, so the first click and keystroke could replace it.
- **Multiple choice for Booklet A (P8b)** — `mcq.to_mcq` turns a generated question with a
  numeric or fraction answer into four-option multiple choice: the correct option is the
  engine's answer, the distractors are the worked solution's intermediate values (stopping a
  step early), near misses, halving/doubling and place-value slips (fractions: the unshaded
  part, shaded : unshaded, off-by-one). The paper generator fills Booklet A's slots this way
  (P6: 8 of 15, P5: 7 of 15 with today's content); `verify_snapshot` checks the correct option
  reads exactly as the re-solved answer, so these stay engine-proven. Options now print as a
  (1)–(4) grid after the figure, with real units (cm², °); edit ops are not offered on a
  multiple-choice copy.
- **Keep / swap / lock (P8d)** — per-question actions on a generated paper: "Another like
  this" (same slot and marks, same topic: a sibling blueprint or a new seed), "Another
  topic" (same marks, a topic the paper uses less), "Write my own" (an empty placeholder
  keeping the slot's marks), "Fill with a question" / "Another topic" on a placeholder, a
  lock toggle (Booklet A questions stay multiple choice through swaps), and
  "Regenerate unlocked" in the editor's top bar, which refills every unlocked generated
  question and empty placeholder and never touches locked questions, bank questions or
  anything the teacher wrote. Pure engine transforms (`paper_swap.swap_question`,
  `regenerate_unlocked`) that keep every P8a rule; `POST /documents/{id}/swap` and
  `POST /documents/{id}/regenerate` (owner-scoped, optimistic concurrency like PUT)
  (document schema `1.11.0`: a question's `locked`).
- **Multi-part blueprints (P8c, first three)** — a blueprint can now produce a shared stem
  with lettered parts, each with its own answer, marks, marking scheme and worked steps
  (YAML `parts:`; the solver returns `answers`, one per part; `BlueprintSpec.is_multipart` /
  `part_count`). Three Paper 2 Section B blueprints, each with (b) building on (a):
  `ratio_structured` (5 marks), `speed_structured` (4) and `volume_structured` (5).
  `document.verify_snapshot` re-solves and checks every part's label, answer and marks;
  a multi-part question is offered only whole-question edits (regenerate, edit names); the
  editor draws generated multi-part questions and their key entries with the engine's
  renderer. The paper generator fills Paper 2 Section B with these first (real multi-part
  questions, not stand-ins; P6 now 3 multi-part + 9 single-part stand-ins) and never puts them
  in short-answer or MCQ slots; the report counts them per section. Keep / swap / lock and
  "regenerate unlocked" follow the same order (multi-part first, then stand-ins). No schema change (the
  canonical schema already allowed parts).

## [0.1.0] — 2026-07-25

First tagged checkpoint: the **MVP is complete**. A deterministic,
blueprint-driven engine generates syllabus-aligned Singapore **P5–P6 Standard**
math questions with provably-correct step-by-step answer keys and accurate
diagrams — no LLM in the generation path. The schema-gated canonical question
object is the single source of truth. Delivered across vertical slices V1–V7
(see `docs/planning/mvp/SLICES.md`), plus a post-MVP polish wave.

### Added

- **Engine (V1–V3)** — pure, deterministic `generate(blueprint_code, seed)`
  pipeline (sample → validate → solve → validate → assemble → schema-validate,
  bounded retry); canonical object builder + JSON-Schema load gate; structured
  engine errors. Full **Ratio** ladder (`ratio_easy` / `medium` / `hard`).
- **Answer keys & diagrams (V2)** — typed answers, ordered M/A/B marking schemes,
  and `solution_steps` from solver intermediates; `bar_model` spec builder +
  consistency check + deterministic spec→SVG renderer.
- **Edit operations (V3)** — object→object, re-validated transforms:
  regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram,
  driven by topic difficulty ladders.
- **Review gate + worksheet tray (V4)** — client-side (Svelte), ephemeral
  current-worksheet store with approve/discard, reorder, dedup, and total marks.
  No server state.
- **Preview + PDF export (V5)** — pure `render_worksheet_html` /
  `render_answer_key_html` (vendored self-contained KaTeX + inline SVG + print
  CSS); headless-Chromium `html_to_pdf` at the API boundary;
  `POST /export/{preview,worksheet,answer-key}`. Completes **L3 acceptance for
  Ratio**. Engine assets and content/schema data ship as package data (wheel).
- **Remaining topic ladders (V6)** — Fractions, Percentage, and Speed ladders
  (easy/medium/hard) with goldens; `shaded_fraction` mandatory figure; fully live
  topic × difficulty selector.
- **PSLE figure geometry (V6b)** — `geometry_angle` and `geometry_area` ladders on
  a general `geometry_figure` diagram system with strictly-PSLE curated parametric
  templates and auto-selected π (schema **v1.3.0**).
- **Headless CLI (V7)** — `mathgen generate/edit/export` driving the pure engine
  with no web/API (proves the engine is UI/HTTP-agnostic); own ~15-line Chromium
  PDF boundary with lazily-imported Playwright.
- **Sourced-object interchange (V7)** — hand-authored past-paper objects
  (`source_type:"sourced"`, `created_by:"ingested"`, `source`/`license`, `raster`
  data-URI figure) validate against the same schema and render in a mixed
  worksheet/answer-key alongside generated questions; wired the `raster` renderer
  branch (Python + TS mirror).
- **Verification** — every blueprint ships an independent seed-sweep invariant
  test (the correctness authority); hand-verified goldens are regression anchors.
  Verification graduated to Hypothesis (generative strategies + shrinking).
- **Foundation & CI/CD** — GitHub Actions merge gate (7 required checks),
  branch protection on `main`, secret scan + dependency audit + Dependabot,
  pre-push hook mirroring CI, ruff + mypy (Python) and eslint + svelte-check +
  vitest (web) quality gates, browser e2e.
- **Schema v1.4.0** — before/after bar-model `view_mode` + `parts`, and a
  `toggle-bar-view` edit op.

### Changed (post-MVP polish)

- Unified the crafting UI and print output with the landing-page design system
  (shared tokens, type roles, dark mode).
- `change-to-decimals` renders monetary/decimal values at 2 dp.
- Geometry figures label vertices with letters; running-track figure draws the
  semicircle radius as a dotted dimension line; rebalanced `geometry_area`
  difficulty rungs.
- `shaded_fraction` uses distinct outline vs fill colours so segment borders stay
  visible.

[0.1.0]: https://github.com/leejianrong/exam-paper-synthesis/releases/tag/v0.1.0
