"""T6 — the ``cube_stack`` diagram (schema 1.12.0): a heightmap of unit cubes and its views.

The authored data is only ``heights`` (rows back to front, columns left to right: the
number of cubes stacked on each cell). Every picture is derived from it, so "which view
is this?" questions are right by construction and the usual ambiguity (cubes hidden
behind taller stacks) cannot arise: the heightmap says exactly what is there.

* ``view: "iso"`` — the stack drawn from the front-right above (cubes painted far to near).
* ``view: "front"`` — looking from the front: column ``c`` shows ``max`` over rows.
* ``view: "side"`` — looking from the right: front row on the left, back row on the right.
* ``view: "top"`` — looking down: every occupied cell is a square.

* :func:`check_cube_stack_consistency` — spec-only invariants (run by the load gate).
* :func:`front_view` / :func:`side_view` / :func:`top_view` / :func:`view_key` /
  :func:`cube_count` — the derivations, for blueprints and invariant tests.
* :func:`render_cube_stack_svg` — deterministic, Inter only.

No FastAPI/Pydantic (ADR-0016) and no import of ``diagram``.
"""

from __future__ import annotations

import math

_INK = "#1f2433"
_TOP = "#f1f3f9"
_LEFT = "#d9deee"
_RIGHT = "#b9c1dd"
_SQ = "#e8ecf8"
_MAX_H = 8
_MAX_SIDE = 6
_VIEWS = ("iso", "front", "side", "top")
_COS = math.cos(math.pi / 6)
_SIN = 0.5


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
# Derivations
# ---------------------------------------------------------------------------


def cube_count(heights: list[list[int]]) -> int:
    return sum(sum(row) for row in heights)


def front_view(heights: list[list[int]]) -> list[int]:
    """Visible stack height of each column, left to right, seen from the front."""
    return [max(row[c] for row in heights) for c in range(len(heights[0]))]


def side_view(heights: list[list[int]]) -> list[int]:
    """Visible stack height of each row seen from the right: front row first (left)."""
    return [max(row) for row in reversed(heights)]


def top_view(heights: list[list[int]]) -> list[list[bool]]:
    """Occupied cells, back row first (top of the picture)."""
    return [[h > 0 for h in row] for row in heights]


def view_key(heights: list[list[int]], view: str) -> object:
    """A hashable form of what ``view`` shows, so two figures can be compared for equality."""
    if view == "front":
        return tuple(front_view(heights))
    if view == "side":
        return tuple(side_view(heights))
    if view == "top":
        return tuple(tuple(r) for r in top_view(heights))
    return tuple(tuple(r) for r in heights)


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def check_cube_stack_consistency(spec: dict) -> dict[str, bool]:
    """Spec-only invariants; every value is a ``bool`` (``True`` = holds)."""
    heights = spec.get("heights")
    rows_ok = (
        isinstance(heights, list)
        and 1 <= len(heights) <= _MAX_SIDE
        and all(isinstance(r, list) for r in heights)
    )
    width = len(heights[0]) if rows_ok else 0
    rectangular = rows_ok and 1 <= width <= _MAX_SIDE and all(len(r) == width for r in heights)
    cells_ok = rectangular and all(_is_int(h) and 0 <= h <= _MAX_H for r in heights for h in r)
    return {
        "view_known": spec.get("view", "iso") in _VIEWS,
        "heights_rectangular": bool(rectangular),
        "heights_in_range": bool(cells_ok),
        "has_cubes": bool(cells_ok and cube_count(heights) > 0),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _wrap(w: float, h: float, label: str, body: list[str], title: str | None) -> str:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(w)} {_n(h)}" '
        f'width="{_n(w)}" height="{_n(h)}" role="img" aria-label="{_esc(label)}" '
        f'font-family="Inter, system-ui, sans-serif" font-size="12">'
    ]
    if title:
        out.append(
            f'<text x="{_n(w / 2)}" y="18" text-anchor="middle" font-size="13" '
            f'font-weight="600" fill="{_INK}">{_esc(title)}</text>'
        )
    return "".join(out + body + ["</svg>"])


def _poly(pts: list[tuple[float, float]], fill: str) -> str:
    p = " ".join(f"{_n(x)},{_n(y)}" for x, y in pts)
    return f'<polygon points="{p}" fill="{fill}" stroke="{_INK}" stroke-width="1.2" />'


def _render_iso(heights: list[list[int]], title: str | None) -> str:
    rows, cols = len(heights), len(heights[0])
    s = 34.0  # cube edge in px
    a, b = s * _COS, s * _SIN  # screen step per +col (right-down) / +row (left-down)
    tallest = max(max(r) for r in heights)
    top_pad = 30 if title else 12
    # origin: screen position of the back-left-bottom corner (c=0, r=0, z=0).
    ox = 12 + rows * a
    oy = top_pad + tallest * s

    def pt(c: float, r: float, z: float) -> tuple[float, float]:
        return (ox + (c - r) * a, oy + (c + r) * b - z * s)

    w = 12 + (rows + cols) * a + 12
    h = oy + (rows + cols) * b + 12
    body = []
    order = sorted(
        ((r, c, z) for r in range(rows) for c in range(cols) for z in range(heights[r][c])),
        key=lambda t: (t[0] + t[1], t[2], t[0]),
    )
    for r, c, z in order:
        # top face, front face (+row side, left on screen), right face (+col side)
        body.append(
            _poly(
                [
                    pt(c, r, z + 1),
                    pt(c + 1, r, z + 1),
                    pt(c + 1, r + 1, z + 1),
                    pt(c, r + 1, z + 1),
                ],
                _TOP,
            )
        )
        body.append(
            _poly(
                [
                    pt(c, r + 1, z),
                    pt(c + 1, r + 1, z),
                    pt(c + 1, r + 1, z + 1),
                    pt(c, r + 1, z + 1),
                ],
                _LEFT,
            )
        )
        body.append(
            _poly(
                [
                    pt(c + 1, r, z),
                    pt(c + 1, r + 1, z),
                    pt(c + 1, r + 1, z + 1),
                    pt(c + 1, r, z + 1),
                ],
                _RIGHT,
            )
        )
    return _wrap(w, h, title or "A stack of cubes", body, title)


def _render_elevation(profile: list[int], title: str | None, label: str) -> str:
    s = 30.0
    tallest = max(profile)
    top_pad = 30 if title else 12
    w = 24 + len(profile) * s
    h = top_pad + tallest * s + 12
    body = [
        f'<rect x="{_n(12 + i * s)}" y="{_n(top_pad + (tallest - k - 1) * s)}" width="{_n(s)}" '
        f'height="{_n(s)}" fill="{_SQ}" stroke="{_INK}" stroke-width="1.2" />'
        for i, height in enumerate(profile)
        for k in range(height)
    ]
    return _wrap(w, h, title or label, body, title)


def _render_top(cells: list[list[bool]], title: str | None) -> str:
    s = 30.0
    top_pad = 30 if title else 12
    w = 24 + len(cells[0]) * s
    h = top_pad + len(cells) * s + 12
    body = [
        f'<rect x="{_n(12 + c * s)}" y="{_n(top_pad + r * s)}" width="{_n(s)}" height="{_n(s)}" '
        f'fill="{_SQ}" stroke="{_INK}" stroke-width="1.2" />'
        for r, row in enumerate(cells)
        for c, on in enumerate(row)
        if on
    ]
    return _wrap(w, h, title or "A stack of cubes seen from above", body, title)


def render_cube_stack_svg(spec: dict) -> str:
    heights = spec["heights"]
    view = spec.get("view", "iso")
    title = spec.get("title")
    if view == "front":
        return _render_elevation(front_view(heights), title, "A stack of cubes seen from the front")
    if view == "side":
        return _render_elevation(side_view(heights), title, "A stack of cubes seen from the right")
    if view == "top":
        return _render_top(top_view(heights), title)
    return _render_iso(heights, title)
