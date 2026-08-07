# papers/ — extracted paper transcripts (untracked)

Drop extracted exam-paper Markdown here. **Only this README is tracked.**

Exam papers are copyrighted and this repo is **public**, so transcripts and
source PDFs are kept local and never committed — the same rule
`docs/syllabus/` follows for the MOE syllabus. The `.gitignore` enforces it
(`docs/planning/editor/papers/*` with this README re-included), and `*.pdf` is
already ignored repo-wide.

## Naming

One file per paper, per section if you extracted it in pieces:

```
docs/planning/editor/papers/
  2023-psle-paper1-bookletA.md
  2023-psle-paper1-bookletB.md
  2023-psle-paper2.md
  acme-primary-2024-prelim-paper2.md
```

## The flow

1. Run a paper through the prompt in
   [`../extraction-prompt.md`](../extraction-prompt.md) in an external LLM tool.
2. Save the Markdown here and say which file to read.
3. Findings — verdict per question, gaps confirmed or killed — accumulate in
   [`../SCHEMA-FIT.md`](../SCHEMA-FIT.md), which **is** tracked.
4. Attempted canonical objects go to `tests/fixtures/sourced/` and are
   schema-gated like any other object.

## What may be committed from a paper

Findings and metadata, not reproductions. A fixture built from a real question
carries its `source` block (origin, year, paper, reference) and `license`, plus
whatever structure the finding is about — but not the paper's verbatim text or
artwork. Where a fixture needs question text to be meaningful, reword it or use
a structurally equivalent stand-in, and note in `SCHEMA-FIT.md` that it is a
paraphrase.

Keep the original PDFs (also untracked). When a figure description turns out
ambiguous, looking at that one figure is the fastest way to settle it.
