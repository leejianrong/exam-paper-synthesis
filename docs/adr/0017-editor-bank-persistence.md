# ADR-0017: Editor bank persistence — local SQLite, schema-validated rows, no new storage mechanism

- Status: Accepted
- Deciders: project owner
- Related: `docs/planning/editor/SHAPING.md` (R1, Shape A1–A2), ADR-0001 (access/deployment), ADR-0004 (canonical object), ADR-0011 (bank retrieval permitted)

## Context

The MVP is deliberately stateless: the current-worksheet tray is client-side and
ephemeral (ADR-0010). The editor initiative's first requirement is a **durable**
place to put both generated and hand-authored (`sourced`) questions, reached from
the engine and CLI, with no accounts or hosted state (already decided in
`docs/planning/editor/README.md`). We need to fix the storage shape before any
schema growth lands on top of it.

## Decision

- **A single local SQLite file** is the bank. No server process, no accounts, no
  network access — backup is copying the file.
- **One row per canonical question object, stored as the same JSON the engine's
  load gate already validates.** The bank is never allowed to hold an object that
  wouldn't pass `canonical.validate` — this is checked on write *and* on read, so
  a bank row is exactly as trustworthy as a freshly-generated object.
- **No separate blob-storage mechanism for figures.** Raster figures stay
  self-contained `data:` URIs inside the object's `diagram.asset_ref`, exactly as
  V7 established for sourced questions. A second storage path (files-on-disk,
  a blob table) is not introduced; at single-user, hundreds-of-questions scale
  this is not a performance concern, and one storage mechanism is simpler to
  reason about than two.
- **The bank is reached through `engine/`, not a new layer.** CLI and the later
  web editor call the same bank functions; there is no bank-specific service
  process.
- A thin, indexed search/query layer sits over the object rows (topic,
  difficulty, level, `source_type`, paper id, reviewed status) — see ADR-0019 for
  the reviewed-status semantics and ADR-0018 for the paper/section/group
  container this bank also stores.

## Consequences

- Schema growth (ADR-0020) and container growth (ADR-0018) both slot into this
  bank without a storage migration — they're new JSON shapes and new tables, not
  a new persistence mechanism.
- Because every row is schema-validated on read as well as write, a bank that
  predates a schema bump still loads correctly as long as the bump is additive
  (see ADR-0020) — nothing needs a data migration, only a `schema_version` bump.
- KAN-163 (retrieve an alternative from the bank on `make-harder`/`make-easier`)
  becomes buildable once this ADR lands, but is explicitly deferred — see
  `docs/planning/editor/SHAPING.md` R8.3.
