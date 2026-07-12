"""A5 — diagram consistency check + deterministic spec → inline SVG renderer.

The ``diagram`` field of a canonical object is a discriminated union keyed by
``type`` (ADR-0012). V2 implements the ``bar_model`` variant (the ratio aid family,
ADR-0007). Both functions here are **pure** and **deterministic** — no timestamps,
no RNG, no hash-ordered iteration — so ``generate(blueprint_code, seed)`` stays
reproducible and the rendered SVG is stable byte-for-byte.

Nothing here imports FastAPI/Pydantic: the engine stays UI/HTTP-agnostic (ADR-0016).
"""

from __future__ import annotations

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
    raise ValueError(f"no consistency check for diagram type {dtype!r}")


def check_bar_model_consistency(
    spec: dict, params: dict, solution: dict
) -> dict[str, bool]:
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
    max_ann_units = max(
        (a.get("to_unit", a.get("from_unit", 0)) for a in annotations), default=0
    )
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
        y = (
            _PAD_TOP
            + stage_group_h
            + _STAGE_GAP
            + stage_group_h
            + _ANN_GAP
        )
        for ann in annotations:
            lines.append(
                f'<text x="{_LABEL_W}" y="{y + _ANN_ROW_H - 8}" text-anchor="start" '
                f'fill="#66708a">{_esc(ann["label"])}</text>'
            )
            y += _ANN_ROW_H

    lines.append("</svg>")
    return "".join(lines)
