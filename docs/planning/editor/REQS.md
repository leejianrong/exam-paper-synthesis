# REQS — Question editor + persistent bank (initiative: `editor`)

> Raw idea capture (owner's words, lightly structured). This is the seed input for
> the product-planning process (Grill → PRD → Shaping → Breadboard → Slice). It is
> deliberately not a polished spec — downstream docs formalize it. Edit freely.
>
> Context: the **v0.1.0 MVP** shipped a deterministic, blueprint-driven engine that
> generates P5–P6 Standard math questions with provably-correct answer keys (no
> LLM). The canonical question object (schema **v1.4.0**) is the single source of
> truth. This initiative is the first big change *after* that checkpoint.

## The idea

I want an **editor** where the users (teachers) can customize questions.

- **At minimum**, they should be able to make questions *similar* to the ones we
  already generate (start from an existing question / blueprint and tweak it).
- **Ideally**, the editor is very **expressive and flexible** — teachers can
  basically author **any question they want** and have it saved in our
  standardized canonical schema.

I (the owner) will be the **first user**: I'll be looking at a PDF bank of
past-paper questions and crafting them by hand using this editor.

## Why (the pull)

- The engine only produces what its blueprints can generate. Real worksheets draw
  on a much wider space of questions (past papers, textbook items, bespoke wording).
- A teacher's judgement should be able to enter the system directly, not only
  through the deterministic generator.
- I need a way to build up a **reusable library** of hand-crafted, schema-valid
  questions I can assemble into worksheets — the current worksheet tray is
  ephemeral and per-session.

## What "success" looks like (rough)

- I can sit with a PDF of past-paper questions and, for each one, recreate it in
  the editor and save it to a durable bank — text, answer, marking, working, and a
  figure — as a schema-valid canonical object.
- Later I can browse/search that bank and pull questions into a worksheet and
  export, exactly like generated questions.
- Editing "make similar" from an existing generated question is fast and obvious.

## Known design threads (already discussed — inputs, not yet decisions)

1. **Trust model.** Generated questions are *engine-proven* (a solver computed the
   answer key). Hand-authored questions are *human-vouched* (I assert the answer).
   The schema already encodes this distinction via `source_type`
   (`generated` | `sourced`) and `created_by` (`ingested`). This initiative is,
   in effect, the productization of the V7 sourced-object interchange path. The
   correctness guarantee changes for authored questions and that should be explicit
   and honest in the product.
2. **Persistence.** The MVP is deliberately stateless — the worksheet tray lives
   client-side and is ephemeral; there is no server state. A hand-built bank must
   be **durable and searchable**, so persistence is likely the single biggest new
   piece of this initiative (and a departure from a stated MVP convention).
3. **Figure expressiveness.** "Any question" mostly means "any *figure*." Text,
   answers, marking schemes, multi-part stems are already expressible in the schema.
   For arbitrary figures the pragmatic path is likely the **`raster`** escape hatch
   (embed an image, e.g. snipped from the PDF) rather than building a
   general-purpose diagram editor; the existing parametric figure types
   (`bar_model`, `geometry_figure`, `shaded_fraction`) stay for the common cases
   that benefit from being editable/re-renderable.

## Open questions (seeds for grilling)

- How far does "any question" go — do we cap expressiveness at "anything the
  current schema can hold," or do we expect the schema itself to grow?
- Where does the bank live (local file(s), SQLite, a real server DB)? Single-user
  (just me) or eventually multi-user?
- Is authoring always free-form, or is "make similar" a distinct, more-guarded
  mode that keeps the engine's correctness guarantee (re-run the solver on edited
  params)?
- What's the smallest first useful version — just author + save one question, then
  grow?
- How do authored questions and generated questions coexist in one bank and one
  worksheet without the trust distinction getting lost?

## Ground-truth references

- `docs/SCHEMA.md` — the canonical question object explained.
- `engine/exam_engine/schemas/canonical-question.schema.json` — schema v1.4.0.
- `docs/planning/mvp/V7-plan.md` — sourced-object interchange (the path this builds on).
- `docs/planning/mvp/PRD.md` — the MVP PRD (prior art for format + decisions).
