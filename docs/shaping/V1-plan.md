---
shaping: true
---

# V1 Slice Plan — Generate one Ratio question

> **Slice V1 of `docs/shaping/SLICES.md`.** The thinnest full-stack path that produces a
> question a teacher can trust. Ground truth for R and Shape A: `docs/shaping/SHAPING.md`.
> Schema contract: `schemas/canonical-question.schema.json` (+ `docs/SCHEMA.md`).
> Blueprint model: ADR-0003. Layout/stack: ADR-0006. Ladder: `docs/DIFFICULTY.md`.
>
> **Demo goal:** in the browser, click **Generate** → a fresh, schema-valid
> `ratio_medium` question appears with its final typed answer and a **pass**
> validation badge. Click again → different numbers, still correct.

---

## Scope

**In (Shape-A parts A1, A2, A3, A9):**
- **A1** — canonical object load/validate/serialize against the JSON Schema;
  provenance + versioning stamping.
- **A2** — blueprint loader + declared-parameter-schema validation; solver plugin
  interface; **one** blueprint `ratio_medium` (+ solver) with **golden fixtures**.
- **A3** — `generate(blueprint_code, seed)` pipeline: sample → solve → validate →
  fill templates → assemble → schema-validate; retry ≤ 20 → structured error;
  in-session dedup.
- **A9** — thin `POST /generate`; minimal Svelte page (Generate button + one card).

**Explicitly deferred (later slices):**
- Diagrams / bar model, worked-solution *rendering*, `[n]` marks display → **V2**
  (the object *carries* `solution_steps` + `marking_scheme` from V1; V1 just
  doesn't render them richly).
- Difficulty ladder + edit ops (harder/easier/decimals/toggle/regenerate button)
  → **V3**. V1 pins topic=Ratio, difficulty=medium.
- Approve/discard, worksheet tray → **V4**. Export/PDF → **V5**.
- Other 4 topics + geometry diagrams → **V6**. CLI + sourced load → **V7**.

**Single blueprint for V1:** `ratio_medium` — *three quantities shared in a
3-term ratio* (DIFFICULTY.md "3-term ratio / ratio given the difference").
Single-part, answer = **quantity** in `$` (clean positive integer). Multi-part
(R1.7) is exercised later; the schema already supports it via `parts[]`.

---

## Repo layout (new files)

Per ADR-0006 (`engine/`, `api/`, `web/`, `content/`, `tests/`). **Python 3.12**,
**uv workspace** (`engine` + `api` as members sharing one lockfile/venv; `api`
takes `engine` as a **path dependency** so both — and the later `mathgen` CLI —
call one implementation, R7.6). pytest for tests.

### Schema representation — jsonschema vs Pydantic (decided)

Two roles, one source of truth:

- **Canonical question object** = the interchange contract. Represented in-engine
  as a plain `dict` built by the assembler and **gated by `jsonschema`** against
  `schemas/canonical-question.schema.json` (Draft 2020-12). This hand-written
  schema is authoritative (ADR-0014) — Pydantic does **not** own or regenerate it,
  because its `if/then` conditional requirements, `oneOf` unions,
  `additionalProperties:false`, and `unit` enum would drift from a
  Pydantic-generated schema. The canonical object rides *inside* API responses as
  validated JSON, never as a Pydantic model.
- **API request/response envelopes** = **Pydantic** models (`GenerateRequest`,
  `GenerateResponse`), FastAPI-native, giving request validation + OpenAPI docs.
  These wrap `list[dict]` canonical objects; they do not re-describe them.

> Typed engine-side models (Pydantic/dataclass mirrors of the canonical object)
> are **out of scope for V1** — if added later they must ship a contract test
> asserting every instance serializes to jsonschema-valid output, with jsonschema
> still the authority.

```
pyproject.toml                      # uv workspace root; [tool.uv.workspace] members=["engine","api"]; dev: pytest, httpx
engine/
  pyproject.toml                    # deps: jsonschema  (NO fastapi — engine is UI/HTTP-agnostic)
  exam_engine/
    __init__.py
    canonical.py                    # A1: load/validate/serialize + provenance stamping
    schema.py                       # A1: load schemas/*.json; validate(obj) -> report (path-pointed)
    blueprints/
      __init__.py
      registry.py                   # A2: discover + load content/blueprints/*.yaml, bind solver
      base.py                       # A2: Solver Protocol + BlueprintSpec dataclass + param-schema validate
      solvers/
        __init__.py
        ratio_medium.py             # A2: sample/solve/validate for ratio_medium
    pipeline.py                     # A3: generate(blueprint_code, seed); retry; dedup; assemble
    errors.py                       # A3: InfeasibleConstraints, BlueprintMisconfigured
api/
  pyproject.toml                    # deps: exam-engine (workspace path dep), fastapi, uvicorn, pydantic
  app/
    main.py                         # A9: FastAPI app
    models.py                       # A9: Pydantic GenerateRequest/GenerateResponse (API envelopes only)
    routes_generate.py              # A9: POST /generate
content/
  syllabus/
    ratio.yaml                      # minimal: strand/topic/skill_codes for Ratio (placeholder codes until MOE doc)
  blueprints/
    ratio_medium.yaml               # A2: the blueprint data
web/
  (Svelte + Vite scaffold)
  src/lib/api.ts                    # fetch wrapper for POST /generate
  src/lib/QuestionCard.svelte       # renders one canonical object (V1: text + answer + badge)
  src/routes/+page.svelte           # Generate panel (topic/difficulty pinned) + card list
tests/
  golden/
    ratio_medium.jsonl              # hand-verified params -> expected answer/marks
  test_generate_ratio_medium.py     # primary seam
  test_schema_validation.py         # A1 validator seam (worked examples + negative controls)
  test_pipeline_retry.py            # A3 retry/infeasibility
  test_api_generate.py              # thin TestClient contract test
```

---

## A2 — Blueprint & solver

### `content/blueprints/ratio_medium.yaml`

Declarative data only (ADR-0003). Wording uses named placeholders filled from
sampled params + solved values.

```yaml
code: ratio_medium
syllabus:
  level: P5
  strand: "Ratio"
  topic: "Ratio"
  subtopic: "Sharing in a ratio"
  skill_codes: ["RATIO.SHARE.3TERM"]      # placeholder until MOE syllabus doc (Q-M1)
cognitive:
  difficulty: medium
  cognitive_level: complex_familiar
  difficulty_levers: ["Reasoning depth", "Number type / magnitude"]
marks: 3                                   # total; single part carries all 3
parameter_schema:                          # ADR-0014: declared, validated after sample
  type: object
  additionalProperties: false
  required: [names, ratio, total]
  properties:
    names:  { type: array, items: {type: string}, minItems: 3, maxItems: 3 }
    ratio:  { type: array, items: {type: integer, minimum: 1, maximum: 9}, minItems: 3, maxItems: 3 }
    total:  { type: integer, minimum: 12, maximum: 2000 }
story_templates:                           # 2-3 variants, chosen by seed (ADR B5)
  - stem: null
    text: >
      {names[0]}, {names[1]} and {names[2]} share ${total} in the ratio
      {ratio[0]} : {ratio[1]} : {ratio[2]}. How much does {names[2]} receive?
solution_template:
  steps:
    - text: "Total units = {ratio[0]} + {ratio[1]} + {ratio[2]} = {units_total}."
      expr: "{ratio[0]}+{ratio[1]}+{ratio[2]}"
    - text: "Value of 1 unit = ${total} ÷ {units_total} = ${unit_value}."
      expr: "{total}/{units_total}"
    - text: "{names[2]}'s share = {ratio[2]} × ${unit_value} = ${answer_value}."
      expr: "{ratio[2]}*{unit_value}"
marking_scheme:
  - { mark: 1, type: M, description: "Sum the ratio units to find total units." }
  - { mark: 1, type: M, description: "Divide total by units to find one unit's value." }
  - { mark: 1, type: A, description: "Correct final share with $ unit." }
answer:
  type: quantity
  unit: "$"
diagram: null                              # aid bar_model added in V2
```

### Solver interface — `engine/blueprints/base.py`

```python
class Solver(Protocol):
    def sample(self, schema: dict, rng: random.Random) -> dict: ...
    def solve(self, params: dict) -> dict:        # -> {"answer": {...}, "intermediates": {...}}
        ...
    def validate(self, params: dict, solution: dict) -> dict:   # -> {"ok": bool, "checks": {...}}
        ...
    # def diagram(self, params, solution) -> dict   # optional; not in V1
```

- `sample` draws `names` (from a small fixed name pool, seed-selected), `ratio`
  (three integers 1–9, not all equal), and `total`.
- **Non-degeneracy constraints enforced in `sample`** (constraints are *by
  construction*, ADR-0014 — not solution enumeration): `total % sum(ratio) == 0`
  so every share is a positive integer; ratio terms not all equal; largest share
  ≠ others so "how much does X receive" is unambiguous. If a draw violates a
  constraint, `sample` redraws internally (or returns a sentinel the pipeline
  retries — see A3).
- `solve` returns `answer = {type:"quantity", value: names[2]'s share, unit:"$"}`
  and `intermediates = {units_total, unit_value, answer_value}` used to fill the
  solution/step templates.
- `validate` re-derives the share independently and asserts equality
  (`answer_verified`), asserts shares sum to `total` (`sums_to_total`), asserts
  within-level magnitude (`within_level`). Returns a checks dict → becomes
  `canonical.validation.checks`.

### Syllabus & placeholder skill codes

`syllabus.skill_codes` is a plain `array of string` in the schema (**not an
enum**), so placeholders validate fine. Convention: `TOPIC.SUBSKILL.VARIANT`
uppercase-dotted. Keep them in one provisional registry so remapping later (when
the MOE P5–P6 syllabus doc arrives, Q-M1) is a mechanical find/replace — and since
generated objects are ephemeral, there is **no data migration**.

```yaml
# content/syllabus/ratio.yaml  — PROVISIONAL codes; remap to MOE outcomes when available
strand: "Ratio"
skills:
  RATIO.SHARE.2TERM:   "Share a quantity in a 2-term ratio (direct)"
  RATIO.SHARE.3TERM:   "Share a quantity in a 3-term ratio"            # used by ratio_medium
  RATIO.BEFORE_AFTER:  "Before-after with an invariant quantity"
```

**One rule:** nothing in v1 may branch on `skill_code` *values* (selection,
filtering) — they will change. V1 **carries** them, never queries them.

---

## A3 — Generation pipeline (`engine/pipeline.py`)

`generate(blueprint_code: str, seed: int) -> dict` (canonical object), a **pure
function of its inputs**:

1. Load blueprint spec + bound solver from the registry.
2. Seed `rng = random.Random(seed)`.
3. **Retry loop, ≤ 20 attempts:** `params = solver.sample(schema, rng)` →
   validate params against `parameter_schema` → `solution = solver.solve(params)`
   → `report = solver.validate(params, solution)`. On failure (bad params or
   `report.ok == False`), re-loop. After 20 failures raise
   `InfeasibleConstraints`. Track failure rate; if a blueprint fails > 50% of
   attempts across a run, log/raise `BlueprintMisconfigured` (author signal).
4. **Fill templates** — substitute params + intermediates into the chosen
   `story_template` and `solution_template.steps`.
5. **Assemble** the canonical object (see mapping below).
6. **Schema-validate** the assembled object (A1); on failure this is an *engine
   bug*, not infeasibility → raise loudly.
7. Set `validation.status = "pass"` iff solver `report.ok` **and** schema-valid.

**In-session dedup:** the caller (batch loop) tracks seen `(blueprint_code, seed)`
and a normalized-parameter hash; a duplicate triggers a re-generate with the next
seed. (V1 exposes single generation; the dedup helper lands here so V-later batch
reuse is free.)

### Canonical assembly — field mapping (→ schema)

| Canonical field | V1 source |
|---|---|
| `schema_version` | `"1.0.0"` (const in engine) |
| `id` | deterministic `f"{blueprint_code}:{seed}"` (see **id scheme** below) |
| `source_type` | `"generated"` |
| `blueprint_code` | `"ratio_medium"` |
| `seed` | the seed arg |
| `syllabus` | copied from blueprint `syllabus` |
| `cognitive` | copied from blueprint `cognitive` |
| `parameters` | sampled `params` (validated against `parameter_schema`) |
| `question.stem` | `null` (single-part) |
| `question.parts[0]` | `{label:"", text: filled, marks:3, answer, marking_scheme, solution_steps, diagram:null}` |
| `question.total_marks` | `3` (== sum of part marks — asserted) |
| `validation` | `{status, checks}` from solver report |
| `provenance` | `{created_by:"engine", llm_used:false, created_at:null, parent_id:null, version:1}` |

> **`created_at` is stamped at the API boundary** (decided). The engine emits
> `null` so `generate(blueprint_code, seed)` stays a pure, reproducible function;
> `api/` sets the ISO-8601 timestamp as the object crosses HTTP.

### id scheme

- **V1:** `id = f"{blueprint_code}:{seed}"` (e.g. `ratio_medium:12345`).
  Deterministic (no clock/random → reproducible + cacheable), human-readable, and
  **its own dedup key**: the in-session dedup pair `(blueprint_code, seed)` *is*
  the id, so "same id ⇒ same question" is automatic.
- **Edits (V3, noted now so V1 doesn't paint us in):**
  - `make-harder` / `make-easier` re-sample a sibling blueprint → naturally a
    fresh `ratio_hard:678` with `provenance.parent_id = ratio_medium:12345`.
  - `change-to-decimals` / `toggle-diagram` transform the *same* sample → derived
    id `f"{parent_id}+{op}"` (e.g. `ratio_medium:12345+decimals`). `version` bumps
    on every edit regardless.
- **Collisions:** repeat `(blueprint_code, seed)` in a session → rejected by dedup
  (same question). Across sessions ids may recur — harmless, state is ephemeral
  (ADR-0001).
- **Future (if a saved library lands):** durable global uniqueness → a **content
  hash** (sha256 of the canonical object minus `id`/`provenance`) or a run-scoped
  UUID prefix. Not needed in V1.

---

## A1 — Canonical object + validator

- `schema.py`: load `schemas/canonical-question.schema.json` once; expose
  `validate(obj) -> Report` returning **path-pointed** errors (jsonschema's
  `best_match` / `absolute_path`). Objects are closed (`additionalProperties:false`)
  — the schema enforces this; the validator surfaces stray-field errors.
- `canonical.py`: `assemble(...)` builder + `load(dict)` (validates on entry,
  rejects invalid) + `to_json()`. This is the seam every test asserts against.

---

## A9 — API + web

- **`POST /generate`** body `{ "blueprint_code": "ratio_medium", "seed": <int?>,
  "count": 1 }` → returns `{ "questions": [<canonical object>, ...] }`. If `seed`
  omitted, API supplies seeds (the *only* place entropy enters; engine stays
  pure). Synchronous (ADR-0006).
- **Web:** `+page.svelte` — a Generate panel with topic/difficulty **pinned to
  Ratio / medium** (real selectors arrive in V3/V6), a **Generate** button that
  POSTs and appends a `QuestionCard`. `QuestionCard.svelte` (V1) shows: part text,
  final answer formatted (`$<value>`), and a validation badge from
  `validation.status`. Steps/marks/diagram intentionally minimal until V2.

---

## Golden fixtures — `tests/golden/ratio_medium.jsonl`

One JSON object per line, hand-computed and human-verified (**never
LLM-verified**, ADR-0003):

```json
{"params": {"names": ["Aisha","Ben","Chloe"], "ratio": [2,3,5], "total": 200}, "expected": {"answer": {"type": "quantity", "value": 100, "unit": "$"}, "total_marks": 3}}
{"params": {"names": ["Aisha","Ben","Chloe"], "ratio": [1,2,4], "total": 140}, "expected": {"answer": {"type": "quantity", "value": 80, "unit": "$"}, "total_marks": 3}}
```

`test_generate_ratio_medium.py` feeds each fixture's `params` straight to
`solver.solve` and asserts the expected answer/marks — decoupled from sampling, so
it pins the **maths** regardless of the RNG.

---

## Tests (pytest)

| Test | Asserts | Seam |
|---|---|---|
| `test_generate_ratio_medium` | For fixed seeds, `generate` returns a **schema-valid** object with expected difficulty/cognitive tags, part count = 1, answer `type/value/unit`, `total_marks=3` | A3 primary seam |
| (same file) golden loop | Each fixture's `params` → `solve` → expected answer/marks | A2 correctness anchor |
| `test_schema_validation` | Assembled object **passes**; negative controls (stray field, `total_marks` ≠ Σ marks, bad answer union tag, out-of-vocab unit) **fail with path-pointed errors** | A1 validator |
| `test_pipeline_retry` | A solver stub that always fails `validate` raises `InfeasibleConstraints` after 20 attempts; > 50%-failure flag fires | A3 |
| `test_api_generate` | FastAPI `TestClient` `POST /generate` returns schema-valid objects; `count` honored; missing blueprint → 4xx | A9 thin contract |

---

## Demo / acceptance (V1 done when)

1. `uv run pytest` green (all tables above).
2. `uv run uvicorn app.main:app` + `npm run dev` in `web/`; open the page.
3. Click **Generate** ≥ 5 times → each card shows a different, sensible
   3-term-ratio sharing question with a correct `$` answer and a **pass** badge.
4. Deliberately break `ratio_medium.solve` (e.g. wrong divisor) → the golden test
   goes red. Revert.

---

## Decisions resolved (were the deferred Q-K4/K5 opens)

V1 forced these; all now settled:

1. ✅ **Python 3.12**; `jsonschema` (Draft 2020-12) gates the canonical object.
2. ✅ **uv workspace**; `engine` is a path dependency of `api` — one
   implementation shared by API + future CLI, no publish step.
3. ✅ **Schema representation:** jsonschema-gated `dict` for the canonical object
   (single source of truth); **Pydantic only for API envelopes**. Typed engine
   models deferred (would need a serialize-validates contract test).
4. ✅ **`created_at` stamped at the API boundary**; engine emits `null` to stay
   pure/reproducible.
5. ✅ **`id = "{blueprint_code}:{seed}"`** in V1; edit-lineage suffix in V3;
   content-hash reserved for a future saved library.
6. ✅ **Placeholder `skill_codes`** under a provisional `content/syllabus/*.yaml`
   registry until the MOE doc (Q-M1); carried-not-queried in v1.

These specify/extend ADR-0006 (stack & layout) and ADR-0014 (schema authority);
worth capturing as a short **ADR-0016 (tech-stack specifics)** if you want them in
the decision register rather than only in this slice plan.
