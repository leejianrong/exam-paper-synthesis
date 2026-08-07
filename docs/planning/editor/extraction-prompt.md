# Paper extraction prompt

The prompt used to turn a scanned exam paper (PDF) into a text-only Markdown
transcript, for the schema-fit exercise in [`SCHEMA-FIT.md`](SCHEMA-FIT.md).

Paste it into an external LLM tool along with the paper. Output lands in
[`papers/`](papers/README.md) (untracked — the papers are copyrighted and this
repo is public).

## Why the prompt looks like this

Three constraints shaped it, and each is worth keeping if the prompt is edited:

- **It forbids solving anything.** The schema requires `answer`,
  `marking_scheme` and `solution_steps` on every part, so a helpful extractor
  will be tempted to compute a missing answer. That would put LLM-generated
  maths into our fixtures — the one thing this project exists to avoid (no LLM in
  the truth path). A paper with no answer key is a *finding*, not a problem to
  paper over: it tells us the editor must support authoring a key by hand.
- **It asks for structured figure data, not prose.** The exercise is judging
  whether our diagram types can hold real figures. "A triangle with two angles
  labelled" can't be turned into a `geometry_figure` (which needs named points,
  which pairs are joined, each angle's value or unknown flag, ticks, shading), so
  a prose description makes "our primitives can't express this" indistinguishable
  from "the description didn't carry enough detail."
- **It asks for confidence flags.** Same reason: an OCR failure must not be
  mistaken for a schema gap.

Keep the original PDF. When a figure description is ambiguous, the fastest
resolution is looking at that one figure.

## Usage notes

- **Feed long papers in sections.** Extraction quality degrades well before a
  context limit, and Booklet A's MCQs are the most important part to get intact.
- **Include the answer key** in the same conversation if it's a separate
  document, otherwise `answer_given` defaults to `not given` throughout.

---

## The prompt

````text
You are transcribing a Singapore primary-school maths exam paper (P5/P6) into
Markdown for a schema-design exercise. Fidelity matters far more than polish.

ABSOLUTE RULES
1. Transcribe only. Do NOT solve anything, do NOT compute or infer any answer,
   do NOT fill in a missing answer key. If the paper gives no answer, write
   `not given`. An invented answer would corrupt the downstream work.
2. Quote question and option text verbatim, including printed units, answer
   blanks, and mark allocations. Don't paraphrase, correct, or tidy.
3. If you cannot read something confidently, say so in that item's
   `confidence` field. A flagged gap is useful; a confident guess is harmful.

OUTPUT

Start with paper metadata:

  paper: <school / book, year, "Paper 1" or "Paper 2", booklet if shown>
  total_marks: <as printed, or not given>
  answer_key_present: yes | no

Then one block per question, in order:

  ## Q<n>  [<marks> marks]  (<section, e.g. Paper 1 Booklet A>)
  type: mcq | short-answer | structured
  stem: <verbatim; the shared lead-in text if the question has parts>
  figure: none | FIG-<n>            # FIG shared by several parts -> name it here
  answer_blank: <exactly as printed, e.g. "______ cm²", or none>
  options:                          # MCQ only, verbatim with original labels
    (1) ...
    (2) ...
    correct: <label, or not given>
  parts:                            # omit if the question has no (a)/(b) parts
    (a) [<marks>] <verbatim text>
        figure: none | FIG-<n>
        answer_given: <verbatim from the answer key, or not given>
        working_shown: <verbatim if the paper prints worked solutions, else none>
  confidence: high | low — <what was unclear, if anything>

Then a FIGURES section at the end. For each figure, give STRUCTURED data, not
just prose — this part is the point of the exercise:

  ### FIG-<n>  (used by: Q7a, Q7b)
  kind: geometric | bar model | table | line graph | bar chart | pie chart |
        net | number line | clock face | 3D solid | coordinate grid |
        context picture | other (<name it>)
  printed_text: [every label, number and unit printed on the figure, verbatim]
  structure:
    # geometric: name the vertices (A, B, C… — invent labels if the figure has
    #   none and say so); list which pairs are joined; every marked angle as
    #   "at B between A and C = 50°" or "= unknown/x"; every marked length;
    #   right-angle marks; equal-side ticks; which region is shaded; whether any
    #   part is a circle/arc and its centre.
    # table: reproduce it as a real Markdown table, including blank cells the
    #   pupil must fill.
    # graph/chart: axis titles, ranges, gridline interval, and every plotted or
    #   labelled value.
    # other kinds: whatever a person would need to redraw it exactly.
  prose: <one or two sentences of plain description>
  confidence: high | low — <what was unclear>

Do the whole paper. Don't summarise or skip repetitive questions.
````
