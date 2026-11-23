"""T1 — the ``chart`` diagram (schema 1.7.0): bar / line / pie.

Schema 1.17.0 (EXA-158 part 2) adds a line graph over a numeric x axis (``x_axis`` min/max/step and
``points`` per series: the water in a tank over time) and a ``fraction`` pie (each sector a
whole number of equal parts, printed as a stacked fraction in lowest terms).

A structured statistical figure: the data *is* the spec, and the drawing is
derived from it (never the other way round), so a printed chart is provably the
chart described by the object. Three pure, deterministic pieces:

* :func:`check_chart_consistency` — spec-only invariants (series align with
  categories, values sit on the axis, the axis step divides its span, a percent
  pie sums to 100). Used by the canonical load gate, so a sourced chart whose
  numbers disagree with its own axis is rejected on import.
* :func:`render_chart_svg` — deterministic spec -> inline ``<svg>``. Inter only
  (EXA-94); black on white (EXA-135): bar series are told apart by grey tone
  and a legend, line series by dash pattern and marker fill, pie sectors are
  white, outlined and labelled. A value with ``show_value: false`` is drawn at its true size
  but is never written as text.
* :func:`leaked_hidden_values` — the "no leak" proof: the hidden numbers of a
  spec must not appear in any text node or ``aria-label`` of its own SVG.

No FastAPI/Pydantic here (engine stays UI/HTTP-agnostic, ADR-0016) and no
import of ``diagram`` (``diagram`` dispatches *to* this module).
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

from exam_engine import palette

_EPS = 1e-9
_MAX_TICKS = 50

_FILLS = palette.SERIES
_DASHES = ("", "7 4", "2 4", "9 3 2 3")
_INK = palette.INK
_GRID = palette.GRID
_AXIS = palette.INK


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _n(v: float) -> str:
    """Compact, locale-free number: ``3``, ``2.5``, ``0.125`` (≤ 3 dp)."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _is_num(v: object) -> bool:
    """A real, finite number (``Infinity``/``NaN`` pass JSON Schema's ``number``)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _prints_exactly(v: object) -> bool:
    """True when ``_n`` shows ``v`` without rounding it away (<= 3 decimals)."""
    return _is_num(v) and abs(v) < 1e12 and abs(round(v, 3) - v) < 1e-9  # type: ignore[call-overload,arg-type]


def _ticks(axis: dict) -> list[float]:
    lo, hi, step = axis["min"], axis["max"], axis["step"]
    count = round((hi - lo) / step)
    return [lo + i * step for i in range(count + 1)]


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def check_chart_consistency(spec: dict) -> dict[str, bool]:
    """Spec-only invariants; every value is a ``bool`` (``True`` = holds)."""
    kind = spec.get("kind")
    if kind == "pie":
        return _check_pie(spec)
    if kind in ("bar", "line"):
        return _check_axes_chart(spec)
    return {"kind_known": False}


def _check_pie(spec: dict) -> dict[str, bool]:
    sectors = spec.get("sectors") or []
    values = [s.get("value") for s in sectors]
    labels = [s.get("label") for s in sectors]
    positive = bool(values) and all(_is_num(v) and v > 0 for v in values)
    checks = {
        "has_sectors": len(sectors) >= 2,
        "values_positive": positive,
        "labels_unique": len(set(labels)) == len(labels),
        "values_print_exactly": all(_prints_exactly(v) for v in values),
    }
    if spec.get("value_unit") == "%":
        checks["percent_sums_to_100"] = positive and abs(sum(values) - 100) < 1e-6
    if spec.get("value_unit") == "fraction":
        # each value is a count of equal parts; the sector prints value / total, in lowest terms
        checks["fraction_parts_whole"] = positive and all(float(v).is_integer() for v in values)
    return checks


def sector_fraction(spec: dict, i: int) -> Fraction:
    """The fraction of the whole pie sector ``i`` is (what a ``fraction`` pie prints)."""
    values = [s["value"] for s in spec["sectors"]]
    return Fraction(int(values[i]), int(sum(values)))


def _axis_range(axis: dict) -> tuple[bool, bool, float, float]:
    """(range valid, step divides the span, min, max) of a numeric axis."""
    raw = (axis.get("min"), axis.get("max"), axis.get("step"))
    if not (all(_is_num(v) for v in raw) and raw[0] < raw[1] and raw[2] > 0):  # type: ignore[operator]
        return False, False, 0.0, 0.0
    lo, hi, step = (float(v) for v in raw)  # type: ignore[arg-type]
    n = (hi - lo) / step
    return True, abs(n - round(n)) < 1e-6 and round(n) <= _MAX_TICKS, lo, hi


def is_numeric_x(spec: dict) -> bool:
    """A line graph over a numeric x axis (time in minutes, EXA-158) instead of categories."""
    return "categories" not in (spec.get("x_axis") or {})


def _check_axes_chart(spec: dict) -> dict[str, bool]:
    x_axis = spec.get("x_axis") or {}
    axis = spec.get("y_axis") or {}
    series = spec.get("series") or []
    axis_ok, span_ok, lo, hi = _axis_range(axis)
    raw = [axis.get(k) for k in ("min", "max", "step")]
    names = [s.get("name") for s in series]
    if is_numeric_x(spec):
        return _check_numeric_x(spec, x_axis, series, (axis_ok, span_ok, lo, hi), raw, names)
    cats = x_axis.get("categories") or []
    values = [v for s in series for v in s.get("values", []) if v is not None]
    checks = {
        "has_categories": len(cats) >= 1,
        "categories_unique": len(set(cats)) == len(cats),
        "series_align_with_categories": bool(series)
        and all("points" not in s and len(s.get("values", [])) == len(cats) for s in series),
        "axis_range_valid": axis_ok,
        "step_divides_span": span_ok,
        "values_within_axis": axis_ok and all(_is_num(v) and lo <= v <= hi for v in values),
        "series_names_unique": len(set(names)) == len(names),
        "values_print_exactly": all(_prints_exactly(v) for v in (*raw, *values) if v is not None),
    }
    if spec.get("kind") == "bar":
        # A bar's length is its value only from a zero baseline; a truncated or
        # negative axis would draw a misleading bar.
        checks["bar_axis_starts_at_zero"] = axis_ok and lo == 0
    return checks


def _check_numeric_x(
    spec: dict,
    x_axis: dict,
    series: list[dict],
    y_range: tuple[bool, bool, float, float],
    y_raw: list,
    names: list,
) -> dict[str, bool]:
    y_ok, y_span, lo, hi = y_range
    x_ok, x_span, x_lo, x_hi = _axis_range(x_axis)
    x_raw = [x_axis.get(k) for k in ("min", "max", "step")]
    pts = [p for s in series for p in s.get("points") or []]
    pairs = all(isinstance(p, list) and len(p) == 2 and all(map(_is_num, p)) for p in pts)
    xs = [[p[0] for p in s.get("points") or []] for s in series] if pairs else []
    return {
        "numeric_x_is_a_line": spec.get("kind") == "line",
        "series_are_points": bool(series)
        and all("values" not in s and len(s.get("points") or []) >= 2 for s in series),
        "points_are_pairs": pairs,
        "x_increasing": pairs and all(a < b for x in xs for a, b in zip(x, x[1:], strict=False)),
        "x_axis_range_valid": x_ok,
        "x_step_divides_span": x_span,
        "axis_range_valid": y_ok,
        "step_divides_span": y_span,
        "values_within_axis": pairs
        and x_ok
        and y_ok
        and all(x_lo <= x <= x_hi and lo <= y <= hi for x, y in pts),
        "series_names_unique": len(set(names)) == len(names),
        "values_print_exactly": all(
            _prints_exactly(v) for v in (*x_raw, *y_raw, *(c for p in pts for c in p))
        )
        if pairs
        else False,
    }


# ---------------------------------------------------------------------------
# Hidden values
# ---------------------------------------------------------------------------


def _value_tokens(spec: dict, shown: bool) -> list[str]:
    """How the shown (or hidden) pie values print: ``25`` for a number, ``3/8`` for a fraction."""
    if spec.get("kind") != "pie":
        return []
    frac = spec.get("value_unit") == "fraction"
    return [
        f"{f.numerator}/{f.denominator}"
        if frac and (f := sector_fraction(spec, i))
        else _n(s["value"])
        for i, s in enumerate(spec.get("sectors", []))
        if bool(s.get("show_value", True)) is shown
    ]


def leaked_hidden_values(spec: dict, svg: str) -> list[str]:
    """Return hidden values that still appear in the SVG's text or aria-label.

    A hidden value may legitimately equal a *shown* one (two 25% sectors), so a
    token counts as leaked only when it occurs more often in the visible text
    than the shown sectors carrying it account for. A stacked fraction is two text
    nodes, numerator then denominator, so it reads back as ``n/d``.
    """
    nodes = [t.strip() for t in re.findall(r">([^<]*)<", svg) if t.strip()]
    visible = " ".join(nodes + re.findall(r'aria-label="([^"]*)"', svg))
    if spec.get("value_unit") == "fraction":
        visible = re.sub(r"(?<![\d./])(\d+) (\d+)(?![\d./])", r"\1/\2", visible)
    shown = _value_tokens(spec, True)
    leaks = []
    for token in sorted(set(_value_tokens(spec, False))):
        found = len(re.findall(rf"(?<![\d./]){re.escape(token)}(?![\d./])", visible))
        if found > shown.count(token):
            leaks.append(token)
    return leaks


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_chart_svg(spec: dict) -> str:
    kind = spec["kind"]
    if kind == "pie":
        return _render_pie(spec)
    if kind in ("bar", "line"):
        return _render_axes_chart(spec)
    raise ValueError(f"unknown chart kind {kind!r}")


def _header(width: int, height: int, spec: dict) -> str:
    # aria-label names the figure only; it must never carry data (see
    # leaked_hidden_values).
    label = _esc(spec.get("title") or f"{spec['kind']} chart")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{label}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="12">'
    )


def _title(spec: dict, width: int) -> str:
    if not spec.get("title"):
        return ""
    return (
        f'<text x="{_n(width / 2)}" y="18" text-anchor="middle" font-size="13" '
        f'font-weight="600" fill="{_INK}">{_esc(spec["title"])}</text>'
    )


def _render_axes_chart(spec: dict) -> str:
    numeric = is_numeric_x(spec)
    cats = [] if numeric else spec["x_axis"]["categories"]
    axis = spec["y_axis"]
    series = spec["series"]
    legend = len(series) > 1
    width = 460
    left, right, top = 62, 18, 34
    legend_rows = 1
    if legend:
        x = left
        for s in series:
            entry = 17 + 8 * len(str(s["name"])) + 18
            if x > left and x + entry > width - right:
                legend_rows, x = legend_rows + 1, left
            x += entry
    # a time graph is shorter, so a two-part question with it still fits a page with its working
    height = (250 if numeric else 320) + (legend_rows - 1) * 20
    bottom = 64 + (22 + (legend_rows - 1) * 20 if legend else 0)
    pw, ph = width - left - right, height - top - bottom
    lo, hi = axis["min"], axis["max"]

    def y(v: float) -> float:
        return top + ph - (v - lo) / (hi - lo) * ph

    out = [_header(width, height, spec), _title(spec, width)]
    for t in _ticks(axis):
        out.append(
            f'<line x1="{left}" y1="{_n(y(t))}" x2="{left + pw}" y2="{_n(y(t))}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
            f'<text x="{left - 8}" y="{_n(y(t) + 4)}" text-anchor="end" '
            f'fill="{_INK}">{_n(t)}</text>'
        )
    if numeric:
        xa = spec["x_axis"]

        def xp(v: float) -> float:
            return left + (v - xa["min"]) / (xa["max"] - xa["min"]) * pw

        for t in _ticks(xa):
            out.append(
                f'<line x1="{_n(xp(t))}" y1="{top}" x2="{_n(xp(t))}" y2="{top + ph}" '
                f'stroke="{_GRID}" stroke-width="1"/>'
                f'<text x="{_n(xp(t))}" y="{top + ph + 17}" text-anchor="middle" '
                f'fill="{_INK}">{_n(t)}</text>'
            )
    out.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + ph}" stroke="{_AXIS}"/>'
        f'<line x1="{left}" y1="{top + ph}" x2="{left + pw}" y2="{top + ph}" stroke="{_AXIS}"/>'
    )
    y_title = axis.get("title")
    if axis.get("unit"):
        y_title = f"{y_title} ({axis['unit']})" if y_title else f"({axis['unit']})"
    if y_title:
        out.append(
            f'<text transform="translate(14 {_n(top + ph / 2)}) rotate(-90)" '
            f'text-anchor="middle" fill="{_INK}">{_esc(y_title)}</text>'
        )

    band = pw / max(len(cats), 1)
    for i, cat in enumerate(cats):
        cx = left + band * (i + 0.5)
        out.append(
            f'<text x="{_n(cx)}" y="{top + ph + 17}" text-anchor="middle" '
            f'fill="{_INK}">{_esc(cat)}</text>'
        )
    x_title = spec["x_axis"].get("title")
    if x_title:
        out.append(
            f'<text x="{_n(left + pw / 2)}" y="{top + ph + 38}" text-anchor="middle" '
            f'fill="{_INK}">{_esc(x_title)}</text>'
        )

    if spec["kind"] == "bar":
        group = band * 0.72
        bw = group / len(series)
        for si, s in enumerate(series):
            for i, v in enumerate(s["values"]):
                if v is None:
                    continue
                bx = left + band * i + (band - group) / 2 + bw * si
                out.append(
                    f'<rect x="{_n(bx)}" y="{_n(y(v))}" width="{_n(bw)}" '
                    f'height="{_n(y(lo) - y(v))}" fill="{_FILLS[si % len(_FILLS)]}" '
                    f'stroke="{_INK}" stroke-width="0.8"/>'
                )
                if s.get("show_values"):
                    out.append(
                        f'<text x="{_n(bx + bw / 2)}" y="{_n(y(v) - 4)}" '
                        f'text-anchor="middle" fill="{_INK}">{_n(v)}</text>'
                    )
    else:
        for si, s in enumerate(series):
            # every line is ink; the dash pattern and the marker fill tell series apart
            color, dash = _FILLS[si % len(_FILLS)], _DASHES[si % len(_DASHES)]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            if numeric:
                pts: list[tuple[float, float] | None] = [(xp(a), y(b)) for a, b in s["points"]]
                vals: list[float | None] = [b for _, b in s["points"]]
            else:
                pts = [
                    None if v is None else (left + band * (i + 0.5), y(v))
                    for i, v in enumerate(s["values"])
                ]
                vals = s["values"]
            run: list[str] = []
            for pt in [*pts, None]:
                if pt is not None:
                    run.append(f"{_n(pt[0])},{_n(pt[1])}")
                    continue
                if len(run) > 1:
                    out.append(
                        f'<polyline points="{" ".join(run)}" fill="none" stroke="{_INK}" '
                        f'stroke-width="2"{dash_attr}/>'
                    )
                run = []
            for pt, v in zip(pts, vals, strict=True):
                if pt is None or v is None:
                    continue
                px, py = pt
                out.append(
                    f'<circle cx="{_n(px)}" cy="{_n(py)}" r="3.5" fill="{color}" '
                    f'stroke="{_INK}" stroke-width="0.8"/>'
                )
                if s.get("show_values"):
                    out.append(
                        f'<text x="{_n(px)}" y="{_n(py - 8)}" text-anchor="middle" '
                        f'fill="{_INK}">{_n(v)}</text>'
                    )

    if legend:
        lx, row = left, 0
        for si, s in enumerate(series):
            entry = 17 + 8 * len(str(s["name"])) + 18
            if lx > left and lx + entry > width - right:
                lx, row = left, row + 1  # wrap rather than run off the figure
            ly = height - 14 - (legend_rows - 1 - row) * 20
            out.append(
                f'<rect x="{lx}" y="{ly - 9}" width="12" height="12" '
                f'fill="{_FILLS[si % len(_FILLS)]}" stroke="{_INK}" stroke-width="0.8"/>'
                f'<text x="{lx + 17}" y="{ly + 1}" fill="{_INK}">{_esc(s["name"])}</text>'
            )
            lx += entry
    out.append("</svg>")
    return "".join(out)


def _render_pie(spec: dict) -> str:
    sectors = spec["sectors"]
    unit = spec.get("value_unit") or ""
    frac = unit == "fraction"
    width, height, r = 560, 360 if frac else 320, 100
    cx, cy = width / 2, 180 if frac else 172
    total = sum(s["value"] for s in sectors)
    out = [_header(width, height, spec), _title(spec, width)]
    angle = -math.pi / 2  # 12 o'clock, clockwise
    for i, s in enumerate(sectors):
        sweep = s["value"] / total * 2 * math.pi
        a0, a1 = angle, angle + sweep
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        large = 1 if sweep > math.pi else 0
        out.append(
            f'<path d="M {_n(cx)} {_n(cy)} L {_n(x0)} {_n(y0)} '
            f'A {r} {r} 0 {large} 1 {_n(x1)} {_n(y1)} Z" '
            f'fill="{palette.PAPER}" stroke="{_INK}" stroke-width="1.5"/>'
        )
        mid = (a0 + a1) / 2
        if frac:
            out.append(_fraction_label(spec, i, cx, cy, r, mid))
            angle = a1
            continue
        lx, ly = cx + (r + 16) * math.cos(mid), cy + (r + 16) * math.sin(mid)
        anchor = "start" if math.cos(mid) > 0.15 else "end" if math.cos(mid) < -0.15 else "middle"
        text = _esc(s["label"])
        if s.get("show_value", True):
            text += f" {_n(s['value'])}{_esc(unit)}"
        out.append(
            f'<text x="{_n(lx)}" y="{_n(ly + 4)}" text-anchor="{anchor}" '
            f'fill="{_INK}">{text}</text>'
        )
        angle = a1
    out.append("</svg>")
    return "".join(out)


def _fraction_label(spec: dict, i: int, cx: float, cy: float, r: float, mid: float) -> str:
    """A sector's name with its fraction stacked underneath, the block just clear of the
    circle along the sector's middle direction."""
    s = spec["sectors"][i]
    f = sector_fraction(spec, i)
    shown = s.get("show_value", True)
    w = max(7.5 * len(s["label"]), 8 * len(str(f.denominator)) + 6)
    h = 44 if shown else 14
    ux, uy = math.cos(mid), math.sin(mid)
    d = r + 10 + abs(ux) * w / 2 + abs(uy) * h / 2
    bx, by = cx + d * ux, cy + d * uy - h / 2  # block centre x, block top
    out = (
        f'<text x="{_n(bx)}" y="{_n(by + 11)}" text-anchor="middle" '
        f'fill="{_INK}">{_esc(s["label"])}</text>'
    )
    if shown:
        bar = 7 * len(str(f.denominator)) + 4
        out += (
            f'<text x="{_n(bx)}" y="{_n(by + 27)}" text-anchor="middle" '
            f'fill="{_INK}">{f.numerator}</text>'
            f'<line x1="{_n(bx - bar / 2)}" y1="{_n(by + 30)}" x2="{_n(bx + bar / 2)}" '
            f'y2="{_n(by + 30)}" stroke="{_INK}" stroke-width="1"/>'
            f'<text x="{_n(bx)}" y="{_n(by + 43)}" text-anchor="middle" '
            f'fill="{_INK}">{f.denominator}</text>'
        )
    return out
