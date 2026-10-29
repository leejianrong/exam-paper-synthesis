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
| P6a | Marking margin ("Do not write in this space") and tally markup in `render`, per-section toggle, on by default for working sections | S–M |
| P6b | Paginator script + `data-marks`, PDF and preview, oversize clamp, seed-sweep test | M |
| P6c | Multi-part split between parts | S |
| P6d | Editor indicative page frames + tally preview | M |

Open: owner to confirm the tally box dimensions and where the margin sits relative to the
Ans: line before P6a.
