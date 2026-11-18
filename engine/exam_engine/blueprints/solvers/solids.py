"""Solvers for the solids blueprints (EXA-147): stacks of cubes and nets of a cube.

Real P6 prelims ask about cube stacks (counting, completing, views) and nets in nearly every
paper. All four are 1- or 2-mark questions on no difficulty ladder.

* ``cubes_count``    — count the cubes in a drawn solid, the hidden ones under a visible top
  included (1 mark).
* ``cubes_complete`` — the least number of cubes to add, without moving any, to make the solid
  into a cuboid or a cube (2 marks).
* ``cubes_view``     — which picture is the solid's front or side view: picture options,
  so the blueprint asks multiple choice itself (1 mark, Booklet A).
* ``net_opposite``   — which face of a folded net is opposite a marked face: letter options
  (1 mark, Booklet A).

The figures are drawn from the same parameters the maths uses: a ``cube_stack`` heightmap or a
``net``. A heightmap is only used when its ``iso`` picture shows every stack's top
(:func:`cube_stack.readable`), so the picture fixes the count and no cube hides behind a taller
stack. ``solve`` counts layer by layer and folds nets by rolling a cube over them; the invariant
tests count stack by stack, march rays through the picture and fold nets with rotations.
"""

from __future__ import annotations

import random
from fractions import Fraction

from ...cube_stack import (
    cube_count,
    front_view,
    readable,
    side_view,
    top_view,
    visible_cubes,
)
from ...net import fold, normalise
from ...net import opposite as opposite_cell
from ..registry import register

LABELS = ("1", "2", "3", "4")
_MAX_H = 4


# ---------------------------------------------------------------- heightmaps


def _stepped(heights: list[list[int]]) -> bool:
    """Each column is no taller at the front than behind, the way textbook pictures step down
    towards the viewer. An iso picture cannot tell a stack one row nearer and one column to
    the right from one a cube higher, so a taller stack in front reads two ways; stepping
    down rules that out while the back stacks still hide cubes."""
    return all(
        front <= back
        for b, f in zip(heights, heights[1:], strict=False)
        for back, front in zip(b, f, strict=True)
    )


def _layers(heights: list[list[int]]) -> list[int]:
    """Cubes in each layer, bottom first."""
    tallest = max(max(row) for row in heights)
    return [sum(h > z for row in heights for h in row) for z in range(tallest)]


def _layer_text(layers: list[int]) -> str:
    names = ["bottom layer", "2nd layer", "3rd layer", "4th layer"]
    parts = [f"{names[i]} {n}" for i, n in enumerate(layers)]
    return "Count the cubes layer by layer: " + ", ".join(parts) + "."


def _sample_heights(
    rng: random.Random, rows: tuple[int, int], cols: tuple[int, int], top: int
) -> list[list[int]]:
    """A random heightmap: a stack on every cell (a gap makes the picture hard to read),
    stepped down towards the front, every top visible."""
    while True:
        r, c = rng.randint(*rows), rng.randint(*cols)
        heights = [[rng.randint(1, top) for _ in range(c)] for _ in range(r)]
        if _stepped(heights) and readable(heights):
            return heights


def _heights_ok(heights: list[list[int]]) -> bool:
    return (
        2 <= len(heights) <= 3
        and all(2 <= len(row) == len(heights[0]) <= 4 for row in heights)
        and all(1 <= h <= _MAX_H for row in heights for h in row)
        and _stepped(heights)
        and readable(heights)
    )


def _stack_spec(heights: list[list[int]], view: str = "iso", front: bool = False) -> dict:
    spec: dict = {"type": "cube_stack", "heights": [list(r) for r in heights], "view": view}
    if front:
        spec["show_front"] = True
    return spec


def _spread(
    slips: list[tuple[int, str]], answer: int, key: int
) -> list[tuple[int | Fraction, str]]:
    """``slips`` (best first) reordered so the first two lie both below, either side of, or
    both above ``answer``, by ``key``. Options print in ascending order and only the last wrong
    one is chosen to move the answer, so this keeps the answer's place from giving it away."""
    below = [s for s in slips if s[0] < answer]
    above = [s for s in slips if s[0] > answer]
    first = [below[:2], below[:1] + above[:1], above[:2]][key % 3]
    if len(first) < 2:
        first = below[:1] + above[:1]
    return [*first, *(s for s in slips if s not in first)]


# ---------------------------------------------------------------- count


class CubesCountSolver:
    """``heights`` — the heightmap (rows back to front, columns left to right)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            heights = _sample_heights(rng, (2, 3), (2, 3), 3)
            n = cube_count(heights)
            if 6 <= n <= 18 and visible_cubes(heights) < n:  # at least one hidden cube
                return {"heights": heights}

    def solve(self, params: dict) -> dict:
        layers = _layers(params["heights"])
        total = sum(layers)
        return {
            "answer": {"type": "integer", "value": total},
            "intermediates": {
                "step1": _layer_text(layers),
                "step2": f"Number of cubes = {' + '.join(map(str, layers))} = {total}.",
                "e2": "+".join(map(str, layers)),
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Counting slips, best first, some too few and some too many (the answer's place among
        the ascending options must not give it away)."""
        heights = params["heights"]
        n = cube_count(heights)
        hidden = n - visible_cubes(heights)
        rows, cols = len(heights), len(heights[0])
        tallest = max(max(r) for r in heights)
        slips = [
            (n - hidden, "counted only the cubes that can be seen"),
            (n + hidden, "counted the hidden cubes twice"),
            (rows * cols * tallest, "counted the whole cuboid around the solid"),
            (sum(1 for row in heights for h in row if h), "counted the top faces only"),
            (
                sum(front_view(heights)) + sum(side_view(heights)) + rows * cols,
                "added the squares seen from the front, the side and the top",
            ),
            (sum(front_view(heights)), "counted the squares seen from the front"),
        ]
        return _spread(slips, n, n + rows * cols)

    def validate(self, params: dict, solution: dict) -> dict:
        heights = params["heights"]
        checks = {
            "heights_ok": _heights_ok(heights),
            "a_cube_is_hidden": visible_cubes(heights) < cube_count(heights),
            "answer_verified": solution["answer"]["value"] == cube_count(heights),
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _stack_spec(params["heights"])


# ---------------------------------------------------------------- complete


def _target(heights: list[list[int]], shape: str) -> tuple[int, int, int]:
    """The smallest cuboid or cube that holds the solid without moving it: (long, wide, high)."""
    rows, cols, tallest = len(heights), len(heights[0]), max(max(r) for r in heights)
    if shape == "cube":
        side = max(rows, cols, tallest)
        return side, side, side
    return cols, rows, tallest


class CubesCompleteSolver:
    """``heights`` — the heightmap; ``shape`` — make a ``cuboid`` or a ``cube``."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            heights = _sample_heights(rng, (2, 3), (2, 4), 3)
            shape = rng.choice(["cuboid", "cube"])
            box = _target(heights, shape)
            gap = box[0] * box[1] * box[2] - cube_count(heights)
            if 4 <= gap <= 40 and max(max(r) for r in heights) >= 2:
                return {"heights": heights, "shape": shape}

    def solve(self, params: dict) -> dict:
        heights, shape = params["heights"], params["shape"]
        layers = _layers(heights)
        have = sum(layers)
        a, b, c = _target(heights, shape)
        whole = a * b * c
        if shape == "cube":
            why = (
                f"The smallest cube that holds the solid has edges of {a} cubes "
                f"(the solid's longest side). It has {a} × {a} × {a} = {whole} cubes."
            )
        else:
            why = (
                f"The smallest cuboid that holds the solid is {a} cubes long, {b} cubes wide "
                f"and {c} cubes high. It has {a} × {b} × {c} = {whole} cubes."
            )
        return {
            "answer": {"type": "integer", "value": whole - have},
            "intermediates": {
                "step1": f"{_layer_text(layers)} The solid has {have} cubes.",
                "e1": "+".join(map(str, layers)),
                "step2": why,
                "e2": f"{a}*{b}*{c}",
                "step3": f"Cubes to add = {whole} − {have} = {whole - have}.",
                "e3": f"{whole}-{have}",
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        heights, shape = params["heights"], params["shape"]
        have = cube_count(heights)
        a, b, c = _target(heights, shape)
        other = "cube" if shape == "cuboid" else "cuboid"
        oa, ob, oc = _target(heights, other)
        hidden = have - visible_cubes(heights)
        front_gaps = sum(c - h for h in heights[-1])  # the gaps on the front row's tops only
        slips = [
            (a * b * c - have + hidden, "did not count the hidden cubes"),
            (a * b * c - have - hidden, "counted the hidden cubes twice"),
            (a * b * c, f"gave the number of cubes in the whole {shape}"),
            (oa * ob * oc - have, f"made the smallest {other} instead of a {shape}"),
            (a * b * (c - 1) - have, f"made the {shape} one layer too low"),
            (front_gaps, "filled only the gaps in the front row"),
            (have, "gave the number of cubes in the solid"),
        ]
        return _spread(slips, a * b * c - have, have + len(heights[0]))

    def validate(self, params: dict, solution: dict) -> dict:
        heights, shape = params["heights"], params["shape"]
        a, b, c = _target(heights, shape)
        checks = {
            "heights_ok": _heights_ok(heights),
            "answer_verified": solution["answer"]["value"] + cube_count(heights) == a * b * c,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _stack_spec(params["heights"])


# ---------------------------------------------------------------- views


def picture(spec: dict) -> frozenset[tuple[int, int]]:
    """The unit squares a ``front`` / ``side`` / ``top`` option draws, as (x, y) with y up."""
    heights, view = spec["heights"], spec["view"]
    if view == "top":
        rows = len(heights)
        return frozenset(
            (c, rows - 1 - r)
            for r, row in enumerate(top_view(heights))
            for c, on in enumerate(row)
            if on
        )
    profile = front_view(heights) if view == "front" else side_view(heights)
    return frozenset((x, y) for x, h in enumerate(profile) for y in range(h))


def _wrong_views(heights: list[list[int]], view: str) -> list[tuple[dict, str]]:
    """Wrong pictures a pupil picks, best first, each with the reason."""
    mirror = [row[::-1] for row in heights]
    flipped = heights[::-1]
    if view == "front":
        return [
            (_stack_spec(heights, "side"), "the view from the right side"),
            (_stack_spec(mirror, "front"), "the front view flipped left to right"),
            (_stack_spec([heights[-1]], "front"), "only the front row of stacks"),
            (_stack_spec(heights, "top"), "the view from the top"),
        ]
    return [
        (_stack_spec(heights, "front"), "the view from the front"),
        (_stack_spec(flipped, "side"), "the view from the left side"),
        (_stack_spec([[r[-1]] for r in heights], "side"), "only the right-hand column"),
        (_stack_spec(heights, "top"), "the view from the top"),
    ]


def _plain(heights: list[list[int]], view: str) -> bool:
    """The view is a plain rectangle (every stack seen equally tall): too easy to ask."""
    profile = front_view(heights) if view == "front" else side_view(heights)
    return len(set(profile)) == 1


_VIEW_WORDS = {"front": "the front", "side": "the right side"}


def view_options(heights: list[list[int]], view: str) -> list[tuple[dict, str | None]]:
    """The correct picture, then the first three wrong ones that look different from it and
    from each other (``reason`` None for the correct one)."""
    out: list[tuple[dict, str | None]] = [(_stack_spec(heights, view), None)]
    seen = {picture(out[0][0])}
    for spec, why in _wrong_views(heights, view):
        if picture(spec) not in seen and len(out) < 4:
            seen.add(picture(spec))
            out.append((spec, why))
    return out


class CubesViewSolver:
    """``heights`` — the heightmap; ``view`` — front or side (from the right; with a stack on
    every cell the top view is a plain rectangle, so it is only ever a wrong option);
    ``arrangement`` — where each option prints: ``arrangement[i]`` is the position of option
    ``i`` of :func:`view_options` (0 is the correct one)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            heights = _sample_heights(rng, (2, 2), (2, 3), 3)
            view = rng.choice(["front", "side"])
            if len(view_options(heights, view)) == 4 and not _plain(heights, view):
                arrangement = [0, 1, 2, 3]
                rng.shuffle(arrangement)
                return {"heights": heights, "view": view, "arrangement": arrangement}

    def solve(self, params: dict) -> dict:
        heights, view, where = params["heights"], params["view"], params["arrangement"]
        chosen = view_options(heights, view)
        slots: list[tuple[dict, str | None]] = [chosen[0]] * 4
        for i, item in enumerate(chosen):
            slots[where[i]] = item
        options = [
            {"label": lab, "text": None, "diagram": spec}
            for lab, (spec, _) in zip(LABELS, slots, strict=True)
        ]
        correct = LABELS[where[0]]
        profile = front_view(heights) if view == "front" else side_view(heights)
        across = "columns, left to right," if view == "front" else "rows, front row on the left,"
        heights_text = ", ".join(map(str, profile[:-1])) + f" and {profile[-1]}"
        seen = f"the {across} show their tallest stacks: {heights_text} squares high"
        wrong = "; ".join(f"({LABELS[where[i]]}) is {chosen[i][1]}" for i in range(1, 4))
        return {
            "answer": {"type": "choice", "options": options, "correct": correct},
            "intermediates": {
                "view_words": _VIEW_WORDS[view],
                "step1": f"Seen from {_VIEW_WORDS[view]}, {seen}. This is option ({correct}).",
                "step2": f"The others: {wrong}.",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        heights, view, where = params["heights"], params["view"], params["arrangement"]
        chosen = view_options(heights, view)
        answer = solution["answer"]
        right = next(o for o in answer["options"] if o["label"] == answer["correct"])
        checks = {
            "heights_ok": _heights_ok(heights),
            "arrangement_is_a_permutation": sorted(where) == [0, 1, 2, 3],
            "view_not_a_plain_rectangle": not _plain(heights, view),
            "four_different_pictures": len({picture(o["diagram"]) for o in answer["options"]})
            == len(chosen)
            == 4,
            "answer_verified": picture(right["diagram"]) == picture(_stack_spec(heights, view)),
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _stack_spec(params["heights"], front=True)


# ---------------------------------------------------------------- nets

_MAX_NET = (4, 5)  # at most 4 rows by 5 columns (some net fits 3 x 4 or 2 x 5 either way up)


def _grow_net(rng: random.Random) -> list[tuple[int, int]]:
    while True:
        cells = {(0, 0)}
        while len(cells) < 6:
            r, c = rng.choice(sorted(cells))
            dr, dc = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            cells.add((r + dr, c + dc))
        out = normalise(list(cells))
        rows = 1 + max(r for r, _ in out)
        cols = 1 + max(c for _, c in out)
        if fold(out) is not None and rows <= _MAX_NET[0] and cols <= _MAX_NET[1]:
            return out


def _net_neighbours(cells: list[tuple[int, int]], cell: tuple[int, int]) -> set:
    r, c = cell
    return {(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)} & set(cells)


def net_choices(params: dict) -> tuple[str, list[str]]:
    """The answer letter and the three wrong letters offered: faces next to the marked one on
    the cube, the ones that do not touch it in the net first (they look far away)."""
    cells = [(r, c) for r, c in params["cells"]]
    letters = params["letters"]
    asked = cells[params["asked"]]
    answer_cell = opposite_cell(cells, asked)
    if answer_cell is None:
        raise ValueError("the six squares do not fold into a cube")
    answer = letters[cells.index(answer_cell)]
    near = _net_neighbours(cells, asked)
    wrong = sorted(
        (i for i, c in enumerate(cells) if c not in (asked, answer_cell)),
        key=lambda i: (cells[i] in near, letters[i]),
    )
    return answer, [letters[i] for i in wrong[:3]]


def net_spec(params: dict) -> dict:
    faces = []
    for i, (r, c) in enumerate(params["cells"]):
        shaded = params["marked"] == "shaded" and i == params["asked"]
        faces.append(
            {"row": r, "col": c, "label": None if shaded else params["letters"][i]}
            | ({"shaded": True} if shaded else {})
        )
    return {"type": "net", "faces": faces}


class NetOppositeSolver:
    """``cells`` — the six squares (row, col); ``letters`` — their letters, in cell order;
    ``asked`` — the marked square; ``marked`` — ``letter`` (by its letter) or ``shaded``."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        cells = _grow_net(rng)
        letters = list("ABCDEF")
        rng.shuffle(letters)
        return {
            "cells": [list(c) for c in cells],
            "letters": "".join(letters),
            "asked": rng.randrange(6),
            "marked": rng.choice(["letter", "shaded"]),
        }

    def solve(self, params: dict) -> dict:
        answer, wrong = net_choices(params)
        texts = sorted([answer, *wrong])
        options = [{"label": lab, "text": t} for lab, t in zip(LABELS, texts, strict=True)]
        cells = [tuple(c) for c in params["cells"]]
        asked = cells[params["asked"]]
        mark = (
            "the shaded face"
            if params["marked"] == "shaded"
            else f"face {params['letters'][params['asked']]}"
        )
        others = sorted(
            params["letters"][i]
            for i, c in enumerate(cells)
            if c != asked and params["letters"][i] != answer
        )
        return {
            "answer": {
                "type": "choice",
                "options": options,
                "correct": LABELS[texts.index(answer)],
            },
            "intermediates": {
                "mark": mark,
                "step1": (
                    f"When the net is folded, faces {', '.join(others[:-1])} and {others[-1]} "
                    f"each share an edge with {mark}."
                ),
                "step2": f"The face left over, {answer}, is opposite {mark}.",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        cells = [tuple(c) for c in params["cells"]]
        letters = params["letters"]
        answer = solution["answer"]
        right = next(o["text"] for o in answer["options"] if o["label"] == answer["correct"])
        faces = fold(cells) if len(cells) == 6 else None
        asked = cells[params["asked"]]
        opposite = {"D": "U", "U": "D", "N": "S", "S": "N", "E": "W", "W": "E"}
        checks = {
            "folds_into_a_cube": faces is not None,
            "fits_the_page": normalise(cells) == sorted(cells)
            and max(r for r, _ in cells) < _MAX_NET[0]
            and max(c for _, c in cells) < _MAX_NET[1],
            "letters_a_to_f": sorted(letters) == list("ABCDEF"),
            "answer_verified": faces is not None
            and faces[cells[letters.index(right)]] == opposite[faces[asked]],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return net_spec(params)


register("cubes_count", CubesCountSolver())
register("cubes_complete", CubesCompleteSolver())
register("cubes_view", CubesViewSolver())
register("net_opposite", NetOppositeSolver())
