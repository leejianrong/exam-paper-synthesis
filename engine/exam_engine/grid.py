"""EXA-144 — the ``grid`` diagram (schema 1.13.0): a square grid with points, lines and shading.

Real P5/P6 papers set parallel and perpendicular lines, symmetry, directions and area by
counting squares on a square grid (lines or dots). The spec says what is on the grid in grid
units; the renderer draws it, so a question's numbers and its picture come from one place.

Coordinates: ``x`` runs 0..``cols`` left to right and ``y`` runs 0..``rows`` top to bottom
(grid points, where the lines cross). Cell ``(col, row)`` is the square whose top-left corner
is the point ``(col, row)``.

* ``cells``    — whole squares, shaded and/or lettered (a letter sits in the square's middle).
* ``polygons`` — figures with vertices on grid points, shaded or outlined.
* ``segments`` — straight lines between grid points, solid or dashed (a line of symmetry).
* ``points``   — lettered grid points, drawn as dots.
* ``compass``  — a four-point compass rose beside the grid (north is up).

* :func:`check_grid_consistency` — spec-only invariants (run by the load gate).
* :func:`render_grid_svg` — deterministic, Inter only, the print palette, labels placed clear
  of every line by :mod:`label_layout`.

No FastAPI/Pydantic (ADR-0016) and no import of ``diagram``.
"""

from __future__ import annotations

import math

from exam_engine import palette

from .label_layout import Layout

_INK = palette.INK
_MAX_COLS = 16
_MAX_ROWS = 12
_S = 30.0  # px per grid square
_PAD = 24.0  # px around the grid (room for point letters outside it)
_ROSE = 110.0  # px of width the compass rose takes beside the grid
_FONT = 13


def _n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _pt(v: object) -> tuple[int, int] | None:
    if isinstance(v, list | tuple) and len(v) == 2 and all(_is_int(c) for c in v):
        return int(v[0]), int(v[1])
    return None


def _cross(o: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_meet(
    p: tuple[int, int], q: tuple[int, int], r: tuple[int, int], s: tuple[int, int]
) -> bool:
    """Do the closed segments pq and rs share a point?"""
    d1, d2 = _cross(r, s, p), _cross(r, s, q)
    d3, d4 = _cross(p, q, r), _cross(p, q, s)
    if ((d1 > 0) != (d2 > 0)) and d1 and d2 and ((d3 > 0) != (d4 > 0)) and d3 and d4:
        return True

    def on(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> bool:
        return (
            _cross(a, b, c) == 0
            and min(a[0], b[0]) <= c[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
        )

    return on(r, s, p) or on(r, s, q) or on(p, q, r) or on(p, q, s)


def is_simple(vertices: list[tuple[int, int]]) -> bool:
    """A polygon whose sides meet only at shared corners, with no repeated vertex."""
    n = len(vertices)
    if n < 3 or len(set(vertices)) != n:
        return False
    sides = [(vertices[i], vertices[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                # neighbours share one corner; they must not fold back over each other
                a, b = sides[i]
                c, d = sides[j]
                shared = b if j == i + 1 else a
                far1 = a if j == i + 1 else b
                far2 = d if j == i + 1 else c
                if _cross(shared, far1, far2) == 0 and (
                    (far1[0] - shared[0]) * (far2[0] - shared[0])
                    + (far1[1] - shared[1]) * (far2[1] - shared[1])
                    > 0
                ):
                    return False
                continue
            if _segments_meet(*sides[i], *sides[j]):
                return False
    return True


def check_grid_consistency(spec: dict) -> dict[str, bool]:
    """Spec-only invariants; every value is a ``bool`` (``True`` = holds)."""
    cols, rows = spec.get("cols"), spec.get("rows")
    size_ok = (
        _is_int(cols) and _is_int(rows) and 1 <= cols <= _MAX_COLS and 1 <= rows <= _MAX_ROWS  # type: ignore[operator]
    )
    c_max = cols if size_ok else -1
    r_max = rows if size_ok else -1

    def inside(p: tuple[int, int] | None) -> bool:
        return p is not None and 0 <= p[0] <= c_max and 0 <= p[1] <= r_max  # type: ignore[operator]

    cells = [c for c in spec.get("cells") or [] if isinstance(c, dict)]
    where = [(repr(c.get("col")), repr(c.get("row"))) for c in cells]
    cells_inside = all(
        _is_int(c.get("col"))
        and _is_int(c.get("row"))
        and 0 <= c["col"] < c_max
        and 0 <= c["row"] < r_max
        for c in cells
    )

    polygons = [p for p in spec.get("polygons") or [] if isinstance(p, dict)]
    shapes = [[_pt(v) for v in p.get("vertices") or []] for p in polygons]
    polygons_inside = all(all(inside(v) for v in vs) for vs in shapes)
    polygons_simple = polygons_inside and all(
        is_simple([v for v in vs if v is not None]) for vs in shapes
    )

    segs = [s for s in spec.get("segments") or [] if isinstance(s, dict)]
    ends = [(_pt(s.get("from")), _pt(s.get("to"))) for s in segs]
    segments_inside = all(inside(a) and inside(b) for a, b in ends)

    points = [p for p in spec.get("points") or [] if isinstance(p, dict)]
    spots = [_pt([p.get("x"), p.get("y")]) for p in points]
    # repr: a junk label (a list) is compared, not hashed
    labels = [repr(p.get("label")) for p in points]
    labels += [repr(c.get("label")) for c in cells if c.get("label")]
    return {
        "size_in_range": size_ok,
        "cells_inside": size_ok and cells_inside,
        "cells_unique": len(set(where)) == len(where),
        "polygons_inside": size_ok and polygons_inside,
        "polygons_simple": polygons_simple,
        "segments_inside": size_ok and segments_inside,
        "segments_not_points": all(a != b for a, b in ends),
        "points_inside": size_ok and all(inside(p) for p in spots),
        "points_distinct": len(set(spots)) == len(spots),
        "labels_unique": len(set(labels)) == len(labels),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _rose(cx: float, cy: float, lay: Layout) -> list[str]:
    """A four-point compass rose: long N/E/S/W arms (N with an arrowhead), short diagonals."""
    out = []
    long, short = 26.0, 14.0
    for k in range(8):
        a = math.radians(45 * k)
        r = long if k % 2 == 0 else short
        x, y = cx + r * math.sin(a), cy - r * math.cos(a)
        width = 1.6 if k % 2 == 0 else 1.0
        out.append(
            f'<line x1="{_n(cx)}" y1="{_n(cy)}" x2="{_n(x)}" y2="{_n(y)}" '
            f'stroke="{_INK}" stroke-width="{width}"/>'
        )
        lay.stroke([(cx, cy), (x, y)], width)
    head = [(cx, cy - long - 2), (cx - 5, cy - long + 8), (cx + 5, cy - long + 8)]
    out.append(
        '<polygon points="'
        + " ".join(f"{_n(x)},{_n(y)}" for x, y in head)
        + f'" fill="{_INK}" stroke="{_INK}" stroke-width="1"/>'
    )
    lay.stroke([*head, head[0]], 1)
    for letter, (dx, dy) in (("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("W", (-1, 0))):
        x, y = lay.place(letter, lay.away(cx, cy, [(dx, dy)], letter, long + 2, (0, 2, 4, 8)))
        out.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" font-weight="600" '
            f'fill="{_INK}">{letter}</text>'
        )
    return out


# Where a point's letter may go, best first: inside one of the four squares at the point, off
# every grid line (a letter centred on a line would sit on it), then a little farther out.
_SPOTS = sorted(
    {
        (sx * fx, sy * fy)
        for sx in (1, -1)
        for sy in (-1, 1)
        for fx, fy in ((0.4, 0.4), (0.55, 0.35), (0.35, 0.55), (0.6, 0.6), (0.5, 0.5))
    },
    key=lambda d: (round(abs(d[0]) + abs(d[1]), 2), d[1], -d[0]),
) + [(sx * fx, sy * fy) for fx, fy in ((1.4, 0.5), (0.5, 1.4)) for sx in (1, -1) for sy in (-1, 1)]


def _near(px: float, py: float) -> list[tuple[float, float]]:
    return [(px + dx * _S, py + dy * _S) for dx, dy in _SPOTS]


def render_grid_svg(spec: dict) -> str:
    cols, rows = spec["cols"], spec["rows"]
    title = spec.get("title")
    top = _PAD + (22 if title else 0)
    rose = bool(spec.get("compass"))
    w = 2 * _PAD + cols * _S + (_ROSE if rose else 0)
    h = top + rows * _S + _PAD
    if rose:  # the rose needs about 100 px of height beside a short grid
        h = max(h, top + 100)
    lay = Layout(_FONT)

    def X(x: float) -> float:
        return _PAD + x * _S

    def Y(y: float) -> float:
        return top + y * _S

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(w)} {_n(h)}" '
        f'width="{_n(w)}" height="{_n(h)}" role="img" '
        f'aria-label="{_esc(title or "A figure on a square grid")}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="{_FONT}">'
    ]
    if title:
        out.append(
            f'<text x="{_n(w / 2)}" y="18" text-anchor="middle" font-size="13" '
            f'font-weight="600" fill="{_INK}">{_esc(title)}</text>'
        )
        lay.reserve(w / 2, 18, title, "middle")

    # shading first, so the grid lines show through it as on a printed grid
    for c in spec.get("cells") or []:
        if c.get("shaded", True):
            out.append(
                f'<rect x="{_n(X(c["col"]))}" y="{_n(Y(c["row"]))}" width="{_n(_S)}" '
                f'height="{_n(_S)}" fill="{palette.SHADE}"/>'
            )
    for p in spec.get("polygons") or []:
        if p.get("shaded", True):
            pts = " ".join(f"{_n(X(x))},{_n(Y(y))}" for x, y in p["vertices"])
            out.append(f'<polygon points="{pts}" fill="{palette.SHADE}"/>')

    if spec.get("style", "lines") == "dots":
        for i in range(cols + 1):
            for j in range(rows + 1):
                out.append(
                    f'<circle cx="{_n(X(i))}" cy="{_n(Y(j))}" r="1.6" fill="{palette.TINT_DARK}"/>'
                )
                lay.stroke([(X(i) - 1.6, Y(j)), (X(i) + 1.6, Y(j))], 3.2)
    else:
        for i in range(cols + 1):
            out.append(
                f'<line x1="{_n(X(i))}" y1="{_n(Y(0))}" x2="{_n(X(i))}" y2="{_n(Y(rows))}" '
                f'stroke="{palette.GRID}" stroke-width="1"/>'
            )
            lay.stroke([(X(i), Y(0)), (X(i), Y(rows))], 1)
        for j in range(rows + 1):
            out.append(
                f'<line x1="{_n(X(0))}" y1="{_n(Y(j))}" x2="{_n(X(cols))}" y2="{_n(Y(j))}" '
                f'stroke="{palette.GRID}" stroke-width="1"/>'
            )
            lay.stroke([(X(0), Y(j)), (X(cols), Y(j))], 1)

    for p in spec.get("polygons") or []:
        vs = [(X(x), Y(y)) for x, y in p["vertices"]]
        pts = " ".join(f"{_n(x)},{_n(y)}" for x, y in vs)
        out.append(f'<polygon points="{pts}" fill="none" stroke="{_INK}" stroke-width="2"/>')
        lay.stroke([*vs, vs[0]], 2)
    for s in spec.get("segments") or []:
        (x1, y1), (x2, y2) = s["from"], s["to"]
        dash = ' stroke-dasharray="6 4"' if s.get("dashed") else ""
        out.append(
            f'<line x1="{_n(X(x1))}" y1="{_n(Y(y1))}" x2="{_n(X(x2))}" y2="{_n(Y(y2))}" '
            f'stroke="{_INK}" stroke-width="2"{dash}/>'
        )
        lay.stroke([(X(x1), Y(y1)), (X(x2), Y(y2))], 2)

    points = spec.get("points") or []
    for p in points:
        out.append(f'<circle cx="{_n(X(p["x"]))}" cy="{_n(Y(p["y"]))}" r="3" fill="{_INK}"/>')
        lay.stroke([(X(p["x"]) - 3, Y(p["y"])), (X(p["x"]) + 3, Y(p["y"]))], 6)

    for c in spec.get("cells") or []:
        if c.get("label"):
            x, y = lay.place(c["label"], [(X(c["col"] + 0.5), Y(c["row"] + 0.5))])
            out.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" font-weight="600" '
                f'fill="{_INK}">{_esc(c["label"])}</text>'
            )
    if rose:  # first, so point letters keep clear of its letters
        out += _rose(X(cols) + _ROSE / 2 + 10, Y(0) + 46, lay)
    for p in points:
        x, y = lay.place(p["label"], _near(X(p["x"]), Y(p["y"])))
        out.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" font-weight="600" '
            f'fill="{_INK}">{_esc(p["label"])}</text>'
        )
    out.append("</svg>")
    return "".join(out)
