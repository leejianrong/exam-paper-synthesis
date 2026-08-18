---
shaping: true
---

# E2 Slice Plan — Schema v2: MCQ, stem diagram, optional marks

> **Slice E2 of `docs/planning/editor/SLICES.md`.** The first schema-growth
> slice: `answer.type:"choice"` (A3), a stem-level `question.diagram` with
> per-part unknown binding (A4), and optional `part.marks`/`marking_scheme`
> (A5) — all additive, no breaking change to existing v1.4.0 objects. Ground
> truth: `docs/planning/editor/SHAPING.md` (R2.3, R2.7–R2.8, R7.1–R7.3, R7.7),
> `docs/planning/editor/SCHEMA-FIT.md` (G1, G2, G5, G9). Decision: ADR-0020.
> Schema bumps **1.4.0 → 1.5.0**.
>
> **Demo goal:** `mathgen bank import` a hand-authored MCQ (some options
> text-only, one carrying its own diagram) — `mathgen export preview` renders
> lettered options with no answer revealed, the answer key marks the correct
> one. Separately, import a two-part question sharing one stem-level
> `geometry_figure` with two angles bound one-per-part (mirroring G5's FIG-24:
> ∠LOK for part (a), ∠LNM for part (b)) where one part also carries no
> `marks`/`marking_scheme` — the figure renders once, not duplicated per part,
> and the unmarked part prints no fabricated `[n]`.

---

## Scope

**In (Shape-A parts A3, A4, A5):**
- **A3** — `answer.type:"choice"` sub-schema: `options[]` (each `label` +
  optional `text`/`diagram`) + `correct` label; worksheet/answer-key render
  branch (Python only — see Decision 2 below on the TS mirror).
- **A4** — `diagram` allowed on `question` (stem-level, sibling to `stem`);
  `geometry_figure.angles[]` gains an optional `part_label` so a shared
  figure's unknowns can each be bound to the part that asks for them.
- **A5** — `part.marks`/`part.marking_scheme` become optional; both renderers
  stop fabricating a `[n]` or an empty M/A/B list when absent.

**Explicitly deferred (later slices / out of this milestone):**
- `table`, `grid`+`polygons`, `construction` answers → **E3**.
- The paper/section/group container → **E4**.
- A web UI for authoring any of this → **E5**.
- The web app's TS diagram mirror (`web/src/lib/barModel.ts`) and
  `QuestionCard.svelte` — see **Decision 1**.
- The `geometry_figure` consistency check's per-part resolution is added as a
  direct, unit-tested extension only (no live blueprint caller yet) — see
  **Decision 2**.
- MCQ presentational sugar with no evidence requirement this slice: an
  options-list header spanning all four choices (SCHEMA-FIT G1's P1 Q7) is not
  modelled; it can be folded into the stem's prose. Not needed for E2's own
  demo, and doesn't block E4's acceptance paper either (it's cosmetic).
- Enforcing `answer.correct` actually names one of `options[].label`, or that
  every option carries at least one of `text`/`diagram` — left to human review
  (ADR-0019), not JSON Schema. Consistent with how the schema already leaves
  "does the marking scheme's sum match the marks" etc. unenforced for sourced
  content — schema catches *structure*, the reviewer catches *correctness*.

---

## Repo layout (new/changed files)

```
engine/
  exam_engine/
    canonical.py                                    # SCHEMA_VERSION -> "1.5.0"
    diagram.py                                       # check_geometry_figure_consistency: + part_solutions kwarg
    render.py                                        # MCQ options renderer, stem diagram, optional marks
    schemas/
      canonical-question.schema.json                 # answer_choice, question.diagram, optional part.marks/marking_scheme, angles[].part_label
docs/
  SCHEMA.md                                          # document the three additions
  planning/editor/SLICES.md                          # link E2-plan.md under the E2 section (ripple, mirrors E1)
tests/
  fixtures/sourced/
    psle_2023_mcq.json                                # NEW
    psle_2023_stem_diagram.json                        # NEW
  test_schema_validation.py                          # + structural tests for all three additions
  test_sourced_interchange.py                          # + fixture-based load/render tests
  test_geometry_figure.py                              # + per-part unknown consistency test
  test_render.py                                       # + MCQ/options/stem-diagram/optional-marks render tests
```

No new workspace member, no new dependency, no CLI change — `mathgen bank
import`/`list`/`search`/`review` and `mathgen export {preview,worksheet,
answer-key}` already accept any schema-valid object (E1); a v1.5.0 object
"just works" through them once the schema and renderers accept it.

---

## A3 — `answer.type:"choice"` (MCQ)

### Schema

```json
"answer_choice": {
  "type": "object", "additionalProperties": false,
  "required": ["type", "options", "correct"],
  "properties": {
    "type": { "const": "choice" },
    "options": {
      "type": "array", "minItems": 2,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["label"],
        "properties": {
          "label": { "type": "string", "minLength": 1 },
          "text": { "type": ["string", "null"] },
          "diagram": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/diagram" } ] }
        }
      }
    },
    "correct": { "type": "string", "minLength": 1 }
  }
}
```

Add `{ "$ref": "#/$defs/answer_choice" }` to the `answer` `oneOf` union
(`$defs.answer`).

### Render (`render.py`)

An option is question content (the four choices), not the answer, so
`_render_part_head` prints all options on the **worksheet** too — only
`correct` is secret. Add a shared helper and thread a `reveal_correct` flag
down from `_render_questions`'s existing `answer_key` bool:

```python
def _render_options(answer: dict, *, reveal_correct: bool) -> list[str]:
    correct = answer.get("correct")
    out = ['<ol class="options">']
    for opt in answer.get("options", []):
        cls = "option option-correct" if reveal_correct and opt["label"] == correct else "option"
        out.append(f'<li class="{cls}">')
        out.append(f'<span class="option-label">({_esc(opt["label"])})</span>')
        if opt.get("text"):
            out.append(f'<span class="option-text">{_mathify(opt["text"])}</span>')
        if opt.get("diagram"):
            out.append(f'<figure class="diagram">{diagram.render_svg(opt["diagram"])}</figure>')
        out.append("</li>")
    out.append("</ol>")
    return out
```

- `_render_part_head(part, *, multipart, answer_key)` (new `answer_key` param)
  calls `_render_options(part["answer"], reveal_correct=answer_key)` right
  after the part text/marks line, whenever `part["answer"]["type"] ==
  "choice"`.
- `_render_questions`'s per-part loop: when the part is an MCQ, **skip** the
  `.answer-space` filler div for the worksheet branch (there's nothing to
  write beyond circling a lettered option) — only render it for constructed
  responses.
- `_fmt_answer` (answer-key "Answer:" line) gains a `choice` branch: looks up
  the option matching `correct` and prints `(label)` plus its `text` if
  present, e.g. `Answer: (2) a rhombus`.

### Fixture

`tests/fixtures/sourced/psle_2023_mcq.json` — a single-part MCQ modelled on
the shape of SCHEMA-FIT G1's P1 Q8 (four candidate options, correct one
marked), simplified from the real question for fixture maintainability: two
options carry only `text`, one carries a small `geometry_figure` diagram, one
carries both — this exercises the full text/diagram/both combination space
without hand-authoring four full net diagrams (the *shape* is what this slice
proves, not a literal transcription — same standing as the existing
`psle_2023_ratio.json` fixture).

---

## A4 — stem-level `question.diagram` + per-part unknown binding

### Schema

```json
"question": {
  ...
  "properties": {
    "stem": { ... },
    "diagram": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/diagram" } ] },
    "parts": { ... },
    "total_marks": { ... }
  }
}
```

`geometry_figure.angles[]` items gain one optional field:

```json
"part_label": {
  "type": ["string", "null"],
  "description": "Which part.label this unknown answers, when the figure is stem-level and serves more than one part. Null/absent when the figure is part-scoped or has a single unknown (today's default)."
}
```

### Render (`render.py`)

`_render_questions` prints the stem-level diagram once, right after the stem
and before the parts loop (mirrors how `stem` itself already prints once,
not per part):

```python
q_diagram = obj["question"].get("diagram")
if q_diagram is not None:
    out.append(f'<figure class="diagram">{diagram.render_svg(q_diagram)}</figure>')
```

Per-part `part.diagram` rendering is unchanged (both can coexist — no
exclusivity rule; a question may have a stem figure *and* a part with its own
supplementary figure).

### Diagram-consistency check (`diagram.py`)

**Decision 2 (see below) scopes this to a direct, unit-tested extension of
`check_geometry_figure_consistency`, not new pipeline wiring**, because
`canonical.assemble()` only ever builds single-part objects today (no
blueprint produces a multi-part, shared-stem-diagram question) — there is no
live caller to wire this into.

```python
def check_geometry_figure_consistency(
    spec: dict, params: dict, solution: dict,
    *, part_solutions: dict[str, dict] | None = None,
) -> dict[str, bool]:
    ...
    unknowns = [a for a in angles if a.get("unknown")]
    if part_solutions is not None:
        def _bound_ok(ang: dict) -> bool:
            part_ans = (part_solutions.get(ang.get("part_label")) or {}).get("answer", {})
            return _num_eq(ang.get("value_deg"), part_ans.get("value"))
        checks["unknown_angle_matches_answer"] = all(_bound_ok(a) for a in unknowns) if unknowns else True
    elif unknowns:
        ans_val = answer.get("value")
        checks["unknown_angle_matches_answer"] = ans_val is not None and all(
            _num_eq(a.get("value_deg"), ans_val) for a in unknowns
        )
    else:
        checks["unknown_angle_matches_answer"] = True
```

Backward compatible: `part_solutions` defaults to `None`, so every existing
call site (`pipeline.py`, the single-part geometry ladders' invariant tests)
is untouched and keeps today's single-unknown behaviour.

### Fixture

`tests/fixtures/sourced/psle_2023_stem_diagram.json` — two parts sharing one
`question.diagram` (a `geometry_figure` with two angles, each `unknown:true`
with a distinct `part_label` — `"a"` and `"b"`), mirroring G5's FIG-24
(∠LOK / ∠LNM). Part (b) additionally carries **no** `marks`/`marking_scheme`,
so this one fixture demonstrates A4 and A5 together — matching real-paper
evidence that these two gaps co-occur (a shared-stem structured question with
an unequal/absent per-part mark split).

---

## A5 — optional `part.marks` / `part.marking_scheme`

### Schema

Drop `marks` and `marking_scheme` from `part`'s `required` array (they stay
declared as optional properties, already correctly typed).

### Render (`render.py`)

`_render_part_head` currently does `part["marks"]` (direct index) — change to
`.get`, and only emit the bracket when present:

```python
marks = part.get("marks")
if marks is not None:
    out.append(f'<span class="marks">[{marks}]</span>')
```

The worksheet answer-space div's `--marks` CSS variable (used to size the
blank) falls back to `1` when absent: `part.get("marks", 1)`.
`_render_solution`'s `marking_scheme` loop already uses `.get("marking_scheme",
[])` (defensive since it was written) — no change needed there; an absent
marking scheme now simply renders an empty `<ul class="marking-scheme">`.

---

## Tests

| Test | Asserts | Seam |
|---|---|---|
| `test_schema_validation.py::test_choice_answer_valid` | A well-formed MCQ part (`options[]` + `correct`) validates | A3 |
| `test_schema_validation.py::test_choice_missing_options_or_correct_rejected` | Dropping `options` or `correct` is rejected | A3 |
| `test_schema_validation.py::test_question_diagram_valid` | `question.diagram` (stem-level) validates | A4 |
| `test_schema_validation.py::test_angle_part_label_valid` | `angles[].part_label` accepted (string and null) | A4 |
| `test_schema_validation.py::test_part_without_marks_or_marking_scheme_valid` | A part omitting both `marks` and `marking_scheme` now validates (previously rejected) | A5 |
| `test_schema_validation.py::test_v1_4_0_golden_fixtures_still_validate` | Every existing golden/fixture object (unmodified) still validates under the grown schema — the additive-only proof (R7.7) | A3/A4/A5 |
| `test_sourced_interchange.py::test_mcq_fixture_loads_and_renders` | `psle_2023_mcq.json` loads via `canonical.load`; worksheet HTML shows all four lettered options with **no** `option-correct` class anywhere; answer key HTML marks exactly the correct one and prints `Answer: (label)...` | A3 |
| `test_sourced_interchange.py::test_stem_diagram_fixture_loads_and_renders` | `psle_2023_stem_diagram.json` loads; rendered worksheet/answer-key contain exactly **one** `<figure class="diagram">` for the question (not duplicated per part); both parts' text present; part (b) prints no `[n]` bracket | A4, A5 |
| `test_render.py::test_worksheet_never_reveals_mcq_correct_option` | Direct unit test on `render_worksheet_html` with a hand-built MCQ object: no `option-correct` class, no "Answer:" text anywhere | A3 |
| `test_render.py::test_answer_key_marks_correct_option` | Direct unit test on `render_answer_key_html`: `option-correct` on the right `<li>`, `Answer: (label)` present | A3 |
| `test_render.py::test_stem_diagram_renders_once_before_parts` | A hand-built 2-part object with `question.diagram` renders exactly one diagram figure, positioned before the first `.part` block | A4 |
| `test_render.py::test_part_without_marks_omits_bracket_worksheet_and_key` | A part with no `marks` renders with no `<span class="marks">` in both worksheet and answer key | A5 |
| `test_geometry_figure.py::test_per_part_unknown_consistency` | `check_geometry_figure_consistency(spec, params, solution, part_solutions={"a": {...}, "b": {...}})` passes when each `part_label`-bound unknown matches its own part's answer, and flips to `False` when two parts' answers are swapped | A4 |
| `test_geometry_figure.py::test_single_unknown_path_unchanged` | Calling without `part_solutions` (today's existing tests) behaves exactly as before — regression guard for the signature change | A4 |

Existing invariant tests, goldens, and the V7 sourced-interchange tests are
unmodified and must stay green (`uv run pytest`) — the additive-schema proof
is that nothing that passed before needs to change.

---

## Demo / acceptance (E2 done when)

1. `uv run pytest` green (all tables above, plus the full existing suite
   unmodified).
2. `EXAM_BANK_PATH=/tmp/demo.sqlite3 mathgen bank import
   tests/fixtures/sourced/psle_2023_mcq.json` → inserts; `mathgen export
   preview tests/fixtures/sourced/psle_2023_mcq.json` shows four lettered
   options, no answer revealed; `export answer-key ... --out ak.pdf` marks the
   correct option.
3. `mathgen bank import tests/fixtures/sourced/psle_2023_stem_diagram.json` →
   inserts; `export preview` shows the shared figure once, both parts' text,
   and no fabricated `[n]` on the unmarked part.
4. Every object that validated under v1.4.0 (goldens + existing fixtures)
   still validates unmodified under v1.5.0.

---

## Decisions resolved

1. ✅ **`answer.type:"choice"` carries `options[]` + `correct`, not a sibling
   `part.options` field.** Matches `SHAPING.md`/ADR-0020's literal wording
   ("`answer.type:"choice"` — `options[]`... plus the correct label") and
   needs no new field on `part` beyond the existing discriminated-union
   pattern already used for every other answer type.
2. ✅ **The web app's TS diagram mirror (`barModel.ts`) and
   `QuestionCard.svelte` are NOT touched in this slice**, despite ADR-0020's
   consequence line naming "both renderers." Traced concretely: the web app's
   live preview only ever renders objects returned by `/generate`/`/edit`;
   `canonical.assemble()` builds exactly one part per object (`"single-part
   (R1.7 multi-part exercised in later slices)"`, `canonical.py`), no
   blueprint solver emits `answer.type:"choice"` or `question.diagram`, and
   the bank (E1) has no wiring into the web tray yet. There is no code path
   in this milestone that would ever hand a v1.5.0-only shape to the browser
   — updating `types.ts`'s deliberately-loose mirror or `barModel.ts` now
   would be unexercised, speculative work. E5 (the actual web editor, which
   *does* author this content) is where the TS side genuinely needs it.
3. ✅ **The `geometry_figure` consistency check's per-part resolution is a
   backward-compatible, optional-kwarg extension proven by a direct unit
   test, not new pipeline wiring.** No blueprint generates a multi-part
   question at all today, so there is no live call site to wire a stem-level,
   multi-unknown check into. Extending the existing function (default
   `None` → today's behaviour unchanged) satisfies ADR-0020's stated
   consequence — the mechanism exists and is proven — without fabricating a
   caller that doesn't exist yet.
4. ✅ **No schema-level enforcement that `answer.correct` names an existing
   `options[].label`, or that every option carries `text` and/or `diagram`.**
   Left to human review (ADR-0019), consistent with other sourced-content
   correctness properties (e.g. marking-scheme-sum-matches-marks) that the
   schema already doesn't enforce structurally.
5. ✅ **MCQ options render on the worksheet, not only the answer key** — the
   options are the question; only which one is correct is secret. The
   worksheet's per-part answer-space filler is skipped for MCQ parts (nothing
   to hand-write beyond circling a letter).
6. ✅ **Schema bumps to 1.5.0.** Additive-only per ADR-0020; no existing
   object needs edits (the schema does not gate on an exact `schema_version`
   string, only its semver shape), so this is a version-number bump plus new
   optional surface, not a migration.
