# ADR-0013: Question structure (multi-part) and answer typing

- Status: Accepted
- Deciders: project owner
- Related: Q-S3, Q-S4, ADR-0004

## Context

Real PSLE questions are frequently multi-part (a)(b)(c), and answers come in
several distinct forms (integer, fraction, ratio, …). Both must be represented
precisely for the schema to be interchange-grade.

## Decision

- **Multi-part (Accepted):** one canonical object = one whole question, with an
  optional shared `stem` and a `parts[]` array. Each part carries its own `text`,
  `answer`, `marking_scheme`, `solution_steps`, and optional `diagram`. Top level
  aggregates `total_marks`. Single-part questions are a `parts` array of length 1.
- **Answer typing (Accepted):** `answer` is a **discriminated union keyed by
  `type`**, closed set: `integer`, `decimal`, `fraction`, `ratio`, `quantity`
  (value + unit), `set` (e.g. "x = 2 or 3"), `text` (explanation). Units use a
  **controlled vocabulary** (not free text). `text` is retained for O-Level
  future / AO3; primary MVP rarely uses it.

## Consequences

- Marks aggregate cleanly from parts; worksheet numbering renders (a)(b)(c).
- Each answer is strictly validatable by type; the verifier can check numeric
  answers by re-substitution where an `expr` is present.

## Resolved

- Answer-type set closed (above); units = controlled vocabulary; `text` retained
  but rarely used in primary. Formal shapes in `schemas/` (ADR-0014).
