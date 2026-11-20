# Shared stems (EXA-90 part 3) — shaping note

**Problem.** Real papers print one stem (a sentence, a table, a figure) and then several
consecutively numbered questions that all refer to it: "Use the table below to answer
Questions 12 and 13." Each question keeps its own number, marks, working space and Ans: line,
and in Booklet A each can be a separate MCQ. That is not one multi-part question (a)(b): parts
share one number and are marked as one.

## The two shapes considered

| | A: `questionGroup` wrapper | B: flat `groupStem` block (chosen) |
|---|---|---|
| Model | a top-level node holding a stem and 2+ question children | a top-level block before its questions, `attrs.count` = how many follow |
| Numbering, sections, totals, cover table | every walker over the top level (engine `paper_outline`, `numbered_blocks`, render loops, `paper.py`, `paper_swap.py`, the API's hint/stamp loops, docx export; the web's `paperOutline`, `blockPlace`, `blockPlacements`, the key view) must learn to descend | unchanged: questions stay top-level blocks, the stem is not numbered |
| Generated questions | swap / regenerate / lock must find and replace children | unchanged |
| Editor | ProseMirror enforces the shape; dragging in and out is natural | a small plugin keeps the count right through edits; moving a question at a group's edge steps it in or out |

B touches only the code that prints or edits the stem itself, and every existing paper and
feature keeps working untouched. The price is that membership is a count, not a containment,
so the editor has to keep it honest (below). We chose B.

## The rules

- `groupStem` (document schema **1.18.0**): `attrs` `block_id`, `count` (1–20); `content` is
  text blocks (paragraphs with inline equations, lists, images). At most 40 per paper.
- Its questions are the next `count` question blocks after it. Rich text between them stays in
  the group. A section, blank page, cover or another stem ends the group early, so a stem never
  reaches into the next part of the paper. A stem with no question after it yet is valid (the
  editor autosaves while it is being written); it prints without a lead line.
- The lead line is **derived** from the members' printed numbers (`stem_sentence`), never
  stored: "Use the information below to answer Question 7." / "Questions 12 and 13." /
  "Questions 3 to 5." `number_from` (Booklet B) applies.
- Numbering, section ranges and marks, totals and the cover's examiner table ignore the stem.
- Student paper: the stem prints before its first question, unnumbered, inside the marking
  margin when the section has one. It has `break-after: avoid`, so the paginator keeps it on the
  page of its first question (or first part). In a structured section, where each question
  starts a page, the stem starts the page instead and its first question follows it there.
- Answer key: the worked-solutions key repeats the stem above the first of its questions that is
  in the key, when `key_options.show_question` is on. The school (compact) key never prints
  question text, so no stem.
- Generated questions inside a group verify and get the wording check exactly as elsewhere.

## Editor

- **Insert ▸ Shared stem**: with the caret in a question, the stem goes above it (that question
  and the next share it); otherwise after the current block. The caret lands in the stem.
- The stem shows its lead line live, "N questions", **−** (let the last question go) and
  **+** (take in the next one), and **Delete stem** (its questions stay). All are real buttons.
- Its questions carry a bar down their left (a node decoration).
- Membership follows the questions through edits (`keepMembers`, an `appendTransaction`): the
  group ends at the last of its old questions still after it, so deleting a question does not
  pull the next one in, and a question inserted or moved between two of its questions joins.
- Moving a question (its menu, or its shortcut) at a group's edge steps it out of or into the
  group first: down from the last place lets it go, up from just below takes it in.

Not done: copying the stem into a question's bank entry, and a generator for linked questions
(P8 coverage could add blueprints that produce a stem and its questions together).
