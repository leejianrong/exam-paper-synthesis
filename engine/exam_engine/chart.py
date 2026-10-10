"""T1 — the ``chart`` diagram (schema 1.7.0): bar / line / pie.

A structured statistical figure: the data *is* the spec, and the drawing is
derived from it (never the other way round), so a printed chart is provably the
chart described by the object. Three pure, deterministic pieces:

* :func:`check_chart_consistency` — spec-only invariants (series align with
  categories, values sit on the axis, the axis step divides its span, a percent
  pie sums to 100). Used by the canonical load gate, so a sourced chart whose
  numbers disagree with its own axis is rejected on import.
* :func:`render_chart_svg` — deterministic spec -> inline ``<svg>``. Inter only
  (EXA-94); series are told apart by fill *and* line style so a greyscale print
  stays readable. A value with ``show_value: false`` is drawn at its true size
  but is never written as text.
* :func:`leaked_hidden_values` — the "no leak" proof: the hidden numbers of a
  spec must not appear in any text node or ``aria-label`` of its own SVG.

No FastAPI/Pydantic here (engine stays UI/HTTP-agnostic, ADR-0016) and no
import of ``diagram`` (``diagram`` dispatches *to* this module).
"""

from __future__ import annotations

import math
import re

_EPS = 1e-9
_MAX_TICKS = 50

_FILLS = ("#2f5fe0", "#9fb0e8", "#66708a", "#c9cedb", "#1d3a8a", "#e7ebf7")
_DASHES = ("", "7 4", "2 4", "9 3 2 3")
_INK = "#1f2433"
_GRID = "#d9dde8"
_AXIS = "#66708a"


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
    return isinstance(v, (int, float)) and not isinstance(v, bool)


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
    }
    if spec.get("value_unit") == "%":
        checks["percent_sums_to_100"] = positive and abs(sum(values) - 100) < 1e-6
    return checks


def _check_axes_chart(spec: dict) -> dict[str, bool]:
    cats = (spec.get("x_axis") or {}).get("categories") or []
    axis = spec.get("y_axis") or {}
    series = spec.get("series") or []
    raw = (axis.get("min"), axis.get("max"), axis.get("step"))
    axis_ok = all(_is_num(v) for v in raw) and raw[0] < raw[1] and raw[2] > 0  # type: ignore[operator]
    lo = hi = 0.0
    span_ok = False
    if axis_ok:
        lo, hi, step = (float(v) for v in raw)  # type: ignore[arg-type]
        n = (hi - lo) / step
        span_ok = abs(n - round(n)) < 1e-6 and round(n) <= _MAX_TICKS
    values = [v for s in series for v in s.get("values", []) if v is not None]
    names = [s.get("name") for s in series]
    return {
        "has_categories": len(cats) >= 1,
        "categories_unique": len(set(cats)) == len(cats),
        "series_align_with_categories": bool(series)
        and all(len(s.get("values", [])) == len(cats) for s in series),
        "axis_range_valid": axis_ok,
        "step_divides_span": span_ok,
        "values_within_axis": axis_ok and all(_is_num(v) and lo <= v <= hi for v in values),
        "series_names_unique": len(set(names)) == len(names),
    }


# ---------------------------------------------------------------------------
# Hidden values
# ---------------------------------------------------------------------------


def _hidden_values(spec: dict) -> list[float]:
    if spec.get("kind") == "pie":
        return [s["value"] for s in spec.get("sectors", []) if s.get("show_value", True) is False]
    return []


def _shown_values(spec: dict) -> list[float]:
    if spec.get("kind") == "pie":
        return [s["value"] for s in spec.get("sectors", []) if s.get("show_value", True)]
    return []


def leaked_hidden_values(spec: dict, svg: str) -> list[str]:
    """Return hidden values that still appear in the SVG's text or aria-label.

    A hidden value may legitimately equal a *shown* one (two 25% sectors), so a
    token counts as leaked only when it occurs more often in the visible text
    than the shown sectors carrying it account for.
    """
    visible = " ".join(re.findall(r">([^<]*)<", svg) + re.findall(r'aria-label="([^"]*)"', svg))
    shown = [_n(v) for v in _shown_values(spec)]
    leaks = []
    for token in sorted({_n(v) for v in _hidden_values(spec)}):
        found = len(re.findall(rf"(?<![\d.]){re.escape(token)}(?![\d.])", visible))
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
    cats = spec["x_axis"]["categories"]
    axis = spec["y_axis"]
    series = spec["series"]
    legend = len(series) > 1
    width, height = 460, 320
    left, right, top = 62, 18, 34
    bottom = 64 + (22 if legend else 0)
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

    band = pw / len(cats)
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
            color, dash = _FILLS[si % len(_FILLS)], _DASHES[si % len(_DASHES)]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            run: list[str] = []
            for i, v in enumerate(s["values"] + [None]):
                if v is not None:
                    run.append(f"{_n(left + band * (i + 0.5))},{_n(y(v))}")
                    continue
                if len(run) > 1:
                    out.append(
                        f'<polyline points="{" ".join(run)}" fill="none" stroke="{color}" '
                        f'stroke-width="2"{dash_attr}/>'
                    )
                run = []
            for i, v in enumerate(s["values"]):
                if v is None:
                    continue
                px, py = left + band * (i + 0.5), y(v)
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
        lx = left
        ly = height - 14
        for si, s in enumerate(series):
            out.append(
                f'<rect x="{lx}" y="{ly - 9}" width="12" height="12" '
                f'fill="{_FILLS[si % len(_FILLS)]}" stroke="{_INK}" stroke-width="0.8"/>'
                f'<text x="{lx + 17}" y="{ly + 1}" fill="{_INK}">{_esc(s["name"])}</text>'
            )
            lx += 17 + 8 * len(str(s["name"])) + 18
    out.append("</svg>")
    return "".join(out)


def _render_pie(spec: dict) -> str:
    sectors = spec["sectors"]
    unit = spec.get("value_unit") or ""
    width, height, r = 420, 320, 100
    cx, cy = width / 2, 172
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
            f'fill="{_FILLS[i % len(_FILLS)]}" stroke="#ffffff" stroke-width="2"/>'
        )
        mid = (a0 + a1) / 2
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
