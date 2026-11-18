"""The ``net`` diagram (schema 1.13.0, EXA-147): a net of a cube drawn on a square grid.

The authored data is six unit squares ``faces[i] = {row, col, label?, shaded?}`` (rows top to
bottom, columns left to right). Real papers ask which face is opposite a marked one once the
net is folded, or which figure folds into a cube.

* :func:`check_net_consistency` — spec-only invariants (run by the load gate): six distinct
  cells joined edge to edge, short unique labels. Whether the six squares fold into a cube is
  *not* a load rule, so a "which of these is not a net?" figure can be drawn too.
* :func:`fold` — folds the net by rolling a cube across it: which cube face each square
  becomes, or ``None`` when two squares land on the same face (not a net of a cube).
* :func:`opposite` — the square opposite a given one on the folded cube.
* :func:`render_net_svg` — deterministic, Inter only, print palette; a label sits in the
  middle of its square, well clear of the square's edges.

No FastAPI/Pydantic (ADR-0016) and no import of ``diagram``.
"""

from __future__ import annotations

from exam_engine import palette

_INK = palette.INK
_PAPER = palette.PAPER
_SHADE = palette.SHADE
_S = 40.0  # square edge, px
_PAD = 12.0
_MAX_CELL = 5

Cell = tuple[int, int]

# Cube faces by the direction they point while the cube sits on the first square:
# D(own), U(p), N (towards row - 1), S, E (towards col + 1), W.
_OPPOSITE = {"D": "U", "U": "D", "N": "S", "S": "N", "E": "W", "W": "E"}
# Rolling one square in a direction: the face that ends up underneath, and so on.
_ROLL = {
    (0, 1): {"D": "E", "E": "U", "U": "W", "W": "D", "N": "N", "S": "S"},
    (0, -1): {"D": "W", "W": "U", "U": "E", "E": "D", "N": "N", "S": "S"},
    (1, 0): {"D": "S", "S": "U", "U": "N", "N": "D", "E": "E", "W": "W"},
    (-1, 0): {"D": "N", "N": "U", "U": "S", "S": "D", "E": "E", "W": "W"},
}


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


def cells_of(spec: dict) -> list[Cell]:
    return [(f["row"], f["col"]) for f in spec["faces"]]


# ---------------------------------------------------------------------------
# Folding
# ---------------------------------------------------------------------------


def fold(cells: list[Cell]) -> dict[Cell, str] | None:
    """Roll a cube over the net from ``cells[0]``: the face that lies on each square is the
    face that square becomes. ``None`` if the squares are not joined or two of them would be
    the same face (the figure does not fold into a cube)."""
    if len(set(cells)) != len(cells):
        return None
    todo = set(cells)
    # orientation: which original face points each way (start: each face points its own way)
    start = {d: d for d in _OPPOSITE}
    seen: dict[Cell, dict[str, str]] = {cells[0]: start}
    queue = [cells[0]]
    while queue:
        cell = queue.pop(0)
        here = seen[cell]
        for (dr, dc), roll in _ROLL.items():
            nxt = (cell[0] + dr, cell[1] + dc)
            if nxt in todo and nxt not in seen:
                seen[nxt] = {d: here[roll[d]] for d in here}
                queue.append(nxt)
    if len(seen) != len(cells):
        return None
    faces = {cell: o["D"] for cell, o in seen.items()}
    return faces if len(set(faces.values())) == len(cells) == 6 else None


def opposite(cells: list[Cell], cell: Cell) -> Cell | None:
    """The square opposite ``cell`` once the net is folded (``None`` if it does not fold)."""
    faces = fold(cells)
    if faces is None:
        return None
    want = _OPPOSITE[faces[cell]]
    return next(c for c, f in faces.items() if f == want)


def normalise(cells: list[Cell]) -> list[Cell]:
    """The cells moved to the top-left corner (smallest row and column 0), sorted."""
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return sorted((r - r0, c - c0) for r, c in cells)


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _connected(cells: list[Cell]) -> bool:
    todo = set(cells)
    if not todo:
        return False
    stack = [next(iter(todo))]
    seen = set(stack)
    while stack:
        r, c = stack.pop()
        for nxt in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if nxt in todo and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen == todo


def check_net_consistency(spec: dict) -> dict[str, bool]:
    """Spec-only invariants; every value is a ``bool`` (``True`` = holds)."""
    raw = spec.get("faces")
    faces = [f for f in raw if isinstance(f, dict)] if isinstance(raw, list) else []
    in_range = len(faces) == 6 and all(
        _is_int(f.get("row")) and _is_int(f.get("col")) for f in faces
    )
    in_range = in_range and all(
        0 <= f["row"] <= _MAX_CELL and 0 <= f["col"] <= _MAX_CELL for f in faces
    )
    cells = [(f["row"], f["col"]) for f in faces] if in_range else []
    labels = [f.get("label") for f in faces if f.get("label") is not None]
    return {
        "six_squares": len(faces) == 6 and len(faces) == len(raw or []),
        "cells_in_range": in_range,
        "cells_distinct": in_range and len(set(cells)) == 6,
        "squares_joined": in_range and _connected(cells),
        "labels_short": all(isinstance(t, str) and 1 <= len(t.strip()) <= 2 for t in labels),
        "labels_unique": len(set(labels)) == len(labels),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_net_svg(spec: dict) -> str:
    faces = spec["faces"]
    title = spec.get("title")
    top = 30.0 if title else _PAD
    rows = max(f["row"] for f in faces) + 1
    cols = max(f["col"] for f in faces) + 1
    w = 2 * _PAD + cols * _S
    h = top + rows * _S + _PAD
    label = title or "A net of a cube"
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
    for f in faces:
        x, y = _PAD + f["col"] * _S, top + f["row"] * _S
        fill = _SHADE if f.get("shaded") else _PAPER
        out.append(
            f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(_S)}" height="{_n(_S)}" '
            f'fill="{fill}" stroke="{_INK}" stroke-width="1.4" />'
        )
    for f in faces:
        if f.get("label"):
            cx, cy = _PAD + (f["col"] + 0.5) * _S, top + (f["row"] + 0.5) * _S
            out.append(
                f'<text x="{_n(cx)}" y="{_n(cy + 5.5)}" text-anchor="middle" font-size="16" '
                f'font-weight="600" fill="{_INK}">{_esc(f["label"])}</text>'
            )
    out.append("</svg>")
    return "".join(out)
