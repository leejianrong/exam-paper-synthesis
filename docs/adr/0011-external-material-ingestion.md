# ADR-0011: External material — out of scope tooling; schema must be interchange-grade

- Status: Accepted (supersedes the earlier "build a pipeline" proposal)
- Deciders: project owner
- Related: Q-N1, Q-N5, Q-N6, Q-C1/ADR-0004

## Context

The owner initially wanted an internal ingestion pipeline (OCR/parse historical
PDFs → canonical form → question bank). On reflection, that processing will be
done **outside this project**.

## Decision

- **This project does NOT build an ingestion / OCR / parsing pipeline.** The owner
  prepares external material (past papers, assessment books; ~hundreds of
  questions) into canonical form separately.
- The question bank is **internal**; the owner **holds the rights/licence** and is
  permitted to use the material. **The app MAY retrieve from the bank** as an
  additional source for **swapping** questions (e.g. make-harder/easier, or
  pulling an alternative question) — updated from the earlier "no retrieval"
  stance now that permissions are confirmed. No public redistribution is implied.
- The load-bearing requirement that remains: the **canonical schema must be
  interchange-grade** — versioned, strictly validated, and able to represent
  **sourced** questions as first-class citizens alongside **generated** ones.

## Consequences

- Effort shifts from "build a pipeline" to "make the schema rock-solid and
  well-defined" (see ADR-0004 and the forthcoming formal schema).
- Sourced-question support in the schema (nullable blueprint/parameters,
  raster-diagram references, `source`/`license`, human-verified provenance) is a
  hard requirement, not a nice-to-have.
- No OCR/vision/LLM ingestion dependencies enter this project.

## Superseded proposal

The prior six-stage pipeline (intake → OCR → segment → extract → verify → persist)
is dropped from scope. Retained only as context for what the external process will
produce.
