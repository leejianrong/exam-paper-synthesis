# Editor initiative — question editor + persistent bank

The next initiative after the **v0.1.0** MVP checkpoint. Planning artifacts for
the question editor land here (product description first, then shaping and
implementation plans).

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
- **Authoring scope: not yet decided — being settled empirically.** Rather than
  choose parametric vs free-form in the abstract, we are running the schema-fit
  exercise in [`SCHEMA-FIT.md`](SCHEMA-FIT.md): take real exam questions, try to
  express each as a canonical object, and record what the schema cannot hold.
  Schema gaps found there get fixed before the editor is designed around them.

## Open design threads to resolve during planning

- **Trust model** — generated questions are *engine-proven*; hand-authored ones
  are *human-vouched*. The schema already encodes this via
  `source_type` (`generated` | `sourced`) and `created_by` (`ingested`). This
  initiative productizes the V7 sourced-object path.
- **Persistence** — the MVP is deliberately stateless (client-side, ephemeral
  worksheet tray). A durable, searchable question **bank** is likely the biggest
  new piece.
- **Figure expressiveness** — arbitrary figures likely lean on the `raster`
  (embedded-image) escape hatch; parametric figure types stay for the common,
  re-renderable cases.

> Ground-truth references: [`../../SCHEMA.md`](../../SCHEMA.md),
> [`../mvp/PRD.md`](../mvp/PRD.md), and the V7 sourced-object work in
> [`../mvp/V7-plan.md`](../mvp/V7-plan.md).
