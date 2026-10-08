---
shaping: true
---

# W1a — Parameter roles: how blueprints mark names vs numbers

> First sub-slice of **W1** (see `WYSIWYG.md`, ADR-0021). Implements edit **tier 1**
> (cosmetic slots) for templated questions. Tier 2 (numeric edits) is *designed for*
> here but not built.

## Why this is needed (what the code does today)

Each blueprint YAML has a `parameter_schema` (JSON Schema) and `story_templates` /
`solution_template` filled by `str.format` from `params + intermediates`. Nothing says
what a param *means*. Surveying all 18 blueprints, params fall into four kinds:

| Kind | Examples | Safe to edit freely? |
|---|---|---|
| **person name** | `names[]`, `name`, `name1`/`name2` (each solver keeps its own `NAME_POOL`) | Yes — never enters `solve()` |
| **item noun** | `percentage_hard.context` ("price of a {context}", sampled from `ITEM_POOL`) | Yes, but needs article care ("a umbrella") |
| **number** | `ratio`, `total`, `percent`, `d1`, `speed`, … | No — drives the answer; some are *derived by construction* (e.g. `total = sum(ratio) × unit_value`) |
| **choice (structural enum)** | `direction` (increase/decrease), geometry `shape`/`kind` | No — a different choice is a *different question* (changes the working, marking scheme, diagram) |

Good news from the survey: no template contains a gendered pronoun (so names need no
pairing today), and names flow into the diagram only via `solver.diagram(params, …)` (bar
labels), which is deterministic from params.

## Decision: a top-level `param_roles` block per blueprint

```yaml
parameter_schema: { … unchanged … }
param_roles:            # every property of parameter_schema MUST appear here
  names:  { role: name }      # array → role applies to each element
  ratio:  { role: number }
  total:  { role: number }
```

Roles: `name | item | number | choice`. Only `name` and `item` are tier-1 editable.

**Why a separate block, not `x-role` annotations inside `parameter_schema`:** the schema
stays pure JSON Schema validated by `validate_against` (ADR-0014), and the role map is
diffable on its own (ADR-0003). **Why not infer from key names:** `context` and `name1`
show names aren't consistent, and silent misclassification would let a numeric param be
"cosmetically" edited — the one failure that breaks the correctness guarantee.

`BlueprintSpec` gains `param_roles`; the loader fails if a schema property has no role or a
role names a non-existent property (so a new blueprint can't ship unclassified).

## The edit: one code path, re-solve — never string substitution

1. **Refactor `pipeline.py`:** extract `build_from_params(spec, solver, seed, params)`
   (validate params → solve → `solver.validate` → diagram + consistency → `assemble`) out of
   `run_pipeline`'s loop. Sampling and editing share it, so an edited object goes through
   exactly the gates a generated one does.
2. **New edit op `set-cosmetic`** in `edits.py`: `apply("set-cosmetic", obj, changes={…})`:
   - `EditNotApplicable` unless `source_type=="generated"`, and every changed key has role
     `name`/`item` (numbers and choices are refused with a pointer to the right op).
   - Validate values (below), merge into `parameters`, call `build_from_params`, stamp
     lineage (`parent_id`, `version+1`, same `seed`).
   - **Replay the source's view state** on the rebuilt object, since a rebuild resets it:
     decimals representation (`validation.checks.representation`), diagram toggled off, and
     bar `view_mode`. (Risk: this is the fiddly part — covered by tests below.)
3. **Value validation** (names are user input rendered into HTML/SVG, and SaaS means
   untrusted input): non-empty, ≤ 24 chars, letters/spaces/hyphen/apostrophe only (Unicode
   letters allowed — "Nurul Aini", "Ng", "Muhammad"), distinct across all name slots in the
   question, whitespace-normalised. `item` values must come from the blueprint's curated
   item pool in v1 (dropdown, no free text) — removes the article problem until we add an
   `a/an` helper.
4. **No schema bump** — `parameters` is already free-form in the canonical schema; `source_type`
   stays `generated` and the answer stays engine-proven because it was re-solved.

`param_hash` (in-session dedup) is left as-is: it hashes all params, so renaming makes a
question "different". Revisit only if teachers complain about near-duplicate detection.

## Surface

- **API:** `POST /edit/set-cosmetic` (object + `changes`) alongside the existing edit
  routes; `GET /blueprints/{code}/params` returns each editable slot with role, count, constraints,
  and (for `item`) the allowed pool — the editor builds its popover from this.
- **CLI:** `mathgen edit set-cosmetic q.json --set names=Ann,Ben,Cal --out q2.json`.
- **Editor UI (W1):** an "Edit names" popover on the templated block (fields labelled
  Name 1…n), not click-on-token editing — token click would need span offsets in the
  rendered text; deferred.

## Tests (the correctness authority)

| Test | Asserts |
|---|---|
| `test_param_roles_complete` | every blueprint: roles ⇔ schema properties, roles in the allowed set |
| `test_template_has_no_pronouns` | no story/solution template contains he/she/his/her/him (keeps names unpaired) |
| `test_set_cosmetic_invariants` (seed sweep × all blueprints with name/item slots) | after renaming: answer, marks, marking scheme, numeric solution-step values identical; new names appear in `question.parts[0].text`, steps, and bar-model labels; old names gone; object schema-valid |
| `test_set_cosmetic_rejects_numeric_and_choice` | `ratio`, `direction`, … → `EditNotApplicable` |
| `test_set_cosmetic_validates_values` | empty, too long, `<script>`, duplicate names, item outside pool → rejected |
| `test_set_cosmetic_preserves_view_state` | decimals view, diagram-off, bar `view_mode` survive a rename |
| `test_set_cosmetic_escapes_in_render` | a name with `&`/`'` renders escaped in worksheet HTML and SVG |
| API/CLI smoke | route + `mathgen edit set-cosmetic` round-trip |

## Out of scope / later (tier 2 design note)

Numeric editing needs a notion of **free vs derived** params (a future `derived: true`
flag on `number` roles — not added in W1a, to avoid guessing): the form would expose only free params (`ratio`, `unit_value`) and recompute
`total`; solvers whose `sample()` builds constraints "by construction" would need a
`from_free_params()` hook. Not built in W1.

## Acceptance

`mathgen edit set-cosmetic` renames the people in a `ratio_medium` question; worksheet, answer
key and bar model all show the new names; every number and the answer are unchanged; the
object is schema-valid; the same op refused on `ratio` with a clear error.

## Implementation notes (as built)

- `set-cosmetic` is in `edits.KNOWN_OPS` and `edits.apply(..., changes=…)` but **not** in
  `available_ops()`: that set drives one-click buttons and many tests pin it exactly, while
  this op needs a form. Use `edits.applicable(op, obj)` / `cosmetic.editable_slots(code)`.
- Item pools live on the solver (`ITEM_POOL` class attribute on the two percentage solvers),
  not in YAML, to avoid duplicating the list the solver samples from.
- `ParamsInvalid` (new) is raised by `pipeline.build_from_params` when edited params are
  infeasible; the API maps it to 422 like `EditNotApplicable`.
- Status: **implemented** (PR for branch `feat/w1a-param-roles`).
