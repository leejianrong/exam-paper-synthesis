# Syllabus reference (local-only)

The authoritative curriculum reference for this project — the **MOE Primary
Mathematics Syllabus (2021, updated Oct 2025)**. This is the "Q-M1" source the
PRD flagged as needed for real `skill_codes`; blueprint authoring and the
`content/syllabus/*.yaml` skill-code registries should map to it (they currently
use provisional placeholders, see ADR-0016).

## Contents (not committed)

- `primary_mathematics_syllabus_2021_updated_oct_2025_llm.md` — an LLM-readable
  Markdown extraction of the official PDF (diagrams rendered as structured text).
- `2021 Primary Mathematics Syllabus P1 to P6 Updated October 2025.pdf` — the
  source PDF.

## Why these files are git-ignored

© Curriculum Planning and Development Division, MOE. The document permits
reproduction **for personal and non-commercial use only**. This repository is
**public**, so the source files are deliberately kept **local-only** (see the
`docs/syllabus/*` rule in `.gitignore`) to avoid republishing copyrighted
material. Only this README is tracked.

To work with the syllabus, place the two files in this folder locally. If the
repository is ever made private, or a licence permits it, this decision can be
revisited.

## Scope note

The 2021 syllabus covers **P1–P6** across three strands (Number & Algebra,
Measurement & Geometry, Statistics). This project's MVP deliberately targets only
a slice of it (P5–P6 Standard: Ratio, Fractions, Percentage, Area/Geometry,
Speed). Forward-looking diagram/figure needs uncovered while reading the syllabus
are captured in [`../shaping/diagram-roadmap.md`](../shaping/diagram-roadmap.md).
