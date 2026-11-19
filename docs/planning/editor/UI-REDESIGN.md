# Editor and app UI redesign: research and proposal

Cards: **EXA-159** (answer key clutter), **EXA-160** (editor top bars), **EXA-161** (per-question buttons), plus an app-wide pass the owner asked for.
Status: approved by the owner on 2026-11-19 (section 10). Built: S2 (EXA-159, section 11), S1 (EXA-160), S3 (EXA-161), S5 (EXA-163, section 12), S8 (EXA-166, section 13), S4 (EXA-162, section 14), S7 (EXA-165, section 15), S6 (EXA-164, section 16) and S10 (EXA-168, section 18).

Research build: worktree off `origin/main` at `f54b92c`, API on :8100 (dev auth, throwaway stores), Vite on :5273. Papers generated with `POST /documents/generate` (P6, seed 11) and through the New dialog (an exam set in a folder).

The screenshots and the mockup were local to the research run and are not committed. The real school keys were looked at for their structure only; none of their text is recorded here, and they are never to be committed.

---

## 1. Findings

### 1.1 Editor top bar (EXA-160)

The editor has three horizontal layers: the app bar (`.bar`), the formatting toolstrip, and on narrower screens the "This paper" panel, which drops between them.

**The bar overflows on the laptops teachers actually use.** Measured `scrollWidth` against the viewport:

| Viewport | Page width | Bar height | Result |
|---|---|---|---|
| 1440 | 1440 | 85 px | fits, labels wrap onto two lines |
| 1366 (common school laptop) | 1399 | 95 px | **Preview and the PDFs are off-screen** |
| 1280 | 1399 | 95 px | same |
| 1024 | 1399 | 95 px | Preview at x=1124, Full copy at x=1347 (unreachable without horizontal scroll) |

The two actions a teacher came for, Preview and Export, are the first to fall off.

**Inventory of the app bar** (`web/src/lib/editor/EditorPage.svelte` lines ~502–598):

| Control | What it does | How often needed | Notes |
|---|---|---|---|
| ← Papers | back to list | every session | label wraps to two lines |
| Saved chip | autosave state | glanced at | fine |
| "55 marks" (red) | paper total | glanced at | red reads as an error. `--mark` is meant for marks on paper, not a warning |
| Marks shown (select) | paper-level marks placement | once per paper, if ever | **duplicates** the section-level "Marks shown" with different wording and options |
| Time (min) | paper time | once per paper | prefilled by template |
| First Q | number_from | once per Booklet B / Paper 2 | prefilled by the exam-set flow |
| Answer key: Full/Compact | key layout | once | belongs with the key |
| ☐ question | key repeats question | once | label "question" is meaningless out of context. Silently disabled in Compact |
| ☐ M/A marks | key marking scheme | once | jargon |
| "30 exports left today" | quota | rarely | belongs in the Export menu |
| Regenerate unlocked | refill the paper | a few times per generated paper | destructive-ish. Sits next to a quota label |
| AccountChip | name, sign out, data, delete account | rarely | in production adds two more buttons here |
| Preview | paginated preview | often | |
| Student PDF / Answer key PDF / Full copy PDF | export | once or twice at the end | three equal-weight buttons, no primary |

**Formatting toolstrip** (same file, ~lines 637–738): B, I, U, H1, H2, H3, bullet, numbered, Section, Cover page, Blank page, Page break, Equation, Image, Undo, Redo. That is 16 equal buttons. Structure inserts (section, cover, blank page, page break) use icons that are hard to tell apart (`ToolIcon`). Equation is greyed with no reason given (it needs a text caret). There is no "+ Question" here. The only add-question affordances are the "Add question" button at the foot of the page and "+ Add below" on each block.

**Settings live in five places.** Paper settings sit in the top bar. Section settings (mode, target, marks shown, marking margin) sit inline above each section. Cover settings sit inline in an expanded cover card at the top of the page. Key options sit in the top bar. Account settings (one toggle) are on `#/settings`. A teacher looking for "where do I change X" has no single answer.

### 1.2 Per-question actions (EXA-161)

On hover or selection a generated question shows **13 buttons in three rows**: Another like this, Another topic, Write my own, Lock; Regenerate, Make easier, Make harder, Edit names, Convert to free-form, ↑, ↓; + Add below, Delete. When idle the buttons are hidden but **their space stays reserved**, so every question carries a ~90 px blank band under its Ans: line (`04-question-idle`). That band is not working space and does not print, yet it looks like it might.

Code: `QuestionBlock.svelte` lines 129–166 (`paper tools` and `question tools` groups). Free-form questions build the same row imperatively in `freeformQuestion.ts` lines 164–200 (+ Add part, Fill with a question, Another topic, Lock, ↑, ↓, + Add below, Delete). Swap/lock logic is in `paperOps.ts`.

| Action | Frequency (teacher reviewing a generated paper) | Comment |
|---|---|---|
| Another like this | high | the main review verb |
| Regenerate | medium | **near-duplicate** of "Another like this" (new seed, same blueprint vs same slot and topic). A teacher can't tell them apart |
| Lock | medium | state, should be visible only when on |
| Make easier / Make harder | medium | |
| Another topic | low–medium | |
| Edit names | low | |
| Write my own | low | label hides that it empties the question |
| Convert to free-form | low | jargon. "free-form" vs "Write my own" vs the picker's "Free-form" tab |
| ↑ / ↓ | low | drag or Alt+↑/↓ would do |
| + Add below | low | |
| Delete | low | always-visible danger button |

### 1.3 Answer key (EXA-159)

What we produce for one P6 exam set (Booklet A 15 MCQ, Booklet B 15 Q, Paper 2 17 Q):

| | Full (the default) | Compact | Real school keys (4 papers) |
|---|---|---|---|
| Booklet A | **10 pages**: one MCQ per page, each with the question, figure, four options, working, "Answer:", A1 line and distractor reasons | 1 page: grid | a third of a page: grid |
| Booklet B | 8 pages | 3 pages | 1–2 pages |
| Paper 2 | 13 pages | 5 pages | 3–4 pages |
| Whole set | **31 pages, 3 files** | 9 pages, 3 files | **4–7 pages, one document** |

Specific clutter in our key:

- **Full layout paginates the key like the student paper**, so most key pages are half empty. The Full layout repeats every question, figure and MCQ option.
- **M1/A1 lines on every question, on by default.** None of the four real keys has a marking scheme.
- **MCQ distractor reasons** ("Wrong options: (1) read the digits…") print in the key. They're useful to a teacher reviewing the paper, but no school key carries them.
- A green "ANSWER" kicker before every answer in the editor's key view, plus an "in key" checkbox and a red [n] on every row.
- **The editor's key view ignores the Compact setting.** It always shows the Full style, so the teacher never sees on screen what will print.
- Header duplication: "P6 Paper 1 Booklet A — Answer Key / Total: 20 marks", then a LEVEL/SUBJECT block. School and exam name are left blank unless the cover was filled in.
- One-mark Booklet B answers carry two or three lines of working and an A1 line, where schools give the answer alone.
- Section headings say "Section A / Section B" where schools head the key by booklet ("Booklet B", "Paper 2").

**How the four schools lay out keys** (structure only):

- **One document for the whole exam**, appended after Paper 2, typed, not scanned. 4 to 7 pages.
- **Header block** at the top, left-aligned with colon-aligned labels: SCHOOL, LEVEL, SUBJECT, TERM/exam. Then a rule.
- **Booklet A: an answer grid.** One row of Q1–Q10 with the option numbers beneath, then Q11–Q15 with empty cells to fill the row. Grey header cells. No working at all. It takes a third of a page.
- **Booklet B: a ruled two-column table.** A narrow label column (Q16, Q21(a)) and a wide working column. One-mark questions get just the answer or one line. Two-mark questions get 2–4 lines of working. One school packs **two questions per table row** (four columns) to halve the length.
- **Paper 2: the same table with "short working".** Typically 2–5 lines per part, then a right-aligned **"ANS : …"** (parts on separate lines "(a) … (b) …"). Answers that are figures are pasted pictures or "See figure".
- **Marks are not shown.** No [n], no M1/A1. The paper already printed them.
- **Question text is never repeated.**
- Density: about 8–12 Booklet B questions or 4–7 Paper 2 questions per page, small type, single-line spacing.

Our **Compact** layout is close to this already: grid for Booklet A, label | working | right-aligned Ans: table. The gap is defaults, the M/A lines, one-mark density, and three separate files instead of one.

### 1.4 The rest of the app

| Screen | Clutter, wording, consistency | Navigation |
|---|---|---|
| Sign in | No product name or one-line description. Three equal provider buttons with no logos. The page says "Sign in" twice | none needed |
| Documents list | Brand reads `exam-paper-synthesis` (the repo slug). Every row shows **Move** and a red **Delete**. US timestamps ("11/19/2026, 9:05:14 AM") for Singapore teachers. Two papers with the same title can't be told apart. The folder's "Booklet A / Booklet B / Paper 2" pills look like buttons but aren't interactive. Folders can't collapse. No search or sort | Settings is a small grey link. The account chip appears only in production |
| Empty list | "No papers yet. Start with + New." Fine but bare. Doesn't name the one-click exam set | |
| List error | Raw `API 500: boom` in red. No retry | |
| New dialog | **"New folder" is the first and focused choice**, ahead of the exam set and the single paper teachers actually want. Step 2's three buttons mix level choice with "Empty starters". A dense explanatory paragraph | After creating a set you stay on the list with no confirmation of what was made or where |
| Editor, not found | A red "not found" banner **over a live, empty editor that says "Saved"** with an active toolbar | should be a plain error page |
| Editor page | Title plus "Name: ____ Total: 20 marks" header shown even when the cover replaces it in print. Cover card expanded inline with 10 fields, taking the first screen of every paper. "PAGE OF ITS OWN" card. Section settings inline above each section | |
| Inspector / "This paper" | Useful but passive: three counts and a hint. Question view shows blueprint code and seed to teachers. At ≤1280 it jumps above the toolstrip | |
| Add question | Tabs "Templated / From my bank / Free-form". "Templated" is internal vocabulary. No level or marks filter. Topic defaults to Ratio. Candidates are tall cards, two per screen | |
| Bank (inside Add question) | The bank exists only as a tab of the Add-question dialog. Cards carry a ~100 px empty band. "Unreviewed" badge in red on every imported item | no way to browse or manage the bank outside a paper |
| Bank import | "Import canonical question JSON" (developer wording) inside a question picker | |
| Preview | Good. The page-chip index at the top is three lines of small links. The modal can't export directly | |
| Export (top bar) | Three peer buttons. The quota sits elsewhere. A key export without a filled cover gives a key with no school name | |
| Settings | One toggle. Paper defaults (school name, level, marks placement, key style) that a teacher would set once are not here | "← Your papers" link only |
| Classic (off / on) | Different visual language: black primary button, uppercase field labels, its own logo mark. **No link back** to papers or settings when on | dead end |

---

## 2. How popular editors stay clean

| Product | Pattern | What fits a teacher building a paper |
|---|---|---|
| **PowerPoint / Word** | Ribbon tabs group commands by task (Home, Insert, Layout). **Contextual tabs** (Picture Format, Table Design) appear only while that object is selected. **File backstage** is a full-screen page for document-level work: info, print, export, share | Contextual = question tools appear only for the selected question. Backstage = export and print as one destination with options, not three buttons |
| **Google Docs** | **Title and a text menu bar** (File, Edit, View, Insert, Format, Tools) stacked at top left, then **one slim toolbar** of the most-used formatting. Everything is in a menu; the toolbar is the shortcut layer. Right side: Share (primary), comments, avatar. Toolbar collapses into a `⋮` overflow as the window narrows | The two-row header. A single primary on the right. Overflow as width drops, never horizontal scroll |
| **VS Code** | Activity bar picks a side view. Each view has a title bar with 2–3 icons and a **`…` overflow** for the rest. **Command palette** (Ctrl+Shift+P) reaches every command by name. Right-click context menus. Settings UI is searchable, grouped, with "modified" markers | `⋯` overflow on a block. A command palette as the keyboard route to everything. One searchable settings page |
| **Notion** | Nothing shows on a block until hover. Then a **⋮⋮ handle** appears in the left gutter: drag to move, click for the block menu (Delete, Duplicate, Turn into, Move to, Color). **"/" slash commands** insert anything at the caret | Gutter handle for move and the block menu. Slash command for "insert a question / section / page break" |
| **Figma** | Left: layers. Right: a **properties panel that changes with the selection** (nothing selected = page/document properties). Top bar is small: menu, tools, file name, share and present | Right panel with **Paper** properties when nothing is selected and **Question** properties when a question is selected |
| **Canva** | Contextual toolbar above the canvas changes with the selection. A floating mini-toolbar sits on the selected element (lock, duplicate, delete, `⋯`). Lock is a small padlock that stays visible on locked elements | Floating mini-toolbar with Lock and `⋯`. Padlock badge stays visible when locked |

The patterns that fit:

1. **Selection decides what you see** (contextual tabs, Figma's panel, Canva's mini-toolbar). Question tools exist only for the selected question.
2. **Menus hold everything; the toolbar holds the frequent few** (Docs). Nothing important is reachable only through a menu, and nothing rare gets a permanent button.
3. **One primary action** at top right (Docs' Share). For us that's Export.
4. **Overflow, never scroll** (Docs, VS Code). The header degrades by moving items into `⋯`.
5. **State shows as a badge, actions hide** (Canva lock).
6. **A keyboard route to every command** (VS Code palette, Notion slash).

---

## 3. Answer key redesign (EXA-159)

### Drop

- The **Full layout as the default**. Keep it as "Worked solutions" for teachers who want to hand it to pupils after the test.
- **M1/A1 lines** by default. Keep as a toggle "Marking scheme (M1, A1)".
- **Distractor reasons** in the printed key by default. Keep them in the editor's key view and in Worked solutions.
- **Repeated question text** in the school-style key. Not offered there. In Worked solutions it stays on.
- The "Answer Key" title plus "Total: n marks" line, replaced by the school header block (SCHOOL, LEVEL, SUBJECT, EXAM) taken from the cover page. If the cover's school is empty, print the block without that line (as today) and warn once at export.
- The green "ANSWER" kicker and per-row "in key" checkbox in the editor's key view. "Leave out of key" moves into the question's `⋯` menu, and left-out rows show struck through with a small "Not in key" tag.
- **Per-question pagination in any key layout.** A key flows continuously, and a row never splits across pages.

### Defaults per section type

| Section mode | Default key form | Working | Marks |
|---|---|---|---|
| `mcq` | Answer grid, 10 per row, Q-number header cells, option number below, empty cells to complete the last row | none | hidden |
| `short`, 1-mark questions | Two questions per table row (label, answer, label, answer). Working only if the solver has more than one step and the teacher opts in | answer only | hidden |
| `short`, 2-mark questions | Two-column row (label, working) | the solver's steps, max ~4 lines, then right-aligned **Ans:** | hidden |
| `structured` | Two-column row per question, parts on their own lines "(a) … Ans: …" | short working per part | hidden |
| no mode | as `short` | | |

Options, kept short and placed **in the key view itself** (see 4.3), not in the top bar:

- **Style:** School key (default) · Worked solutions
- **Show:** Marking scheme (M1, A1) ☐ · Marks per question ☐ · Working for 1-mark questions ☐
- (Worked solutions only) Repeat the question ☑

Later slice (built as S10, section 18): **Exam-set key.** From a folder that holds a complete exam set (the list already detects a complete set), export one key covering Booklet A, Booklet B and Paper 2 with booklet headings, the way schools issue it.

Schema impact: `settings.key_options.layout` already exists (`full` | `compact`). The default flips to `compact` for new and generated papers. Papers that already have a saved setting keep it. `show_scheme` defaults to false for new papers. A new optional `show_marks` and `one_mark_working` came in document schema 1.16.0. No change to verification.

---

## 4. Editor redesign (EXA-160)

### 4.1 One header, two rows (Docs model)

The header has two rows: a 56 px **app header** (title, menus, primary actions) and a 40 px **toolbar**. The current three layers become two. All paper settings leave the bar.

**Before** (1440 px, wraps to 85 px; overflows below 1400 px):

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│← Papers [Saved] 55 marks  Marks shown[beside the answer line▾] Time(min)[90] First Q[1] Answer key[Full▾]    │
│                          ☑question ☑M/A marks  30 exports left today [Regenerate unlocked] [Preview][Student│
│                                                                                    PDF][Answer key PDF][Full…│ → off-screen
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│          [B][I][U] [H1][H2][H3] [•][1.][§][▤][▢][⤓] [Σ][▣] [↶][↷]                       ┌ This paper ──────┐ │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**After:**

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ←  P6 Prelims 2026 / P6 Paper 2   ✓ Saved                [ Paper | Answer key ]  55/55 marks  [Preview] [Export ▾] (MT)│
│    Paper  Insert  View  Help                                                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [+ Question] [+ Section] │ ↶ ↷ │ Normal text ▾ │ B I U │ • 1. │ Σ ▣ │                                 [⋯]      │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
  desk ┌──────────── page ────────────┐   ┌ Paper │ Question ┐  ← right panel, 300 px
       │                              │   │ …                │
```

Always visible: back, folder/title breadcrumb (title editable in place), save state, the **Paper / Answer key** view switch, marks total (neutral ink; it turns `--mark` only when a section is off target), **Preview** (secondary), **Export ▾** (the one green primary), account avatar.

Narrow widths: at < 1200 px the view switch becomes an icon pair and "55/55 marks" drops into the Paper panel. At < 1024 px the toolbar's tail (lists, Σ, image) goes into its own `⋯`. Preview and Export never leave the screen.

### 4.2 Menus

| Menu | Items (in order) |
|---|---|
| **Paper** | Paper settings… (opens the Paper panel) · Cover page… · Regenerate unlocked questions… (shows the count) · ─ · Rename · Move to folder… · Make a copy · ─ · Delete paper… |
| **Insert** | Question… `Ctrl+Enter` · Section · Cover page · Blank or rough-work page · Page break · ─ · Image… · Equation `Ctrl+M` |
| **View** | Paper · Answer key (`Ctrl+Alt+K`) · ─ · Preview pages `Ctrl+P` · Show side panel `Ctrl+\` · ─ · Show working space outlines ☑ |
| **Help** | Keyboard shortcuts `Ctrl+/` · What "verified" means · Send feedback |
| **Export ▾** | Student paper (PDF) · Answer key (PDF) · Paper and key together (PDF) · ─ · *24 exports left today* (muted footer) |

A command palette (`Ctrl+K`) lists every menu item by name. Today there are no keyboard shortcuts at all beyond the editor's own.

### 4.3 Where settings live

| Setting | Today | Proposed |
|---|---|---|
| Time, first question number, marks shown (paper) | top bar | **Paper panel** (right side, the default tab when no question is selected) |
| Level, regenerate unlocked | top bar button | Paper panel "Generated paper" group, plus the Paper menu |
| Section mode, target, marks shown, marking margin | inline above every section | Section header shows only title and "Questions 1–5 · 10/10 marks". Clicking the header selects the section and the panel shows its settings. One "Marks shown" vocabulary for paper and section ("Default (paper setting)", "In the section header", "Beside each question", "After the Ans: line", "Both") |
| Cover page fields | expanded card at the top of the page | collapsed card that looks like the printed cover (school, exam, level, paper). Click to edit in the panel |
| Answer key options | top bar | the **Answer key view**: a slim options strip above the key (Style · Show) |
| Export quota | top bar | footer of the Export menu |
| Account | AccountChip (editor and list only) | avatar menu everywhere: name · Settings · Download my data · Sign out |
| Paper defaults (school name, level, key style, marks placement) | none | **Settings page** "New paper defaults" |

### 4.4 Answer key as a view, not an appendix

Today the key is a second document appended under the paper. Make it a **view** switched in the header (`Paper | Answer key`). The key view renders exactly what will print in the selected style, with the options strip on top and per-row hover actions (`⋯` → Leave out of key, Edit answer). The paper and key share the selection: selecting Q12 in the paper and switching views scrolls the key to Q12.

---

## 5. Per-question actions (EXA-161)

### Options compared

| Option | Clean at rest | Discoverable | Speed for "another like this" | Keyboard / a11y | Fit |
|---|---|---|---|---|---|
| **A. `⋯` overflow menu only** | yes | medium (one visible button) | 2 clicks | easy: menu button pattern | good, but the main review verb is buried |
| **B. Floating toolbar on hover/selection** (Canva) | yes | high | 1 click | fine on selection. Hover-only fails keyboard and touch | good if it holds ≤ 3 items |
| **C. Right-click context menu** | yes | **low**: teachers rarely right-click in a web page | 2 clicks | needs a keyboard equivalent (Shift+F10) | only as a secondary route |
| **D. Notion-style gutter handle ⋮⋮** | yes | medium | 2 clicks | handle must be focusable | great for move/drag, weak for the swap verbs |
| **E. Hybrid: selection pill (B) with `⋯` (A), plus a gutter handle (D) for move, plus right-click (C) opening the same menu** | yes | high | **1 click** | one menu, three routes | **recommended** |

### Recommendation: E

- **At rest:** nothing. No reserved band. Only a **padlock badge** next to the question number when the question is locked, and a dashed outline on placeholders.
- **Hover:** a faint ⋮⋮ handle in the left gutter (drag to reorder; click opens the menu). Nothing else, so moving the mouse down a paper stays calm.
- **Selected** (click or keyboard focus): a pill on the block's top-right edge with three controls:
  `[↻ Another like this]  [🔒 Lock]  [⋯]`
  For free-form questions, `[+ Part]  [🔒]  [⋯]`. For placeholders, `[Fill with a question]  [⋯]`.
- **Right-click** on a question and **Shift+F10** open the same `⋯` menu.
- "Regenerate" and "Another like this" merge into one verb. The server's `swap like` already covers a new seed of the same blueprint.

```
   ⋮⋮ 6.  Postage costs $1.90 for a 500 g letter …          [↻ Another like this] [🔒] [⋯]
          ┌─────────────────────────────────────────┐                             ┌──────────────────────────────┐
          │                                         │                             │ Another like this         R  │
          │            working space                │                             │ Another topic                │
          └─────────────────────────────────────────┘                             │ Make easier               [  │
                                   Ans: $ ____________ [2]                        │ Make harder               ]  │
                                                                                  │ Edit names…                  │
   🔒 7.  The table shows …                         (locked: badge only)          │ Slice into units             │
                                                                                  │ ──────────────────────────── │
                                                                                  │ Lock                      L  │
                                                                                  │ Leave out of answer key      │
                                                                                  │ ──────────────────────────── │
                                                                                  │ Move up               Alt+↑  │
                                                                                  │ Move down             Alt+↓  │
                                                                                  │ Add question below  Ctrl+↵   │
                                                                                  │ ──────────────────────────── │
                                                                                  │ Replace with my own question │
                                                                                  │ Edit as my own text…         │
                                                                                  │ ──────────────────────────── │
                                                                                  │ Delete                  Del  │
                                                                                  └──────────────────────────────┘
```

Menu order follows frequency, top to bottom: change it, keep it, place it, take it over, remove it. Items that don't apply are hidden (Make harder on the top rung), not greyed. Op-specific items (Change to decimals, Show model in key, Slice into units) appear in the first group only when `available_ops` offers them.

Wording changes: "Write my own" → **Replace with my own question** (it empties the slot). "Convert to free-form" → **Edit as my own text…** (with a one-line confirm: "It won't be checked by the engine any more"). Picker tab "Templated" → **Generate**, "Free-form" → **Write my own**.

---

## 6. Keyboard and accessibility

- Every pill and menu control is a real `<button>`. The `⋯` follows the WAI-ARIA menu button pattern (`aria-haspopup="menu"`, `aria-expanded`; arrows move, Esc closes and returns focus).
- Question blocks become focusable (`tabindex="0"`, `role="group"`, `aria-label="Question 6, 2 marks, locked"`). Focusing a block shows its pill, so keyboard users get what hover users get. Hover-only UI is never the only route.
- Shortcuts on a focused block: `R` another like this, `L` lock, `[`/`]` easier/harder, `Alt+↑/↓` move, `Del` delete (with undo toast rather than a confirm), `Shift+F10` or the Menu key opens the menu.
- Global: `Ctrl+K` command palette, `Ctrl+Enter` add question, `Ctrl+Alt+K` toggle Paper/Answer key, `Ctrl+P` preview, `Ctrl+/` shortcut sheet.
- The padlock badge has text for screen readers ("locked") and a tooltip. It is not colour-only.
- The marks total uses text ("10/10") and only turns `--mark` red with an icon when off target. Red is never the resting state.
- The header's overflow behaviour replaces horizontal scroll at every width ≥ 768 px.
- Focus ring stays the existing `:focus-visible` (2 px `--verify`). Reduced-motion: the pill and menus appear without transition.
- Destructive actions (Delete paper, Regenerate unlocked) confirm in a dialog that names what happens ("Replaces 13 unlocked questions. 2 locked questions stay."). Delete question uses undo instead.

---

## 7. App-wide

### 7.1 One navigation model

```
┌ App header (every screen) ──────────────────────────────────────────────────┐
│ ▦ Papers   Question bank                                     (MT) ▾         │   ← list, bank, settings
└──────────────────────────────────────────────────────────────────────────────┘
┌ Editor header (replaces the app header inside a paper) ─────────────────────┐
│ ←  Folder / Title  ✓Saved   Paper  Insert  View  Help   [Paper|Key] [Preview][Export ▾] (MT) │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Two top-level places: **Papers** and **Question bank** (promoted out of the Add-question dialog into a page with filters, review state and Import). Settings and account live under the avatar menu on every screen.
- The Classic generator, when turned on, appears as a third tab "Classic" with the same header, so it stops being a dead end.
- Inside a paper, the editor header replaces the app header. "←" always returns to the folder the paper was in.

### 7.2 Component vocabulary

| Element | Rule |
|---|---|
| **Primary button** | One per screen, `--verify` fill, white text: "+ New" on the list, "Export" in the editor, "Import" in the import dialog, "Add to paper" in the picker. The Classic page's black button goes |
| **Secondary button** | White, `--line` border, `--ink` text: Preview, Cancel, Move |
| **Quiet / icon button** | No border at rest, `--wash` on hover, 32 px square, always with `aria-label` and a tooltip that names the shortcut |
| **Danger** | Never at rest on a list row or block. Lives at the bottom of a menu, red text, and confirms or offers undo |
| **Menu** | 8 px radius, `--shadow`, 13.5 px items, shortcut right-aligned in `--ink-faint`, separators between groups |
| **Chip / badge** | Status only, never clickable: Saved, Verified, Unreviewed (amber-neutral, not red), Locked |
| **Labels** | Sentence case, verb first for actions ("Add question", "Export answer key"), noun for settings ("Time", "Marks shown"). No uppercase micro-labels (Classic, cover card "COVER PAGE", "PAGE OF ITS OWN") |
| **Icons** | One stroke set (1.5 px, 16 px), always paired with text in menus. Icon-only only in the toolbar and the pill, and always with a tooltip |
| **Spacing** | 4 px base: 8 inside controls, 12 between controls in a group, 24 between groups, 32 page gutters |
| **Dates** | `19 Nov 2026, 9:05 am` (en-SG), or relative ("edited 5 min ago") on the list |
| **Words** | paper, question, section, answer key, question bank, generated (not "templated"), my own question (not "free-form"), exam set |

### 7.3 Issues ranked by impact on a teacher

| # | Issue | Where | Impact |
|---|---|---|---|
| 1 | Preview and Export off-screen below 1400 px | editor bar | **Blocks the core job** on a standard school laptop |
| 2 | Answer key defaults to 31 pages across three files, half-empty pages, M1/A1 and distractor notes | export, key | Wastes paper and time. Teachers redo it by hand |
| 3 | 13 buttons per question, and a blank band under every question at rest | question block | Paper looks unfinished. Review is slow. "Regenerate" vs "Another like this" confuses |
| 4 | Settings scattered across bar, inline section and cover cards, key strip and Settings page; two different "Marks shown" | editor | Teachers can't find or trust a setting |
| 5 | Editor key view doesn't match the exported key | key view | What you see is not what prints |
| 6 | Bank hidden inside the Add-question dialog, developer wording for import | bank | A teacher's own collection is hard to find |
| 7 | "Not found" shows a live, "Saved" empty editor. Raw `API 500` errors | states | Alarming, and edits typed there go nowhere |
| 8 | New dialog leads with "New folder". No confirmation after making a set | list | Slows the first-run path |
| 9 | Always-visible red Delete on every list row; no search; US dates; same-name papers indistinguishable | list | Risky and noisy as the list grows |
| 10 | Classic page is a dead end with a different look | classic | Lost users (few, it's off by default) |
| 11 | Sign-in page has no product name; brand is the repo slug | login, list | First impression |
| 12 | Icon-only structure buttons (cover, blank page, page break); Equation disabled without reason | toolbar | Guesswork |

---

## 8. Slices (PR-sized, ordered by value)

| # | Slice | Cards | Scope | Notes |
|---|---|---|---|---|
| S1 | **Header that fits** | EXA-160 | New two-row editor header: breadcrumb title, save state, marks total in neutral ink, Preview, **Export ▾** (three exports + quota footer), avatar. Move Time / First Q / Marks shown / Regenerate unlocked into the right panel's **Paper** tab. Overflow instead of horizontal scroll down to 768 px | Biggest single win. Pure web. Playwright width test at 1024 / 1366 |
| S2 | **School-style key by default** | EXA-159 | Default `layout: compact` and `show_scheme: false` for new and generated papers. Drop distractor reasons from the compact key. Fix key pagination (continuous flow, rows don't split). Header block from the cover | Engine render + small schema default. Goldens for key HTML |
| S3 | **Question pill and menu** | EXA-161 | Remove the reserved band. Selection pill (Another like this · Lock · ⋯), menu with the groups above, padlock badge, gutter handle for drag. Merge Regenerate into Another like this. Same for free-form blocks | Shared menu component reused in S5 and S8 |
| S4 | **Key as a view** | EXA-159 | Paper/Answer key switch in the header. The key view renders the chosen style. Options strip. "Leave out of key" via the menu | Depends on S2, S3 |
| S5 | **Menus and shortcuts** | EXA-160 | Paper / Insert / View / Help menus, toolbar trimmed to + Question, + Section, undo/redo, text style dropdown, B I U, lists, Σ, image. Shortcut sheet. Command palette can follow as S5b | |
| S6 | **Section and cover settings in the panel** | EXA-160 | Collapsed section header and cover card. Settings edit in the panel. One "Marks shown" vocabulary | |
| S7 | **States** | app | Not-found and error pages with retry. Plain-language errors (no `API 500`). Loading skeleton for list and editor | Small, independent, can go any time |
| S8 | **Documents list cleanup** | app | Row `⋯` menu (Open, Rename, Move, Make a copy, Delete). New dialog leads with Exam set. en-SG dates. Search. Collapsible folders. ~~Non-button set-progress ticks~~ (dropped: the owner asked for no ticks, section 10) | |
| S9 | **App header and Question bank page** | app | Shared header (Papers, Question bank, avatar menu with Settings and Sign out on every screen). Bank as its own page with filters, review and Import ("Import questions from a file"). Classic as a tab when on | |
| S10 | **Exam-set key** | EXA-159 | One key PDF for a complete set in a folder, booklet headings | Engine + API. After S2 |
| S11 | **Settings: new-paper defaults** | app | School name, level, key style, marks placement prefilled into new papers | Needs settings keys |
| S12 | **Sign-in polish** | app | Product name and one line, provider marks | |

---

## 9. Mockup

A local mockup page (not committed): self-contained, existing tokens (`web/src/app.css`), Inter embedded as data URIs (no new font). Three frames: the editor (header, toolbar, paper with a selected question's pill and open menu, a locked question, the Paper panel), the Answer key view in school style, and the documents list.

Verification run on the mockup (frontend-design verify steps), served from `127.0.0.1:5274`:

- Console: no errors on load (the only entry is the static server's missing favicon).
- Overflow: `scrollWidth` equals the viewport at 1440, 1024 and 375 px.
- Fonts: Inter 400, 600 and 700 all report `loaded`. No other family.
- Tokens: the only hex values are the `:root` token definitions. One proposed new token, `--on-accent`, replaces three bare `#fff`.
- Keyboard: Tab order runs back, title, Paper, Insert, View, Help, view switch, Preview, Export, matching the visual order. Every stop shows the existing 2 px `--verify` focus ring.
- Accessibility tree: no unlabelled buttons. Icon-only buttons carry `aria-label` with the shortcut. Headings run h1 → h2 → h3 → h4.
- Contrast: `--ink-faint` on white is about 5.3:1, white on `--verify` about 5.4:1. Light only, as the app is.
- Not checked: real menu keyboard behaviour (the mockup is static) and screen-reader announcements.

Step 2 sources: the popular-editor patterns in section 2 come from product knowledge, not a web search done for this research.

---

## 10. Owner decisions (2026-11-19)

- The design is approved as proposed. One change: **remove the green-check exam-set status ticks** (Booklet A / Booklet B / Paper 2) from the folder headers in the papers list (EXA-166).
- Cards: S1 = EXA-160, S2 = EXA-159, S3 = EXA-161, S4 = EXA-162, S5 = EXA-163, S6 = EXA-164, S7 = EXA-165, S8 = EXA-166, S9 = EXA-167, S10 = EXA-168, S11 = EXA-169, S12 = EXA-170.
- **New papers get the school-style key by default.** Add an account setting (Settings page) for the preferred answer-key style, defaulting to school style; new papers take it. Saved papers keep their own setting.
- **Keyboard shortcuts now** (EXA-163 pulled forward, right after S1 and S3), as proposed in section 6, including the Ctrl+K command palette.

---

## 11. S2 as built (EXA-159)

- New, template and generated papers write `settings.key_options` explicitly: the school key is
  `{layout: compact, show_scheme: false, show_marks: false, one_mark_working: false}`, worked
  solutions are `{layout: full, show_question: true, show_scheme: true}`. Which one a new paper
  gets is the account setting `answer_key_style` (`school` by default) on the Settings page.
- Document schema 1.16.0 adds `show_marks` and `one_mark_working`. An absent option keeps the
  behaviour the paper had before it existed, so saved papers print as they did (no key options:
  worked solutions with M/A lines; a compact key saved before 1.16.0 keeps its 1-mark working).
- The key was never paginated question by question: Chromium lays it out, and a worked solution
  is kept whole on a page, which is what left most of the Full key's pages half empty. The school
  key flows on, and a table row (`break-inside: avoid`) never splits; a PDF test reads this back.
- Measured on one P6 exam set (seed 11), key PDFs: worked solutions 10 + 8 + 13 = 31 pages; the
  school key 1 + 1 + 3 = 5 pages.
- Not in S2: the editor's key view still shows the worked layout (S4), and the options stay in
  the top bar's "Answer key" group until S1 and S4 move them.

---

## 12. S5 as built (EXA-163)

- The menu row is `MenuBar.svelte` (WAI-ARIA menubar: one Tab stop, ←/→ between menus and between
  open menus, the pointer moving onto another name opens it) over the existing `Menu.svelte`,
  which gained checkbox rows and Mac labels. Below 900 px it folds into one "Menu" button.
- Paper > Cover page… goes to the cover's first field, adding a cover first if there is none (S6
  moves its fields to the panel). View > Answer key scrolled to the key under the paper until S4
  made it a view (section 14). "Send feedback" is left out: there is no feedback address or page yet. View > Show working space outlines is not built.
- Make a copy has no API of its own: the browser creates a paper ("Copy of …", same folder) and
  saves this paper's content and settings into it, then opens it.
- The side panel's visibility is kept in `localStorage` (`exam.editor.sidePanel`), wrapped in
  try/catch; without storage the panel shows and a hide lasts for the visit.
- The palette lists the selected question's menu rows first (the block registers them in
  `shortcuts.ts`, busy blocks list none and a run re-checks busy), then every enabled menu row
  and the three exports. Words match anywhere in the name or its menu; labels rank first.

**Keyboard shortcuts** (Cmd in place of Ctrl on a Mac, labels ⌘ and ⌥ there):

| Group | Keys |
|---|---|
| Paper | Ctrl+K command palette · Ctrl+Enter add a question · Ctrl+Alt+K answer key / back to the paper · Ctrl+P preview pages · Ctrl+\\ side panel · Ctrl+/ shortcut sheet |
| Questions (a selected question) | R another like this · L lock · [ easier · ] harder · Alt+↑/↓ move · Del delete (with undo) · Shift+F10 or the Menu key its menu |
| Text | Ctrl+B/I/U · Ctrl+M equation · Shift+Enter line break · Ctrl+Z undo · Ctrl+Y redo |

Ctrl+Enter and Ctrl+M never fire from a form field (the title, a marks box, a dialog). With a
dialog open no global shortcut runs, though Ctrl+P is still kept from printing the screen.


---

## 13. S8 as built (EXA-166)

- A paper row is `PaperRow.svelte`: the title links to the editor, the line under it reads
  "12 marks · edited 5 min ago", and a ⋯ `Menu` holds Open, Rename, Move to folder…, Make a copy
  and Delete… (danger, last, after a rule). The ⋯ shows on hover or focus where there is a
  mouse (`@media (hover: hover) and (pointer: fine)`), always on touch. Shift+F10, the Menu key
  or a right-click on the row opens it; a right-click on the title link keeps the browser's own
  menu (Open in new tab). Move to folder… is off, with a reason, while there are no folders.
- Rename and Make a copy have no endpoint of their own: rename reads the paper and saves it with
  the new title (a version bump, as an editor rename is); a copy is a create plus a save, and a
  copy whose save fails is deleted again (`docsApi.renameDocument`, `copyDocument`, which the
  editor's Make a copy uses too, passing the content it holds). The copy's title is cut to the
  schema's 200 characters. The list shows the copy under its original until it reloads; the API
  orders papers by last edit, so after a reload the copy comes first. The list stays where it
  is (the editor's Make a copy opens the copy). A rename that takes a paper out of the current
  search results moves focus to the search box.
- Delete paper and Delete folder use `ConfirmDialog`; Move uses the editor's `MoveDialog`, so the
  old inline "Confirm delete" and `MoveMenu.svelte` are gone. `MoveDialog` ignores Escape, the
  backdrop and × while a move runs, so a failure still shows in it. After a delete focus goes to the
  "Your papers" heading; after a move, to the paper's ⋯ in its new folder.
- A folder's header is a disclosure button (chevron, folder icon, name) with the paper count
  and a ⋯ menu: New paper in folder…, Rename folder, Delete folder…. The collapsed folders are
  kept in `localStorage` (`exam.papers.collapsed`, a list of folder ids), read and written in
  try/catch; without storage a collapse lasts for the visit. The folder body stays in the DOM
  (`hidden`) so the toggle's `aria-controls` always names it. A folder the wizard just filled,
  or a paper was just moved into, opens.
- Search (`folders.titleMatches`): every word typed must appear in the title, ignoring case and
  accents. While searching, folders without a match are hidden, the rest show their matches and
  their names are plain headings (no collapse) with "N matches" in place of the paper count,
  the status line announces "N papers match …", and Escape in the box clears it. The box is
  hidden while there are no papers and no search; under 600 px it takes its own line.
- Dates (`dates.ts`): `fullDate` "19 Nov 2026, 9:05 am" (en-SG, the viewer's time zone) and
  `editedWhen`: "just now", "N min ago" under an hour, "today, 9:05 am", "yesterday, 4:40 pm",
  then the full date. The full date is the `<time>` tooltip. The list's clock ticks each minute.
- The exam-set chips are removed (owner decision), with `FolderGroup.parts`, `paperPart` and
  `partOf`, and the web client's `paper_part` field; the server still derives `paper_part`
  (nothing in the web app reads it now).
- The New dialog's cards are Exam set (focused), Single paper, Blank paper, New folder. Back from
  a step returns focus to the card that was picked.
- Not in S8: the shared app header (brand, Papers / Question bank, S9), a "Generated / Mixed"
  kind badge and a question count on rows (the list summary has neither), and the folder's
  "Set key" button (S10).

---

## 14. S4 as built (EXA-162)

- **One renderer.** The key view is `KeyView.svelte`: the paper's `GET /documents/{id}/preview/key`
  (the HTML the Answer key PDF is made from) in a `srcdoc` iframe at the print width (178 mm),
  inside an A4 sheet with the print margins. There is no web-side key renderer any more: the old
  `AnswerKey.svelte` and `FragmentView`'s CSS mirror of the key options are deleted. The key is
  not paginated (Chromium numbers its pages), so the view is one continuous sheet.
- **Refresh.** The view loads only while it is shown. Any change to the paper's content, settings
  or title makes it stale; it saves pending edits (`autosave.flush`) and asks again 600 ms after
  the last change, or at once when the view opens. The new key loads in a hidden iframe and
  replaces the old one once drawn, and the sheet's height follows the key's own (a
  `ResizeObserver` in the frame, for KaTeX and fonts), so the page keeps its scroll position.
  While a swap or regenerate runs it waits. A failed load says so with Try again and keeps the
  last key on screen; it never retries on its own.
- **Scroll.** Each view keeps its own scroll position. Switching to the key with a question
  selected scrolls to that question's row: `keyRows.ts` finds it by its printed label (`Q16` in a
  table row or a grid column head) or, for worked solutions, by its place among the questions in
  the key.
- **Options strip** above the key: Style (School key / Worked solutions, radios styled as the
  Settings page's segmented control) and Show (the question, worked solutions only; marking
  scheme (M1, A1); marks and working for 1-mark questions, the school key only). Same
  `setKeyLayout` defaults as before; the side panel's Answer key group is gone.
- **Left out of the key.** The question ⋯ menu's Leave out of / Include in answer key (EXA-161)
  is the way out. The printed key can't show a left-out row struck through (it isn't in the
  print), so a line under the strip, "Not in the key", lists them with an Include button each.
- **Answers you write.** The old key region was also where a teacher's own question got its
  answer. That moved to **Edit answer…** in the question's ⋯ menu (`AnswerDialog.svelte`: the
  question for reference, then one answer editor, or one per part). The key view lists your own
  questions under "Your answers" (those without an answer marked "to write"), and clicking an own
  question's row in the printed key opens its answer too.
- **Header.** The Paper | Answer key switch sits before the marks total (an icon pair below
  1200 px). Below 600 px it hides so the title keeps its room; Menu > View still switches. In the
  key view the toolbar keeps only + Question, + Section, undo and redo. Anything that puts
  something into the paper (+ Question, + Section, the Insert menu, Paper > Cover page…,
  Ctrl+Enter, Ctrl+M) switches to the paper first, so nothing lands unseen in the hidden page.
  Keys pressed inside the printed key reach the editor's shortcuts (Ctrl+Alt+K back, Ctrl+P,
  Ctrl+K), and a press inside it closes an open menu as a press anywhere else does.
- **Stale keys.** Each key on screen remembers the question numbers and own questions it was
  asked for, so a click or a scroll on it maps to the right question even while a newer key is
  due. A scroll asked for while a refresh is due or loading waits for the new key (and is
  dropped if that load fails or the view is left). A key that finishes loading after a newer
  one never replaces it.
- **Uploads.** Edit answer… waits for an image still uploading ("Image still uploading…")
  before Done or Esc closes it, so the image isn't lost.
- **Not built:** per-row hover actions inside the printed key (a ⋯ on each row). Rows are print
  markup inside an iframe; only the own-answer click is wired there. The exam-set key (S10) is
  still to come.

---

## 15. S7 as built (EXA-165)

- **One wording.** `web/src/lib/errors.ts`: every failed request is an `ApiError` (status,
  the server's `detail`, a 429's `Retry-After`) whose message is already plain language, so
  each `catch` that showed `e.message` shows words without being touched. `fail(res)` replaced
  the four copies of "throw `API ${status}: ${detail}`" (api.ts, docsApi.ts, assets.ts, the
  bank import) and `docsApi`'s own `ApiError`. `http.reach` (and `apiFetch` on top of it) turns
  a request that never reached the server into `ApiError(0)`. The status and detail go to the
  console (`console.warn`), never on screen. Only a JSON `detail` counts as the server's words:
  a body that isn't JSON (a proxy's error page) leaves the detail empty, so a status text such
  as "Payload Too Large" never shows, and FastAPI's own "Not Found" / "Method Not Allowed" are
  treated as no detail.
- **The words.** 0: "Can't reach the server. Check your internet connection." 401: "You're
  signed out…". 403: "You don't have access to this." 404: named where the server's detail
  says what is missing ("This paper doesn't exist or was deleted."). 409: "This paper changed
  in another tab or window. Reload…". 413 / 400 / 422: the server's short reason as a sentence
  ("Image is larger than 2 MB."), but never a validation dump ("invalid question: …", a list
  of schema errors), which becomes "The server couldn't accept this, so nothing was changed."
  429: "Too many requests. Try again in N seconds/minutes/hours." from Retry-After. 503: "The
  server is busy." Other 5xx: "Something went wrong on our side. Try again in a moment." A
  detail the server wrote as a sentence for people (the export allowance, a swap that isn't
  possible, empty placeholders) is shown as it is.
- **What didn't happen, then why.** `errorText(e, action)` puts the action first: "Couldn't
  load your papers.", "The question wasn't swapped.", "The setting wasn't saved.", "The image
  wasn't added.", "Couldn't export the PDF.", "Couldn't open the preview.", "Couldn't list your
  folders.", "Couldn't make a copy.", "Couldn't generate questions.", "Couldn't load your
  question bank.", "The paper wasn't moved / deleted / renamed.", "The folder wasn't renamed /
  deleted / made", "The review mark wasn't changed.", "The answer key didn't load / update."
- **Try again** (`ErrorNote.svelte`, the answer key view's alert-and-retry pattern made shared:
  alert icon, text, a secondary button) shows only when `canRetry`: unreachable, 408, 5xx, or
  a 429 whose Retry-After is absent or at most 60 s (the daily export allowance says "in 3
  hours": a button would only fail again). A 404, 409 or 422 won't change by asking again.
  Where: the papers list (in place of the list), the paper templates, opening a paper, saving,
  exports, the preview, swap, regenerate, listing folders, generating questions, the question
  bank, a setting. Every write of the editor's error strip goes through one setter
  (`showError`) that sets its retry too, so an image error never inherits an export's Try
  again.
- **Creates are not retried.** Make a copy (editor and list) and the New dialog's single paper
  offer no Try again: after a lost reply (unreachable, 5xx) the paper may exist, so the text
  ends "Check Your papers before trying again." (`createFailedText`). The exam-set rows' own
  "Try Booklet B again" (EXA-153) is unchanged.
- **Saving.** The chip said "Save failed — will retry", but nothing retried until the next
  edit. It now says **Not saved**; the strip under the header gives the reason (the autosaver's
  new `onError`) and Try again, offered only when `canRetry` (a 413 or 422 would fail the same
  way), saves the kept change (`autosave.flush`). The next edit tries again either way.
- **Opening a paper.** `PaperUnavailable.svelte` replaces the whole editor (header and desk
  hidden; the old banner sat over a live, empty editor showing "Saved", because `.desk`'s own
  `display` beat `.hidden`). 404: "This paper doesn't exist or was deleted", only Back to Your
  papers. Another account's paper is a 404 from the server too (documents are owner-scoped);
  the 403 page ("You don't have access to this paper") is a defensive fallback only.
  Unreachable: "Can't reach the server" with Try again first. Other failures: "This paper
  couldn't be opened" with the reason, and Try again when it can help; a fault in the page
  itself (not an `ApiError`) gets a generic sentence, never the script's message, and Try
  again. Try again runs the load again in place (`openPaper`), which first disposes anything a
  part-way failure left (subscription, autosaver, editor, the half-built page), so a retry
  never runs two editors. The heading takes focus. No save runs from a page that didn't open.
- **Skeletons.** Grey bars (`.skel` in `app.css`, a slow sheen; still under
  `prefers-reduced-motion`): four paper rows in the list box, and for the editor its header
  and an A4 page (`EditorSkeleton.svelte`, which hides the real header too, so nothing claims
  "Saved" before the paper is in). Each is a `role="status"` with hidden text ("Loading your
  papers…", "Opening the paper…"), without `aria-busy` (a busy live region holds back its own
  announcement).
- **Not changed:** the sign-in page's own messages (S12), the Classic page beyond the shared
  wording, and the add-question picker's "Loading your bank…" line (a dialog, not a first load).

---

## 16. S6 as built (EXA-164)

- **On the page.** A section is a compact header (`sections.ts` node view): its title ("Untitled
  section" in faint ink when it has none), the derived "Questions 16–30 · 40 / 40 marks" (in
  `--mark` when off target, as before), short cues in faint ink (the mode, "marking margin" when
  it will print one) and its instructions. The header is an editing aid, not a print preview: a
  generic title ("Section A", "Booklet 2", "Part B", the engine's `_GENERIC_TITLE`, EXA-139) is
  not printed, so it shows faint with the cue "title not printed" (`titlePrints`), and the
  printed marks sentence is not reproduced. The cover is a compact card
  (`pages.ts`): a "Cover page" caption, then school, exam, and "level · subject · paper" centred,
  or "Add the school and exam" when empty. Neither has form fields; the inline forms and their
  CSS are deleted. The blank page keeps its small inline form (not in this slice).
- **Selecting.** A click on the header or card selects the block (a ProseMirror node selection),
  as do the arrow keys. The side panel's second tab follows the selection: the question
  inspector, or the selected section's settings (tab named by its title, else "Section N") or the
  cover's ("Cover page"); selecting a different one brings that tab forward, as a question did.
  Only a new selection does: the page counts the author's selections (`settingsPick`, bumped
  when the selection is not just the previous one mapped through the change), so a section
  inserted, removed or undone above the selected one moves its place without pulling the panel
  off the Paper tab.
  `blockSettings.ts` reads the selection (`selectedSettingsBlock`) and writes a change
  (`settingsTransaction`), which keeps the block selected so the panel stays on it while you
  type. The section is found again by its place among the sections, since sections carry no id
  and the document schema did not change.
- **Edit and Alt+Enter.** Each header and card has a quiet **Edit** button (shown on hover, focus
  or when selected, always on touch). It, Alt+Enter on the selected block, and Paper > Cover
  page… select the block, show the side panel if it was hidden (the S5 toggle, remembered as
  before) and focus its first field. Escape in the settings goes back to the page with the block
  still selected. Plain selection while the panel is hidden does not open it; the visible Edit
  button is the offer. The block-selection guard (EXA-129) now leaves Alt+Enter alone, so it no
  longer types a new line after the block. Alt+Enter is listed in the shortcut sheet.
- **Fields.** Section: Title, Instructions, Mode, Marks target, Marks shown, Marking margin, with
  the range and marks on top. Cover: School, Exam, Level, Subject, Paper, Date, Instructions, For
  examiner's use table, Parent's signature line, Pad to an even number of pages, and the note on
  what comes from the paper. Same limits and the same attrs as the old forms.
- **One "Marks shown".** `MarksShown.svelte` is the control for both the paper and a section, with
  the labels in `layout.MARKS_SHOWN`: After the Ans: line, Beside each question, Both, and for a
  section In the section header plus its default: "Same as the paper", or "Multiple choice
  default" / "Short answer default" for the modes the engine keeps in the header. The section's
  long "Default: …" option text no longer fits a 300 px panel, so the line under the control says
  what the choice comes to ("Follows the paper: after the Ans: line."). The paper's control says
  that sections follow it unless they set their own, and that multiple-choice and short-answer
  sections show marks in the section header (the engine's `section_placement`).
- **During a swap or regenerate** the section and cover settings are a disabled `<fieldset>`,
  and the page ignores any change that still arrives (`opInFlight`): `applyServerContent` would
  otherwise drop it.

- **Narrow widths.** Below 900 px the panel stacks above the page as before; Edit scrolls to and
  focuses the field there. No horizontal scroll at 820 px.
- **Not changed:** a generated paper with no text in it still opens with the cover node-selected
  (there is nowhere for `startWithTextCursor` to put a caret; this predates S6). The panel shows
  the Paper tab until you click something, and typing still goes after the cover (EXA-129).

---

## 18. S10 as built (EXA-168)

- **Where.** A folder's ⋯ menu on Your papers has **Download the set’s answer key** when the folder
  holds any paper of an exam set. With one Booklet A, one Booklet B and one Paper 2 it downloads
  one PDF ("<folder name> answer key.pdf"); otherwise it is greyed out with the reason on a
  second line ("This folder has no Booklet B.", "This folder has more than one Booklet A.").
  Folders with no set paper don't offer it. Other papers in the folder (a spare worksheet) are
  ignored. A search doesn't change it: the status counts every paper in the folder. `Menu`
  items gained an optional `note` line for this.
- **Which papers, in what order.** By the server-derived `paper_part` (the cover's paper line,
  the title as fallback), the list summary's field the web reads again (`folders.setKeyStatus`).
  The engine's `document.exam_set_order` is the rule, applied again by the API, which answers
  409 `incomplete_set` / `ambiguous_set` with the same sentence; a doubled part is reported
  before a missing one. A paper with no questions is a 422. Empty generator placeholders are a
  409 `unfilled_placeholders` naming the paper and questions ("Paper 2 question 1 is still
  empty…"), and the list offers **Download anyway** (`allow_placeholders=true`), as the editor's
  exports do.
- **The key.** `render.render_set_key_html(title, [(title, doc), …])`: the cover lines (school,
  level, subject, exam; each from the first cover that fills it) head the first page once, or
  the folder name when every cover is empty. Then each paper, under "Paper 1 Booklet A",
  "Paper 1 Booklet B" or "Paper 2", is exactly its own key minus its cover lines and paper name:
  its style (school key or worked solutions), its options, its left-out questions, its numbers
  (Booklet B from 16; worked solutions get explicit numbers so Paper 2 restarts at 1). Paper 1's
  two booklets flow on; Paper 2 starts a new page (`break-before: page`), since it is a separate
  sitting. Like every key, it is not paginated by the script: Chromium's `@page key` counter
  numbers the pages through the whole set.
- **API.** `POST /folders/{id}/key` (PDF) and `GET /folders/{id}/key/preview` (HTML, free),
  owner-scoped (another owner's folder is a 404). The PDF spends one export from the allowance
  (429 with Retry-After when used up), after every refusal above, and a failed render is
  refunded. No store change: the folder is checked with `list_folders` and the papers read with
  `list` + `get`, so both backends behave alike (`tests/test_api_set_key.py` runs on Postgres in
  CI).
- **Tests.** `tests/test_set_key.py`: the invariant (each paper's part of the set key is its own
  key, every in-key question once, in order, under its heading) over P5 and P6 sets of eight
  seeds, the title block, mixed styles and left-out questions, the set rule, and a PDF read back
  for page numbers 1…n and Paper 2 starting a page. `test_monochrome_print.py` covers the set key
  in both styles. e2e `tests/e2e/set-key.spec.js` downloads the key of a generated set from the
  folder menu.
- **Measured** on the P6 set of seed 11 with the school key: 5 pages (Paper 1 on pages 1–2,
  Paper 2 on 3–5).
- **Not built:** an Export menu item in the editor for a paper that belongs to a complete set
  (the editor doesn't load the folder's other papers; the folder menu is one click away).
