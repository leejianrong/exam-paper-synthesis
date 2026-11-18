"""Independent correctness authority for the solids blueprints (EXA-147).

Every check reads the *drawn figure* (the stem's ``cube_stack`` or ``net`` spec, and for
picture options the rendered SVG) and the printed question, never the parameters:

* ``cubes_count``    — the cubes are counted stack by stack (``solve`` counts layer by layer),
  and rays marched through the picture in small steps show that every stack's top can be seen
  (so the picture fixes the count) and that some cube is hidden.
* ``cubes_complete`` — the cuboid or cube is built from the cubes' own coordinates and its
  empty unit places are counted one by one (``solve`` subtracts two products).
* ``cubes_view``     — the view is cast from the cubes (a square wherever a cube lies along the
  line of sight) and compared with the squares drawn in each option's SVG: exactly one option
  matches, and it is the key's.
* ``net_opposite``   — the net is folded with 90° rotations about each hinge and the face
  centres compared in space (``solve`` rolls a cube over the net instead).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from fractions import Fraction

import pytest
from exam_engine import generate
from exam_engine.diagram import render_svg

SWEEP = range(1, 301)

Cube = tuple[int, int, int]  # (col, row, level)


def _cubes(heights: list[list[int]]) -> set[Cube]:
    return {(c, r, z) for r, row in enumerate(heights) for c, h in enumerate(row) for z in range(h)}


def _behind(cubes: set[Cube], p: tuple[float, float, float]) -> bool:
    """March from ``p`` towards the viewer (front-right above: +col, +row, +level)."""
    k = 0.013
    while k < 12:
        x, y, z = (v + k for v in p)
        if (int(x // 1), int(y // 1), int(z // 1)) in cubes:
            return True
        k += 0.013
    return False


def _stem(obj: dict) -> dict:
    return obj["question"]["parts"][0]["diagram"]


def _text(obj: dict) -> str:
    return obj["question"]["parts"][0]["text"]


# ---------------------------------------------------------------- cubes_count


def _check_picture_fixes_heights(heights: list[list[int]]) -> None:
    cubes = _cubes(heights)
    for r, row in enumerate(heights):
        for c, h in enumerate(row):
            assert h >= 1, "a gap in the solid"
            assert not _behind(cubes, (c + 0.5, r + 0.5, h)), f"stack {r},{c} top is hidden"


def check_count(obj: dict) -> None:
    heights = _stem(obj)["heights"]
    _check_picture_fixes_heights(heights)
    by_stacks = sum(sum(row) for row in heights)
    assert obj["question"]["parts"][0]["answer"]["value"] == by_stacks
    cubes = _cubes(heights)

    def seen(c: int, r: int, z: int) -> bool:
        faces = []
        if (c, r, z + 1) not in cubes:
            faces.append((c + 0.5, r + 0.5, z + 1))
        if (c, r + 1, z) not in cubes:
            faces.append((c + 0.5, r + 1, z + 0.5))
        if (c + 1, r, z) not in cubes:
            faces.append((c + 1, r + 0.5, z + 0.5))
        return any(not _behind(cubes, f) for f in faces)

    assert any(not seen(*cube) for cube in cubes), "no hidden cube to count"


# ---------------------------------------------------------------- cubes_complete


def check_complete(obj: dict) -> None:
    heights = _stem(obj)["heights"]
    _check_picture_fixes_heights(heights)
    cubes = _cubes(heights)
    dims = [1 + max(cube[i] for cube in cubes) for i in range(3)]
    shape = re.search(r"into a (cuboid|cube)\?$", _text(obj))[1]
    if shape == "cube":
        dims = [max(dims)] * 3
    empty = sum(
        (x, y, z) not in cubes
        for x in range(dims[0])
        for y in range(dims[1])
        for z in range(dims[2])
    )
    assert obj["question"]["parts"][0]["answer"]["value"] == empty


# ---------------------------------------------------------------- cubes_view


def _drawn_squares(svg: str) -> frozenset[tuple[int, int]]:
    """The unit squares an option's SVG draws, as (x, y) with y counted up from the bottom."""
    rects = [
        tuple(float(v) for v in m)
        for m in re.findall(
            r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg
        )
    ]
    size = rects[0][2]
    left, bottom = min(r[0] for r in rects), max(r[1] for r in rects)
    return frozenset((round((x - left) / size), round((bottom - y) / size)) for x, y, _, _ in rects)


def _cast(cubes: set[Cube], view: str, rows: int) -> frozenset[tuple[int, int]]:
    if view == "front":  # looking along -row: across = column, up = level
        return frozenset((c, z) for c, _, z in cubes)
    # from the right, looking along -col: the front row (largest row) is on the left
    return frozenset((rows - 1 - r, z) for _, r, z in cubes)


def check_view(obj: dict) -> None:
    stem = _stem(obj)
    assert stem["view"] == "iso" and stem["show_front"] is True
    assert ">Front</text>" in render_svg(stem)
    _check_picture_fixes_heights(stem["heights"])
    view = "front" if _text(obj).endswith("from the front?") else "side"
    assert view == "front" or _text(obj).endswith("from the right side?")
    want = _cast(_cubes(stem["heights"]), view, len(stem["heights"]))
    answer = obj["question"]["parts"][0]["answer"]
    drawn = {o["label"]: _drawn_squares(render_svg(o["diagram"])) for o in answer["options"]}
    assert len(set(drawn.values())) == 4, "two options look the same"
    assert [label for label, sq in drawn.items() if sq == want] == [answer["correct"]]


# ---------------------------------------------------------------- net_opposite

Point = tuple[Fraction, Fraction, Fraction]
Move = Callable[[Point], Point]


def _hinge(parent: tuple[int, int], child: tuple[int, int]) -> Move:
    """Turn the child square up (towards +z) by 90° about the edge it shares with its parent,
    in the flat net's coordinates (x = col, y = row)."""
    (pr, pc), (cr, cc) = parent, child
    if cr == pr:  # an upright edge at x0
        x0 = Fraction(max(pc, cc))
        if cc > pc:
            return lambda p: (x0 - p[2], p[1], p[0] - x0)
        return lambda p: (x0 + p[2], p[1], x0 - p[0])
    y0 = Fraction(max(pr, cr))
    if cr > pr:
        return lambda p: (p[0], y0 - p[2], p[1] - y0)
    return lambda p: (p[0], y0 + p[2], y0 - p[1])


def fold_centres(cells: list[tuple[int, int]]) -> dict[tuple[int, int], Point]:
    """Each square's centre once every hinge is folded up by 90°: a child's placement is its
    parent's placement after the child's own hinge turn."""
    place: dict[tuple[int, int], Move] = {cells[0]: lambda p: p}
    todo = [cells[0]]
    while todo:
        cell = todo.pop()
        for nxt in ((cell[0] + 1, cell[1]), (cell[0] - 1, cell[1]), (cell[0], cell[1] + 1),
                    (cell[0], cell[1] - 1)):  # fmt: skip
            if nxt in cells and nxt not in place:
                outer, turn = place[cell], _hinge(cell, nxt)
                place[nxt] = lambda p, outer=outer, turn=turn: outer(turn(p))
                todo.append(nxt)
    half = Fraction(1, 2)
    return {(r, c): place[(r, c)]((c + half, r + half, Fraction(0))) for r, c in cells}


def _d2(a: Point, b: Point) -> Fraction:
    return sum((x - y) ** 2 for x, y in zip(a, b, strict=True))


def check_net(obj: dict) -> None:
    faces = _stem(obj)["faces"]
    cells = [(f["row"], f["col"]) for f in faces]
    centres = fold_centres(cells)
    assert len(set(centres.values())) == 6, "two squares fold onto the same face"
    m = re.search(r"opposite (?:face ([A-F])|the shaded face)\?$", _text(obj))
    asked = next(
        (f["row"], f["col"]) for f in faces if (f.get("label") == m[1] if m[1] else f.get("shaded"))
    )
    label = {(f["row"], f["col"]): f.get("label") for f in faces}
    gaps = {cell: _d2(centres[asked], centres[cell]) for cell in cells if cell != asked}
    assert sorted(gaps.values()) == [Fraction(1, 2)] * 4 + [1]  # a cube: 4 next to it, 1 across
    across = label[next(c for c, d in gaps.items() if d == 1)]
    answer = obj["question"]["parts"][0]["answer"]
    texts = {o["label"]: o["text"] for o in answer["options"]}
    assert texts[answer["correct"]] == across
    beside = {label[c] for c, d in gaps.items() if d != 1}
    assert {t for k, t in texts.items() if k != answer["correct"]} <= beside


CHECKS = {
    "cubes_count": check_count,
    "cubes_complete": check_complete,
    "cubes_view": check_view,
    "net_opposite": check_net,
}


@pytest.mark.parametrize("code", CHECKS)
def test_seed_sweep(code):
    for seed in SWEEP:
        CHECKS[code](generate(code, seed))


def test_the_hinge_fold_knows_a_net_from_a_non_net():
    """The test's own folding, checked on figures whose answer is known by hand."""
    cross = [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (3, 1)]  # the Latin cross
    centres = fold_centres(cross)
    assert len(set(centres.values())) == 6
    assert _d2(centres[(0, 1)], centres[(2, 1)]) == 1  # two apart in a column: opposite
    assert _d2(centres[(1, 0)], centres[(1, 2)]) == 1
    row_of_five = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 0)]
    assert len(set(fold_centres(row_of_five).values())) < 6  # 1st and 5th squares meet
