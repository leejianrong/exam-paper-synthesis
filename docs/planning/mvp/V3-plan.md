---
shaping: true
---

# V3 Slice Plan — Ratio ladder + edit operations

> **Slice V3 of `docs/planning/mvp/SLICES.md`.** The teacher can nudge a question
> without leaving it. Ground truth for R and Shape A: `docs/planning/mvp/SHAPING.md`
> (part **A4**; requirements **R1.1–R1.2**, **R4.3–R4.8**). Difficulty model:
> `docs/DIFFICULTY.md` + ADR-0015. Edit semantics: **ADR-0009**; lineage/versioning:
> **ADR-0004**. Diagram policy: ADR-0007. Schema contract:
> `schemas/canonical-question.schema.json` (v1.1.0 — **no schema change in V3**).
>
> **Demo goal:** the Ratio card gains a row of edit buttons —
> **regenerate / make-harder / make-easier / change-to-decimals / toggle-diagram**.
> make-harder on `medium` yields a `hard` question; make-harder on `hard` hides the
> button; change-to-decimals rewrites the same question in decimals; toggle-diagram
> shows/hides the bar model (and is itself hidden on families with no aid diagram).
> Every edit produces a **new** object linked to its parent via
> `provenance.parent_id`, with `version` bumped, re-validated against the schema.

---

## Scope

Two halves. **(a)** finish the Ratio difficulty ladder so "harder/easier" has
siblings to swap to; **(b)** the edit-operation engine + API + web buttons. (a) is a
hard prerequisite of make-harder/make-easier, so it lands first.

**In:**

**(a) Ratio ladder — two new blueprints (author in parallel; each mirrors the
`ratio_medium` pattern exactly: YAML + solver + hand-verified golden fixtures):**
- **`ratio_easy`** — share a total in a **2-term ratio** (direct). One aid bar model
  (2 bars), reusing the V2 `bar_model` spec/check/renderer (all already generalise
  over `len(ratio)`).
- **`ratio_hard`** — **before-after with an invariant quantity** (hidden structure,
  inverse/work-backwards). Ships **with a new `bar_model_before_after` aid diagram**
  (equalised-units before/after model — the "model method" that makes the invariant
  visible). This is a **new diagram-union variant** (Decisions §D3), so it adds a
  minor, backward-compatible schema bump (1.1.0 → 1.2.0).

**(b) Edit operations (A4) — object→object transforms, each re-validated, each
setting `provenance.parent_id` + bumping `version` (ADR-0004/0009):**
- `regenerate` — resample within the *same* blueprint/rung (new seed).
- `make-harder` / `make-easier` — swap to the sibling blueprint one rung up/down the
  same topic ladder; **unavailable at the ends** (no easier than `easy`, no harder
  than `hard`).
- `change-to-decimals` — representation transform of the *current* object (money
  shown to 1 dp); answer becomes a `decimal`.
- `toggle-diagram` — aid families only; toggles `parts[0].diagram` between its spec
  and `null`; **hidden for families with no aid diagram** (e.g. `ratio_hard`).
- Engine: `engine/exam_engine/ladder.py` (topic ladder + sibling lookup) and
  `engine/exam_engine/edits.py` (the four transforms + availability). API:
  `POST /edit/{op}`. Web: buttons on `QuestionCard`, availability-gated, replacing
  the source card in place with its edited child.

**Explicitly deferred (do NOT build here):**
- Approve/discard + worksheet tray → **V4**. Preview + PDF export → **V5**.
- Other four topic ladders + mandatory geometry diagrams → **V6**. CLI + sourced
  objects → **V7**.
- Pulling an alternative from the internal bank on swap (R6.4) → deferred (V8 if
  promoted).
- Persisting lineage anywhere server-side. Edits are **stateless**: the client holds
  the object and posts it back; the server returns the child. (A store arrives with
  the worksheet in V4.)

---

## Schema impact — one minor, additive change

Most of V3 needs no schema change:
- `provenance.parent_id` (lineage) and `provenance.version` (≥1) already exist.
- `answer_decimal` (`type: "decimal"`, `value: number`, optional `dp`, `unit`) is
  already a union member → `change-to-decimals` needs no schema change.
- `parts[].diagram` already accepts `null` → `toggle-diagram` needs no schema change.
- `cognitive.difficulty` enum already includes `easy`/`hard`.

**One addition:** the `diagram` discriminated union (ADR-0012) gains a new member
`diagram_bar_model_before_after` (for `ratio_hard`). This is **backward-compatible**
(existing objects still validate), so `schema_version` bumps **1.1.0 → 1.2.0**
(minor). Touch points: add the `$def` + oneOf entry in
`schemas/canonical-question.schema.json`; bump `SCHEMA_VERSION` in `canonical.py`;
update `docs/SCHEMA.md` (and the `1.1.0` reference in `CLAUDE.md`). Every edited or
generated object still passes `canonical.load` (the A1 gate).

---

## Files touched

```
docs/planning/mvp/V3-plan.md                                  # NEW — this plan
docs/planning/mvp/SLICES.md                                   # note the ratio_hard no-diagram deferral (D3)

# (a) ladder
content/blueprints/ratio_easy.yaml                       # NEW
content/blueprints/ratio_hard.yaml                       # NEW
engine/exam_engine/blueprints/solvers/ratio_easy.py      # NEW  (sample/solve/validate/diagram = bar_model)
engine/exam_engine/blueprints/solvers/ratio_hard.py      # NEW  (sample/solve/validate/diagram = bar_model_before_after)
engine/exam_engine/blueprints/solvers/__init__.py        # import the two new solver modules
schemas/canonical-question.schema.json                   # + diagram_bar_model_before_after variant (1.2.0)
engine/exam_engine/canonical.py                          # SCHEMA_VERSION 1.1.0 → 1.2.0
engine/exam_engine/diagram.py                            # + before-after consistency check + SVG renderer
web/src/lib/barModel.js                                  # + before-after render branch (mirror engine)
docs/SCHEMA.md                                           # document the new diagram variant + 1.2.0
tests/golden/ratio_easy.jsonl                            # NEW — hand-verified
tests/golden/ratio_hard.jsonl                            # NEW — hand-verified
tests/test_generate_ratio_easy.py                        # NEW  (mirror test_generate_ratio_medium)
tests/test_generate_ratio_hard.py                        # NEW
tests/test_diagram_before_after.py                       # NEW  (consistency valid/corrupt, SVG smoke, determinism)

# (b) edit ops
engine/exam_engine/ladder.py                             # NEW — topic ladder + sibling(code, dir)
engine/exam_engine/edits.py                              # NEW — regenerate/harder/easier/decimals/toggle + availability
engine/exam_engine/errors.py                             # + EditNotApplicable
tests/test_ladder.py                                     # NEW
tests/test_edits.py                                      # NEW
api/app/routes_edit.py                                   # NEW — POST /edit/{op}
api/app/models.py                                        # + EditRequest / EditResponse
api/app/main.py                                          # include the edit router
web/src/lib/api.js                                       # + editQuestion(op, obj[, seed])
web/src/lib/QuestionCard.svelte                          # + edit-button row, availability-gated
web/src/App.svelte                                       # replace source card with edited child in place

# if V3 ships
site/index.html                                          # roadmap V3 → Shipped; status chip
```

---

## (a) The Ratio ladder

Both siblings follow the `ratio_medium` template to the letter: a blueprint YAML
(`code`, `syllabus`, `cognitive` with `difficulty` + `difficulty_levers`, `marks`,
`parameter_schema`, `story_templates`, `solution_template`, `marking_scheme`,
`answer`), a solver class (`sample`/`solve`/`validate`, plus `diagram` only for
`easy`) registered by name, and a hand-verified `tests/golden/<code>.jsonl`. All
constraints satisfied **by construction** (ADR-0014) so `validate` never has to
reject a well-formed sample.

### `ratio_easy` — 2-term share (direct)

- **Story:** "{A} and {B} share ${total} in the ratio {r0} : {r1}. How much does {B}
  receive?" Answer: quantity in `$` (positive integer).
- **cognitive:** `difficulty: easy`, `cognitive_level: routine_procedural`,
  `difficulty_levers: ["Reasoning depth"]` (1–2 steps). **marks: 2** (fewer than
  medium's 3 — composition lever, DIFFICULTY.md §1).
- **sample:** 2 distinct names; `ratio = [randint(1,9), randint(1,9)]` with the two
  terms unequal; `unit_value ∈ [3,60]`; `total = sum(ratio) * unit_value` (exact,
  in `[12,2000]`). Same construction as medium, two terms.
- **solve:** `unit_value = total // sum(ratio)`, answer = `ratio[1] * unit_value`.
- **validate:** `divides_evenly`, `sums_to_total`, `answer_verified`, `within_level`
  (mirror medium).
- **diagram:** `bar_model`, 2 bars `{label: name, units: term}`, unit annotation
  `"1 unit = $<unit_value>"`, `total_bracket "Total = $<total>"`. The V2
  `check_bar_model_consistency` + `render_svg` already handle any `len(bars)` — a
  quick unit test with 2 bars confirms, no engine change expected.
- **marking_scheme (sums to 2):** `M` find value of 1 unit; `A` correct share with $.
- **golden (hand-verified example):** `{names:[Aisha,Ben], ratio:[2,3], total:100}`
  → 1 unit = $20, Ben = 3×20 = **$60**. (2 more with different ratios/totals.)

### `ratio_hard` — before-after, invariant quantity (hidden structure)

The hard rung deliberately pulls **Direction (inverse/work-backwards)** + **Hidden
structure** + **Reasoning depth** (DIFFICULTY.md). One person's amount is invariant
across a before/after change; the student must realise that and equalise its units.

- **cognitive:** `difficulty: hard`, `cognitive_level: non_routine_heuristic`,
  `difficulty_levers: ["Direction", "Hidden structure", "Reasoning depth"]`.
  **marks: 4.**
- **Story:** "{A}'s and {B}'s savings were in the ratio {a} : {b}. After {A} spent
  ${spent}, the ratio became {c} : {d}. {B}'s savings did not change. How much did
  {B} have?" Answer: quantity in `$`. **{B} is the invariant.**

**Construction (guarantees clean integers; author verifies each golden by hand):**
Pick two lowest-terms 2-term ratios `a:b` (before) and `c:d` (after) with the second
term the invariant, chosen so `a/b > c/d` (A's share strictly shrinks). Let
`L = lcm(b, d)`; scale each ratio to `L` invariant-units:
- A-before units = `a*L/b`, A-after units = `c*L/d`, B units = `L`.
- `ΔU = a*L/b − c*L/d` (a positive integer) is how many units A lost.
Pick a per-unit dollar value `v`. Then, all integers by construction:
- `spent = ΔU * v`, and the **answer** `B = L * v`.
- (Cross-checks: A-before `= a*L/b * v`, A-after `= c*L/d * v`,
  `A_before − A_after == spent`, `A_before : B == a : b`, `A_after : B == c : d`.)

- **sample:** draw `a,b,c,d ∈ [1,6]`, reduce each pair to lowest terms, require
  `gcd(a,b)=gcd(c,d)=1`, `a/b > c/d`, and `b ≠ d` (non-trivial LCM so the "equalise
  units" step is real); pick `v` so `spent` and `B` stay in a P6-sensible range
  (e.g. `B ≤ 2000`). Reject degenerate draws; retry budget covers it.
- **solve:** recompute `L, ΔU, v = spent / ΔU, B = L * v`; return answer + rich
  `intermediates` (`L`, `a_before_units`, `a_after_units`, `delta_units`,
  `unit_value`, `b_amount`, …) so `solution_steps` can narrate the equalise step.
- **validate:** `spent_divisible_by_delta` (`spent % ΔU == 0`), `ratios_consistent`
  (both before/after ratios reduce correctly against `B` and the A-amounts),
  `answer_verified` (`B == L*v`), `within_level`.
- **solution_steps:** (1) equalise {B}'s units across before/after (state `L`);
  (2) A lost `ΔU` units = ${spent}; (3) 1 unit = ${spent} ÷ ΔU = $v; (4) {B} = L × $v
  = ${B}.
- **marking_scheme (sums to 4):** `M` equalise the invariant's units;
  `M` find units lost by A; `M` value of 1 unit; `A` correct {B} with $.
- **parameters** (the givens): `{names:[A,B], ratio_before:[a,b], ratio_after:[c,d],
  spent}`. `solve` recomputes `L, a_before_units, a_after_units, ΔU, unit_value,
  b_amount`. Sampling constructs `spent = ΔU·v` so it is divisible by `ΔU` by
  construction.
- **golden (hand-verified examples, in parameter terms):**
  - `ratio_before [2,3], ratio_after [1,2], spent 20`: `L=6`, A units 4→3, `ΔU=1`,
    `v=20`, **B = $120** (A: $80→$60; 80:120=2:3 ✓, 60:120=1:2 ✓, spent 20 ✓).
  - `ratio_before [5,3], ratio_after [1,2], spent 70`: `L=6`, A units 10→3, `ΔU=7`,
    `v=10`, **B = $60** (A: $100→$30; 100:60=5:3 ✓, 30:60=1:2 ✓, spent 70 ✓).
    *(ΔU>1 → genuinely needs the equalise-then-divide reasoning, not a read-off.)*
  - `ratio_before [5,4], ratio_after [1,2], spent 45`: `L=4`, A units 5→2, `ΔU=3`,
    `v=15`, **B = $60** (A: $75→$30; 75:60=5:4 ✓, 30:60=1:2 ✓, spent 45 ✓).
    *(`b=4 ≠ d=2` → the LCM step is real.)*

**Before-after aid diagram (`bar_model_before_after`).** The "model method" figure,
drawn in **equalised units** (B has the same `L` units in both stages — that *is*
the invariant, made visible). Solver `diagram(params, solution)` emits:

```jsonc
{
  "type": "bar_model_before_after",
  "stages": [
    {"name": "Before", "bars": [{"label": A, "units": a_before_units}, {"label": B, "units": L}]},
    {"name": "After",  "bars": [{"label": A, "units": a_after_units},  {"label": B, "units": L}]}
  ],
  "annotations": [{"label": "1 unit = $<v>"}, {"label": "<A> spent = $<spent>"}],
  "total_bracket": {"label": "<B> = $<b_amount>"}
}
```

- **Schema:** new `$def` `diagram_bar_model_before_after` added to the `diagram`
  oneOf; `stages` is exactly 2 objects `{name, bars[]}`, reusing the `{label, units}`
  bar item; optional `annotations[]` and `total_bracket` (same shapes as `bar_model`).
- **Consistency check** (`diagram.py`, dispatched on the new `type`): 2 stages named
  Before/After; before bars = `[A→a_before_units, B→L]`, after bars =
  `[A→a_after_units, B→L]`; **invariant** `before.B.units == after.B.units == L`;
  labels == `[A, B]`; `"1 unit = $<v>"` and `"<A> spent = $<spent>"` present in
  annotations; `total_bracket.label == "<B> = $<b_amount>"`. A corrupted spec fails.
- **Renderer** (`diagram.py` + mirror in `web/src/lib/barModel.js`): two stacked
  bar groups, each with a stage label ("Before"/"After") in the left gutter, reusing
  the V2 per-bar drawing (rect + per-unit dividers); annotations under; a vertical
  brace on B → its `$` total. Pure/deterministic (integer coords, no RNG/clock).
  `renderDiagram`/`render_svg` gain a `bar_model_before_after` branch; the existing
  `bar_model` path is untouched (lower regression risk than overloading it).
- Because `ratio_hard` is now a full aid family, **toggle-diagram is available on all
  three Ratio rungs** (see below).

---

## (b) Edit operations

### Common contract (all four ops — ADR-0004/0009)

Each op is a **pure function** `obj → obj` (regenerate/harder/easier also take a
`seed`), producing a **new** canonical object that:
1. is schema-valid (`canonical.load`) — the A1 gate applies to edits too;
2. sets `provenance.parent_id = source["id"]`, `provenance.version =
   source["provenance"]["version"] + 1`, keeps `created_by="engine"`,
   `llm_used=false`, `created_at=null` (stamped at the API boundary);
3. gets a fresh unique `id`. Rule: resampling ops (new seed) → the natural
   `f"{code}:{seed}"`; in-place transforms (same seed) →
   `f"{code}:{seed}:v{version}"` to avoid colliding with the parent. (Uniqueness
   within a session is all that's required pre-V4.)
4. is **never mutated in place** — the source object is returned untouched.

`edits.py` exposes `apply(op, obj, *, seed=None) -> dict` and
`available_ops(obj) -> set[str]` (drives both the API guard and the UI). An op that
isn't applicable raises `EditNotApplicable` (→ HTTP 422).

### `regenerate`
Resample the same blueprint at a new seed: effectively `generate(obj["blueprint_code"],
new_seed)`, then stamp lineage (parent_id/version) onto the result. Same rung, new
numbers. Always available.

### `make-harder` / `make-easier`
`ladder.sibling(code, +1|-1) -> code | None` via the topic ladder. If a sibling
exists, `generate(sibling_code, new_seed)` + lineage stamp (the new `cognitive`
block comes from the sibling blueprint, so `difficulty` reflects the new rung). If
`None` (top/bottom of ladder), the op is **not available** — `available_ops` omits
it and the endpoint raises `EditNotApplicable`. (Params can't carry across
different blueprints, so this is a resample, per ADR-0009 — "not merely larger
numbers".)

**Ladder registry (`ladder.py`):** group blueprints into ordered topic ladders. For
V3 the only ladder is `ratio: [ratio_easy, ratio_medium, ratio_hard]`. Represent it
explicitly (a small module-level dict, or derive by grouping loaded blueprints on
`syllabus.topic` and ordering by `cognitive.difficulty`) — explicit dict is simplest
and unambiguous for one ladder; note it must grow with V6's topics. `sibling` returns
the adjacent code or `None` at the ends.

### `change-to-decimals`
Representation transform of the **current** object: show every monetary quantity to
1 dp by dividing by 10. Because the source is an already-verified **exact integer**
solution, dividing by 10 is exact at 1 dp — provably correct. It rewrites
`parts[0].text`, `solution_steps`, `answer` (→ `{type:"decimal", value, dp:1,
unit:"$"}`), and the diagram's annotation/`total_bracket` labels (if a diagram is
present). Recommended implementation: **re-render from the blueprint's templates**
with a scaled context (load the blueprint by `blueprint_code`, divide the `$`
context values by 10, re-fill the same story/solution templates) — cleaner and less
brittle than regex-scaling stored strings. `parameters` is **left as the original
integer sample** (it is the provenance of how the object was made; the decimals view
is derived from it — see Decisions §D2). Records `validation.checks["representation"]
= "decimals"`. Available whenever the answer is a `$` quantity (all three Ratio
rungs). Idempotence/round-tripping is out of scope — one transform level is enough
for the demo.

### `toggle-diagram`
Aid families only. If `parts[0].diagram` is present → return a child with it set to
`null`; if it is `null` **and the blueprint declares an aid diagram family** → rebuild
it via the solver's `diagram(params, solution)` and re-run `check_consistency`.
`available_ops` includes `toggle-diagram` **iff** the blueprint is an aid family
(`spec.diagram` set — `bar_model` for easy/medium, `bar_model_before_after` for
hard) — so it is present on **all three Ratio rungs**, and will be **hidden** on the
future mandatory-geometry families (ADR-0007), whose figures aren't toggleable. (The
"toggle hidden" UI path is therefore first exercised in V6, not V3.) Re-validated
against the schema after the toggle.

---

## API — `POST /edit/{op}` (`routes_edit.py`)

- Path param `op ∈ {regenerate, make-harder, make-easier, change-to-decimals,
  toggle-diagram}` (unknown op → 404).
- Body: `EditRequest { question: dict (the source canonical object), seed?: int }`.
- Flow: `canonical.load(question)` (reject a tampered/invalid source → 422), guard
  `op in available_ops(question)` else 422, `child = edits.apply(op, question,
  seed=…)`, stamp `child["provenance"]["created_at"]` here (the only entropy/clock
  boundary, ADR-0016), return `EditResponse { question: child }`.
- Errors map like `/generate`: `UnknownBlueprint`→404, `InfeasibleConstraints`→422,
  `EditNotApplicable`→422.

The engine stays UI/HTTP-agnostic: all transform logic lives in `engine/`; the route
only marshals, guards, and stamps the clock.

## Web — buttons on the card

- `web/src/lib/api.js`: `editQuestion(op, obj, seed?)` → `POST /edit/{op}`, returns
  the child object (mirrors `generate`'s error handling).
- `web/src/lib/QuestionCard.svelte`: an **edit-button row**
  (regenerate · make-easier · make-harder · change-to-decimals · toggle-diagram).
  Compute availability **client-side from the object** so buttons that can't apply
  never show: hide make-easier on `easy`, make-harder on `hard` (from
  `cognitive.difficulty`); hide toggle-diagram unless the object is an aid family
  (heuristic: `blueprint_code` starts a known aid family / `parts[0].diagram` is
  non-null OR was — simplest: show toggle iff blueprint ∈ aid set; `ratio_hard`
  excluded). Emit an event (or accept a callback) so the parent can swap the card.
- `web/src/App.svelte`: on edit, **replace the source card in place** with the
  returned child (preserving list position; lineage visible via `parent_id`). A
  small busy state on the card during the request.

The card keeps its V2 look/feel; the button row is the only new chrome. Topic/
difficulty selectors remain out of scope (they arrive with V6); the pinned panel
stays, but the ladder now moves via make-harder/easier on the card.

---

## Tests (pytest)

| Test | Asserts |
|---|---|
| `test_generate_ratio_easy` | schema-valid; `difficulty==easy`; total_marks 2; 2 bars whose units == ratio; `diagram_consistent`; deterministic; goldens (params→answer). |
| `test_generate_ratio_hard` | schema-valid (**1.2.0**); `difficulty==hard`; total_marks 4; `parts[0].diagram.type=="bar_model_before_after"`; `diagram_consistent`; deterministic; goldens verify the before/after cross-checks (both ratios + `spent`). |
| `test_diagram_before_after` | consistency all-true for the built spec; corrupting a stage bar / breaking the invariant / altering an annotation flips a check to `False`; `render_svg` smoke (starts `<svg`, contains both names, both stage labels, the `$v`/`$spent`/total labels); render is deterministic. |
| `test_ladder` | `sibling(ratio_easy,-1) is None`; `sibling(ratio_easy,+1)==ratio_medium`; `…medium±1`; `sibling(ratio_hard,+1) is None`. |
| `test_edits::regenerate` | new object, same blueprint, `parent_id==source.id`, `version==source.version+1`, schema-valid, source unmutated. |
| `…::make_harder/_easier` | swaps rung; `difficulty` matches sibling; `available_ops` omits harder on hard / easier on easy; applying an unavailable op raises `EditNotApplicable`. |
| `…::change_to_decimals` | answer.type==`decimal`, dp==1, every `$` value == source/10 exactly; text/steps rewritten; schema-valid; `parameters` unchanged. |
| `…::toggle_diagram` | present→null and null→rebuilt-consistent for `ratio_easy`/`medium`; **not** in `available_ops(ratio_hard)`. |
| `…::lineage_invariants` | for every op: `created_by=="engine"`, `llm_used is False`, `created_at is None`, unique `id`, source object deep-equal to before. |
| `test_api_edit` (httpx TestClient) | `POST /edit/regenerate` 200 + lineage + `created_at` stamped; `POST /edit/make-harder` on a hard object → 422; unknown op → 404; tampered body → 422. |

All V1/V2 tests must stay green (three blueprints now register; the ladder additions
don't touch `ratio_medium`).

---

## Demo / acceptance (V3 done when)

1. `uv run pytest` green (V1/V2 + all the above).
2. `npm --prefix web run build` compiles; `npm run e2e` (V3 flow) passes if extended.
3. In the browser: Generate a Ratio (medium) card → click **make-harder** → a `hard`
   before-after question replaces it and **make-harder is now hidden**; **make-easier**
   twice returns to `easy` and **make-easier is hidden**; **change-to-decimals**
   rewrites the same question with 1-dp money and a decimal answer;
   **toggle-diagram** hides/re-shows the bar model on easy/medium and **is absent on
   the hard card**; **regenerate** gives fresh numbers at the same rung. Every child
   carries `parent_id` to its source.
4. Site roadmap V3 flips to **Shipped** and the status chip updates (only after merge).

---

## Decisions / notes

- **D1 — Edits are stateless & object-carrying.** No server-side lineage store in
  V3 (that arrives with the worksheet in V4). The client posts the source object;
  the server returns the child. Keeps V3 additive and the engine pure.
- **D2 — `change-to-decimals` keeps `parameters` as the integer sample.** The param
  schema constrains `total` to an integer, and `parameters` records *how the object
  was sampled*. The decimals view is a faithful **derivation** (÷10) of that sample,
  applied to the displayed text/steps/answer/diagram. Documented so the parameters↔
  text relationship is understood, not surprising.
- **D3 — `ratio_hard` ships WITH a before-after bar model (owner decision).** ADR-0007
  files ratio (incl. before-after) under the toggleable *aid* tier, so we build the
  `bar_model_before_after` diagram now (new discriminated-union variant, schema
  1.2.0) rather than deferring it. Drawn in **equalised units** so the invariant is
  visible — the actual "model method". Kept as its **own** union member + check +
  renderer branch so the V2 `bar_model` path is untouched (regression-safe). All
  three Ratio rungs are aid families, so `toggle-diagram` shows on all three; the
  "toggle hidden" path moves to V6's mandatory-geometry families.
- **D4 — One minor schema addition; no new deps, no LLM.** Only change is the
  additive `bar_model_before_after` diagram variant (1.2.0). Every edited/generated
  object still round-trips through the same `canonical.load` gate; all transform and
  render logic is stdlib Python in `engine/` (SVG is hand-built strings).
- **D5 — Ladder registry is explicit for now.** One ladder (`ratio`) as an explicit
  ordered list; it must be extended (or switched to topic-grouping) when V6 adds the
  other four topics. Flagged so it isn't forgotten.

---

## Sequencing & fan-out (orchestration)

```
(a) ladder  ──►  (b) edit engine  ──►  API /edit/{op}  ──►  web buttons  ──►  site roadmap
 ├ ratio_easy  (parallel)         depends on ladder     depends on engine   depends on endpoints   after merge
 └ ratio_hard  (parallel)
```

1. **Two parallel agents.** Agent A authors `ratio_easy` (small — reuses the V2
   `bar_model`). Agent B authors the whole `ratio_hard` vertical **including the
   before-after diagram infra** (schema variant + 1.2.0 bump, `diagram.py` check +
   renderer, `barModel.js` mirror, solver, goldens, diagram tests) — the meaty unit.
   Shared files: only `solvers/__init__.py` (both add an import) — integrator
   resolves that one-line merge. Agent B also touches `schema.json`/`canonical.py`/
   `diagram.py`/`barModel.js`/`SCHEMA.md`, which Agent A does not. Each hand-verifies
   its goldens. Worktree isolation keeps them from colliding.
2. **Then** one agent builds `ladder.py` + `edits.py` + `errors.py` + engine tests
   (depends on all three rungs existing).
3. **Then** the API `/edit/{op}` + models + tests (depends on `edits.py`).
4. **Then** the web buttons + `api.js` + in-place swap (depends on the endpoints).
5. Integrator opens one PR per logical unit; merges only when `uv run pytest` +
   `npm --prefix web run build` are green. Site roadmap flip is the final PR, only
   once V3 is actually shipped.
