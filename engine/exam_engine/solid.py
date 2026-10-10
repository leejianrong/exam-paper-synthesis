"""T2 — the ``solid`` diagram (schema 1.8.0): cuboid and container with a fill level.

Like ``chart``, the data *is* the figure: the drawing is derived from the spec, so
a printed solid is provably the one described. A fixed oblique projection (no
perspective): the front face is drawn true to scale, depth recedes up and to the
right at half length, and the hidden edges of the back-bottom-left corner are dashed.

* :func:`check_solid_consistency` — spec-only invariants (positive exact dims, the
  fill sits inside the container, a plain cuboid carries no fill). Run by the
  canonical load gate.
* :func:`render_solid_svg` — deterministic spec -> inline ``<svg>``. Inter only.
  A dimension listed in ``hidden_dims`` (or a fill with ``show_height: false``) is
  drawn at its true size but printed as ``?``.
* :func:`leaked_hidden_values` — the hidden numbers never reach the SVG text.
* :func:`solid_volume` / :func:`fill_volume` — volume claims derived from the dims,
  for blueprints and invariant tests.

No FastAPI/Pydantic here (ADR-0016) and no import of ``diagram``.
"""

from __future__ import annotations

import math
import re

_INK = "#1f2433"
_WATER = "#cfe0ff"
_WATER_TOP = "#e6eeff"
_TOP = "#f1f3f9"
_MAX = 1_000_000
_MIN_DIM = 0.001
_DIMS = ("length", "width", "height")
_DEPTH = 0.5 * math.cos(math.pi / 4)  # drawn depth per unit of width


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
    # Bounded so round()/formatting can never overflow and labels always fit the figure.
    return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) <= _MAX


def _prints_exactly(v: object) -> bool:
    return _is_num(v) and abs(round(v, 3) - v) < 1e-9  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Maths (the claims a question may make about the figure)
# ---------------------------------------------------------------------------


def solid_volume(spec: dict) -> float:
    d = spec["dims"]
    return d["length"] * d["width"] * d["height"]


def fill_volume(spec: dict) -> float:
    """Volume of the contents (0 when empty or not a container)."""
    fill = spec.get("fill")
    if not fill:
        return 0.0
    d = spec["dims"]
    return d["length"] * d["width"] * fill["height"]


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def check_solid_consistency(spec: dict) -> dict[str, bool]:
    """Spec-only invariants; every value is a ``bool`` (``True`` = holds)."""
    dims = spec.get("dims") or {}
    values = [dims.get(k) for k in _DIMS]
    dims_ok = all(_is_num(v) and v >= _MIN_DIM for v in values)  # type: ignore[operator]
    fill = spec.get("fill")
    hidden = spec.get("hidden_dims") or []
    checks = {
        "kind_known": spec.get("kind") in ("cuboid", "container"),
        "dims_positive": dims_ok,
        "dims_print_exactly": all(_prints_exactly(v) for v in values),
        "hidden_dims_unique": len(set(hidden)) == len(hidden),
        "fill_only_on_container": not (fill and spec.get("kind") != "container"),
    }
    if fill:
        fh = fill.get("height")
        checks["fill_within_height"] = bool(dims_ok and _is_num(fh) and 0 <= fh <= dims["height"])
        checks["fill_prints_exactly"] = _prints_exactly(fh)
        # A shown fill label equal to a hidden dimension would print the answer.
        hidden_vals = [dims.get(k) for k in hidden if k in _DIMS]
        checks["fill_label_does_not_reveal_hidden_dim"] = not (
            fill.get("show_height", True) and fh in hidden_vals
        )
    return checks


# ---------------------------------------------------------------------------
# Hidden values
# ---------------------------------------------------------------------------


def _hidden_values(spec: dict) -> list[float]:
    out = [spec["dims"][k] for k in _DIMS if k in (spec.get("hidden_dims") or [])]
    fill = spec.get("fill")
    if fill and fill.get("show_height", True) is False:
        out.append(fill["height"])
    return out


def _shown_values(spec: dict) -> list[float]:
    out = [spec["dims"][k] for k in _DIMS if k not in (spec.get("hidden_dims") or [])]
    fill = spec.get("fill")
    if fill and fill.get("show_height", True):
        out.append(fill["height"])
    return out


def leaked_hidden_values(spec: dict, svg: str) -> list[str]:
    """Hidden values that still appear in the SVG's text or aria-label.

    A hidden value may equal a *shown* one (a cube's three edges), so a token is
    leaked only when it occurs more often than the shown values carrying it.
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


def render_solid_svg(spec: dict) -> str:
    d = spec["dims"]
    length, width, height = d["length"], d["width"], d["height"]
    unit = spec.get("unit") or ""
    hidden = spec.get("hidden_dims") or []
    fill = spec.get("fill")
    container = spec["kind"] == "container"

    scale = min(300 / (length + _DEPTH * width), 200 / (height + _DEPTH * width))
    lw, hh = length * scale, height * scale
    dx = _DEPTH * width * scale  # back-face offset: right by dx, up by dx
    left, top = 64, 40
    svg_w = round(left + lw + dx + 90)
    thin = lw < 56  # narrow front face: stagger the width label below the length label
    svg_h = round(top + hh + dx + (56 if thin else 40))
    x0, y0 = left, top + hh + dx  # front-bottom-left

    def p(x: float, y: float) -> str:
        return f"{_n(x)},{_n(y)}"

    fbl, fbr = (x0, y0), (x0 + lw, y0)
    ftl, ftr = (x0, y0 - hh), (x0 + lw, y0 - hh)
    bbl, bbr = (x0 + dx, y0 - dx), (x0 + lw + dx, y0 - dx)
    btl, btr = (x0 + dx, y0 - hh - dx), (x0 + lw + dx, y0 - hh - dx)

    def text(v: float, key: str | None = None) -> str:
        if key is not None and key in hidden:
            return "?"
        return f"{_n(v)} {_esc(unit)}".strip()

    label = _esc(spec.get("title") or spec["kind"])
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}" role="img" aria-label="{label}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="12">'
    ]
    if spec.get("title"):
        out.append(
            f'<text x="{_n(svg_w / 2)}" y="18" text-anchor="middle" font-size="13" '
            f'font-weight="600" fill="{_INK}">{_esc(spec["title"])}</text>'
        )

    if fill:
        wf = fill["height"] * scale
        wfl, wfr = (fbl[0], y0 - wf), (fbr[0], y0 - wf)
        wbl, wbr = (bbl[0], bbl[1] - wf), (bbr[0], bbr[1] - wf)
        out.append(
            f'<polygon points="{p(*fbl)} {p(*fbr)} {p(*wfr)} {p(*wfl)}" fill="{_WATER}"/>'
            f'<polygon points="{p(*fbr)} {p(*bbr)} {p(*wbr)} {p(*wfr)}" fill="{_WATER}"/>'
            f'<polygon points="{p(*wfl)} {p(*wfr)} {p(*wbr)} {p(*wbl)}" fill="{_WATER_TOP}" '
            f'stroke="{_INK}" stroke-width="0.8"/>'
        )

    # Hidden edges (dashed) of the back-bottom-left corner.
    out.append(
        f'<polyline points="{p(*fbl)} {p(*bbl)} {p(*bbr)}" fill="none" stroke="{_INK}" '
        f'stroke-width="1" stroke-dasharray="5 4"/>'
        f'<line x1="{_n(bbl[0])}" y1="{_n(bbl[1])}" x2="{_n(btl[0])}" y2="{_n(btl[1])}" '
        f'stroke="{_INK}" stroke-width="1" stroke-dasharray="5 4"/>'
    )

    top_fill = "none" if container else _TOP
    out.append(
        f'<polygon points="{p(*fbl)} {p(*fbr)} {p(*ftr)} {p(*ftl)}" fill="none" '
        f'stroke="{_INK}" stroke-width="1.4"/>'
        f'<polygon points="{p(*fbr)} {p(*bbr)} {p(*btr)} {p(*ftr)}" fill="none" '
        f'stroke="{_INK}" stroke-width="1.4"/>'
        f'<polygon points="{p(*ftl)} {p(*ftr)} {p(*btr)} {p(*btl)}" fill="{top_fill}" '
        f'stroke="{_INK}" stroke-width="1.4"/>'
    )

    wy = y0 + 34 if thin else y0 - dx / 2 + 14
    # Dimension labels: length under the front edge, height left, width on the depth edge.
    out.append(
        f'<text x="{_n(x0 + lw / 2)}" y="{_n(y0 + 18)}" text-anchor="middle" fill="{_INK}">'
        f"{text(length, 'length')}</text>"
        f'<text x="{_n(x0 - 8)}" y="{_n(y0 - hh / 2 + 4)}" text-anchor="end" fill="{_INK}">'
        f"{text(height, 'height')}</text>"
        f'<text x="{_n(x0 + lw + dx / 2 + 6)}" y="{_n(wy)}" fill="{_INK}">'
        f"{text(width, 'width')}</text>"
    )
    if fill:
        shown = fill.get("show_height", True)
        fy = bbr[1] - fill["height"] * scale
        out.append(
            f'<line x1="{_n(bbr[0])}" y1="{_n(fy)}" x2="{_n(bbr[0] + 6)}" y2="{_n(fy)}" '
            f'stroke="{_INK}" stroke-width="1"/>'
            f'<text x="{_n(bbr[0] + 9)}" y="{_n(fy + 4)}" fill="{_INK}">'
            f"{text(fill['height']) if shown else '?'}</text>"
        )
    out.append("</svg>")
    return "".join(out)
