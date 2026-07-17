"""A5 — diagram consistency check + deterministic spec → inline SVG renderer.

The ``diagram`` field of a canonical object is a discriminated union keyed by
``type`` (ADR-0012). V2 implements the ``bar_model`` variant (the ratio aid family,
ADR-0007). Both functions here are **pure** and **deterministic** — no timestamps,
no RNG, no hash-ordered iteration — so ``generate(blueprint_code, seed)`` stays
reproducible and the rendered SVG is stable byte-for-byte.

Nothing here imports FastAPI/Pydantic: the engine stays UI/HTTP-agnostic (ADR-0016).
"""

from __future__ import annotations

import math
import re

# ---------------------------------------------------------------------------
# Consistency check (R3.3): every label/dimension in the diagram must equal the
# corresponding parameter or solved value. A deliberately corrupted spec fails.
# ---------------------------------------------------------------------------


def check_consistency(spec: dict, params: dict, solution: dict) -> dict[str, bool]:
    """Dispatch on ``spec['type']``; return a per-check ``{name: bool}`` map."""
    dtype = spec.get("type")
    if dtype == "bar_model":
        return check_bar_model_consistency(spec, params, solution)
    if dtype == "bar_model_before_after":
        return check_bar_model_before_after_consistency(spec, params, solution)
    if dtype == "shaded_fraction":
        return check_shaded_fraction_consistency(spec, params, solution)
    if dtype == "geometry_figure":
        return check_geometry_figure_consistency(spec, params, solution)
    raise ValueError(f"no consistency check for diagram type {dtype!r}")


def check_bar_model_consistency(spec: dict, params: dict, solution: dict) -> dict[str, bool]:
    """Assert a ``bar_model`` spec matches the ratio question's numbers exactly.

    One bar per ratio term (``units`` = the term, ``label`` = the sharer's name),
    plus annotations naming the value of one unit and the total.
    """
    names = params["names"]
    ratio = params["ratio"]
    total = params["total"]
    unit_value = solution["intermediates"]["unit_value"]

    bars = spec.get("bars", [])
    ann_labels = [a.get("label") for a in spec.get("annotations", [])]

    checks: dict[str, bool] = {}
    checks["bar_count"] = len(bars) == len(ratio)
    checks["bar_units"] = len(bars) == len(ratio) and all(
        bars[i].get("units") == ratio[i] for i in range(len(ratio))
    )
    checks["bar_labels"] = len(bars) == len(names) and all(
        bars[i].get("label") == names[i] for i in range(len(names))
    )
    checks["unit_annotation"] = f"1 unit = ${unit_value}" in ann_labels
    total_bracket = spec.get("total_bracket") or {}
    checks["total_bracket"] = total_bracket.get("label") == f"Total = ${total}"
    return checks


def check_bar_model_before_after_consistency(
    spec: dict, params: dict, solution: dict
) -> dict[str, bool]:
    """Assert a ``bar_model_before_after`` spec matches the numbers exactly.

    Two stages ("Before"/"After"), each with A's bar and B's bar in *equalised*
    units. B is the invariant quantity: it must span ``L`` units in both stages.
    Annotations name the unit value and the amount A spent; the total bracket
    labels B's (unchanged) amount.
    """
    a_name, b_name = params["names"]
    spent = params["spent"]
    inter = solution["intermediates"]
    L = inter["L"]
    a_before_units = inter["a_before_units"]
    a_after_units = inter["a_after_units"]
    unit_value = inter["unit_value"]
    b_amount = inter["b_amount"]

    stages = spec.get("stages", [])
    ann_labels = [a.get("label") for a in spec.get("annotations", [])]

    checks: dict[str, bool] = {}
    checks["stage_count"] = len(stages) == 2
    checks["stage_names"] = len(stages) == 2 and [s.get("name") for s in stages] == [
        "Before",
        "After",
    ]

    before_bars = stages[0].get("bars", []) if len(stages) > 0 else []
    after_bars = stages[1].get("bars", []) if len(stages) > 1 else []
    checks["before_bars"] = before_bars == [
        {"label": a_name, "units": a_before_units},
        {"label": b_name, "units": L},
    ]
    checks["after_bars"] = after_bars == [
        {"label": a_name, "units": a_after_units},
        {"label": b_name, "units": L},
    ]
    # Invariant: B's bar is identical (== L) across both stages.
    before_b = before_bars[1].get("units") if len(before_bars) > 1 else None
    after_b = after_bars[1].get("units") if len(after_bars) > 1 else None
    checks["invariant"] = before_b == L and after_b == L and before_b == after_b

    checks["unit_annotation"] = f"1 unit = ${unit_value}" in ann_labels
    checks["spent_annotation"] = f"{a_name} spent = ${spent}" in ann_labels
    total_bracket = spec.get("total_bracket") or {}
    checks["total_bracket"] = total_bracket.get("label") == f"{b_name} = ${b_amount}"
    return checks


_SHADED_FRACTION_SHAPES = frozenset({"rectangle", "circle", "bar"})


def check_shaded_fraction_consistency(spec: dict, params: dict, solution: dict) -> dict[str, bool]:
    """Assert a ``shaded_fraction`` figure matches the answer fraction exactly.

    The figure partitions a shape into ``total_parts`` equal cells with
    ``shaded_parts`` filled — these must equal the answer's denominator and
    numerator respectively (the printed figure is *provably* the printed
    answer). ``shape`` must be a known shape and the shaded count must lie in
    ``[0, total_parts]``.
    """
    answer = solution.get("answer", {})
    numerator = answer.get("numerator")
    denominator = answer.get("denominator")

    total_parts = spec.get("total_parts")
    shaded_parts = spec.get("shaded_parts")
    shape = spec.get("shape")

    checks: dict[str, bool] = {}
    checks["shape_valid"] = shape in _SHADED_FRACTION_SHAPES
    checks["total_matches_denominator"] = total_parts == denominator
    checks["shaded_matches_numerator"] = shaded_parts == numerator
    checks["shaded_in_range"] = (
        isinstance(total_parts, int)
        and isinstance(shaded_parts, int)
        and 0 <= shaded_parts <= total_parts
    )
    return checks


# --- geometry_figure (PSLE angle + area/perimeter figures, plan A5) ---------


def _leading_number(text: object) -> float | None:
    """Parse the first signed int/decimal out of a label string (``"8 cm"`` → 8.0)."""
    match = re.search(r"-?\d+(?:\.\d+)?", str(text))
    return float(match.group()) if match else None


def _num_eq(a: object, b: object) -> bool:
    """Exact numeric equality for two values that should both be present."""
    if not isinstance(a, (int, float, str)) or not isinstance(b, (int, float, str)):
        return False
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return False


def check_geometry_figure_consistency(spec: dict, params: dict, solution: dict) -> dict[str, bool]:
    """Assert a ``geometry_figure`` spec matches its solver's numbers exactly.

    The figure is a **mandatory** geometry aid: every value drawn on it must be
    provably the solver's value, so a corrupted spec flips a check to ``False``
    (raised loudly as ``DiagramInconsistent`` by the pipeline, ADR-0014).

    **Param / solution key contract** (what KAN-229/230 solvers must produce so
    this check can cross-verify — all keys optional; a missing group is skipped):

    - ``params["lengths"]``: ``{ "<from>-<to>": <exact length> }`` — one entry per
      **labelled** segment. The key names the segment's endpoints (either
      direction matches); the value is the true length. The check requires a
      segment with that endpoint pair to exist, to carry a ``label``, and for the
      leading number parsed out of that label to equal the value. (Catches a
      dropped or mistyped length label.)
    - ``params["radii"]``: ``{ "<center id>": <exact radius> }`` — one entry per
      arc whose radius is a given/derived length. The check requires an arc
      centred on that point whose ``radius`` field equals the value; if that arc
      also carries a ``label``, the label's leading number must match too.
    - ``params["angles"]``: ``{ "<from>-<at>-<to>": <given value in degrees> }``
      — one entry per **given** (``unknown: false``) angle mark. Rays may be
      listed in either order. The check requires a non-unknown angle at that
      vertex whose ``value_deg`` equals the value.
    - ``solution["answer"]``: the solved answer object. For an **angle** figure
      its ``value`` (integer degrees) must equal the ``value_deg`` of every angle
      flagged ``unknown: true`` (there is normally exactly one). Area/perimeter
      figures carry no unknown angle, so this check is vacuously true for them —
      their answer (area/length) is verified by the solver, not drawn on the
      figure.

    Degeneracy guards (independent of params): point ids are non-null and
    distinct, every arc radius is > 0, every numeric ``value_deg`` lies in
    ``(0, 180)``, and every ``shaded[].boundary`` id exists in ``points``.
    """
    points = spec.get("points") or []
    ids = [p.get("id") for p in points]
    idset = {i for i in ids}
    segments = spec.get("segments") or []
    arcs = spec.get("arcs") or []
    angles = spec.get("angles") or []
    shaded = spec.get("shaded") or []

    lengths = (params or {}).get("lengths", {}) or {}
    radii = (params or {}).get("radii", {}) or {}
    given_angles = (params or {}).get("angles", {}) or {}
    answer = (solution or {}).get("answer", {}) or {}

    checks: dict[str, bool] = {}

    # --- degeneracy guards --------------------------------------------------
    checks["points_distinct"] = len(ids) == len(idset) and all(i is not None for i in ids)
    checks["radii_positive"] = all(float(arc.get("radius", 0)) > 0 for arc in arcs)
    numeric_angle_vals: list[float] = []
    for ang in angles:
        v = ang.get("value_deg")
        if isinstance(v, (int, float)):
            numeric_angle_vals.append(float(v))
    checks["angle_values_in_range"] = all(0 < v < 180 for v in numeric_angle_vals)
    checks["shaded_boundary_valid"] = all(
        all(pid in idset for pid in (region.get("boundary") or [])) for region in shaded
    )

    # --- labelled value ↔ param cross-checks --------------------------------
    def _segment_for(key: str) -> dict | None:
        for seg in segments:
            fr, to = seg.get("from"), seg.get("to")
            if f"{fr}-{to}" == key or f"{to}-{fr}" == key:
                return seg
        return None

    def _length_ok(key: str, value: object) -> bool:
        seg = _segment_for(key)
        if seg is None:
            return False
        return _num_eq(_leading_number(seg.get("label")), value)

    checks["segment_labels_match"] = all(_length_ok(k, v) for k, v in lengths.items())

    def _radius_ok(center: str, value: object) -> bool:
        matches = [a for a in arcs if a.get("center") == center]
        if not matches:
            return False
        ok = any(_num_eq(a.get("radius"), value) for a in matches)
        # If a matching arc carries a label, it must also state the radius.
        for a in matches:
            if a.get("label") is not None and not _num_eq(_leading_number(a.get("label")), value):
                return False
        return ok

    checks["arc_radii_match"] = all(_radius_ok(c, v) for c, v in radii.items())

    def _angle_for(key: str) -> dict | None:
        for ang in angles:
            at, fr, to = ang.get("at"), ang.get("from"), ang.get("to")
            if ang.get("unknown"):
                continue
            if f"{fr}-{at}-{to}" == key or f"{to}-{at}-{fr}" == key:
                return ang
        return None

    def _given_ok(key: str, value: object) -> bool:
        ang = _angle_for(key)
        return ang is not None and _num_eq(ang.get("value_deg"), value)

    checks["given_angles_match"] = all(_given_ok(k, v) for k, v in given_angles.items())

    unknowns = [a for a in angles if a.get("unknown")]
    if unknowns:
        ans_val = answer.get("value")
        checks["unknown_angle_matches_answer"] = ans_val is not None and all(
            _num_eq(a.get("value_deg"), ans_val) for a in unknowns
        )
    else:
        checks["unknown_angle_matches_answer"] = True

    return checks


# ---------------------------------------------------------------------------
# Spec → inline SVG (R3.4): crisp, inspectable, no external libs.
# ---------------------------------------------------------------------------

# Layout constants (integers → deterministic, no float formatting drift).
_LABEL_W = 96  # left gutter for the bar label (name)
_UNIT_W = 34  # width of one ratio unit
_BAR_H = 30  # height of a bar row
_ROW_GAP = 12  # vertical gap between bar rows
_PAD_TOP = 16
_PAD_RIGHT = 24
_ANN_ROW_H = 26  # height per annotation row (drawn under the bars)
_ANN_GAP = 14  # gap between the bars block and the annotations block
_BRACE_GAP = 12  # gap from the longest bar to the total brace spine
_BRACE_W = 9  # how far the brace cusp pokes right
_BRACE_LABEL_GAP = 8  # gap from the brace cusp to its label
_CHAR_W = 7  # ~px per character at font-size 13 (label-width estimate)
_STAGE_HEAD_H = 22  # height of a stage-name heading row (before/after variant)
_STAGE_GAP = 18  # vertical gap between the two stage groups


def render_svg(spec: dict) -> str:
    """Render a diagram spec to a self-contained inline ``<svg>`` string."""
    dtype = spec.get("type")
    if dtype == "bar_model":
        return _render_bar_model(spec)
    if dtype == "bar_model_before_after":
        return _render_bar_model_before_after(spec)
    if dtype == "shaded_fraction":
        return _render_shaded_fraction(spec)
    if dtype == "geometry_figure":
        return _render_geometry_figure(spec)
    raise ValueError(f"no SVG renderer for diagram type {dtype!r}")


def _esc(text: object) -> str:
    """Minimal XML text escaping (deterministic, order-fixed)."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_bar_model(spec: dict) -> str:
    bars = spec["bars"]
    annotations = spec.get("annotations", [])

    total_bracket = spec.get("total_bracket")

    # Canvas spans the widest thing drawn: the longest bar / annotation, plus the
    # right-hand total brace and its label when present.
    max_bar_units = max((b["units"] for b in bars), default=1)
    max_ann_units = max((a.get("to_unit", a.get("from_unit", 0)) for a in annotations), default=0)
    span_units = max(max_bar_units, max_ann_units, 1)
    right = _LABEL_W + span_units * _UNIT_W
    if total_bracket:
        brace_x = _LABEL_W + max_bar_units * _UNIT_W + _BRACE_GAP
        label_x = brace_x + _BRACE_W + _BRACE_LABEL_GAP
        right = max(right, label_x + len(total_bracket["label"]) * _CHAR_W + 4)
    width = right + _PAD_RIGHT

    bars_block_h = len(bars) * _BAR_H + (len(bars) - 1) * _ROW_GAP if bars else 0
    ann_block_h = len(annotations) * _ANN_ROW_H
    height = _PAD_TOP + bars_block_h + (_ANN_GAP + ann_block_h if annotations else 0) + _PAD_TOP

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'font-family="system-ui, sans-serif" font-size="13">'
    ]

    # --- bars ---
    y = _PAD_TOP
    for bar in bars:
        units = bar["units"]
        label = bar["label"]
        bar_w = units * _UNIT_W
        text_y = y + _BAR_H // 2 + 4

        # Name label in the left gutter (right-aligned to the bar start).
        lines.append(
            f'<text x="{_LABEL_W - 8}" y="{text_y}" text-anchor="end">{_esc(label)}</text>'
        )
        # Outer bar rectangle.
        lines.append(
            f'<rect x="{_LABEL_W}" y="{y}" width="{bar_w}" height="{_BAR_H}" '
            f'fill="#eef2fb" stroke="#2f5fe0" stroke-width="1.5"/>'
        )
        # Per-unit divider lines so units are countable.
        for u in range(1, units):
            x = _LABEL_W + u * _UNIT_W
            lines.append(
                f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + _BAR_H}" '
                f'stroke="#2f5fe0" stroke-width="0.75"/>'
            )
        y += _BAR_H + _ROW_GAP

    # --- total brace: a vertical curly brace across all bars → the total ---
    if total_bracket:
        y_top = _PAD_TOP
        y_bot = _PAD_TOP + bars_block_h
        y_mid = (y_top + y_bot) // 2
        bx = _LABEL_W + max_bar_units * _UNIT_W + _BRACE_GAP  # spine, near the bars
        cx = bx + _BRACE_W  # cusp, pointing right toward the label
        # Two cubic Béziers meeting at the cusp form a `}` (prongs left, cusp right).
        d = (
            f"M {bx} {y_top} C {cx} {y_top}, {bx} {y_mid}, {cx} {y_mid} "
            f"C {bx} {y_mid}, {cx} {y_bot}, {bx} {y_bot}"
        )
        lines.append(f'<path d="{d}" fill="none" stroke="#66708a" stroke-width="1.25"/>')
        lines.append(
            f'<text x="{cx + _BRACE_LABEL_GAP}" y="{y_mid + 4}" text-anchor="start" '
            f'fill="#66708a">{_esc(total_bracket["label"])}</text>'
        )

    # --- annotations (spanning braces + label under the bars) ---
    if annotations:
        y = _PAD_TOP + bars_block_h + _ANN_GAP
        for ann in annotations:
            from_u = ann.get("from_unit", 0)
            to_u = ann.get("to_unit", from_u)
            x1 = _LABEL_W + from_u * _UNIT_W
            x2 = _LABEL_W + to_u * _UNIT_W
            mid = (x1 + x2) // 2
            tick_y = y + 8
            # Span line with end ticks.
            lines.append(
                f'<line x1="{x1}" y1="{tick_y}" x2="{x2}" y2="{tick_y}" '
                f'stroke="#66708a" stroke-width="1"/>'
            )
            lines.append(
                f'<line x1="{x1}" y1="{tick_y - 4}" x2="{x1}" y2="{tick_y + 4}" '
                f'stroke="#66708a" stroke-width="1"/>'
            )
            lines.append(
                f'<line x1="{x2}" y1="{tick_y - 4}" x2="{x2}" y2="{tick_y + 4}" '
                f'stroke="#66708a" stroke-width="1"/>'
            )
            lines.append(
                f'<text x="{mid}" y="{y + _ANN_ROW_H - 4}" text-anchor="middle" '
                f'fill="#66708a">{_esc(ann["label"])}</text>'
            )
            y += _ANN_ROW_H

    lines.append("</svg>")
    return "".join(lines)


def _render_bar_model_before_after(spec: dict) -> str:
    """Render the before-after aid: two stacked stage groups (each a heading + its
    bars), the annotations below, and a vertical brace on the invariant person's bar.

    Pure + deterministic — integer coordinates only, reuses the ``bar_model``
    drawing style (rect + per-unit dividers + left-gutter label).
    """
    stages = spec["stages"]
    annotations = spec.get("annotations", [])
    total_bracket = spec.get("total_bracket")

    # Widest bar across both stages drives the unit span; B (invariant) sits at the
    # second row of each stage and its right edge anchors the total brace.
    all_bars = [bar for stage in stages for bar in stage["bars"]]
    max_bar_units = max((b["units"] for b in all_bars), default=1)
    # B's width (invariant): the second bar of the first stage.
    b_units = stages[0]["bars"][1]["units"] if len(stages[0]["bars"]) > 1 else max_bar_units

    span_units = max(max_bar_units, 1)
    right = _LABEL_W + span_units * _UNIT_W

    # Brace on B's bar → the total label (drawn on the last stage's B bar).
    brace_x = label_x = None
    if total_bracket:
        brace_x = _LABEL_W + b_units * _UNIT_W + _BRACE_GAP
        label_x = brace_x + _BRACE_W + _BRACE_LABEL_GAP
        right = max(right, label_x + len(total_bracket["label"]) * _CHAR_W + 4)

    for ann in annotations:
        right = max(right, _LABEL_W + len(ann["label"]) * _CHAR_W + 4)

    stage_bars_h = 2 * _BAR_H + _ROW_GAP  # each stage has exactly two bars
    stage_group_h = _STAGE_HEAD_H + stage_bars_h
    ann_block_h = len(annotations) * _ANN_ROW_H
    height = (
        _PAD_TOP
        + stage_group_h
        + _STAGE_GAP
        + stage_group_h
        + (_ANN_GAP + ann_block_h if annotations else 0)
        + _PAD_TOP
    )
    width = right + _PAD_RIGHT

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'font-family="system-ui, sans-serif" font-size="13">'
    ]

    # Track the vertical extent of B bars so the brace can span the last one.
    last_b_top = last_b_bot = _PAD_TOP

    y = _PAD_TOP
    for stage in stages:
        # Stage heading.
        lines.append(
            f'<text x="{_LABEL_W - 8}" y="{y + _STAGE_HEAD_H - 6}" text-anchor="end" '
            f'font-weight="bold">{_esc(stage["name"])}</text>'
        )
        y += _STAGE_HEAD_H
        for row, bar in enumerate(stage["bars"]):
            units = bar["units"]
            label = bar["label"]
            bar_w = units * _UNIT_W
            text_y = y + _BAR_H // 2 + 4
            lines.append(
                f'<text x="{_LABEL_W - 8}" y="{text_y}" text-anchor="end">{_esc(label)}</text>'
            )
            lines.append(
                f'<rect x="{_LABEL_W}" y="{y}" width="{bar_w}" height="{_BAR_H}" '
                f'fill="#eef2fb" stroke="#2f5fe0" stroke-width="1.5"/>'
            )
            for u in range(1, units):
                x = _LABEL_W + u * _UNIT_W
                lines.append(
                    f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + _BAR_H}" '
                    f'stroke="#2f5fe0" stroke-width="0.75"/>'
                )
            if row == 1:  # B (the invariant person) — remember its extent
                last_b_top = y
                last_b_bot = y + _BAR_H
            y += _BAR_H + _ROW_GAP
        y += _STAGE_GAP - _ROW_GAP  # the trailing _ROW_GAP already added above

    # --- total brace on the invariant person's (B's) last bar → its amount ---
    if total_bracket:
        assert brace_x is not None  # set together with total_bracket above
        y_top = last_b_top
        y_bot = last_b_bot
        y_mid = (y_top + y_bot) // 2
        bx = brace_x
        cx = bx + _BRACE_W
        d = (
            f"M {bx} {y_top} C {cx} {y_top}, {bx} {y_mid}, {cx} {y_mid} "
            f"C {bx} {y_mid}, {cx} {y_bot}, {bx} {y_bot}"
        )
        lines.append(f'<path d="{d}" fill="none" stroke="#66708a" stroke-width="1.25"/>')
        lines.append(
            f'<text x="{cx + _BRACE_LABEL_GAP}" y="{y_mid + 4}" text-anchor="start" '
            f'fill="#66708a">{_esc(total_bracket["label"])}</text>'
        )

    # --- annotations (plain labelled lines under the stages) ---
    if annotations:
        y = _PAD_TOP + stage_group_h + _STAGE_GAP + stage_group_h + _ANN_GAP
        for ann in annotations:
            lines.append(
                f'<text x="{_LABEL_W}" y="{y + _ANN_ROW_H - 8}" text-anchor="start" '
                f'fill="#66708a">{_esc(ann["label"])}</text>'
            )
            y += _ANN_ROW_H

    lines.append("</svg>")
    return "".join(lines)


# --- shaded_fraction (Fractions mandatory figure, plan D1) ------------------
# A shape partitioned into ``total_parts`` equal cells with ``shaded_parts``
# filled. rectangle → vertical strips; bar → horizontal strips; circle → equal
# pie sectors. Integer coordinates (circle sectors round trig to ints) → pure +
# deterministic. Palette matches the bar-model aid.

_SF_CELL = 40  # px per cell (rectangle strip width / bar row height)
_SF_RECT_H = 80  # rectangle total height
_SF_BAR_W = 72  # bar total width
_SF_CIRCLE_R = 60  # circle radius
_SF_PAD = 8  # padding around the figure
_SF_SHADE = "#2f5fe0"  # filled cell
_SF_EMPTY = "#eef2fb"  # empty cell
_SF_STROKE = "#2f5fe0"  # cell border


def _render_shaded_fraction(spec: dict) -> str:
    """Render a ``shaded_fraction`` figure to a self-contained inline ``<svg>``."""
    shape = spec["shape"]
    total_parts = spec["total_parts"]
    shaded_parts = spec["shaded_parts"]
    if shape == "rectangle":
        return _render_sf_strips(total_parts, shaded_parts, horizontal=False)
    if shape == "bar":
        return _render_sf_strips(total_parts, shaded_parts, horizontal=True)
    if shape == "circle":
        return _render_sf_circle(total_parts, shaded_parts)
    raise ValueError(f"unknown shaded_fraction shape {shape!r}")


def _sf_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'font-family="system-ui, sans-serif" font-size="13">'
    )


def _render_sf_strips(total_parts: int, shaded_parts: int, *, horizontal: bool) -> str:
    """Rectangle (vertical strips) / bar (horizontal strips): equal cells, first
    ``shaded_parts`` filled."""
    cell = _SF_CELL
    if horizontal:
        fig_w, fig_h = _SF_BAR_W, cell * total_parts
    else:
        fig_w, fig_h = cell * total_parts, _SF_RECT_H
    width = fig_w + 2 * _SF_PAD
    height = fig_h + 2 * _SF_PAD

    lines: list[str] = [_sf_header(width, height)]
    for i in range(total_parts):
        fill = _SF_SHADE if i < shaded_parts else _SF_EMPTY
        if horizontal:
            x, y, cw, ch = _SF_PAD, _SF_PAD + i * cell, fig_w, cell
        else:
            x, y, cw, ch = _SF_PAD + i * cell, _SF_PAD, cell, fig_h
        lines.append(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" '
            f'fill="{fill}" stroke="{_SF_STROKE}" stroke-width="1.5"/>'
        )
    lines.append("</svg>")
    return "".join(lines)


def _render_sf_circle(total_parts: int, shaded_parts: int) -> str:
    """Circle partitioned into ``total_parts`` equal pie sectors, first
    ``shaded_parts`` filled. Sector vertices round trig to integers so the SVG is
    byte-stable for a given spec."""
    r = _SF_CIRCLE_R
    cx = cy = _SF_PAD + r
    size = 2 * r + 2 * _SF_PAD

    lines: list[str] = [_sf_header(size, size)]

    if total_parts == 1:
        # A single "sector" is the whole circle — no partition lines to draw.
        fill = _SF_SHADE if shaded_parts >= 1 else _SF_EMPTY
        lines.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" '
            f'fill="{fill}" stroke="{_SF_STROKE}" stroke-width="1.5"/>'
        )
    else:

        def point(k: int) -> tuple[int, int]:
            # Start at the top (12 o'clock), sweep clockwise.
            angle = 2 * math.pi * k / total_parts - math.pi / 2
            return round(cx + r * math.cos(angle)), round(cy + r * math.sin(angle))

        for i in range(total_parts):
            x1, y1 = point(i)
            x2, y2 = point(i + 1)
            fill = _SF_SHADE if i < shaded_parts else _SF_EMPTY
            # Sector angle is 360/total_parts <= 180 for total_parts >= 2, so the
            # large-arc flag is always 0; sweep flag 1 draws the arc clockwise.
            d = f"M {cx} {cy} L {x1} {y1} A {r} {r} 0 0 1 {x2} {y2} Z"
            lines.append(f'<path d="{d}" fill="{fill}" stroke="{_SF_STROKE}" stroke-width="1.5"/>')

    lines.append("</svg>")
    return "".join(lines)


# --- geometry_figure (PSLE angle + area/perimeter figures, plan A5) ----------
# A general 2D figure: named points (figure coords) + segments (with tick marks
# and length labels) + arcs + angle marks (right-angle square when marked) +
# shaded regions + free labels. Figure coordinates are floats scaled uniformly
# into a fixed canvas; all output coordinates are rounded via ``_r`` (floor(v+.5))
# so Python and the TS mirror (web/src/lib/barModel.ts) agree byte-for-byte.
# Labelled *values* stay exact (they come from the label strings / params, not
# from measuring the drawing). Convention: figure coordinates are screen-like
# (x right, y DOWN); arc/angle degrees are measured with the same y-down frame,
# so positive degrees advance clockwise on screen.

_GF_SIZE = 240  # target max drawing dimension (px, before padding)
_GF_PAD = 28  # padding around the figure (room for labels)
_GF_ANGLE_R = 18  # angle-mark arc radius (canvas px)
_GF_RIGHT = 14  # right-angle square side (canvas px)
_GF_TICK = 6  # equal-length tick half-length (canvas px)
_GF_TICK_SP = 4  # spacing between adjacent tick marks
_GF_LABEL_OFF = 13  # perpendicular offset of a segment length label
_GF_STROKE = "#2f5fe0"  # figure edges / arcs
_GF_FILL = "#dbe4fb"  # shaded region fill
_GF_TEXT = "#334155"  # text labels


def _r(v: float) -> int:
    """Round half-up to an int — identical in Python and JS (``Math.floor(v+0.5)``)."""
    return math.floor(v + 0.5)


def _gf_arc_extent(cx: float, cy: float, r: float, start: float, end: float) -> list[tuple]:
    """Points bounding an arc: its two endpoints + any cardinal (0/90/180/270/360)
    that the sweep passes through. Assumes ``start <= end``."""
    lo, hi = (start, end) if start <= end else (end, start)
    pts: list[tuple] = []
    for deg in (start, end, 0, 90, 180, 270, 360):
        if lo <= deg <= hi or deg in (start, end):
            rad = math.radians(deg)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
    return pts


def _gf_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        f'font-family="system-ui, sans-serif" font-size="13">'
    )


def _gf_unit(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)


def _render_geometry_figure(spec: dict) -> str:
    """Render a ``geometry_figure`` spec to a self-contained inline ``<svg>``."""
    points = spec.get("points") or []
    pmap: dict = {p["id"]: (float(p["x"]), float(p["y"])) for p in points}
    segments = spec.get("segments") or []
    arcs = spec.get("arcs") or []
    angles = spec.get("angles") or []
    shaded = spec.get("shaded") or []
    labels = spec.get("labels") or []

    # Bounding box over points + arc extents.
    xs = [p[0] for p in pmap.values()]
    ys = [p[1] for p in pmap.values()]
    for arc in arcs:
        cx, cy = pmap[arc["center"]]
        r = float(arc["radius"])
        xs.append(cx)
        ys.append(cy)
        for ax, ay in _gf_arc_extent(cx, cy, r, arc["start_deg"], arc["end_deg"]):
            xs.append(ax)
            ys.append(ay)

    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    w = maxx - minx
    h = maxy - miny
    denom = max(w, h)
    if denom <= 0:
        denom = 1.0
    scale = _GF_SIZE / denom

    def tx(x: float) -> int:
        return _r(_GF_PAD + (x - minx) * scale)

    def ty(y: float) -> int:
        return _r(_GF_PAD + (y - miny) * scale)

    width = _r(w * scale) + 2 * _GF_PAD
    height = _r(h * scale) + 2 * _GF_PAD

    lines: list[str] = [_gf_header(width, height)]

    # --- shaded regions (drawn first, behind the strokes) -------------------
    for region in shaded:
        boundary = region.get("boundary") or []
        pts = [(tx(pmap[pid][0]), ty(pmap[pid][1])) for pid in boundary]
        if len(pts) < 2:
            continue
        d = f"M {pts[0][0]} {pts[0][1]} " + " ".join(f"L {x} {y}" for x, y in pts[1:]) + " Z"
        lines.append(f'<path d="{d}" fill="{_GF_FILL}" stroke="none"/>')

    # --- segments (edges + tick marks + length labels) ----------------------
    for seg in segments:
        ax, ay = pmap[seg["from"]]
        bx, by = pmap[seg["to"]]
        x1, y1, x2, y2 = tx(ax), ty(ay), tx(bx), ty(by)
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{_GF_STROKE}" stroke-width="2"/>'
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ux, uy = _gf_unit(x2 - x1, y2 - y1)
        nx, ny = -uy, ux  # perpendicular
        ticks = seg.get("ticks") or 0
        for i in range(ticks):
            off = (i - (ticks - 1) / 2) * _GF_TICK_SP
            cxp, cyp = mx + ux * off, my + uy * off
            lines.append(
                f'<line x1="{_r(cxp - nx * _GF_TICK)}" y1="{_r(cyp - ny * _GF_TICK)}" '
                f'x2="{_r(cxp + nx * _GF_TICK)}" y2="{_r(cyp + ny * _GF_TICK)}" '
                f'stroke="{_GF_STROKE}" stroke-width="1.5"/>'
            )
        label = seg.get("label")
        if label is not None:
            lx = _r(mx + nx * _GF_LABEL_OFF)
            ly = _r(my + ny * _GF_LABEL_OFF + 4)
            lines.append(
                f'<text x="{lx}" y="{ly}" text-anchor="middle" '
                f'fill="{_GF_TEXT}">{_esc(label)}</text>'
            )

    # --- arcs (whole/semi/quarter circles) ----------------------------------
    for arc in arcs:
        cx, cy = pmap[arc["center"]]
        r = float(arc["radius"])
        start, end = float(arc["start_deg"]), float(arc["end_deg"])
        p1x = tx(cx + r * math.cos(math.radians(start)))
        p1y = ty(cy + r * math.sin(math.radians(start)))
        p2x = tx(cx + r * math.cos(math.radians(end)))
        p2y = ty(cy + r * math.sin(math.radians(end)))
        rr = _r(r * scale)
        large = 1 if abs(end - start) > 180 else 0
        sweep = 1 if end >= start else 0
        lines.append(
            f'<path d="M {p1x} {p1y} A {rr} {rr} 0 {large} {sweep} {p2x} {p2y}" '
            f'fill="none" stroke="{_GF_STROKE}" stroke-width="2"/>'
        )
        label = arc.get("label")
        if label is not None:
            mid = math.radians((start + end) / 2)
            lx = _r(tx(cx + r * math.cos(mid)) + math.cos(mid) * 12)
            ly = _r(ty(cy + r * math.sin(mid)) + math.sin(mid) * 12 + 4)
            lines.append(
                f'<text x="{lx}" y="{ly}" text-anchor="middle" '
                f'fill="{_GF_TEXT}">{_esc(label)}</text>'
            )

    # --- angle marks (small arc, or a square for right angles) --------------
    for ang in angles:
        vx, vy = pmap[ang["at"]]
        ax, ay = pmap[ang["from"]]
        bx, by = pmap[ang["to"]]
        vX, vY = tx(vx), ty(vy)
        dax, day = _gf_unit(tx(ax) - vX, ty(ay) - vY)
        dbx, dby = _gf_unit(tx(bx) - vX, ty(by) - vY)
        if ang.get("right"):
            s = _GF_RIGHT
            p1 = (_r(vX + dax * s), _r(vY + day * s))
            p2 = (_r(vX + (dax + dbx) * s), _r(vY + (day + dby) * s))
            p3 = (_r(vX + dbx * s), _r(vY + dby * s))
            lines.append(
                f'<polyline points="{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}" '
                f'fill="none" stroke="{_GF_STROKE}" stroke-width="1.5"/>'
            )
        else:
            rr = _GF_ANGLE_R
            p1x, p1y = _r(vX + dax * rr), _r(vY + day * rr)
            p2x, p2y = _r(vX + dbx * rr), _r(vY + dby * rr)
            a1 = math.degrees(math.atan2(day, dax))
            a2 = math.degrees(math.atan2(dby, dbx))
            diff = (a2 - a1 + 180) % 360 - 180
            sweep = 1 if diff > 0 else 0
            lines.append(
                f'<path d="M {p1x} {p1y} A {rr} {rr} 0 0 {sweep} {p2x} {p2y}" '
                f'fill="none" stroke="{_GF_STROKE}" stroke-width="1.5"/>'
            )
            value = ang.get("value_deg")
            if value is not None and not ang.get("unknown"):
                bisx, bisy = _gf_unit(dax + dbx, day + dby)
                if bisx == 0 and bisy == 0:
                    bisx, bisy = -day, dax  # straight angle: fall back to perpendicular
                lx = _r(vX + bisx * (rr + 12))
                ly = _r(vY + bisy * (rr + 12) + 4)
                text = f"{_esc(value)}°"
                lines.append(
                    f'<text x="{lx}" y="{ly}" text-anchor="middle" fill="{_GF_TEXT}">{text}</text>'
                )

    # --- free text labels ---------------------------------------------------
    for lab in labels:
        px, py = pmap[lab["at"]]
        lines.append(
            f'<text x="{tx(px) + 6}" y="{ty(py) - 6}" fill="{_GF_TEXT}">{_esc(lab["text"])}</text>'
        )

    lines.append("</svg>")
    return "".join(lines)
