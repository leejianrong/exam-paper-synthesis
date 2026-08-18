---
shaping: true
---

# E3 Slice Plan — Schema v2: table, grid, construction

> **Slice E3 of `docs/planning/editor/SLICES.md`.** The second schema-growth
> slice, building directly on E2's schema v2 groundwork: a content-level
> `table` type (A6), a `grid` background + `polygons[]` on `geometry_figure`
> (A7), and a `construction` answer whose value is itself a diagram (A8) —
> all additive. Ground truth: `docs/planning/editor/SHAPING.md` (R2.4–R2.6,
> R7.4–R7.6), `docs/planning/editor/SCHEMA-FIT.md` (G3, G4, G6). Decision:
> ADR-0020 (items 4–7). Schema bumps **1.5.0 → 1.6.0** (continues from E2;
> **do not start building this slice until E2's PR has merged** — both slices
> touch `canonical-question.schema.json` and `render.py`, so building in
> parallel risks a conflicting version bump and merge conflicts).
>
> **Demo goal:** `mathgen bank import` the water-tariff table question
> (FIG-18-shaped: a given table with one blank cell that *is* the answer) —
> `mathgen export preview` shows a real `<table>` with an empty cell;
> `export answer-key` shows the same table with that cell filled in.
> Separately, import a cube-net question (`geometry_figure` with `grid` +
> `polygons[]`) and a "complete the parallelogram, label point D" construction
> question — the construction's answer key renders the *completed* figure,
> not a printed value.

---

## Scope

**In (Shape-A parts A6, A7, A8):**
- **A6** — `question.table`: a content-level table (sibling of `stem`/
  `diagram`, not a `diagram` variant), whose cells may be plain values or a
  marker binding a cell to a part's answer; real `<table>` render branch,
  worksheet (blank) vs answer-key (filled) modes.
- **A7** — `geometry_figure` gains an optional `grid` background (`cell_size`
  × `cols` × `rows`, optional numbered axes) and `polygons[]` (grid-cell
  regions, outlined/filled) — the substrate for coordinate grids, nets, and
  rod-pattern figures.
- **A8** — `answer.type:"construction"`: an answer whose value is a
  `geometry_figure` (built on A7's grid); the answer-key renderer draws the
  completed figure instead of printing a value.

**Explicitly deferred (later slices / out of this milestone):**
- The paper/section/group container → **E4**.
- A web UI (forms, table/grid authoring) → **E5**; the web app's TS diagram
  mirror (`web/src/lib/barModel.ts`, `QuestionCard.svelte`) is **not** touched
  in this slice, for the identical reason E2 gave (Decision 2 there): the web
  tray only ever holds `/generate`/`/edit` output, no blueprint produces
  tables/grids/construction answers, and the bank has no wiring into the web
  app yet.
- `answer.type:"selection"` (the True/False/Not-possible-to-tell tick matrix,
  SCHEMA-FIT G3's FIG-22 / ranked item 11) is explicitly **not** built here,
  even though it also lives inside a table. A table's blank cell in this
  slice resolves to one of the *existing* scalar answer types via a
  part-reference; a tick-per-row matrix is a structurally different answer
  shape (ADR-0020 keeps it a separate, deferred ranked item) and isn't needed
  for either of this slice's own demo questions.
- Chart-driven tables (SCHEMA-FIT G3's FIG-3, a data table feeding pie-chart
  MCQ options) — charts are ranked item 15, deferred; not needed for this
  slice's acceptance.
- No new `geometry_figure` styling primitives beyond `grid`/`polygons`.
  ADR-0020 item 7 ("segment/figure styling... dashed/construction-line
  style") is **already shipped** — `segments[].dashed` landed in schema 1.4.0
  (KAN-314, `diagram.py`'s `_render_geometry_figure`) — so this slice adds
  nothing further for it; noted so it isn't mistaken for an open item.
- No diagram-consistency-check extension for A7/A8 (unlike A4 in E2, which
  ADR-0020 explicitly calls out). See **Decision 3**.

---

## Repo layout (new/changed files)

```
engine/
  exam_engine/
    canonical.py                                    # SCHEMA_VERSION -> "1.6.0"
    render.py                                        # table renderer, grid+polygons renderer, construction answer-key branch
    schemas/
      canonical-question.schema.json                 # table/table_cell defs, question.table, geometry_figure.grid/.polygons, answer_construction
docs/
  SCHEMA.md                                          # document the three additions
  planning/editor/SLICES.md                          # link E3-plan.md under the E3 section (ripple, mirrors E1/E2)
tests/
  fixtures/sourced/
    psle_2023_table.json                              # NEW
    psle_2023_grid_net.json                            # NEW
    psle_2023_construction.json                        # NEW
  test_schema_validation.py                          # + structural tests for all three additions
  test_sourced_interchange.py                          # + fixture-based load/render tests
  test_geometry_figure.py                              # + grid/polygons render tests (spec-level, hand-crafted)
  test_render.py                                       # + table/construction render tests
```

No new workspace member, no new dependency, no CLI change — same rationale
as E1/E2: `mathgen bank import`/`export` already accept any schema-valid
object.

---

## A6 — `question.table`

### Schema

```json
"table": {
  "type": "object", "additionalProperties": false,
  "required": ["rows"],
  "properties": {
    "caption": { "type": ["string", "null"] },
    "headers": {
      "type": ["array", "null"],
      "items": { "type": ["string", "number", "null"] }
    },
    "rows": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "array", "minItems": 1,
        "items": { "$ref": "#/$defs/table_cell" }
      }
    }
  }
},
"table_cell": {
  "oneOf": [
    { "type": ["string", "number", "null"] },
    {
      "type": "object", "additionalProperties": false,
      "required": ["answer_for"],
      "properties": {
        "answer_for": {
          "type": "string", "minLength": 1,
          "description": "part.label whose answer fills this cell in the answer key; blank on the worksheet."
        }
      }
    }
  ]
}
```

Add `"table": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/table" } ] }`
to `question.properties` (sibling of `stem`/`diagram`(E2)/`parts`/
`total_marks`).

A plain `null` cell is a genuinely empty/decorative cell (spacing, an
intentionally blank header slot); `{"answer_for": "<label>"}` is the one true
"this is the answer surface" marker — kept distinct so the renderer never
has to guess which blanks are meaningful (mirrors A4's `part_label` binding:
shared, stem-level content with an explicit reference to the part it answers,
same design language).

### Render (`render.py`)

```python
def _render_table(table: dict, parts: list[dict], *, answer_key: bool) -> str:
    out = ['<table class="content-table">']
    if table.get("caption"):
        out.append(f'<caption>{_mathify(table["caption"])}</caption>')
    headers = table.get("headers")
    if headers:
        out.append("<thead><tr>")
        out.extend(f"<th>{_mathify(str(h))}</th>" if h is not None else "<th></th>" for h in headers)
        out.append("</tr></thead>")
    out.append("<tbody>")
    for row in table["rows"]:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_render_table_cell(cell, parts, answer_key=answer_key)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _render_table_cell(cell: object, parts: list[dict], *, answer_key: bool) -> str:
    if isinstance(cell, dict):  # {"answer_for": label}
        if not answer_key:
            return '<span class="table-blank" aria-hidden="true"></span>'
        part = next(p for p in parts if p["label"] == cell["answer_for"])
        return _fmt_answer(part["answer"])
    if cell is None:
        return ""
    return _mathify(str(cell))
```

`_render_questions` renders `question.table` once, right after the stem-level
diagram (E2's `question.diagram`) and before the parts loop — same
"shared content prints once" placement as the stem diagram:

```python
q_table = obj["question"].get("table")
if q_table is not None:
    out.append(_render_table(q_table, parts, answer_key=answer_key))
```

### Fixture

`tests/fixtures/sourced/psle_2023_table.json` — single-part question modelled
on SCHEMA-FIT G3's FIG-18 (a water-tariff table with a blank cell that is the
answer): a small given table (tier → rate) with one row's rate cell as
`{"answer_for": "a"}`, `part.answer` a `quantity` (dollars).

---

## A7 — `grid` + `polygons[]` on `geometry_figure`

### Schema

Both added directly to `$defs.diagram_geometry_figure.properties` (already
`additionalProperties: false`, so both must be listed explicitly):

```json
"grid": {
  "type": ["object", "null"],
  "additionalProperties": false,
  "required": ["cell_size", "cols", "rows"],
  "properties": {
    "cell_size": { "type": "number", "exclusiveMinimum": 0 },
    "cols": { "type": "integer", "minimum": 1 },
    "rows": { "type": "integer", "minimum": 1 },
    "origin": {
      "type": ["object", "null"], "additionalProperties": false,
      "properties": { "x": { "type": "number" }, "y": { "type": "number" } },
      "description": "Figure-space coordinate of the grid's top-left corner; defaults to (0, 0)."
    },
    "show_axes": {
      "type": "boolean", "default": false,
      "description": "Numbered x/y axes along the grid edges (coordinate-grid figures) vs a plain square backdrop (nets, rod patterns, construction canvases)."
    }
  }
},
"polygons": {
  "type": "array",
  "items": {
    "type": "object", "additionalProperties": false,
    "required": ["cells"],
    "properties": {
      "cells": {
        "type": "array", "minItems": 1,
        "items": {
          "type": "array", "minItems": 2, "maxItems": 2,
          "items": { "type": "integer", "minimum": 0 }
        },
        "description": "[col, row] 0-indexed grid-cell coordinates; each becomes one outlined/filled unit square."
      },
      "fill": { "type": "boolean", "default": false },
      "label": { "type": ["string", "null"] }
    }
  }
}
```

### Render (`diagram.py`)

`_render_geometry_figure` draws the grid backdrop first (light grid lines,
before points/segments/arcs so they layer on top), then each polygon as its
*individual unit cells* — **not** a traced outer boundary. This is
deliberate (see **Decision 2**): the lines between adjacent unit cells of the
same polygon are genuine content (cube-net fold lines; individually-counted
rod-pattern squares), not rendering noise, so drawing each cell's own bordered
square is both simpler and more faithful to the real figures.

```python
def _draw_grid(lines: list[str], grid: dict, tx, ty) -> None:
    ox = grid.get("origin", {}).get("x", 0) if grid.get("origin") else 0
    oy = grid.get("origin", {}).get("y", 0) if grid.get("origin") else 0
    size = grid["cell_size"]
    for c in range(grid["cols"] + 1):
        x = tx(ox + c * size)
        lines.append(f'<line x1="{x}" y1="{ty(oy)}" x2="{x}" y2="{ty(oy + grid["rows"] * size)}" stroke="#c7d0e0" stroke-width="1"/>')
    for r in range(grid["rows"] + 1):
        y = ty(oy + r * size)
        lines.append(f'<line x1="{tx(ox)}" y1="{y}" x2="{tx(ox + grid["cols"] * size)}" y2="{y}" stroke="#c7d0e0" stroke-width="1"/>')
    # show_axes adds numbered labels along the bottom/left edge — omitted here for brevity,
    # implementer follows the existing `_esc`/text-element conventions used elsewhere in this file.

def _draw_polygons(lines: list[str], polygons: list[dict], grid: dict, tx, ty) -> None:
    ox = grid.get("origin", {}).get("x", 0) if grid.get("origin") else 0
    oy = grid.get("origin", {}).get("y", 0) if grid.get("origin") else 0
    size = grid["cell_size"]
    for poly in polygons:
        fill = _GF_FILL if poly.get("fill") else "none"
        for col, row in poly["cells"]:
            x1, y1 = tx(ox + col * size), ty(oy + row * size)
            x2, y2 = tx(ox + (col + 1) * size), ty(oy + (row + 1) * size)
            lines.append(f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="{fill}" stroke="{_GF_STROKE}" stroke-width="1.5"/>')
```

The figure's bounding-box computation (which currently spans `points` +
`arc` extents, see `_render_geometry_figure`'s `xs`/`ys` accumulation) must
also include the grid's extent (`origin` → `origin + (cols·cell_size,
rows·cell_size)`) when a `grid` is present, so a grid-only figure (no
`points`) still sizes correctly and a figure with both grid and points fits
both.

### Fixture

`tests/fixtures/sourced/psle_2023_grid_net.json` — single-part question:
"The diagram shows the net of a solid. How many faces does the solid have?"
with a `geometry_figure` (`grid` 4 cols × 3 rows, `polygons: [{"cells":
[[1,0],[0,1],[1,1],[2,1],[3,1],[1,2]]}]`, `fill: true`) — a cross-shaped
6-square cube net, answer `integer: 6`.

---

## A8 — `answer.type:"construction"`

### Schema

```json
"answer_construction": {
  "type": "object", "additionalProperties": false,
  "required": ["type", "diagram"],
  "properties": {
    "type": { "const": "construction" },
    "diagram": { "$ref": "#/$defs/diagram_geometry_figure" }
  }
}
```

Add `{ "$ref": "#/$defs/answer_construction" }` to the `answer` `oneOf`
union.

### Render (`render.py`)

The **worksheet** figure the student draws on is the *existing* `part.diagram`
field (unchanged mechanism — a `geometry_figure` with a `grid` and the given/
incomplete points, e.g. 3 of a parallelogram's 4 corners). The **answer-key**
renders the completed figure instead of a text "Answer:" line:

```python
def _render_solution(part: dict) -> list[str]:
    out: list[str] = ['<div class="solution">']
    out.append('<ol class="solution-steps">')
    for step in part.get("solution_steps", []):
        out.append(f'<li class="step">{_mathify(step["text"])}</li>')
    out.append("</ol>")

    answer = part["answer"]
    if answer["type"] == "construction":
        out.append('<figure class="diagram answer-diagram">')
        out.append(diagram.render_svg(answer["diagram"]))
        out.append("</figure>")
    else:
        out.append(f'<p class="final-answer">Answer: {_fmt_answer(answer)}</p>')
    ...
```

`_fmt_answer` gets no `construction` branch — `_render_solution` special-cases
it entirely before ever calling `_fmt_answer`, since "print a figure" isn't a
text-formatting concern.

### Fixture

`tests/fixtures/sourced/psle_2023_construction.json` — modelled on SCHEMA-FIT
G6's P1 Q26b ("complete the parallelogram ABCD and label point D"): `part.
diagram` = the given figure (points A, B, C + a `grid`, no D); `part.answer =
{type: "construction", diagram: {...same grid, points A/B/C/D, segments
closing the parallelogram...}}`. This single fixture demonstrates A7 (grid)
and A8 (construction) together — every construction answer found in
SCHEMA-FIT is grid-based, so this pairing is evidence-driven, not
convenience (same reasoning E2 used to combine A4+A5 into one fixture).

---

## Tests

| Test | Asserts | Seam |
|---|---|---|
| `test_schema_validation.py::test_table_valid` | A `question.table` with a plain-value row and an `answer_for` cell validates | A6 |
| `test_schema_validation.py::test_table_cell_rejects_unknown_shape` | A table cell that's neither a scalar/null nor `{"answer_for": ...}` is rejected | A6 |
| `test_schema_validation.py::test_geometry_figure_grid_and_polygons_valid` | A `geometry_figure` with `grid` + `polygons[]` validates | A7 |
| `test_schema_validation.py::test_grid_requires_cell_size_cols_rows` | A `grid` missing any of `cell_size`/`cols`/`rows` is rejected | A7 |
| `test_schema_validation.py::test_construction_answer_valid` | `answer.type:"construction"` with a nested valid `geometry_figure` validates | A8 |
| `test_schema_validation.py::test_construction_answer_rejects_non_geometry_diagram` | `answer.type:"construction"` whose `diagram.type` isn't `geometry_figure`-shaped (e.g. missing `points`) is rejected | A8 |
| `test_schema_validation.py::test_v1_5_0_objects_still_validate` | E2's fixtures + all pre-existing goldens still validate unmodified under v1.6.0 (additive-only proof, R7.7) | A6/A7/A8 |
| `test_sourced_interchange.py::test_table_fixture_loads_and_renders` | `psle_2023_table.json` loads; worksheet HTML contains a `<table>` with an empty `table-blank` span and no leaked answer; answer-key HTML contains the same table with the value filled in | A6 |
| `test_sourced_interchange.py::test_grid_net_fixture_loads_and_renders` | `psle_2023_grid_net.json` loads; rendered SVG contains grid lines and 6 unit-cell `<rect>`s | A7 |
| `test_sourced_interchange.py::test_construction_fixture_loads_and_renders` | `psle_2023_construction.json` loads; worksheet shows the incomplete (3-point) figure; answer key shows the completed (4-point) figure, not a text "Answer:" line | A7, A8 |
| `test_render.py::test_worksheet_table_blank_cell_hides_answer` | Direct unit test: worksheet render of a hand-built `question.table` never contains the answer's formatted value anywhere in the table | A6 |
| `test_render.py::test_answer_key_table_fills_blank_cell` | Direct unit test: answer-key render fills the `answer_for` cell with `_fmt_answer` of the matching part | A6 |
| `test_render.py::test_construction_answer_key_renders_figure_not_text` | Answer key for a `construction` part contains a second `<figure class="diagram">` (the completed one) and no `<p class="final-answer">` for that part | A8 |
| `test_geometry_figure.py::test_grid_renders_backdrop_lines` | `render_svg` on a spec with `grid` (no points) produces the expected count of grid `<line>` elements (`(cols+1) + (rows+1)`) | A7 |
| `test_geometry_figure.py::test_polygons_render_one_rect_per_cell` | `render_svg` on a spec with a 3-cell polygon produces exactly 3 `<rect>` elements | A7 |
| `test_geometry_figure.py::test_grid_only_figure_has_sane_bounding_box` | A spec with only a `grid` (no `points`) renders a `viewBox`/`width`/`height` sized to the grid's extent, not a degenerate/zero canvas | A7 |

Existing invariant tests, goldens, and E1/E2's tests are unmodified and must
stay green.

---

## Demo / acceptance (E3 done when)

1. `uv run pytest` green (all tables above, plus the full existing suite
   unmodified).
2. `mathgen bank import tests/fixtures/sourced/psle_2023_table.json` →
   inserts; `mathgen export preview` shows a real `<table>` with an empty
   cell; `export answer-key` shows the same table with the cell filled.
3. `mathgen bank import tests/fixtures/sourced/psle_2023_grid_net.json` →
   inserts; `export preview` renders the 6-square cross-shaped net on its
   grid.
4. `mathgen bank import tests/fixtures/sourced/psle_2023_construction.json` →
   inserts; `export preview` shows the incomplete figure; `export
   answer-key` shows the completed one.
5. Every object that validated under v1.5.0 (E2's fixtures + all prior
   goldens) still validates unmodified under v1.6.0.

---

## Decisions resolved

1. ✅ **A table's answer-cell binding (`{"answer_for": "<part.label>"}`)
   mirrors A4's `part_label` binding on `geometry_figure.angles[]`** — same
   design language for "shared, question-level content with an explicit
   pointer to the part it answers." Not schema-enforced that the referenced
   label actually exists on the question (human review, same rationale as
   E2 Decision 4 for `answer.correct`).
2. ✅ **`polygons[]` render as individual bordered unit cells, not a traced
   outer boundary.** Initially considered a boundary-union algorithm, but the
   internal cell lines are genuine content for both evidenced figure kinds —
   cube-net fold lines and individually-counted rod-pattern squares — so the
   simpler approach is also the more correct one. No non-trivial geometry
   algorithm needed.
3. ✅ **No diagram-consistency-check extension for A7/A8**, unlike A4 in E2.
   ADR-0020 names the consistency check as a required consequence only for
   item 2 (stem diagrams/unknown binding, G5) — it does not make the same
   commitment for grid/polygons/construction, and (same reasoning as E2
   Decision 3) nothing calls `check_consistency` on sourced content or
   generates these shapes from a blueprint.
4. ✅ **The construction fixture is also the grid fixture's evidence
   pairing** — every construction answer found across three real papers is a
   drawing on a square grid (ADR-0020 item 6), so A7+A8 share one fixture;
   the *non-construction* grid+polygons demo (a cube net) gets its own
   separate fixture, since SLICES.md's E3 acceptance names it as a distinct
   demo case.
5. ✅ **`answer.type:"selection"` (tick matrices) is out of scope**, despite
   living inside a table in the source evidence (FIG-22). It's a
   structurally different answer shape (a tick per row, not a single scalar)
   and is its own deferred ranked item (11) in ADR-0020 — this slice's table
   mechanism only binds a cell to one of the *existing* scalar answer types.
6. ✅ **The web app's TS diagram mirror is not touched**, for the identical
   reason as E2 Decision 2 — no live caller in this milestone.
7. ✅ **Schema bumps to 1.6.0**, continuing from E2's 1.5.0. This slice must
   not start implementation until E2's PR is merged (shared files: the
   schema JSON and `render.py`).
