# Our generated papers vs real P6 papers (O4)

The O4 comparison (EXA-128, 2026-11-16). A full P6 exam set from the app (seed 20261116: Paper 1
Booklet A, Booklet B, Paper 2, student and key PDFs) was compared with four real 2025 P6
preliminary examinations (Ai Tong, Anglo-Chinese, Catholic High, CHIJ St Nicholas Girls'). The
real papers are copyrighted and kept local and untracked (`papers/`, see `papers/INDEX.md`
there); this document records **findings only**: no question text or artwork is reproduced.
Standard cover boilerplate (e.g. "Do not turn over this page until you are told to do so") is
quoted where it is the finding.

Two independent passes: layout and visuals (both sides' pages viewed as images), and content
(our documents vs the 12 transcripts). Each ends with a ranked change list; the cards on the
board (EXA, epic E15) are taken from them. Already fixed from this round: the answer leak in
bar models (EXA-132, #202), the cover replaced by a toolbar insert (EXA-129, #203), maths in a
fallback font (EXA-130, #204), a "4/1" option and raw LaTeX in working steps (EXA-131/133, #205).

---

# Part 1 — layout and visuals


Compared: our `p1_booklet_a` (5 pp), `p1_booklet_b` (9 pp) and `p2` (15 pp) student PDFs plus their keys, against
Ai Tong (AT), Anglo-Chinese Junior (ACS), Catholic High (CHS) and CHIJ St Nicholas (SN) 2025 P6 prelims (layout notes in
`docs/planning/editor/papers/*-layout.md`; pages checked by eye: AT p1, 3, 4, 13, 15, 23, 27, 32, 39; CHS p1, 2, 3, 9, 10, 11,
19, 20, 23, 28, 35; ACS p10, 12, 20, 23; SN p13, 37). "ours p.N" means the PDF page. The sgexams watermark is ignored.
No question text or artwork from the real papers is copied here.

## 1. Summary

The overall structure is close: three booklets on A4, a cover with numbered instructions, Booklet A as four-option MCQ,
right-aligned `Ans:` lines with units printed, a "Do not write in this space" strip, a diagonal per-page tally box, and
Paper 2 numbered from 1 with `[n]` marks. These are all recognisably right. What still separates our papers from a real
school paper is mostly finish, not structure:
(1) the figures leak answers and their labels collide with the drawing; (2) the pages use colour (blue figures, red marks,
grey boxes, a green key) where real papers are black on white for photocopying; (3) Booklet B numbering restarts at 1 instead of
continuing 16–30; (4) unused space is left as blank page instead of becoming working space, there are no page numbers or end
markers, and empty placeholders print in Booklet A; (5) the cover and section headers lack the real fields (school, exam,
date, question count, parent's signature, page count) and the standard "Questions x to y carry n marks each" wording.

## 2. Comparison table

| Aspect | Real papers (consensus; disagreements noted) | Ours | Gap | Suggested change |
|---|---|---|---|---|
| **Cover: title block** | Crest, then centred bold: school name, "PRELIMINARY EXAMINATION (2025)", "PRIMARY 6/SIX", "MATHEMATICS", "PAPER 1", "(Booklet A)". All 4. | "Primary 6 Mathematics" / "Paper 1 (Booklet A)" only (ours p1 of each). No school, exam name, year or date. | High | Print the authored school, exam, year and date fields (P7 already stores them; they appear unused here or were left empty). Add an optional crest image slot. |
| **Cover: fields** | Name ______ ( ) with brackets for the register number (AT, CHS, SN B/P2); Class: Primary 6 ____; Date; Parent's signature on most covers (AT all, CHS all, ACS P2, SN P2); CHS/SN print "15 questions / 20 marks". | Name line, Class line, separate "Register No." line; "Time: 1 h  Total: 20 marks" centred. No date, parent's signature or question count. | Medium | Name line ending in "( )"; "Class: Primary 6 ____"; add Date, "n questions", "Parent's signature: ____" (toggle). |
| **Cover: time wording** | Paper 1 time is shared and says so: "Total time for Booklets A and B: 1 hour" (all 4). Paper 2: "Time: 1 hour 30 minutes". | Booklet A and B each say "Time: 1 h", which reads as 1 h each. | Medium | Say "Total time for Booklets A and B: 1 h" on both Paper 1 covers. |
| **Cover: instructions** | "INSTRUCTIONS (TO CANDIDATES)", bold and underlined; numbered (AT, ACS) or unnumbered (CHS, SN). Standard lines: "Do not turn over this page until you are told to do so.", "Follow all instructions carefully.", "Answer all questions.", then a booklet-specific line (OAS shading for A; dark blue or black ballpoint pen, no correction fluid or tape, no highlighters for B and P2), and the calculator line with **NOT** bold and underlined. | Numbered list, heading bold but not underlined. Booklet A line 4: "For each question, choose the correct answer." (no OAS or bracket instruction). "not" is plain. Paper 2: "You may use a calculator." | Medium | Underline the heading; bold and underline "NOT"; Booklet A: "Shade your answers on the Optical Answer Sheet (OAS)" or "Write the number of your answer in the brackets"; add pen and correction-fluid lines to B and P2; Paper 2: "The use of an approved calculator is allowed/expected, where appropriate." |
| **Cover: examiner's table** | Two columns, part name and a score cell split by a diagonal with the maximum in the lower right. Booklet A cover: none (CHS, ACS, SN) or a single /20 cell (AT). Booklet B cover: A /20, B /25, Total /45 (CHS, SN). Paper 2 cover: whole-exam table P1 /45 (or A/B split), P2 /55, Total /100 (all 4; ACS uses a four-column Paper/Booklet/Possible/Obtained grid). | Three-column "Marks obtained / Marks available" table, with only this booklet (Booklet A /20, Booklet B /25), and Section A /10, Section B /45 on Paper 2. Never the whole-exam total. | Medium | Diagonal-split score cell style. Booklet B cover: rows A, B, Paper 1 total. Paper 2 cover: P1, P2, Total /100 (needs the paper set, or an authored "other papers" row). |
| **Cover: page count line** | "This booklet consists of N printed pages (and 1 blank page)." at the bottom (CHS, ACS, SN). | None. | Low | Derive it from the paginator and print it at the bottom of the cover. |
| **Blank pages** | Back of each cover is blank, either empty or "- BLANK PAGE -" (AT, SN); a trailing blank page so the booklet has an even page count (AT, CHS, ACS, SN). | No blank pages in any of the three PDFs. | Low | Template option: blank back of cover and pad to an even page count (P7 `blankPage` exists; use it in templates). |
| **Page size, margins** | A4 portrait, about 15–20 mm side margins. | A4 (595.9 × 842.9 pt); about 16 mm sides, 20 mm top. | None | |
| **Fonts and type size** | Arial or Helvetica-like, about 10–11 pt, all black; bold only for numbers in headers. | Inter, about 11.5–12 pt; question numbers grey; marks red; headers grey. Maths fractions used a serif fallback (NotoSansMath / NotoSans embedded; e.g. ours Booklet A p3 Q8 options, p2 Q2) — fixed since in #204 (EXA-130). | Low (font), Medium (colour, see below) | Keep Inter (EXA-94) but set the print body to about 11 pt and make all text black. Fix the maths font fallback separately. |
| **Colour** | Monochrome throughout (papers are photocopied). Figures are black line art; charts use hatching or outline sectors; some grey table headers. | Blue strokes and pale-blue fills on every geometry, solid and bar-model figure; pie charts told apart only by blue or grey tone (ours B p7, P2 p3); red `[n]`; grey rounded working boxes; green key panels. | High | Add a print-monochrome theme as the default for PDF: black strokes, white or very light-grey fill, black marks. Pie: outline sectors with labels inside, or hatching. |
| **Question numbering** | Booklet B continues from Booklet A (16–30) in all 4; Paper 2 restarts at 1. Style: "1" plain (AT, ACS) or "1." (CHS, SN); always black. | Booklet B restarts at 1 (ours B p2–p9: Q1–15). Paper 2 at 1 (correct). "1." style in grey. | High | Paper 1 numbering continues across booklets (a template `number_from`, or a Paper 1 document holding both booklets). Black numbers. |
| **Density** | Booklet A: 2–3 MCQ per page (7–8 pp). Booklet B: 2–3 per page (1-mark), 2 per page (2-mark). Paper 2 Q1–5: 1–2 per page. Paper 2 Q6–17: one question per page, page filled with working space. | Booklet A: 3–5 per page (4 pp of questions). Booklet B: 3, 3, 2, 2, 1, 1, 2, 1 per page. Paper 2: 1, 2, 1, 1, 1, 2, 2, 1, 1, ... Many pages end 40–60% empty (ours B p6, p7, p9; P2 p2, p4, p5, p10, p12). | High | When the next question will not fit, stretch the last working space on the page to fill the rest (real papers do this), instead of leaving a white gap under a small box. |
| **Working space** | Plain white space between stem and `Ans:` line; no box. About 1/3 page (Booklet B), 1/2 page (P2 Q1–5), about a full page per question or 1/3–1/2 per part (P2 Q6–17). Questions separated by a full-width rule (AT, CHS). | A grey rounded bordered box, about 1/6–1/4 page whatever the marks (P2 Section B 3–4-mark questions get the same box as 2-mark ones). No rule between questions. | Medium | Drop the box border in print (or make it optional). Scale default space by marks and section. Add an optional thin rule between questions. |
| **Answer line** | Right-aligned, short (about 4–6 cm): "Ans: ________ unit"; "$" before the line; parts "Ans: (a) ____". Bottom of the working space. | `Ans:` at left with a full-width line (about 13 cm); unit and `$` printed correctly; parts "Ans: (a)". Units render as "cm²" with a raised 2 at a different size (ours P2 p4, p13). | Medium | Right-align a short fixed-width line (about 55 mm), as the real papers do. |
| **Marks placement** | Booklet A, Booklet B and P2 Q1–5: no per-question marks, only in the section header. P2 Q6–17: "[n]" right after each `Ans:` line, per part. (One stray "[2m]" in ACS.) | `[n]` in red on every question: beside the stem in Booklet A, after the `Ans:` line elsewhere. | Medium | Per-section marks placement: `none` for MCQ, 1-mark and 2-mark sections; `answer` for structured. Default the P8 templates to the real pattern. Black text. |
| **Section headers** | No "Section A/B" labels. AT: "Paper 1 Booklet A" (bold underlined) then a paragraph. All: "Questions **1** to **10** carry 1 mark each. Questions **11** to **15** carry 2 marks each. For each question, four options are given. One of them is the correct answer. Make your choice (1, 2, 3 or 4) and shade your answer on the Optical Answer Sheet." with "(20 marks)" right-aligned on the last line, then a full-width rule. Booklet B has two headers (Q16–20 at 1 mark, "(5 marks)"; Q21–30 at 2 marks, "(20 marks)"). P2 has two (Q1–5; Q6–17 "The number of marks available is shown in brackets [ ] ..."). CHS adds "All diagrams are not drawn to scale." | Bold title "Booklet A" / "Section A", a grey meta line "Questions 1–15 · 20 marks · Multiple choice", a one-line italic instruction, then a rule. Booklet B is one section (1- and 2-mark questions mixed under one header). | Medium | Generate the header as a sentence from the derived range and marks ("Questions 16 to 20 carry 1 mark each. ... (5 marks)"), with marks right-aligned. Split Booklet B into a 1-mark and a 2-mark section in the template. Drop the "Section A/B" labels and the meta line from print. |
| **MCQ option layout** | Single vertical column "(1)" ... "(4)" under the stem (all 4 for text options). 2×2 grid or a row only for picture options. No answer brackets on the paper (all 4 use a separate OAS). | 2×2 grid for every question (ours A p2–p5), bold option numbers. No OAS or bracket, so nowhere to record the answer. | Medium | Default to one column for text options; 2×2 when options are short or pictures. Either say "shade on the OAS" on the cover and header, or offer an answer bracket "( )" at the right of the last option (common in school worksheets). |
| **Unfilled placeholders** | n/a | Booklet A Q9 and Q10 print as empty grey boxes with `Ans:` lines inside an MCQ booklet (ours A p4). | High | Block export (or warn loudly) while `unfilled_placeholders` is non-empty; never print an empty placeholder as a free-response box in an MCQ section. |
| **Figures: correctness of what is shown** | A figure gives only what the stem gives. | Bar models print the solution: "1 unit = $25" (A p5 Q14), "1 unit = $49" (B p6 Q11), and on P2 p13 Q15 "Devi = $216", "1 unit = $36" and unit counts "= 2u"/"= 3u". The answer to the question is on the student paper. | High | Student-mode bar models must hide derived values (unit value, unknown totals, answer); show only givens and a "?" for the unknown. Add an invariant: no answer value in the student SVG text (like `leaked_hidden_values` for charts). |
| **Figures: label placement** | Labels clear of strokes; angle values inside arcs; vertex letters outside the vertex. | Collisions: "5 cm"/"3 cm" sit over the rectangle's right edge (A p5 Q15, B p4 Q7); "8 cm" over the vertical side and "A" over the right-angle mark (P2 p4 Q4); "A" over the angle arc and "D" over the vertex (P2 p6 Q6); "O" over the arc (A p4 Q11); "A" over the arc (B p8 Q13); "5 cm" on the altitude and "A" on the vertex (P2 p11 Q13). | High | Offset side labels outward along the edge normal; place vertex letters outside along the angle bisector; collision-test labels against strokes in `diagram.py`. |
| **Figures: size and not-to-scale note** | Figures roughly the width of the text column, or beside the stem; "not drawn to scale" either in the section header (CHS) or the stem. | Size is reasonable, though figures are left-aligned with empty space to the right. The note is a parenthetical in the stem. | Low | Optionally move the note to the section header; centre or float small figures. |
| **Marking margin** | AT: none. CHS, SN: a continuous right strip (vertical rule) down the whole page, caption "Do not write in this space" set horizontally at the top. CHS puts an empty square in the strip beside each `Ans:` line. ACS: strips on both sides, rotated caption. Never in Booklet A. | A right strip drawn as one short vertical rule per question (with gaps between), and the rotated grey caption repeated beside every question (B p2–p9, P2 p2–p15). Not in Booklet A (correct). | Medium | One continuous strip per page from header rule to footer; caption once at the top; optional per-question score box beside each `Ans:` line (CHS style). |
| **Tally box** | AT, SN: a small (about 12 mm) per-page box at the bottom right beside the footer (AT diagonal with the page maximum; SN labelled "MARKS:"). ACS: "Sub-Total: [ ]" per page. CHS: none per page, but a section tally "Total marks for questions 16 to 20" with a diagonal box /5. | Per-page diagonal box, about 20 mm, page maximum lower right (B and P2). Matches AT, but floats alone with no label or footer. | Low | Shrink to about 12 mm, sit it on the footer line, and add an optional "Marks:" / "Sub-total:" label. Optionally offer the CHS-style section tally after the last question of a section. |
| **Headers and footers** | Printed page number on every question page (centre bottom, or top for ACS). "(Go on to the next page)" at the bottom right (CHS every page; ACS some). A footer tag such as "ATS 2025 P6 Math Prelim Paper 1" (AT). End markers: "End of Booklet A", "END OF BOOKLET B / END OF PAPER 1", "End of Paper" (all 4). | No page numbers, footer, "Go on" or end marker on any page. | High | Footer: centred page number (optionally "Page x of y"), optional left tag (school, year, paper), "(Go on to the next page)" except on the last page; "End of Booklet A/B" or "End of Paper" after the last question. |
| **Answer key format** | Separate typed key at the end. Header block "SCHOOL : / LEVEL : / SUBJECT : / TERM :". Booklet A: a compact grid, Q1–Q10 / Q11–Q15 with the option number under each. Booklet B and P2: a two-column table (Q label, then working lines with "ANS : ..." right-aligned); SN uses four columns (two questions per row). No M/A scheme. About 6 pages for the whole exam. | Per-booklet key that repeats each full question, its figure and options (correct option underlined), with a green-tinted panel of numbered steps, "Answer:" in green and M1/A1 badges. 2–3 questions per page: 7 pp for 15 MCQ, 6 pp Booklet B, 10 pp Paper 2 (23 pp in total). | Medium | Add a compact key layout: header block, MCQ answer grid, two-column table of working plus a right-aligned "Ans:", monochrome. Keep M1/A1 as an option (it is a plus over the real keys). P5 `show_question:false` exists; the MCQ grid is new. |
| **Key typography bugs** | n/a | Raw carets: "Answer: 60 cm^2" (P2 key p2), "Answer: 112 cm^2", "in cm^3" in mark-scheme text (P2 key p3; B key p4). Mixed "x" and "×" in working ("speed x time"). Hyphen as minus ("30 - 20"). | Medium | Normalise units ("^2" to "²") and operators (× for multiplication, − for minus) in solution and scheme templates, and add a lint check that no "^" reaches rendered text. |

## 3. Ranked changes (most teacher-visible first)

1. ~~**Stop bar models leaking the answer.**~~ Fixed in #202 (EXA-132). In student mode, hide unit values and derived totals ("1 unit = $…", the answer
   amount) and show "?" for the unknown. Add an invariant that no answer value appears in student SVG text (ours A p5,
   B p6, P2 p13).
2. ~~**Continue Paper 1 numbering into Booklet B (16–30).**~~ Done in #209 (EXA-134): `settings.number_from`, 16 on the Booklet B template. Add a numbering offset or a "continues from" field on the Booklet B
   template, used by the cover, section header ranges and the key.
3. ~~**Monochrome print theme as the PDF default.**~~ Done in #212 (EXA-135). Black strokes, white or light-grey fills, hatched or outlined pie sectors,
   black marks and question numbers, no grey working boxes or green key panels.
4. ~~**Fix figure label collisions.**~~ Done in #213 (EXA-136); the editor and Classic page show the same engine drawing since #218 (EXA-151). Offset edge labels outward, put vertex letters outside along the bisector, keep angle values
   clear of arcs; add a label-vs-stroke overlap test in `diagram.py`.
5. ~~**Never print empty placeholders.** Block or warn on export when `unfilled_placeholders` is non-empty, especially inside an
   MCQ section (ours A p4 Q9–Q10).~~ Done in #211 (EXA-137): export asks first (Fill them / Print anyway); printed anyway, an
   MCQ placeholder is a numbered gap with no `Ans:` line.
6. ~~**Page furniture.** Page number on every question page, "(Go on to the next page)" except on the last page, "End of
   Booklet A/B" / "End of Paper", and an optional footer tag (school, year, paper).~~ Done in #220 (EXA-138): the cover
   counts as page 1; the key's pages are numbered too.
7. ~~**Fill the page with working space.** When the next question moves to a new page, stretch the last question's working space
   to the bottom margin. Give Paper 2 structured questions a page each by default.~~ Done in #220 (EXA-138): a structured
   section gives each question a page (no per-section switch yet).
8. ~~**Real section-header wording.** Generate "Questions X to Y carry n mark(s) each. ... (N marks)" with marks right-aligned and
   a rule beneath. Split Booklet B into 1-mark and 2-mark sections. Drop "Section A/B" and the meta line from print.~~ Done in
   #214 (EXA-139): a teacher's own section title still prints, generic ones do not.
9. ~~**Marks placement per section.** No `[n]` in MCQ, short-answer and 2-mark sections; `[n]` after the `Ans:` line only in the
   structured section. Default the P8 templates to this.~~ Done in #214 (EXA-139): `section.marks_placement`, schema 1.13.0;
   the editing page shows it per section too since #219 (EXA-152).
10. ~~**Short right-aligned `Ans:` line.** About 55 mm, unit after the line, `$` before; borderless working space.~~ Done in
    #214 (EXA-139).
11. ~~**Cover fields.** School, exam name and year, date, "Total time for Booklets A and B: 1 h", "n questions", Name with
    "( )" for the register number, Parent's signature, page-count line, underlined heading, and **NOT** bold and underlined.~~
    Done in #222 (EXA-140): the crest image is not built.
12. ~~**Examiner's table.** Diagonal-split score cells. Booklet B cover: A, B, Paper 1 total. Paper 2 cover: P1, P2, Total /100.~~
    Done in #222 (EXA-140): the other papers' maxima are the templates' standard ones; Booklet A has no table by default.
13. ~~**MCQ options in one column** for text options (2×2 only for short or picture options), and a recording method: OAS wording
    in the cover and header, or an optional "( )" answer bracket.~~ Done in #223 (EXA-141): one column for all text options
    (all 4 schools do so even for short numbers), 2×2 for picture options; numeric options ascending; the OAS sentence ends
    the Booklet A header.
14. ~~**Continuous marking strip.** One rule per page with the caption once at the top; optional per-question score box beside each
    `Ans:` line (CHS style); smaller (about 12 mm) labelled tally box on the footer line.~~ Done in #220 (EXA-138): strip
    and 12 mm tally on the footer line; the CHS score box and a tally label are not built.
15. ~~**Compact answer key.** Header block, Booklet A answer grid, two-column working table with "Ans:", optional M1/A1. Fix the
    raw `^2`/`^3` and the x/- operators in key text.~~ Done in #221 (EXA-142): `key_options.layout: compact`, schema 1.14.0;
    units print cm²/cm³, operators × and −, angles 51°, with a lint test over every blueprint.
16. **Blank pages and type size.** ~~Blank back of cover and pad to an even page count via templates;~~ (done in #222,
    EXA-140) body text about 11 pt; maths fonts fixed in #204
    serif fallback (known bug).

---

# Part 2 — content


Inputs: our one generated P6 set (`ours/p1_booklet_a.json`, `p1_booklet_b.json`, `p2.json`, plus the
student/key PDFs) against the transcripts of Ai Tong (AT), Anglo-Chinese (ACS), Catholic High (CH) and
CHIJ St Nicholas (SN), 2025 Preliminary Examination, Papers 1A, 1B and 2 (47 questions and 100 marks each).
Real question text is not reproduced here; question types are described abstractly.

## 1. Summary

- **The structure matches, but the content is not yet realistic.** Marks per section and the slot pattern
  match the real papers exactly (A 10×1 + 5×2, B 5×1 + 10×2, P2 5×2 + 45 marks). The content behind
  them does not match yet.
- **About 28% of the real questions (52 of 188) are in topics we have no blueprint for.** These are grid
  geometry (drawing, symmetry, directions, parallel and perpendicular lines), measurement and time,
  nets and solids, number patterns, and money heuristics (supposition, coins, excess and shortage).
- **Paper 2 Section B is too shallow.** Real papers have 8–10 multi-part questions out of 12; ours has 3.
  Our 9 single-part stand-ins take 1–2 steps but are worth 3–4 marks each, while real 3–5-mark items
  take 4–8 lines of working and a named heuristic.
- **Too few figures.** 60% of real questions carry a figure (112 of 188), against 40% of ours (18 of 45).
  The figure kinds we lack are square grids, tables, nets, cube stacks, number lines, patterns and
  measuring scales.
- **Booklet A's 2-mark MCQs are filled with the easy rung.** One example is a one-step distance =
  speed × time question worth 2 marks. Real 2-mark MCQs are multi-step heuristic problems, such as age
  ratios, fraction transfers and composite circles.
- **Our MCQ options look different from real ones.** Real numeric options are almost always in ascending
  order (about 36 of about 40); ours are shuffled. A few of our distractors are implausible.
- **Critical defect: the student paper shows bar models with answer values on them.** On the student paper, the
  bar models of `ratio_easy` and `ratio_hard` print "1 unit = $25" (P1A Q14), "1 unit = $49" (P1B Q11)
  and "Devi = $216", which is the answer (P2 Q15). Real papers never print a model in the question.
- **Our answer key gives more than any real key.** Real keys give option numbers for Booklet A and
  working with a final answer elsewhere, with no M/A marking scheme. Ours adds numbered steps and M1/A1
  marking points.

## 2. Composition

### 2a. Per paper part

| | AT | ACS | CH | SN | **Ours** |
|---|---|---|---|---|---|
| **P1 Booklet A**: questions / marks | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 (13 generated + **2 empty 1-mark placeholders**) |
| A: 1-mark × 10, 2-mark × 5 | yes | yes | yes | yes | yes |
| A: MCQs with picture options (nets, pie charts, graphs, solids, shading) | 3 | 2 | 2 | 0 | 0 |
| A: questions with a figure | 6 | 9 | 9 | 8 | 6 |
| **P1 Booklet B**: questions / marks | 15 / 25 | 15 / 25 | 15 / 25 | 15 / 25 | 15 / 25 |
| B: 2-mark questions with two parts (part marks not printed) | 2 | 4 | 3 | 3 | **0** |
| B: answer drawn, shaded or measured on a figure | 2 | 2 | 3 | 1 | **0** |
| B: questions with a figure | 11 | 10 | 7 | 7 | 6 |
| **P2 Section A** (Q1–5, 2 marks each) | 5 single | 5 single | 4 + 1 two-part | 5 single | 5 single |
| **P2 Section B** (Q6–17, 45 marks): questions | 12 | 12 | 12 | 12 | 12 |
| B: multi-part / single-part | 8 / 4 | 10 / 2 | 8 / 4 | 9 / 3 | **3 / 9 (stand-ins)** |
| B: total parts | 21 | 24 | 20 | 26 | 15 |
| B: questions with 3–4 parts | 1 | 2 | 0 | 4 | 0 |
| B: marks mix 3 / 4 / 5 | 6 / 3 / 3 | 6 / 3 / 3 | 5 / 5 / 2 | 6 / 3 / 3 | 5 / 5 / 2 |
| P2 questions with a figure (of 17) | 11 | 10 | 12 | 12 | 6 |
| **Whole set: questions with a figure** (of 47) | 28 | 29 | 28 | 27 | 18 of 45 |

How the marks are split across parts:
- **Real papers** use many splits: 1+2 (most common), 2+2, 2+3, 1+3, 3+2, 1+4, and 1+1+2, 1+2+1,
  1+1+1+2 for 3- and 4-part questions. A cheap 1-mark lead-in part often reads a value off a chart or
  table, or expresses a quantity in terms of a letter.
- **Ours** has only 1+3 (speed), 2+3 (ratio) and 2+3 (volume).

### 2b. Topic coverage (one primary topic per question)

| Topic | AT | ACS | CH | SN | Real avg / set | **Ours** | Blueprint? |
|---|---|---|---|---|---|---|---|
| Whole numbers (numerals in words, rounding, order of ops, factors/HCF) | 3 | 3 | 4 | 3 | 3.3 | 3 | partial (order of ops, remainder, excess-shortage only) |
| Fractions (compare/order, number line, ÷ whole, of remainder, shaded) | 6 | 4 | 6 | 3 | 4.8 | 4 | partial |
| Decimals (place value, compare, round, ÷) | 1 | 3 | 1 | 2 | 1.8 | 4 | partial (no compare/round/place value) |
| Percentage (conversion, discount, GST, increase/decrease, reverse) | 2 | 2 | 2 | 3 | 2.3 | 4 | partial (no discount/GST/successive) |
| Ratio (incl. area ratio, age, successive cuts) | 4 | 2 | 1 | 2 | 2.3 | 4 | yes |
| Rate (tiered charges from a table, rental, filling rate) | 1 | 1 | 2 | 2 | 1.5 | 4 | yes |
| Speed | 1 | 1 | 2 | 1 | 1.3 | 4 | yes (over-represented) |
| Average | 1 | 1 | 1 | 2 | 1.3 | 2 | yes |
| Algebra (substitution, "in terms of", table + letter) | 2 | 2 | 2 | 2 | 2.0 | 2 | partial (numeric answers only) |
| Angles (folding, rhombus/trapezium/parallelogram, reflex) | 5 | 3 | 2 | 6 | 4.0 | 3 | partial |
| Area & perimeter (rectilinear, overlap, tiles) | 3 | 2 | 2 | 1 | 2.0 | 3 | partial |
| Circles (semi/quarter composites, π terms, π = 3.14) | 2 | 2 | 2 | 2 | 2.0 | 1 | weak (one rung, π = 22/7) |
| Volume (tanks, transfer, taps, upside-down container) | 3 | 2 | 1 | 2 | 2.0 | 4 | yes |
| Data (tables, bar/line/pie, chart matching, T/F/NPT) | 4 | 5 | 1 | 5 | 3.8 | 3 | partial (chart readings only) |
| **Nets / solids / views / cube counting** | 2 | 2 | 2 | 1 | 1.8 | 0 | **none** (cube_stack renderer exists) |
| **Grid geometry** (∥/⊥, symmetry, 8-point directions, draw/measure) | 2 | 5 | 4 | 2 | 3.3 | 0 | **none** |
| **Measurement & conversion** (scales, ruler, estimate, ℓ/mℓ, kg/g, ordering) | 3 | 3 | 3 | 2 | 2.8 | 0 | **none** |
| **Time** (durations, timetables, start/end times) | 0 | 2 | 1 | 1 | 1.0 | 0 | **none** |
| **Patterns / sequences** (rods, dots and lines, tiling, general term) | 1 | 0 | 3 | 1 | 1.3 | 0 | **none** |
| **Money heuristics** (supposition, coins, equal number/amount, LCM packs, excess-shortage) | 1 | 2 | 5 | 4 | 3.0 | 0 | **none** (except `whole_numbers_hard`) |
| Placeholder (unfilled) | – | – | – | – | – | 2 | |
| **Total** | 47 | 47 | 47 | 47 | 47 | 47 | |

Topics with no blueprint account for 52 of the 188 real questions (13 a set, about 28%). We
over-produce several topics (ratio, percentage, decimals, speed, rate and volume at 4 each, against real averages of 1.3–2.3). Topic is also a weak
proxy for coverage: even within topics we "cover", the real subtypes are mostly missing. Examples are
fraction comparison and ordering, number-line reading, discount and GST, and reflex or folded angles.

## 3. Question style

- **Names and contexts.**
  - Both use multicultural Singapore names, and ours are fine.
  - Real contexts are more varied and local: water and electricity tariffs with GST, postage tables,
    bus timetables, rental rates, brochures with price tags, fixed pack sizes, and stacking objects.
  - Ours are generic: folding cranes, spelling tests, a car park, a rope cut into pieces.
- **Numbers and units.**
  - Real items mix units in one question (subtracting grams from a mass given in kg; adding minutes to a duration in h and min). They ask for
    answers in a stated unit or format ("in h and min", "in min", "to 1 decimal place", "to the nearest
    percent"). Numbers run to 4–5 digits and up to 3 decimal places.
  - Ours keep one unit throughout, with small whole numbers.
- **Answer blanks and instructions.**
  - Both print "Ans: ____ unit" with the unit after the blank, so that matches.
  - Real papers use "Leave your answer in terms of π" 2× and "in terms of n/p/w/y" about 6×, but have
    no blueprint that asks for either. The `expression` answer type exists (T5), but every algebra
    blueprint is numeric.
  - π: real papers say "Take π = 3.14" 7× and 22/7 once or twice. Our only circle item uses 22/7.
  - We append "(The figure is not drawn to scale.)" to every geometry stem. Real papers print it about 4 times in total.
  - MCQ leak: our MCQ version of `fractions_easy` keeps "Give your answer in its simplest form", which
    makes no sense when the options are given.
- **Shared stems.**
  - Real: Section B multi-part questions share a stem with data, a figure or a table.
  - Real: SN twice uses a shared lead-in for two consecutive numbered questions ("Use the information
    below to answer Questions 9 and 10", and again for 21 and 22).
  - Ours: 3 shared stems, no cross-question lead-ins.
- **Figures.**
  - **Kinds in real papers:** geometric composites (about 35), tables (about 15, some for the pupil to
    tick), square or dot grids for reading or drawing (about 12), line, bar and pie charts (about 14),
    3D solids and containers (about 12), nets (3), number lines (2), and pattern pictures (3) — about 108 of the 112 figures; the rest are hard to classify.
  - **More kinds in real papers:** measuring scales, rulers and beakers (about 4), and context pictures (about 8).
  - **Ours:** geometry figure, chart, solid, shaded-fraction strip, and bar models (which should not
    appear in the question at all).
- **Tasks we cannot express at all.**
  - Tables the pupil completes: True / False / Not possible to tell appears in 3 of 4 schools (AT P2
    Q6b, CH B Q24, SN P2 Q8b).
  - Drawing or shading on a grid: shade squares for symmetry, complete a trapezium, rhombus or net,
    draw a front or side view.
  - Measuring with a protractor or ruler.
- **"Show your working."** Both put it in the section instructions, so they match.

## 4. Difficulty and reasoning depth

- **1-mark questions.**
  - Real 1-mark questions are mostly recall and concept: numerals, rounding, comparing fractions,
    conversion, estimating a mass or length, reading a scale, and the net of a cube.
  - Ours are one-step computations (rate × time, average of three numbers, order of operations). That
    is a reasonable but narrower fit.
- **2-mark questions in Booklet A (MCQ).**
  - Real ones are the hardest items per mark in Paper 1. Examples: an age ratio across two time shifts
    (AT Q15); flour shared until three people hold equal amounts (ACS Q15); a perimeter of
    composite semicircles in terms of π (AT Q13, CH Q14); an area ratio of nested triangles (AT Q14);
    the HCF of two packing quantities (SN Q15).
  - Ours are all easy rungs: d = s × t, 75% of $80, sharing in a ratio, the area of a rectangle, and
    angles on a line.
- **2-mark questions in Booklet B.**
  - Real ones need two or three steps with a twist. Examples: a fraction of a remainder worked
    backwards (AT Q30, SN Q30); a tiered postage table (CH Q22); a calculator-slip reversal (ACS Q22);
    an at-least-k-between spacing problem (CH Q29); a successive discount (ACS Q28); and angles in folded
    paper (AT Q24, ACS Q29).
  - Ours are mostly one or two steps.
- **Paper 2 Section B.**
  - **Our hardest items:**
    - Before–after ratio with one quantity unchanged (4 marks, 4 steps).
    - Ratio difference then transfer (5 marks).
    - Tank-to-tank water level (5 marks).
    - Round-trip average speed (4 marks).
    - Several stand-ins are one or two steps but worth 3–4 marks. Examples: a 35% decrease (3 marks),
      a reverse percentage (4 marks, 2 steps), and a composite area of a triangle plus a semicircle
      (4 marks).
  - **Real top items** (5 marks, 6–10 lines of working, a named heuristic):
    - Three people with equal numbers of coins in mixed denominations, answered by supposition
      (AT Q16, CH Q17).
    - Fraction-of-remainder spending linked to unit costs (CH Q16, SN Q16).
    - Bottles of juice with excess and shortage over fractions of a remainder (ACS Q17).
    - Equal number versus equal amount spent at two prices (CH Q15).
    - Overlapping quarter circles given a shaded area and perimeter (ACS Q15).
    - Tiling a footpath, then the uncovered area and the cost (SN Q17).
    - A tank filled from a line graph, with the time to fill (CH Q12, SN Q13).
    - Grid drawing in 4 parts (SN Q15).
  - Ours are noticeably more formulaic. Every item is a single-topic template; none combines topics,
    such as fraction + money + rate, or data + percentage + money.

## 5. MCQ

- **How real distractors are made:**
  - Partial-step values, such as the first step of a percentage-of-remainder problem.
  - Place-value shifts (options differing by powers of ten) and unit confusions (g vs kg).
  - Structural slips, such as a perimeter with or without the straight edges, or a whole perimeter versus half of it, in terms of π.
  - Picture options for nets, pie charts, solids, graphs and shaded figures.
- **How real options are laid out:** all four share one format and unit. Numeric options are almost
  always in ascending order: about 36 of about 40 numeric-option MCQs; the rest are mostly
  mixed-unit or ratio lists.
- **Our distractors:** they come from per-solver wrong turns, which is the same idea as the real
  partial-step and slip distractors. Most are plausible (for example "the amount in 1 hour", or
  "added instead of multiplied").
- **Our problems:**
  - ~~**Options are shuffled, not sorted.**~~ Sorted ascending since #223 (EXA-141).
  - **Some distractors are implausible:** 4/1 for a shaded fraction (fixed in #205), 243° for an angle on a straight
    line, 234 for m/6 + 18.
  - **Several MCQs are converted from 1-step easy questions**, even in 2-mark slots.
  - **No picture-option MCQs.**
  - **No statement-type MCQs**, such as "which statements are true" (ACS Q14).

## 6. Answer key

| | Real (4 schools) | Ours |
|---|---|---|
| Booklet A | Option numbers only | Correct option + steps + "A1/A2" with a note on why each wrong option is wrong |
| Booklet B / Paper 2 | Working lines + final answer: AT, ACS ("ANS :"), CH. SN often gives working with no final answer stated | Numbered steps + "Answer:" + M1/A1 marking points per part |
| Marking scheme | None printed (CH explicitly has none); per-part marks sometimes missing | Always, and it sums to the marks |
| Drawing answers | Key reproduces the completed drawing or ticked table | n/a (no such items) |
| Errors | Several slips copied as printed (e.g. AT, CH, SN keys) | Engine-proven; one cosmetic issue: a scheme description prints "cm^3" literally (P2 Q5) |

Our key is a strength. The only gap is that it cannot show drawn or ticked answers, because we have no
such items.

## 7. Ranked content gaps → suggested blueprints and features

0. ~~**(Defect) Bar models leak the answer on the student paper.**~~ Fixed in #202 (EXA-132).
   - What: `ratio_easy` and `ratio_hard` print "1 unit = $…", "Devi = $216" and "= 2u / = 3u" labels
     in the question figure.
   - Fix: do not render solution models on student or MCQ papers, or move them to the key only.
   - Real papers never print a model. No new diagram is needed.
1. **Multi-part blueprints for P2 Section B built on real heuristics.** About 7 more are needed to reach
   8–10 per paper.
   - Candidates: supposition / coins with an equal count (3 parts); equal number vs equal amount at two
     prices; fraction of a remainder linked to unit costs; excess and shortage with fractions;
     constant-difference / constant-total transfers; LCM packs of m and n with a budget.
   - Give each a cheap 1-mark (a) and a 2–3-mark (b).
   - No new diagram.
2. **Square-grid geometry family:** ∥/⊥ identification, symmetry (shade k squares), 8-point compass
   directions and turns, area by counting squares, and completing a trapezium, parallelogram or rhombus.
   - Real: 13 questions, about 3 a set, in every paper part.
   - Needs a new `grid` diagram and a grid-cell or point answer type, which can be auto-checked as a cell set.
3. ~~**Booklet A number-sense and measurement 1-markers.** These fill the 2 placeholders and widen 1-mark coverage.~~
   Done in #216 (EXA-145): rounding, comparing decimals and fractions, km/kg/ℓ conversion and
   time durations; Booklet A now has no placeholders at P5 or P6. Not yet built: numerals ↔
   words, number lines, ordering mixed units, timetables, estimating.
   - Candidates: numerals ↔ words, rounding, place value / missing addend, compare/order fractions and
     decimals, fraction or decimal on a number line, unit conversion (km/m, ℓ/mℓ, kg/g, h/min),
     ordering mixed units, time durations and timetables, estimating a sensible mass or length.
   - Real: about 24 questions (6 a set).
   - Uses the existing `number_line` renderer; a scale/ruler reading needs a new small diagram.
4. ~~**Recalibrate rung to marks in the generator.**~~ Done in #225 (EXA-146): 2-mark slots take a
   medium or hard rung and 3+-mark slots a hard one whenever content allows (P8-SHAPING.md).
   - Booklet A 2-mark MCQ and Booklet B 2-mark slots should draw hard or multi-step rungs.
   - Section B 3-mark stand-ins should require 3+ steps.
   - Stop letting a one-step easy rung fill a 2-mark MCQ or a 4-mark slot (2 steps).
   - No diagram.
5. **Solids family: cube-stack views and counting.**
   - Draw or choose the front/side/top view; maximum or least cubes to add without changing the views
     or to make a cube; count cubes.
   - Real: 7 questions on nets, solids, views and cube counting (the topic table), of which 3 are nets.
   - The `cube_stack` diagram (T6) already exists unused, so views and counting need only blueprints.
   - Nets of a cube, cuboid or prism need a new `net` diagram.
6. **Data tables and a T/F/NPT tick table.**
   - Candidates: tiered tariffs with GST; postage, rental and timetables; a line graph of a filling
     tank leading to a rate and a time; pie charts in fractions and percentages; "which chart matches
     this data" MCQ.
   - Real: 15 data questions plus 3 tick tables.
   - Needs a `table` figure (simple) and a tick-table answer type.
7. **Circles ladder.**
   - Composite semicircles and quarter circles (overlapping, S-shapes, logos); perimeter vs area of the
     shaded or unshaded region; "in terms of π" answers through the existing `expression` type; default
     π = 3.14.
   - Real: 8 questions (2 per set, always present); ours: 1.
   - Extends `geometry_figure` with arc composites.
8. **Angles depth.**
   - Folded paper; rhombus, trapezium and parallelogram composites with isosceles or equilateral
     triangles; reflex angles at a point; 2-part angle questions for Section B.
   - Real: 16 questions (the most frequent single topic after fractions); ours: 3, at 1–2 steps.
   - Extends `geometry_figure`; folding needs a two-panel figure (`panels` exists).
9. **Patterns and sequences (figure n, general term, reverse lookup).**
   - Rods, dots and lines, tiling; often with a table to complete. Real: 5 questions, mostly 3–5-mark
     Section B items.
   - Needs a simple pattern-strip diagram (or the `panels` of small figures).
10. **Algebra "in terms of" answers.**
    - Express a total in terms of y/p/w, often as part (a) of a table question, then solve in part (b).
    - Real: about 6. The `expression` answer type exists; the algebra solvers currently force numeric answers.
    - No new diagram.
11. **MCQ polish.**
    - ~~Sort numeric options ascending.~~ Done in #223 (EXA-141).
    - Filter implausible distractors (angles over 180° for an angle on a line; the improper "4/1" is fixed in #205).
    - Drop "simplest form" wording from MCQ stems.
    - Add picture-option and "which statements are true" MCQs once the grid, net and chart families exist.
12. **Realism of wording and numbers.**
    - Mixed-unit inputs, answers requested "in h and min", rounding instructions, 4–5-digit numbers,
      local contexts (GST, tariffs, brochures).
    - Shared lead-ins across two consecutive questions.
    - Use "not drawn to scale" sparingly.
    - Rebalance the topic spread: speed, rate and volume are about 2× over-represented relative to the
      real papers.
