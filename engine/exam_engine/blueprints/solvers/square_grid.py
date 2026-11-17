"""Solvers for the square-grid blueprints (EXA-144), drawn on the ``grid`` diagram.

Real P5/P6 prelims set about 13 square-grid questions a year group (about 3 an exam set). These
four are the ones whose answer is a number or a choice; drawing answers (shade the squares,
complete the figure, draw the line) are not built.

* ``grid_area``      — the area of a shaded figure with 45° cuts, by counting whole and half
  squares (2 marks).
* ``grid_lines``     — which point, joined to C, makes a line parallel or perpendicular to AB
  (1 mark, letter options: the blueprint asks multiple choice itself).
* ``grid_compass``   — which place lies in a direction from O, or which place someone faces
  after a turn (1 mark, letter options).
* ``grid_symmetry``  — which square to shade so the figure is symmetric about the dashed line
  (1 mark, letter options).

Every option letter is drawn at random from four, and options print in letter order, so the
answer's place among (1)–(4) follows the seed. The figure is built from the same parameters the
maths uses; the invariant tests re-derive each answer from the drawn figure a different way.
"""

from __future__ import annotations

import random
from fractions import Fraction
from math import gcd

from ...grid import is_simple
from ..registry import register

LABELS = ("1", "2", "3", "4")

DIRECTIONS = (
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
)
# one grid step in each direction, x right and y down (north is up the page)
_STEP = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def _pt(v: list[int]) -> tuple[int, int]:
    return int(v[0]), int(v[1])


def _choice(letters: str, answer_index: int = 0) -> tuple[list[dict], str]:
    """Letter options in alphabetical order; ``letters[answer_index]`` is the correct one."""
    texts = sorted(letters)
    options = [{"label": lab, "text": t} for lab, t in zip(LABELS, texts, strict=True)]
    return options, LABELS[texts.index(letters[answer_index])]


def _shuffled(rng: random.Random, pool: str) -> str:
    out = list(pool)
    rng.shuffle(out)
    return "".join(out)


def _others(letters: str, reasons: list[str]) -> str:
    """ "Q is ...; R is ..." for the wrong options (``letters[1:]``), in letter order."""
    pairs = sorted(zip(letters[1:], reasons, strict=True))
    return "; ".join(f"{letter} {why}" for letter, why in pairs)


# ---------------------------------------------------------------- area


def _quarters(vertices: list[tuple[int, int]], col: int, row: int) -> int:
    """How many of the cell's four quarter triangles (cut by both diagonals) lie inside the
    figure. A side of the figure runs along grid lines or corner to corner across squares,
    so each quarter is wholly in or out: test a point inside each one."""
    probes = ((0.5, 0.2), (0.8, 0.5), (0.5, 0.8), (0.2, 0.5))
    return sum(_inside(vertices, col + dx, row + dy) for dx, dy in probes)


def _inside(vertices: list[tuple[int, int]], x: float, y: float) -> bool:
    """Even-odd ray cast to the right (the probe is never on a side)."""
    hit = False
    n = len(vertices)
    for i in range(n):
        (x1, y1), (x2, y2) = vertices[i], vertices[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def count_squares(vertices: list[tuple[int, int]]) -> tuple[int, int, int]:
    """``(whole, half, odd)`` squares of the figure; ``odd`` counts cells cut any other way."""
    xs = [x for x, _ in vertices]
    ys = [y for _, y in vertices]
    whole = half = odd = 0
    for col in range(min(xs), max(xs)):
        for row in range(min(ys), max(ys)):
            q = _quarters(vertices, col, row)
            whole += q == 4
            half += q == 2
            odd += q in (1, 3)
    return whole, half, odd


def _cut(vertices: list[tuple[int, int]], i: int, k: int) -> list[tuple[int, int]]:
    """Cut corner ``i`` off along a 45° line, ``k`` squares back along both sides."""
    n = len(vertices)
    p, v, q = vertices[i - 1], vertices[i], vertices[(i + 1) % n]

    def toward(a: tuple[int, int]) -> tuple[int, int]:
        dx, dy = a[0] - v[0], a[1] - v[1]
        return v[0] + k * (dx > 0) - k * (dx < 0), v[1] + k * (dy > 0) - k * (dy < 0)

    return [*vertices[:i], toward(p), toward(q), *vertices[i + 1 :]]


def _base_shape(rng: random.Random) -> list[tuple[int, int]]:
    """A rectangle or an L-shape with corners on grid points, clockwise on the page."""
    w, h = rng.randint(4, 6), rng.randint(3, 5)
    if rng.random() < 0.5:
        return [(0, 0), (w, 0), (w, h), (0, h)]
    nw, nh = rng.randint(1, w - 3), rng.randint(1, h - 2)  # the notch taken from top-right
    return [(0, 0), (w - nw, 0), (w - nw, nh), (w, nh), (w, h), (0, h)]


def _convex(vertices: list[tuple[int, int]], i: int) -> bool:
    (px, py), (vx, vy), (qx, qy) = vertices[i - 1], vertices[i], vertices[(i + 1) % len(vertices)]
    return (vx - px) * (qy - vy) - (vy - py) * (qx - vx) > 0


def _side(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class GridAreaSolver:
    """``vertices`` — the figure's corners on grid points, in order (1 square = 1 cm)."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            shape = _base_shape(rng)
            corners = [i for i in range(len(shape)) if _convex(shape, i)]
            picked = sorted(rng.sample(corners, rng.randint(2, 3)), reverse=True)
            for i in picked:  # from the last, so earlier indices stay put
                shape = _cut(shape, i, rng.choice([1, 1, 2]))
            n = len(shape)
            sides_ok = all(_side(shape[i], shape[(i + 1) % n]) >= 1 for i in range(n))
            if sides_ok and is_simple(shape):
                shape = [(x + 1, y + 1) for x, y in shape]  # one empty square all round
                return {"vertices": [list(v) for v in shape]}

    def solve(self, params: dict) -> dict:
        vertices = [_pt(v) for v in params["vertices"]]
        whole, half, _ = count_squares(vertices)
        area = Fraction(2 * whole + half, 2)
        value: int | float = int(area) if area.denominator == 1 else float(area)
        halves = Fraction(half, 2)
        halves_text = str(int(halves)) if halves.denominator == 1 else f"{float(halves)}"
        return {
            "answer": {"type": "quantity", "value": value, "unit": "cm^2"},
            "intermediates": {
                "step1": f"Count the whole squares: {whole}.",
                "step2": (
                    f"Count the half squares: {half}. Two halves make one square, so they make "
                    f"{half} ÷ 2 = {halves_text} squares."
                ),
                "step3": f"Area = {whole} + {halves_text} = {value} cm².",
                "e3": f"{whole}+{half}/2",
            },
        }

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Counting slips, some too small and some too big, best first."""
        vertices = [_pt(v) for v in params["vertices"]]
        whole, half, _ = count_squares(vertices)
        area = Fraction(2 * whole + half, 2)
        xs, ys = [x for x, _ in vertices], [y for _, y in vertices]
        box = (max(xs) - min(xs)) * (max(ys) - min(ys))
        slips: list[tuple[int | Fraction, str]] = [
            (whole, "counted only the whole squares"),
            (whole + half, "counted each half square as a whole one"),
            (box, "counted every square of the rectangle around the figure"),
            (box - area, "found the unshaded part of the rectangle around the figure"),
            (Fraction(half, 2), "counted only the half squares"),
            (area - 1, "missed one square"),
            (area + 1, "counted one square twice"),
        ]
        # a slip far from the answer would not tempt anyone (a sliver of unshaded rectangle)
        slips = [s for s in slips if area / 2 <= s[0] <= 2 * area]
        below = [s for s in slips if s[0] < area]
        above = [s for s in slips if s[0] > area]
        # Options print in ascending order, so the first two slips lie both below, either side
        # of, or both above the answer, by the figure: its place among them follows the seed.
        key = sum(x + y for x, y in vertices)
        first = [below[:2], below[:1] + above[:1], above[:2]][key % 3]
        if len(first) < 2:
            first = below[:1] + above[:1]
        return [*first, *(s for s in slips if s not in first)]

    def validate(self, params: dict, solution: dict) -> dict:
        vertices = [_pt(v) for v in params["vertices"]]
        whole, half, odd = count_squares(vertices)
        xs, ys = [x for x, _ in vertices], [y for _, y in vertices]
        checks = {
            "simple_figure": is_simple(vertices),
            "every_square_whole_or_half": odd == 0,
            "has_half_squares": half >= 2,
            "fits_the_grid": min(xs) >= 1 and min(ys) >= 1 and max(xs) <= 8 and max(ys) <= 7,
            "answer_verified": Fraction(str(solution["answer"]["value"]))
            == Fraction(2 * whole + half, 2),
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        vertices = [_pt(v) for v in params["vertices"]]
        return {
            "type": "grid",
            "cols": max(x for x, _ in vertices) + 1,
            "rows": max(y for _, y in vertices) + 1,
            "polygons": [{"vertices": [list(v) for v in vertices], "shaded": True}],
        }


# ---------------------------------------------------------------- parallel / perpendicular

_LINE_COLS, _LINE_ROWS = 10, 7
_SLOPES = ((1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2), (1, 1))


def _in_grid(p: tuple[int, int], cols: int, rows: int) -> bool:
    return 0 <= p[0] <= cols and 0 <= p[1] <= rows


def _walk(dx: int, dy: int) -> str:
    """How a line moves on the grid, left to right: "2 squares right for every 1 square up"."""
    g = gcd(dx, dy) or 1
    dx, dy = dx // g, dy // g
    if dx < 0 or (dx == 0 and dy > 0):
        dx, dy = -dx, -dy
    across = f"{dx} square{'s' * (dx != 1)} right"
    if dy == 0:
        return f"straight across ({across})"
    up = f"{abs(dy)} square{'s' * (abs(dy) != 1)} {'up' if dy < 0 else 'down'}"
    if dx == 0:
        return f"straight {up.split()[-1]}"
    return f"{across} for every {up}"


def _relation(ask: str, u: tuple[int, int], v: tuple[int, int]) -> bool:
    if ask == "parallel":
        return u[0] * v[1] - u[1] * v[0] == 0
    return u[0] * v[0] + u[1] * v[1] == 0


def line_candidates(
    a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], ask: str, t: int
) -> tuple[tuple[int, int], list[tuple[tuple[int, int], str]]]:
    """The answer point and the wrong points, best first, each with its reason."""
    g = gcd(b[0] - a[0], b[1] - a[1])
    dx, dy = (b[0] - a[0]) // g, (b[1] - a[1]) // g
    para = (c[0] + t * dx, c[1] + t * dy)
    perp = (c[0] - t * dy, c[1] + t * dx)
    answer, other = (para, perp) if ask == "parallel" else (perp, para)
    other_why = "makes a line perpendicular to AB" if ask == "parallel" else "is parallel to AB"
    if ask == "parallel":
        swapped, mirrored = (c[0] + t * dy, c[1] + t * dx), (c[0] + t * dx, c[1] - t * dy)
    else:
        swapped, mirrored = (c[0] + t * dx, c[1] - t * dy), (c[0] + t * dy, c[1] + t * dx)
    wrong = [
        (other, other_why),
        (swapped if ask == "parallel" else mirrored, "swaps the squares across and up"),
        (mirrored if ask == "parallel" else swapped, "slopes the other way"),
        *(
            ((answer[0] + ex, answer[1] + ey), "is one square off")
            for ex, ey in ((1, 0), (0, 1), (-1, 0), (0, -1))
        ),
    ]
    return answer, wrong


class GridLinesSolver:
    """``a``, ``b`` — the ends of line AB; ``c`` — the point C; ``ask`` — ``parallel`` or
    ``perpendicular``; ``options`` — the four lettered points, the correct one first;
    ``letters`` — their letters, in the same order."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            dx, dy = rng.choice(_SLOPES)
            if rng.random() < 0.5:
                dx, dy = dy, dx
            dx, dy = dx * rng.choice([1, -1]), dy * rng.choice([1, -1])
            k = 2 if max(abs(dx), abs(dy)) == 1 else 1
            a = (rng.randint(0, _LINE_COLS), rng.randint(0, _LINE_ROWS))
            b = (a[0] + k * dx, a[1] + k * dy)
            c = (rng.randint(0, _LINE_COLS), rng.randint(0, _LINE_ROWS))
            ask = rng.choice(["parallel", "perpendicular"])
            t = rng.choice([1, -1]) * (2 if max(abs(dx), abs(dy)) == 1 else 1)
            if not (_in_grid(b, _LINE_COLS, _LINE_ROWS)) or c in (a, b):
                continue
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) == 0:
                continue  # C on line AB
            answer, wrong = line_candidates(a, b, c, ask, t)
            taken = {a, b, c}
            if not _in_grid(answer, _LINE_COLS, _LINE_ROWS) or answer in taken:
                continue
            taken.add(answer)
            chosen = [answer]
            for p, _ in wrong:
                v = (p[0] - c[0], p[1] - c[1])
                ok = _in_grid(p, _LINE_COLS, _LINE_ROWS) and p not in taken
                if ok and not _relation(ask, (b[0] - a[0], b[1] - a[1]), v) and len(chosen) < 4:
                    chosen.append(p)
                    taken.add(p)
            if len(chosen) == 4:
                # move the whole picture to the middle of the grid
                every = [a, b, c, *chosen]
                sx = (_LINE_COLS - max(p[0] for p in every) - min(p[0] for p in every)) // 2
                sy = (_LINE_ROWS - max(p[1] for p in every) - min(p[1] for p in every)) // 2

                a, b, c = ((p[0] + sx, p[1] + sy) for p in (a, b, c))
                chosen = [(p[0] + sx, p[1] + sy) for p in chosen]
                return {
                    "a": list(a),
                    "b": list(b),
                    "c": list(c),
                    "ask": ask,
                    "options": [list(p) for p in chosen],
                    "letters": _shuffled(rng, "PQRS"),
                }

    def _reasons(self, params: dict) -> list[str]:
        a, b, c = _pt(params["a"]), _pt(params["b"]), _pt(params["c"])
        options = [_pt(p) for p in params["options"]]
        found = []
        for p in options[1:]:
            why = "is not on such a line"
            for t in (1, -1, 2, -2):
                _, wrong = line_candidates(a, b, c, params["ask"], t)
                hit = next((w for q, w in wrong if q == p), None)
                if hit:
                    why = hit
                    break
            found.append(why)
        return found

    def solve(self, params: dict) -> dict:
        a, b, c = _pt(params["a"]), _pt(params["b"]), _pt(params["c"])
        letters, ask = params["letters"], params["ask"]
        options, correct = _choice(letters)
        d = _pt(params["options"][0])
        ab = _walk(b[0] - a[0], b[1] - a[1])
        cd = _walk(d[0] - c[0], d[1] - c[1])
        x = letters[0]
        first = (
            f"AB goes {ab}. A line parallel to AB goes the same way."
            if ask == "parallel"
            else f"AB goes {ab}. A line perpendicular to AB makes a right angle with it."
        )
        return {
            "answer": {"type": "choice", "options": options, "correct": correct},
            "intermediates": {
                "ask": ask,
                "step1": first,
                "step2": f"Line C{x} goes {cd}, so C{x} is {ask} to AB.",
                "step3": f"The others: {_others(letters, self._reasons(params))}.",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        a, b, c = _pt(params["a"]), _pt(params["b"]), _pt(params["c"])
        options = [_pt(p) for p in params["options"]]
        ab = (b[0] - a[0], b[1] - a[1])
        meets = [_relation(params["ask"], ab, (p[0] - c[0], p[1] - c[1])) for p in options]
        letters = params["letters"]
        answer = solution["answer"]
        right = next(o["text"] for o in answer["options"] if o["label"] == answer["correct"])
        points = [a, b, c, *options]
        checks = {
            "letters_p_to_s": sorted(letters) == list("PQRS"),
            "points_distinct": len(set(points)) == len(points),
            "points_in_grid": all(_in_grid(p, _LINE_COLS, _LINE_ROWS) for p in points),
            "c_off_ab": (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) != 0,
            "only_one_option_fits": meets == [True, False, False, False],
            "answer_verified": right == letters[0],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        a, b, c = params["a"], params["b"], params["c"]
        points = [
            {"x": a[0], "y": a[1], "label": "A"},
            {"x": b[0], "y": b[1], "label": "B"},
            {"x": c[0], "y": c[1], "label": "C"},
        ]
        points += [
            {"x": p[0], "y": p[1], "label": letter}
            for p, letter in zip(params["options"], params["letters"], strict=True)
        ]
        return {
            "type": "grid",
            "cols": _LINE_COLS,
            "rows": _LINE_ROWS,
            "segments": [{"from": list(a), "to": list(b)}],
            "points": sorted(points, key=lambda p: p["label"]),
        }


# ---------------------------------------------------------------- compass

_COMPASS_SIZE = 8
_TURNS = (90, 135, 225, 270)


def compass_answer(params: dict) -> int:
    """The direction asked for, as an index into :data:`DIRECTIONS`."""
    if params["ask"] == "direction":
        return params["start"]
    steps = params["angle"] // 45
    return (params["start"] + (steps if params["clockwise"] else -steps)) % 8


def _wrong_directions(params: dict, answer: int) -> list[tuple[int, str]]:
    if params["ask"] == "direction":
        return [
            ((answer + 4) % 8, f"is {DIRECTIONS[(answer + 4) % 8]} of O, the opposite way"),
            ((answer + 1) % 8, f"is {DIRECTIONS[(answer + 1) % 8]} of O"),
            ((answer - 1) % 8, f"is {DIRECTIONS[(answer - 1) % 8]} of O"),
            ((answer + 2) % 8, f"is {DIRECTIONS[(answer + 2) % 8]} of O"),
            ((answer - 2) % 8, f"is {DIRECTIONS[(answer - 2) % 8]} of O"),
        ]
    steps = params["angle"] // 45
    sign = 1 if params["clockwise"] else -1
    start = params["start"]
    return [
        ((start - sign * steps) % 8, "is where a turn the other way ends"),
        ((answer + sign) % 8, "is 45° too far round"),
        ((answer - sign) % 8, "is 45° short"),
        ((start + 4) % 8, "is straight behind the starting direction"),
        ((answer + 4) % 8, "is the opposite way"),
    ]


def _direction_of(o: tuple[int, int], p: tuple[int, int]) -> int | None:
    dx, dy = p[0] - o[0], p[1] - o[1]
    for i, (sx, sy) in enumerate(_STEP):
        k = max(abs(dx), abs(dy))
        if k and (dx, dy) == (sx * k, sy * k):
            return i
    return None


_PEOPLE = ("Ben", "Mei", "Ravi", "Siti", "Jun", "Aisha")


class GridCompassSolver:
    """``o`` — the point O; ``ask`` — ``direction`` (which place is ``start`` of O) or
    ``turn`` (facing ``start``, turn ``angle``° ``clockwise`` or not); ``options`` — the four
    lettered places, the correct one first; ``letters`` — their letters; ``name`` — who turns."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        while True:
            ask = rng.choice(["direction", "turn"])
            params: dict = {
                "o": [rng.randint(3, 5), rng.randint(3, 5)],
                "ask": ask,
                "start": rng.randrange(8),
                "angle": rng.choice(_TURNS) if ask == "turn" else 0,
                "clockwise": rng.random() < 0.5,
                "name": rng.choice(_PEOPLE),
            }
            answer = compass_answer(params)
            dirs = [answer]
            for d, _ in _wrong_directions(params, answer):
                if d not in dirs and len(dirs) < 4:
                    dirs.append(d)
            o = _pt(params["o"])
            points = []
            for d in dirs:
                sx, sy = _STEP[d]
                k = rng.randint(1, 3)
                points.append((o[0] + k * sx, o[1] + k * sy))
            if all(_in_grid(p, _COMPASS_SIZE, _COMPASS_SIZE) for p in points):
                params["options"] = [list(p) for p in points]
                params["letters"] = _shuffled(rng, "ABCD")
                return params

    def solve(self, params: dict) -> dict:
        o = _pt(params["o"])
        letters = params["letters"]
        options, correct = _choice(letters)
        answer = compass_answer(params)
        reasons = []
        wrong = dict(_wrong_directions(params, answer))
        for p in params["options"][1:]:
            d = _direction_of(o, _pt(p))
            reasons.append(wrong.get(d, "is in another direction") if d is not None else "")
        x = letters[0]
        if params["ask"] == "direction":
            question = f"Which place is {DIRECTIONS[answer]} of O?"
            step1 = f"On the grid, north is up. {DIRECTIONS[answer].capitalize()} of O is "
            step1 += f"the line from O through {x}."
        else:
            way = "clockwise" if params["clockwise"] else "anticlockwise"
            question = (
                f"{params['name']} stands at O facing {DIRECTIONS[params['start']]}. "
                f"He turns {params['angle']}° {way}. Which place is he facing now?"
            )
            if params["name"] in ("Mei", "Siti", "Aisha"):
                question = question.replace("He turns", "She turns").replace("is he", "is she")
            step1 = (
                f"Each 45° is one step round the compass. {params['angle']}° is "
                f"{params['angle'] // 45} steps {way} from {DIRECTIONS[params['start']]}, "
                f"which ends at {DIRECTIONS[answer]}. Place {x} is {DIRECTIONS[answer]} of O."
            )
        return {
            "answer": {"type": "choice", "options": options, "correct": correct},
            "intermediates": {
                "question": question,
                "step1": step1,
                "step2": f"The others: {_others(letters, reasons)}.",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        o = _pt(params["o"])
        points = [_pt(p) for p in params["options"]]
        dirs = [_direction_of(o, p) for p in points]
        answer = solution["answer"]
        right = next(x["text"] for x in answer["options"] if x["label"] == answer["correct"])
        checks = {
            "letters_a_to_d": sorted(params["letters"]) == list("ABCD"),
            "places_on_compass_lines": None not in dirs,
            "four_directions": len(set(dirs)) == 4,
            "points_in_grid": all(_in_grid(p, _COMPASS_SIZE, _COMPASS_SIZE) for p in points),
            "turn_known": params["ask"] == "direction" or params["angle"] in _TURNS,
            "answer_verified": dirs[0] == compass_answer(params) and right == params["letters"][0],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        o = params["o"]
        points = [{"x": o[0], "y": o[1], "label": "O"}]
        points += [
            {"x": p[0], "y": p[1], "label": letter}
            for p, letter in zip(params["options"], params["letters"], strict=True)
        ]
        return {
            "type": "grid",
            "cols": _COMPASS_SIZE,
            "rows": _COMPASS_SIZE,
            "compass": True,
            "points": sorted(points, key=lambda p: p["label"]),
        }


# ---------------------------------------------------------------- symmetry

_SYM_LONG, _SYM_SHORT = 8, 6  # the grid is 8 squares across the line and 6 along it


def _mirror(cell: tuple[int, int]) -> tuple[int, int]:
    """Reflection in the line between columns 3 and 4 (cells given as (across, along))."""
    return (_SYM_LONG - 1 - cell[0], cell[1])


def _neighbours(cell: tuple[int, int]) -> list[tuple[int, int]]:
    a, b = cell
    return [(a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)]


def symmetry_wrong(
    shaded: set[tuple[int, int]], missing: tuple[int, int]
) -> list[tuple[tuple[int, int], str]]:
    """Wrong squares to offer, best first (cells as (across, along))."""
    partner = _mirror(missing)
    half = _SYM_LONG // 2
    slid = (partner[0] + half if partner[0] < half else partner[0] - half, partner[1])
    out = [(slid, "is the square moved across the line without flipping it")]
    out += [(n, "is one square away from the mirror image") for n in _neighbours(missing)]
    out += [
        (n, "is next to the square without a partner")
        for n in _neighbours(partner)
        if n[0] < half
        if partner[0] < half
    ]
    return [
        (c, why)
        for c, why in out
        if 0 <= c[0] < _SYM_LONG and 0 <= c[1] < _SYM_SHORT and c not in shaded and c != missing
    ]


def _connected(cells: set[tuple[int, int]]) -> bool:
    if not cells:
        return False
    seen, todo = set(), [next(iter(cells))]
    while todo:
        c = todo.pop()
        if c in seen:
            continue
        seen.add(c)
        todo += [n for n in _neighbours(c) if n in cells]
    return seen == cells


class GridSymmetrySolver:
    """``axis`` — the dashed line runs ``vertical`` or ``horizontal``; ``shaded`` — the shaded
    squares and ``options`` — the four lettered squares, the correct one first, both as
    (across, along) where across is measured over the line; ``letters`` — the option letters."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        half = _SYM_LONG // 2
        while True:
            blob = {(half - 1, rng.randrange(1, _SYM_SHORT - 1))}
            size = rng.randint(4, 6)
            while len(blob) < size:
                n = rng.choice(_neighbours(rng.choice(sorted(blob))))
                if 0 <= n[0] < half and 0 <= n[1] < _SYM_SHORT:
                    blob.add(n)
            figure = blob | {_mirror(c) for c in blob}
            missing = rng.choice(sorted(figure))
            shaded = figure - {missing}
            if not _connected(shaded):
                continue
            wrong = []
            for c, _ in symmetry_wrong(shaded, missing):
                if c not in wrong:
                    wrong.append(c)
            if len(wrong) >= 3:
                return {
                    "axis": rng.choice(["vertical", "horizontal"]),
                    "shaded": [list(c) for c in sorted(shaded)],
                    "options": [list(missing), *(list(c) for c in wrong[:3])],
                    "letters": _shuffled(rng, "ABCD"),
                }

    def solve(self, params: dict) -> dict:
        shaded = {_pt(c) for c in params["shaded"]}
        lone = sorted(c for c in shaded if _mirror(c) not in shaded)
        missing = _mirror(lone[0]) if len(lone) == 1 else None
        letters = params["letters"]
        options, correct = _choice(letters)
        reasons = dict(symmetry_wrong(shaded, missing)) if missing else {}
        why = [reasons.get(_pt(c), "is not the mirror image") for c in params["options"][1:]]
        return {
            "answer": {"type": "choice", "options": options, "correct": correct},
            "intermediates": {
                "step1": (
                    "Fold along the dashed line: every shaded square must land on a shaded "
                    "square. One shaded square has no partner on the other side of the line."
                ),
                "step2": f"Its mirror image across the dashed line is square {letters[0]}.",
                "step3": f"The others: {_others(letters, why)}.",
            },
        }

    def validate(self, params: dict, solution: dict) -> dict:
        shaded = {_pt(c) for c in params["shaded"]}
        options = [_pt(c) for c in params["options"]]
        lone = [c for c in shaded if _mirror(c) not in shaded]
        answer = solution["answer"]
        right = next(x["text"] for x in answer["options"] if x["label"] == answer["correct"])
        cells_ok = all(0 <= a < _SYM_LONG and 0 <= b < _SYM_SHORT for a, b in [*shaded, *options])
        checks = {
            "letters_a_to_d": sorted(params["letters"]) == list("ABCD"),
            "cells_in_grid": cells_ok,
            "options_unshaded_and_distinct": len(set(options)) == 4 and not shaded & set(options),
            "one_square_short": len(lone) == 1 and _mirror(lone[0]) == options[0],
            "answer_verified": right == params["letters"][0],
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        vertical = params["axis"] == "vertical"

        def cell(c: list[int], label: str | None = None) -> dict:
            col, row = (c[0], c[1]) if vertical else (c[1], c[0])
            out: dict = {"col": col, "row": row, "shaded": label is None}
            if label:
                out["label"] = label
            return out

        cells = [cell(c) for c in params["shaded"]]
        cells += [
            cell(c, letter) for c, letter in zip(params["options"], params["letters"], strict=True)
        ]
        half = _SYM_LONG // 2
        line = (
            {"from": [half, 0], "to": [half, _SYM_SHORT], "dashed": True}
            if vertical
            else {"from": [0, half], "to": [_SYM_SHORT, half], "dashed": True}
        )
        return {
            "type": "grid",
            "cols": _SYM_LONG if vertical else _SYM_SHORT,
            "rows": _SYM_SHORT if vertical else _SYM_LONG,
            "cells": sorted(cells, key=lambda c: (c["row"], c["col"])),
            "segments": [line],
        }


register("grid_area", GridAreaSolver())
register("grid_lines", GridLinesSolver())
register("grid_compass", GridCompassSolver())
register("grid_symmetry", GridSymmetrySolver())
