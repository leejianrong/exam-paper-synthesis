"""EXA-144 — independent invariants for the square-grid blueprints.

Each answer is re-derived from the **drawn figure** (the ``grid`` spec the paper prints) and
the printed question text, a different way from the solver:

* ``grid_area``: the shoelace formula over the drawn polygon's corners (the solver counts
  squares cell by cell).
* ``grid_lines``: integer vector tests, cross product 0 for parallel and dot product 0 for
  perpendicular, over every lettered point (the solver builds the answer by stepping along
  or across AB).
* ``grid_compass``: the bearing of every place from O by ``atan2`` in degrees, against the
  bearing the question's words give (the solver counts steps round an 8-point list).
* ``grid_symmetry``: reflect the shaded squares plus each lettered square in the drawn dashed
  line and keep the one that maps the figure onto itself (the solver looks for the shaded
  square without a partner).

In every case exactly one option must pass, and it must be the option marked correct.
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

import pytest
from exam_engine import generate

SEEDS = range(1, 301)


def _part(obj: dict) -> dict:
    return obj["question"]["parts"][0]


def _correct_text(answer: dict) -> str:
    return next(o["text"] for o in answer["options"] if o["label"] == answer["correct"])


def _points(figure: dict) -> dict[str, tuple[int, int]]:
    return {p["label"]: (p["x"], p["y"]) for p in figure["points"]}


# ---------------------------------------------------------------- area


def shoelace(vertices: list[list[int]]) -> Fraction:
    n = len(vertices)
    twice = sum(
        vertices[i][0] * vertices[(i + 1) % n][1] - vertices[(i + 1) % n][0] * vertices[i][1]
        for i in range(n)
    )
    return Fraction(abs(twice), 2)


@pytest.mark.parametrize("seed", SEEDS)
def test_area_is_the_shoelace_area_of_the_drawn_figure(seed):
    obj = generate("grid_area", seed)
    part = _part(obj)
    (polygon,) = part["diagram"]["polygons"]
    vertices = polygon["vertices"]
    # every side runs along a grid line or corner to corner across squares, so each square is
    # whole or half and counting squares is the method the question expects
    n = len(vertices)
    for i in range(n):
        dx = vertices[(i + 1) % n][0] - vertices[i][0]
        dy = vertices[(i + 1) % n][1] - vertices[i][1]
        assert dx == 0 or dy == 0 or abs(dx) == abs(dy), (seed, vertices)
    assert part["answer"]["unit"] == "cm^2"
    assert Fraction(str(part["answer"]["value"])) == shoelace(vertices), seed
    assert "1-cm squares" in part["text"]


# ---------------------------------------------------------------- lines


@pytest.mark.parametrize("seed", SEEDS)
def test_lines_exactly_one_point_makes_the_asked_line(seed):
    part = _part(generate("grid_lines", seed))
    ask = re.search(r"gives a line (parallel|perpendicular) to AB", part["text"])[1]
    pts = _points(part["diagram"])
    (seg,) = part["diagram"]["segments"]
    a, b, c = pts["A"], pts["B"], pts["C"]
    assert {tuple(seg["from"]), tuple(seg["to"])} == {a, b}
    ab = (b[0] - a[0], b[1] - a[1])
    fits = []
    for letter in "PQRS":
        v = (pts[letter][0] - c[0], pts[letter][1] - c[1])
        cross, dot = ab[0] * v[1] - ab[1] * v[0], ab[0] * v[0] + ab[1] * v[1]
        if (cross == 0) if ask == "parallel" else (dot == 0):
            fits.append(letter)
    assert fits == [_correct_text(part["answer"])], (seed, ask, pts)


# ---------------------------------------------------------------- compass

_BEARING = {
    "north": 0,
    "north-east": 45,
    "east": 90,
    "south-east": 135,
    "south": 180,
    "south-west": 225,
    "west": 270,
    "north-west": 315,
}


def asked_bearing(text: str) -> int:
    which = re.search(r"Which place is ([a-z-]+) of O\?", text)
    if which:
        return _BEARING[which[1]]
    m = re.search(r"facing ([a-z-]+)\. (?:He|She) turns (\d+)° (clockwise|anticlockwise)", text)
    assert m, text
    turn = int(m[2]) if m[3] == "clockwise" else -int(m[2])
    return (_BEARING[m[1]] + turn) % 360


@pytest.mark.parametrize("seed", SEEDS)
def test_compass_exactly_one_place_lies_on_the_asked_bearing(seed):
    part = _part(generate("grid_compass", seed))
    figure = part["diagram"]
    assert figure["compass"] is True  # north is up the page
    pts = _points(figure)
    o = pts["O"]
    target = asked_bearing(part["text"])
    fits = []
    for letter in "ABCD":
        dx, dy = pts[letter][0] - o[0], pts[letter][1] - o[1]
        bearing = math.degrees(math.atan2(dx, -dy)) % 360  # y grows down the page
        if math.isclose(bearing, target, abs_tol=1e-9) or math.isclose(
            bearing, target + 360, abs_tol=1e-9
        ):
            fits.append(letter)
    assert fits == [_correct_text(part["answer"])], (seed, part["text"], pts)


# ---------------------------------------------------------------- symmetry


@pytest.mark.parametrize("seed", SEEDS)
def test_symmetry_exactly_one_square_completes_the_mirror_image(seed):
    part = _part(generate("grid_symmetry", seed))
    figure = part["diagram"]
    (line,) = figure["segments"]
    assert line["dashed"] is True
    (x1, y1), (x2, y2) = line["from"], line["to"]

    if x1 == x2:  # vertical line x = x1: column c reflects to 2 * x1 - 1 - c

        def mirror(cell: tuple[int, int]) -> tuple[int, int]:
            return (2 * x1 - 1 - cell[0], cell[1])
    else:
        assert y1 == y2

        def mirror(cell: tuple[int, int]) -> tuple[int, int]:
            return (cell[0], 2 * y1 - 1 - cell[1])

    shaded = {(c["col"], c["row"]) for c in figure["cells"] if c["shaded"]}
    lettered = {c["label"]: (c["col"], c["row"]) for c in figure["cells"] if c.get("label")}
    assert sorted(lettered) == list("ABCD")
    assert {mirror(c) for c in shaded} != shaded  # not symmetric yet
    fits = [
        letter
        for letter, cell in sorted(lettered.items())
        if {mirror(c) for c in shaded | {cell}} == shaded | {cell}
    ]
    assert fits == [_correct_text(part["answer"])], seed
