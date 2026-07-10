---
shaping: true
---

# V2 Slice Plan — Worked solution + marks + bar model

> **Slice V2 of `docs/shaping/SLICES.md`.** Make the answer *explainable* and add
> the aid diagram. Ground truth for R and Shape A: `docs/shaping/SHAPING.md`
> (parts **A5**, **A6**; requirements **R2.3–R2.4**, **R2.6**, **R3.2–R3.4**).
> Schema contract: `schemas/canonical-question.schema.json` (`diagram_bar_model`).
> Diagram policy: ADR-0007 (ratio = **aid/bar_model**, toggleable — but the toggle
> itself is **V3**). Diagram representation: ADR-0012 (discriminated union on `type`).
>
> **Demo goal:** the Ratio card now shows the worked solution steps, `[n]` marks
> per part, an accurate bar-model SVG whose bar units equal the ratio terms, and a
> detailed answer-key toggle revealing the M/A/B breakdown. A deliberately
> corrupted bar-model spec is rejected by the consistency check.

---

## Scope

**In (Shape-A parts A5, A6):**
- **A5 — bar-model diagram (engine).**
  - `RatioMediumSolver.diagram(params, solution) -> dict` returns a schema-valid
    `bar_model` spec: one bar per ratio term (`units` = that term, `label` = that
    person's name), plus annotations for the per-unit value and the total. Pure
    and deterministic (derived only from `params` + solved `intermediates`).
  - A **diagram-consistency check** (`engine/exam_engine/diagram.py`) asserting
    every bar's `units`/`label` and each annotation equals the corresponding
    parameter/solved value (R3.3). A deliberately corrupted spec is rejected.
  - A deterministic **spec → inline SVG** renderer (`diagram.py`, pure-Python
    string building, no external libs) producing a crisp, inspectable `<svg>`
    (R3.4) — the print/export source of truth for A7 (V5).
  - Pipeline wires the diagram onto `question.parts[0].diagram` (embedded), and
    records `diagram_consistent` in `validation.checks`.
- **A6 — worked solution + marks (web).** The canonical object already carries
  `solution_steps` and `marking_scheme` (from V1). V2 *renders* them:
  `QuestionCard.svelte` shows the ordered worked steps, per-part `[n]` marks, the
  bar-model SVG, and a **detailed answer-key toggle** revealing M/A/B.

**Explicitly deferred (later slices — do NOT build here):**
- **Diagram toggle** (`toggle-diagram` edit op) and all other edit ops
  (regenerate / make-harder / make-easier / change-decimals) → **V3**. The bar
  model is **embedded and always rendered** in V2; there is no include/exclude
  control.
- Difficulty-ladder sibling blueprints (`ratio_easy`, `ratio_hard`) → **V3**.
- Approve/discard + worksheet tray → **V4**. Preview + PDF export → **V5**
  (the engine SVG renderer built here is what A7 will embed for crisp print).
- Other 4 topics + mandatory geometry diagrams (`composite_geometry`,
  `area_perimeter`, `shaded_fraction`) → **V6**. CLI + sourced/raster → **V7**.

**Single blueprint for V2:** still `ratio_medium` (V1's 3-term sharing question),
now carrying a bar model + rendered solution. No new blueprints.

---

## Where V2 sits vs the schema (no schema change)

The canonical schema already models everything V2 needs:
- `question.parts[].diagram` accepts `null` or a `diagram` union member; V2 emits a
  `diagram_bar_model` (`type`, `bars[]` of `{label, units}`, optional
  `annotations[]` of `{from_unit?, to_unit?, label}`).
- `question.parts[].solution_steps` and `marking_scheme` were already populated in
  V1; V2 only adds a rendering surface for them.
- `validation.checks` is an open string→bool/str/null map; V2 adds
  `diagram_consistent`.

**No edit to `schemas/canonical-question.schema.json`.** The rendered SVG is *not*
stored on the object (the object is closed / `additionalProperties:false` and has
no SVG field): the SVG is a **view** of the spec. The engine renderer is the
authority for print/export (A7/V5); the web renders its own inline SVG from the
same spec for the live card. Both are deterministic functions of the spec, so they
agree by construction.

---

## Files touched

```
docs/shaping/V2-plan.md                         # NEW — this plan
docs/shaping/SLICES.md                          # (only if scope drifts; no drift expected)

engine/exam_engine/diagram.py                   # NEW — A5: consistency check + spec→SVG renderer
engine/exam_engine/blueprints/solvers/ratio_medium.py  # + diagram(params, solution)
engine/exam_engine/pipeline.py                  # build diagram, consistency-gate, pass to assemble
engine/exam_engine/canonical.py                 # assemble(..., diagram=...) → part.diagram
engine/exam_engine/errors.py                    # + DiagramInconsistent
content/blueprints/ratio_medium.yaml            # diagram: bar_model (declares the aid family)

web/src/lib/barModel.js                          # NEW — spec→inline-SVG (mirrors engine renderer)
web/src/lib/QuestionCard.svelte                  # A6: steps, [n] marks, SVG, M/A/B toggle

tests/test_diagram_bar_model.py                  # NEW — consistency (valid/corrupt), SVG smoke, determinism
tests/golden/ratio_medium.jsonl                  # (unchanged; diagram derived in-test from params)
tests/test_generate_ratio_medium.py              # + assert a diagram is present & schema-valid
```

---

## A5 — bar-model diagram (engine)

### Spec builder — `RatioMediumSolver.diagram(params, solution)`

Deterministic; derives everything from `params` + `solution["intermediates"]`:

```python
def diagram(self, params, solution):
    names = params["names"]; ratio = params["ratio"]; total = params["total"]
    unit_value = solution["intermediates"]["unit_value"]
    return {
        "type": "bar_model",
        "bars": [{"label": n, "units": r} for n, r in zip(names, ratio)],
        "annotations": [
            {"from_unit": 0, "to_unit": 1,          "label": f"1 unit = ${unit_value}"},
            {"from_unit": 0, "to_unit": sum(ratio), "label": f"Total = ${total}"},
        ],
    }
```

- **One bar per ratio term**, `units` = the term, `label` = the sharer's name — so
  bar lengths are literally the ratio (R2.6, R3.3).
- Annotations state the two solved anchors: the value of **1 unit**, and the
  **total** spanning all units. Labels are computed strings (checkable).

### Consistency check — `engine/exam_engine/diagram.py`

`check_consistency(spec, params, solution) -> dict[str, bool]` dispatches on
`spec["type"]`. For `bar_model` it asserts, against the *actual* values:

| Check | Asserts |
|---|---|
| `bar_count` | `len(bars) == len(ratio)` |
| `bar_units` | `bars[i].units == ratio[i]` for all i |
| `bar_labels` | `bars[i].label == names[i]` for all i |
| `unit_annotation` | an annotation label equals `"1 unit = $<unit_value>"` |
| `total_annotation` | an annotation label equals `"Total = $<total>"` |

`check_bar_model_consistency` is pure and independently testable: a hand-corrupted
spec (wrong `units`, renamed bar, altered annotation) returns a failing check.
This is R3.3 ("every label/dimension matches the question's numbers exactly").

### Spec → inline SVG — `render_svg(spec) -> str` (same module)

Pure-Python string building, **no external libraries**, fully deterministic (no
timestamps / RNG / hash-ordered iteration; integer coordinates only):
- Left gutter for the bar label (name), fixed unit cell width, one row per bar.
- Each bar drawn as a `<rect>` subdivided into `units` equal cells (per-unit grid
  lines) so the reader can count units — crisp at any zoom (vector, R3.4).
- Annotations drawn as spanning braces/lines under the bars with their label text.
- Text XML-escaped. Output begins with `<svg` and carries `viewBox` (scales cleanly).

`render_svg` dispatches on `type`; only `bar_model` is implemented in V2 (others
raise — they arrive with their families in V6).

### Pipeline & assembly wiring

`pipeline.run_pipeline` — after a successful solve/validate:
1. `diagram_spec = build_part_diagram(solver, params, solution)` (returns `None`
   if the solver has no `diagram` method — keeps V1-style solvers working).
2. If present, run `check_consistency`; record `diagram_consistent` in
   `report["checks"]`. Inconsistency is an **engine/blueprint bug** (a
   deterministic builder must always agree with its own values), so it raises
   `DiagramInconsistent` loudly — it is *not* a retry-able infeasibility.
3. `assemble(..., diagram=diagram_spec)` attaches the spec at
   `question.parts[0].diagram`; the assembled object is schema-validated as before
   (so an off-schema diagram fails the A1 gate).

`generate("ratio_medium", seed)` stays a pure, deterministic function.

---

## A6 — worked solution + marks (web)

`web/src/lib/QuestionCard.svelte` (keep V1 look/feel — same CSS variables, card
chrome, badge, answer formatting):
- **Worked solution:** ordered list of `part.solution_steps[].text`.
- **`[n]` marks:** per-part marks shown as `[n]` (already in the header meta;
  reinforced beside the solution heading).
- **Bar-model SVG:** `web/src/lib/barModel.js` renders `part.diagram` (the
  `bar_model` spec) to an inline `<svg>` string, injected with `{@html}`. This
  mirrors the engine renderer (same layout rules); it exists because the closed
  schema stores the *spec*, not the SVG, and the live card renders client-side
  while the engine renderer serves the eventual PDF path (A7/V5).
- **Detailed answer-key toggle:** a button that expands `part.marking_scheme` as an
  M/A/B breakdown (`[mark] TYPE — description`), collapsed by default (R2.5).

No new topic/difficulty controls, no diagram toggle, no approve/discard — those are
later slices.

---

## Tests (pytest)

| Test | Asserts | Seam |
|---|---|---|
| `test_diagram_bar_model::test_spec_is_schema_valid_bar_model` | solver `diagram()` output validates as a `diagram_bar_model` (via a part round-trip through the canonical validator) | A5 spec |
| `…::test_consistency_passes_for_built_spec` | `check_consistency` returns all-true for the honestly-built spec | A5 check |
| `…::test_consistency_rejects_corruption` | corrupting `units`, a `label`, or an annotation flips the relevant check to `False` | A5 check (R3.3) |
| `…::test_svg_render_smoke` | `render_svg` output is non-empty, starts with `<svg`, contains each name and the unit/total annotation values | A5 render (R3.4) |
| `…::test_svg_is_deterministic` | `render_svg(spec) == render_svg(spec)` and is stable across builds for a fixed seed | determinism |
| `test_generate_ratio_medium` (extended) | generated object still schema-validates **with a diagram present**; `parts[0].diagram.type == "bar_model"`; `validation.checks.diagram_consistent is True`; bars’ units == ratio | A3 + A5 end-to-end |
| golden (in-test) | for each golden `params`, the built diagram’s bars equal `zip(names, ratio)` | A5 correctness anchor |

Determinism and schema-validity of the whole object are re-asserted with the
diagram embedded, so V1 guarantees are preserved.

---

## Demo / acceptance (V2 done when)

1. `uv run pytest` green (V1 tests + the A5/A6 tests above).
2. `cd web && npm install && npm run build` compiles.
3. In the browser, click **Generate** → the Ratio card shows: worked steps, `[n]`
   marks, a bar model whose three bars have lengths equal to the ratio and whose
   annotations read the correct `1 unit = $…` / `Total = $…`, and a working
   **detailed answer key** toggle showing M/A/B.
4. Corrupt the bar-model spec in a test → the consistency check rejects it.

---

## Decisions / notes

1. **SVG is a view, not stored on the object.** The closed canonical schema has no
   SVG field, so the rendered SVG lives outside the object. Engine renderer =
   authority for print (A7/V5); web mirrors it from the same spec. Both are pure
   functions of the spec, so they cannot disagree on content.
2. **Diagram driven by the solver method, not YAML.** The pipeline keys off the
   presence of `solver.diagram`; `content/blueprints/ratio_medium.yaml` sets
   `diagram: bar_model` only to *declare the aid family* (useful when V3 adds the
   toggle and V6 adds mandatory families). No code branches on that value in V2.
3. **Inconsistency raises, not retries.** A deterministic diagram built from
   correct values is always consistent; an inconsistent one signals a code bug, so
   it surfaces loudly like a schema-invalid assembly (mirrors V1's assemble gate).
4. **No new dependencies, no LLM, engine stays UI/HTTP-agnostic.** SVG is
   hand-built strings; the check and renderer live in `engine/` with only stdlib.
