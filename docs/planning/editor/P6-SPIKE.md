# P6 pagination spike — findings (EXA-112)

Question from `PAPER-FORMAT.md`: the per-page tally box needs the marks of the questions on
each printed page, which only the print engine knows. Can we get that reliably from headless
Chromium, and what shape should P6 take?

**Answer: yes.** Measure the paper once, paginate it ourselves, and print explicit pages that
each carry their own tally box. On 12 random papers (103 questions, 5–13 pages each) that
produced exactly the predicted page count, every question on the page we said, every tally on
its page, and no lost text. Code: `scripts/spikes/p6_pagination.py`.

```
uv run --with pypdf python scripts/spikes/p6_pagination.py --papers 12
```

(`pypdf` is a spike-only dependency; ground truth is the real Chromium PDF read back as text,
one unique marker per question.)

## What was tried

| | Approach | Questions on the right page |
|---|---|---|
| A | **Naive**: `floor(top / page height)` on the continuous layout | 16 / 103 (16 %) |
| B | **Simulate** fragmentation over measured item boxes (questions atomic, `break-after: avoid` keeps a heading with the next item, forced breaks) | 99 / 103 (96 %) vs. today's plain PDF |
| C | **Explicit pages**: wrap each simulated page's items in a fixed-height `.pg` box with a tally box, print again | **103 / 103**, page count 12 / 12, tallies 12 / 12, 0 words lost |

- **A is useless.** Breaks push whole questions to the next page, so positions drift by a page
  or more within a few questions. Do not estimate from scroll offsets.
- **B is close, not exact.** It disagrees with Chromium's own fragmentation in ~4 % of
  questions (one paper came out a page longer than plain Chromium printed it). Chromium's
  margin truncation and orphan handling are not worth re-implementing.
- **C sidesteps the problem.** We do not need to predict what Chromium would do; we make the
  PDF *be* our pagination. Each `.pg` is `page height − 2 px` (so rounding never spills a blank
  page), starts with `margin-top: 0`, has `break-after: page`, and holds its tally box
  absolutely positioned bottom-right. Page 1 is shorter by the header above the first item.
  CSS counters, KaTeX and figures survive the wrapping.
- Consequence of C: with the tally on, a paper may paginate differently from today's plain PDF
  (about one page more in 1 of 12 here, because B is slightly conservative). With the tally
  off, do not wrap — keep today's output byte for byte.

## Hazard found: a question taller than a page is clipped

`.pg` uses `overflow: hidden`. A question taller than the 261 mm content area (e.g. 250 mm of
working space plus a long stem) lost its last words (the `Ans:` line) in every `--oversize`
run. Today Chromium splits such a question across two pages, so this would be a regression if
left as is. P6 must detect `item height > page height` in the measuring pass and then shrink
that question's working space by the overflow, and report it as a layout warning in the
editor. It must never clip silently.

## Recommended shape for P6

1. **The engine emits the paginator, the browser runs it.** `render_document_html` stays pure.
   For a paper with the tally/margin on it adds `data-marks` to each unit and a small inline
   script (hashed for CSP like the KaTeX bootstrap, see `inline_script_hashes`) that measures,
   paginates, wraps, injects tallies, then sets `data-paginated="true"`.
   `export.html_to_pdf` waits for that flag as it already does for KaTeX. The **Preview**
   iframe runs the same script, so the preview shows the exact pages the PDF will have, for
   free.
2. **Wait for layout to settle before measuring**: fonts (`document.fonts.ready`), KaTeX (the
   existing flag), and decoded images (`img.decode()`). Measure with the final CSS, including
   the right margin ("Do not write in this space"), since the margin narrows the text and
   changes heights.
3. **Units and marks.** A part's marks count on the page where its answer line falls. The spike
   treated each whole question as one unit (what `.question { break-inside: avoid }` does
   today). Allowing a multi-part question to split *between* parts means measuring `.part`s as
   units with the stem kept with part (a). That extension is straightforward in the simulator
   but was **not** tested here; build it with its own sweep.
4. **The WYSIWYG editor shows indicative frames only** (decision 4). It can run the same
   measure/paginate logic over its DOM for page dividers and a tally preview; the PDF and the
   preview stay authoritative.
5. **Test it like the engine's correctness**: a seed-sweep test that prints random papers and
   asserts, from the PDF text, that every question and every tally is on the page the paginator
   claimed and that no text is lost. This spike script is the starting point.

## Proposed slices after the spike

| # | Slice | Size |
|---|---|---|
| P6a ✅ | Marking margin ("Do not write in this space") and tally markup in `render`, per-section toggle, on by default for working sections | S–M |
| P6b ✅ | Paginator script + `data-marks`, PDF and preview, oversize clamp, seed-sweep test | M |
| P6c | Multi-part split between parts | S |
| P6d | Editor indicative page frames + tally preview | M |

## Design chosen for P6a (tweakable; all in `print.css`)

- **Marking margin**: a 22 mm ruled strip in the page's right margin, 2 mm clear of the text,
  one per question, running the question's full height, with "Do not write in this space" set
  vertically at 7 pt. The text column of those questions gives up 26 mm. It is on for sections
  in `short` or `structured` mode and off for `mcq` (decision 3), and each section can override
  it (`section.marking`). It prints on the student paper only, never in the answer key.
- **Tally box**: a 20 mm square with a 1.2 px border, a diagonal from bottom-left to
  top-right, the upper-left triangle blank for the marks awarded and the page's total
  available marks in the lower-right in 11 pt semibold. It sits bottom-right of the page,
  under the margin strip. `render.render_tally_box(total)` produces it; the P6b paginator places one per page.
- Every question in a marking section carries `data-marks`, which is what the paginator sums.

## As built in P6b

- `engine/exam_engine/assets/paginate.js` is the fourth inline script (CSP-hashed). It runs only
  on a paper the renderer flagged with `data-tally` on `<main>`: the student and full papers
  with at least one marking section. It waits for fonts, KaTeX and images, measures the blocks
  of `.doc-body`, simulates the page breaks, wraps each page in a fixed-height `.pg` box and
  adds a `.tally` box (cloned from `<template id="tally-template">`) when the page holds any
  marks. It always ends by setting `<html data-paginated="true">`; `export.html_to_pdf` and the
  CLI's `_pdf.py` wait for it.
- Every page keeps 22 mm clear at its foot for the tally box, so the pages are a little shorter
  than the plain PDF's. Papers without a marking section are not wrapped at all.
- Oversize: a block (with the heading kept before it) taller than the room is shortened by
  trimming its blank working space, never below 10 mm, and `data-pagination-warnings` is set
  on `<html>`. The sweep found the first version only looked at the question, not the heading
  kept with it, and clipped the tail of the question; that is fixed and covered.
- `tests/test_paginator.py` prints seeded random papers (free-form, multi-part, generated
  questions, an oversize one) and checks, from the PDF read page by page, that every question
  is on the page the paginator put it on, the page count matches, each tally equals the sum of
  its page's marks, and no word is lost against the plain print. `pypdf` is a dev dependency.
- Not yet: surfacing the warning in the editor (P6d), splitting a multi-part question between
  parts (P6c).
