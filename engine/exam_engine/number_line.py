"""T3 — the ``number_line`` diagram (schema 1.9.0).

A horizontal line from ``start`` to ``end`` cut into ``divisions`` equal intervals,
with tick labels printed only at the indices in ``labelled`` (decimal, or fractions
and mixed numbers) and lettered ``marked_points`` the student must read or place.
The data is the figure: tick positions and values are derived, never authored.

* :func:`check_number_line_consistency` — spec-only invariants, run by the load gate:
  a valid finite range, labelled ticks that exist, marked points inside the range and
  on a tick, and an *unknown* point never sits on a labelled tick (its value would be
  printed by the tick label next to it).
* :func:`render_number_line_svg` — deterministic, Inter only.
* :func:`tick_value` — the exact value of tick ``i`` as a ``Fraction``.

No FastAPI/Pydantic (ADR-0016) and no import of ``diagram``.
"""

from __future__ import annotations

from fractions import Fraction

_INK = "#1f2433"
_ACCENT = "#2f5fe0"
_MAX = 1_000_000
_MAX_DIVISIONS = 100


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _n(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _is_num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) <= _MAX


def _frac(v: float | int) -> Fraction:
    """The exact decimal the author wrote (``0.1`` is 1/10, not a binary float)."""
    return Fraction(str(v))


def tick_value(spec: dict, i: int) -> Fraction:
    lo, hi = _frac(spec["start"]), _frac(spec["end"])
    return lo + i * (hi - lo) / spec["divisions"]


def _tick_text(spec: dict, i: int) -> str:
    v = tick_value(spec, i)
    if spec.get("label_style") == "fraction" and v.denominator != 1:
        whole, rem = divmod(abs(v), 1)
        sign = "-" if v < 0 else ""
        return f"{sign}{int(whole) or ''} {rem.numerator}/{rem.denominator}".replace("  ", " ")
    return _n(float(v)) if v.denominator != 1 else str(int(v))


def check_number_line_consistency(spec: dict) -> dict[str, bool]:
    lo, hi, div = spec.get("start"), spec.get("end"), spec.get("divisions")
    range_ok = _is_num(lo) and _is_num(hi) and lo < hi  # type: ignore[operator]
    div_ok = isinstance(div, int) and not isinstance(div, bool) and 1 <= div <= _MAX_DIVISIONS
    labelled = spec.get("labelled") or []
    points = spec.get("marked_points") or []
    checks = {
        "range_valid": range_ok,
        "divisions_valid": div_ok,
        "labelled_unique_and_on_line": div_ok
        and len(set(labelled)) == len(labelled)
        and all(isinstance(i, int) and 0 <= i <= div for i in labelled),  # type: ignore[operator]
        "point_labels_unique": len({p.get("label") for p in points}) == len(points),
    }
    prints = False
    on_ticks = within = no_leak = False
    if range_ok and div_ok:
        spec_ok = {**spec, "labelled": []}
        # a decimal label must print without rounding away digits
        prints = spec.get("label_style") == "fraction" or all(
            abs(float(tick_value(spec_ok, i)) - round(float(tick_value(spec_ok, i)), 3)) < 1e-9
            for i in range(div + 1)  # type: ignore[operator]
        )
        ticks = [tick_value(spec_ok, i) for i in range(div + 1)]  # type: ignore[operator]
        vals = [_frac(p["at"]) for p in points if _is_num(p.get("at"))]
        within = len(vals) == len(points) and all(ticks[0] <= v <= ticks[-1] for v in vals)
        on_ticks = within and all(v in ticks for v in vals)
        shown = {ticks[i] for i in labelled if isinstance(i, int) and 0 <= i <= div}  # type: ignore[operator]
        no_leak = within and all(
            p.get("known", False) or _frac(p["at"]) not in shown for p in points
        )
    checks.update(
        {
            "labels_print_exactly": prints,
            "points_within_range": within,
            "points_on_ticks": on_ticks,
            "unknown_points_not_on_labelled_ticks": no_leak,
        }
    )
    return checks


def _stacked(x: float, y: float, num: int, den: int) -> str:
    w = 7 * max(len(str(num)), len(str(den))) + 4
    return (
        f'<text x="{_n(x)}" y="{_n(y)}" text-anchor="middle" fill="{_INK}">{num}</text>'
        f'<line x1="{_n(x - w / 2)}" y1="{_n(y + 3)}" x2="{_n(x + w / 2)}" y2="{_n(y + 3)}" '
        f'stroke="{_INK}" stroke-width="1"/>'
        f'<text x="{_n(x)}" y="{_n(y + 16)}" text-anchor="middle" fill="{_INK}">{den}</text>'
    )


def render_number_line_svg(spec: dict) -> str:
    div = spec["divisions"]
    lo, hi = float(_frac(spec["start"])), float(_frac(spec["end"]))
    width, height, left, right, y = 560, 150, 40, 40, 82
    span = width - left - right

    def x_of(v: float) -> float:
        return left + (v - lo) / (hi - lo) * span

    label = _esc(spec.get("title") or "number line")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{label}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="13">',
        f'<line x1="{left - 12}" y1="{y}" x2="{width - right + 12}" y2="{y}" '
        f'stroke="{_INK}" stroke-width="1.6"/>',
    ]
    if spec.get("title"):
        out.append(
            f'<text x="{width / 2}" y="18" text-anchor="middle" font-size="13" '
            f'font-weight="600" fill="{_INK}">{_esc(spec["title"])}</text>'
        )
    labelled = set(spec.get("labelled") or [])
    for i in range(div + 1):
        x = left + span * i / div
        big = i in labelled
        out.append(
            f'<line x1="{_n(x)}" y1="{y - (9 if big else 6)}" x2="{_n(x)}" '
            f'y2="{y + (9 if big else 6)}" stroke="{_INK}" stroke-width="{1.6 if big else 1}"/>'
        )
        if not big:
            continue
        v = tick_value(spec, i)
        if spec.get("label_style") == "fraction" and v.denominator != 1:
            whole, rem = divmod(abs(v), 1)
            if whole or v < 0:
                text = ("-" if v < 0 else "") + (str(int(whole)) if whole else "")
                out.append(
                    f'<text x="{_n(x - 9)}" y="{y + 30}" text-anchor="middle" '
                    f'fill="{_INK}">{text}</text>'
                )
                out.append(_stacked(x + 5, y + 26, rem.numerator, rem.denominator))
            else:
                out.append(_stacked(x, y + 26, rem.numerator, rem.denominator))
        else:
            out.append(
                f'<text x="{_n(x)}" y="{y + 28}" text-anchor="middle" '
                f'fill="{_INK}">{_tick_text(spec, i)}</text>'
            )
    for p in spec.get("marked_points") or []:
        x = x_of(float(_frac(p["at"])))
        out.append(
            f'<polygon points="{_n(x - 6)},{y - 24} {_n(x + 6)},{y - 24} {_n(x)},{y - 10}" '
            f'fill="{_ACCENT}" stroke="{_INK}" stroke-width="0.8"/>'
            f'<text x="{_n(x)}" y="{y - 30}" text-anchor="middle" font-weight="600" '
            f'fill="{_INK}">{_esc(p.get("label") or "")}</text>'
        )
    out.append("</svg>")
    return "".join(out)
