# Editor initiative — question editor + persistent bank

The next initiative after the **v0.1.0** MVP checkpoint. Planning artifacts for
the question editor land here: product description and empirical schema-fit
work first, then shaping ([`SHAPING.md`](SHAPING.md)), slices
([`SLICES.md`](SLICES.md)), and ADRs (`docs/adr/0017`–`0020`).

## The vision (owner's framing)

An editor where teachers customize and author questions:

- **At minimum**, make questions similar to the ones the engine already generates.
- **Ideally**, an expressive, flexible surface to author *any* question and have
  it saved in the standardized canonical schema.

First user: the owner, recreating questions by hand from a PDF bank.

## Decisions so far

- **Persistence: local-first, single user.** A durable bank on the owner's own
  machine (SQLite + figure blobs), reachable through the engine and CLI. No
  accounts, no hosted state, no auth — backup is copying the file. This keeps the
  engine's UI/HTTP-agnostic property and defers every multi-user concern.
  Formalized in ADR-0017.
- **Authoring scope: both paths, free-form first.** Settled empirically by the
  schema-fit exercise in [`SCHEMA-FIT.md`](SCHEMA-FIT.md): 36% of a real paper
  cannot be represented at all today, and our six blueprint families reach
  roughly 18 of 47 questions, so the free-form / `sourced` / human-vouched path
  comes first and unblocks recreating a real paper; the parametric path stays
  for topics the engine generates. See the [Verdict on the authoring
  surface](SCHEMA-FIT.md#verdict-on-the-authoring-surface).
- **Paper structure is in scope this milestone.** A container above the
  canonical question object — paper → section → optional shared-stem question
  group — is being built now, not deferred, resolving G15/G16. Formalized in
  ADR-0018; see `SHAPING.md` R3.
- **Schema growth this milestone reaches ranked item 7** of `SCHEMA-FIT.md`'s
  list: MCQ `options`/`choice`, `diagram` on `question` with per-part unknowns,
  optional `marks`/`marking_scheme`, `table`, `grid`+`polygons` on
  `geometry_figure`, and `construction` answers. Ranked items 8+ stay deferred.
  Formalized in ADR-0020; see `SHAPING.md` R7.
- **Import gets a mandatory review step, not a silent conversion**, resolving
  G19 (every real answer key examined contains errors). Unreviewed content is
  flagged, never blocked, since the owner is the sole author and reviewer.
  Formalized in ADR-0019; see `SHAPING.md` R5.
- **KAN-163 (bank retrieval on swap) stays parked** this milestone — the bank
  ships as a save/search/reuse store; `make-harder`/`make-easier` are unchanged
  from the MVP. See `SHAPING.md` R8.3.

## Resolved design threads

The threads below were open when this README was first written; all are now
resolved in [`SHAPING.md`](SHAPING.md) and the ADRs linked above.

- **Trust model** — generated questions are *engine-proven*; hand-authored ones
  are *human-vouched*. The schema already encodes this via
  `source_type` (`generated` | `sourced`) and `created_by` (`ingested`). This
  initiative productizes the V7 sourced-object path, and adds a review gate
  (ADR-0019) the V7 path didn't need.
- **Persistence** — the MVP is deliberately stateless (client-side, ephemeral
  worksheet tray). The bank (ADR-0017) is the new durable, searchable piece.
- **Figure expressiveness** — `raster` (embedded-image) stays the general
  escape hatch; schema v2 (ADR-0020) additionally makes `table`, grid-backed
  `geometry_figure`, and `construction` answers structured rather than opaque
  images, per the evidence in `SCHEMA-FIT.md`.
- **Paper structure vs. a flat worksheet** (G15/G16) — resolved by ADR-0018: a
  container above the canonical object, referencing questions by id rather than
  duplicating shared content into them.

> Ground-truth references: [`../../SCHEMA.md`](../../SCHEMA.md),
> [`../mvp/PRD.md`](../mvp/PRD.md), the V7 sourced-object work in
> [`../mvp/V7-plan.md`](../mvp/V7-plan.md), and this initiative's own
> [`SHAPING.md`](SHAPING.md) / [`SLICES.md`](SLICES.md).
