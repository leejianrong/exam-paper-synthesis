"""Solvers for the deeper P6 angle blueprints (EXA-150).

Real P6 prelims ask angle questions a step or two deeper than the ladder's: folded paper,
a special quadrilateral joined to an isosceles or equilateral triangle, reflex angles at a
point, and two-part angle questions in Paper 2. Four blueprints, on no ladder:

* ``geometry_angle_folded`` (2 marks) — rectangle ABCD with corner B folded along EF onto
  B'. Given ∠AEB', find ∠B'FC: the fold halves the straight angle at E, ∠EB'F is the
  folded right angle, and BFC is a straight line.
* ``geometry_angle_composite`` (3 marks) — ``rhombus_equilateral`` (equilateral CDE on
  side DC of a rhombus; DA = DC = DE), ``parallelogram_isosceles`` (E on DC with EA = ED)
  and ``trapezium_isosceles`` (AB = AD, diagonal BD, alternate angles).
* ``geometry_angle_reflex`` (2 marks) — ``straight_line`` (a reflex angle beyond a straight
  line), ``equal_angles`` (a given reflex angle, two equal angles) and ``crossing_lines``.
* ``geometry_angle_structured`` (4 marks, P8c multi-part) — rhombus ABCD with equilateral
  BCE inside it: (a) ∠BAE (isosceles ABE), (b) ∠DAE (uses (a)).

Every figure is drawn **to scale**: point coordinates are computed from the angles, so the
invariant tests can measure each marked angle off the drawing. Whole degrees by
construction (sampled values are even where a step halves them).
"""

from __future__ import annotations

import math
import random
from fractions import Fraction

from ..base import spread_sides
from ..registry import register

_UNIT = "degrees"
_NOTE = "(The figure is not drawn to scale.)"


def _dir(deg: float) -> tuple[float, float]:
    """Unit vector at ``deg`` measured anticlockwise, maths frame (y up)."""
    r = math.radians(deg)
    return math.cos(r), math.sin(r)


def _points(coords: dict[str, tuple[float, float]]) -> list[dict]:
    """Maths-frame coordinates -> figure points (screen frame: y down), rounded so the
    stored figure is stable."""
    return [
        {"id": pid, "x": round(x, 4) + 0.0, "y": round(-y, 4) + 0.0}
        for pid, (x, y) in coords.items()
    ]


def _segs(*pairs: str, ticks: tuple[str, ...] = ()) -> list[dict]:
    out = []
    for pair in pairs:
        a, b = pair.split("-")
        seg: dict = {"from": a, "to": b}
        if pair in ticks:
            seg["ticks"] = 1
        out.append(seg)
    return out


def _angle(key: str, value: int, *, unknown: bool = False, part: str | None = None) -> dict:
    fr, at, to = key.split("-")
    mark: dict = {"at": at, "from": fr, "to": to, "value_deg": value, "unknown": unknown}
    if part is not None:
        mark["part_label"] = part
    return mark


def _figure(built: dict) -> dict:
    return {
        "type": "geometry_figure",
        "unit": _UNIT,
        "points": _points(built["coords"]),
        "segments": built["segments"],
        "angles": built["angles"],
        "labels": [{"at": pid, "text": pid} for pid in built["coords"]],
    }


def _given_map(angles: list[dict]) -> dict[str, int]:
    return {f"{a['from']}-{a['at']}-{a['to']}": a["value_deg"] for a in angles if not a["unknown"]}


def _single_answer(built: dict) -> dict:
    return {
        "answer": {"type": "integer", "value": built["answer"], "unit": _UNIT},
        "intermediates": {"question_text": built["text"]}
        | {f"step{i}": s for i, s in enumerate(built["steps"], 1)},
    }


# --------------------------------------------------------------------------- folded


_W, _H = 10.0, 7.0  # the rectangle (figure units)


def _build_folded(g: dict) -> dict:
    p = g["p"]  # ∠AEB'
    half = (180 - p) // 2  # ∠B'EF = ∠BEF
    efb = p // 2  # ∠EFB' = ∠EFB
    ans = 180 - p  # ∠B'FC
    # Size the flap so F stays on BC and B' inside the rectangle.
    e = min(5.5, (_H - 0.8) / math.tan(math.radians(half)), (_H - 0.8) / math.sin(math.radians(p)))
    f = e * math.tan(math.radians(half))
    ex, fy = _W - e, _H - f
    bx, by = -math.cos(math.radians(p)), -math.sin(math.radians(p))
    coords = {
        "A": (0.0, _H),
        "E": (ex, _H),
        "B'": (ex + e * bx, _H + e * by),
        "F": (_W, fy),
        "C": (_W, 0.0),
        "D": (0.0, 0.0),
    }
    angles = [_angle("A-E-B'", p), _angle("B'-F-C", ans, unknown=True)]
    return {
        "coords": coords,
        "segments": _segs("A-E", "E-B'", "B'-F", "F-C", "C-D", "D-A", "E-F"),
        "angles": angles,
        "answer": ans,
        "text": (
            "ABCD is a rectangular piece of paper. E is on AB and F is on BC. It is folded "
            "along EF so that the corner B "
            f"lands on B', as shown. ∠AEB' = {p}°. Find ∠B'FC. {_NOTE}"
        ),
        "steps": [
            f"The fold gives ∠B'EF = ∠BEF, and AEB is a straight line, so "
            f"∠B'EF = (180° − {p}°) ÷ 2 = {half}°.",
            f"∠EB'F = ∠EBF = 90° (a corner of the rectangle), so in triangle EB'F, "
            f"∠EFB' = 180° − 90° − {half}° = {efb}°.",
            f"∠EFB = ∠EFB' = {efb}° and BFC is a straight line, so "
            f"∠B'FC = 180° − {efb}° − {efb}° = {ans}°.",
        ],
    }


class GeometryAngleFoldedSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        p = rng.randrange(40, 141, 2)
        return {"template": "corner_fold", "givens": {"p": p}, "angles": {"A-E-B'": p}}

    def solve(self, params: dict) -> dict:
        return _single_answer(_build_folded(params["givens"]))

    @spread_sides
    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        """Common wrong angles (degrees), best first (EXA-122)."""
        p = params["givens"]["p"]
        return [
            (p // 2, "found ∠EFB', not ∠B'FC"),
            ((180 - p) // 2, "found ∠B'EF"),
            (180 - p // 2, "found ∠EFC"),
            (p, "took ∠B'FC equal to ∠AEB'"),
            (90 + p // 2, "found ∠AEF"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        p = params["givens"]["p"]
        ans = solution["answer"]["value"]
        half = (180 - p) // 2
        checks = {
            "fold_halves_straight_angle": p + 2 * half == 180,
            # quadrilateral EBFB': two right angles, so ∠BEB' + ∠BFB' = 180.
            "rule": (180 - p) + (180 - ans) == 180,
            "in_range": 0 < ans < 180,
            "unit_degrees": solution["answer"]["unit"] == _UNIT,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _figure(_build_folded(params["givens"]))


# --------------------------------------------------------------------------- composite


def _build_rhombus_equilateral(g: dict) -> dict:
    d = g["d"]  # ∠ADC
    ans = (120 - d) // 2  # ∠DAE
    s = 6.0
    ax, ay = _dir(d)
    hx, hy = _dir(-60)
    coords = {
        "A": (s * ax, s * ay),
        "B": (s * ax + s, s * ay),
        "C": (s, 0.0),
        "D": (0.0, 0.0),
        "E": (s * hx, s * hy),
    }
    angles = [_angle("A-D-C", d), _angle("D-A-E", ans, unknown=True)]
    sides = ("A-B", "B-C", "C-D", "D-A", "D-E", "C-E")
    return {
        "coords": coords,
        "segments": _segs(*sides, "A-E", ticks=sides),
        "angles": angles,
        "answer": ans,
        "text": (
            "In the figure, ABCD is a rhombus and CDE is an equilateral triangle. "
            f"∠ADC = {d}°. Find ∠DAE. {_NOTE}"
        ),
        "steps": [
            "ABCD is a rhombus and CDE is equilateral, so DA = DC = DE: triangle ADE is isosceles.",
            f"∠ADE = ∠ADC + ∠CDE = {d}° + 60° = {d + 60}°.",
            f"∠DAE = (180° − {d + 60}°) ÷ 2 = {ans}°.",
        ],
    }


def _build_parallelogram_isosceles(g: dict) -> dict:
    b = g["b"]  # ∠ABC
    ans = 180 - 2 * b  # ∠EAB
    m = 5.0  # AD
    de = (m / 2) / math.cos(math.radians(b))
    length = de + 3.0  # AB = DC, so E sits well inside DC
    dx, dy = _dir(180 - b)
    D = (m * dx, m * dy)
    coords = {
        "A": (0.0, 0.0),
        "B": (length, 0.0),
        "C": (D[0] + length, D[1]),
        "D": D,
        "E": (D[0] + de, D[1]),
    }
    angles = [_angle("A-B-C", b), _angle("E-A-B", ans, unknown=True)]
    return {
        "coords": coords,
        "segments": _segs("A-B", "B-C", "C-E", "E-D", "D-A", "A-E", ticks=("E-D", "A-E")),
        "angles": angles,
        "answer": ans,
        "text": (
            "In the figure, ABCD is a parallelogram. E is a point on DC such that EA = ED. "
            f"∠ABC = {b}°. Find ∠EAB. {_NOTE}"
        ),
        "steps": [
            f"∠ADE = ∠ABC = {b}° (opposite angles of a parallelogram).",
            f"EA = ED, so triangle ADE is isosceles and ∠EAD = ∠EDA = {b}°.",
            f"∠DAB = 180° − {b}° = {180 - b}° (AB ∥ DC), so ∠EAB = {180 - b}° − {b}° = {ans}°.",
        ],
    }


def _build_trapezium_isosceles(g: dict) -> dict:
    a, c = g["a"], g["c"]  # ∠DAB, ∠BCD
    base = (180 - a) // 2  # ∠ABD = ∠ADB = ∠BDC
    ans = 180 - base - c  # ∠DBC
    s = 6.0
    dx, dy = _dir(-a)
    D = (s * dx, s * dy)
    h = -D[1]
    coords = {
        "A": (0.0, 0.0),
        "B": (s, 0.0),
        "C": (s + h / math.tan(math.radians(c)), D[1]),
        "D": D,
    }
    angles = [
        _angle("D-A-B", a),
        _angle("B-C-D", c),
        _angle("D-B-C", ans, unknown=True),
    ]
    return {
        "coords": coords,
        "segments": _segs("A-B", "B-C", "C-D", "D-A", "B-D", ticks=("A-B", "D-A")),
        "angles": angles,
        "answer": ans,
        "text": (
            "In the figure, ABCD is a trapezium with AB parallel to DC, and AB = AD. "
            f"∠DAB = {a}° and ∠BCD = {c}°. Find ∠DBC. {_NOTE}"
        ),
        "steps": [
            f"AB = AD, so triangle ABD is isosceles: ∠ABD = (180° − {a}°) ÷ 2 = {base}°.",
            f"AB ∥ DC, so ∠BDC = ∠ABD = {base}° (alternate angles).",
            f"In triangle BCD, ∠DBC = 180° − {base}° − {c}° = {ans}°.",
        ],
    }


_COMPOSITE = {
    "rhombus_equilateral": _build_rhombus_equilateral,
    "parallelogram_isosceles": _build_parallelogram_isosceles,
    "trapezium_isosceles": _build_trapezium_isosceles,
}


def _build_composite(params: dict) -> dict:
    return _COMPOSITE[params["template"]](params["givens"])


class GeometryAngleCompositeSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_COMPOSITE))
        if template == "rhombus_equilateral":
            # d at most 88: past that AE runs close by D and ∠DAE is a sliver (under 16°).
            givens = {"d": rng.randrange(40, 89, 2)}
        elif template == "parallelogram_isosceles":
            givens = {"b": rng.randint(46, 72)}
        else:
            givens = {"a": rng.randrange(100, 141, 2), "c": rng.randint(45, 80)}
        built = _COMPOSITE[template](givens)
        return {"template": template, "givens": givens, "angles": _given_map(built["angles"])}

    def solve(self, params: dict) -> dict:
        return _single_answer(_build_composite(params))

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        g, template = params["givens"], params["template"]
        if template == "rhombus_equilateral":
            d = g["d"]
            return [
                (Fraction(180 - d, 2), "left out the 60° of the equilateral triangle"),
                (120 - d, "forgot to halve"),
                (d + 60, "found ∠ADE, not ∠DAE"),
                (Fraction(240 - d, 2), "subtracted the 60° instead of adding it"),
            ]
        if template == "parallelogram_isosceles":
            b = g["b"]
            return [
                (180 - b, "found ∠DAB, not ∠EAB"),
                (b, "took ∠EAB equal to ∠ABC"),
                (2 * b, "found ∠AEC, not ∠EAB"),
            ]
        a, c = g["a"], g["c"]
        base = (180 - a) // 2
        return [
            (180 - a // 2 - c, "halved ∠DAB to get the base angle ∠ABD"),
            (base, "found ∠BDC, not ∠DBC"),
            (180 - (180 - a) - c, "did not halve for the isosceles triangle"),
            (180 - c, "subtracted only ∠BCD"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        g, template = params["givens"], params["template"]
        ans = solution["answer"]["value"]
        if template == "rhombus_equilateral":
            rule = (g["d"] + 60) + 2 * ans == 180
        elif template == "parallelogram_isosceles":
            rule = 180 - g["b"] == g["b"] + ans  # ∠DAB = ∠EAD + ∠EAB
        else:
            base = (180 - g["a"]) // 2
            rule = g["a"] + 2 * base == 180 and base + g["c"] + ans == 180
        checks = {
            "rule": rule,
            "in_range": 5 <= ans < 180,
            "unit_degrees": solution["answer"]["unit"] == _UNIT,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _figure(_build_composite(params))


# --------------------------------------------------------------------------- reflex


def _rays(lengths: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    """``{id: (direction_deg, length)}`` -> coordinates of rays from O at the origin."""
    out = {"O": (0.0, 0.0)}
    for pid, (deg, length) in lengths.items():
        ux, uy = _dir(deg)
        out[pid] = (length * ux, length * uy)
    return out


def _build_straight_line(g: dict) -> dict:
    a, c = g["a"], g["c"]  # ∠AOC, ∠COD
    bod = 180 - a - c
    ans = 360 - bod  # reflex ∠BOD
    coords = _rays({"A": (180, 5), "B": (0, 5), "C": (180 - a, 4.5), "D": (bod, 4.5)})
    angles = [
        _angle("A-O-C", a),
        _angle("C-O-D", c),
        _angle("B-O-D", ans, unknown=True),
    ]
    return {
        "coords": coords,
        "segments": _segs("A-O", "O-B", "O-C", "O-D"),
        "angles": angles,
        "answer": ans,
        "text": (
            f"In the figure, AOB is a straight line. ∠AOC = {a}° and ∠COD = {c}°. "
            f"Find the reflex angle BOD. {_NOTE}"
        ),
        "steps": [
            f"AOB is a straight line, so ∠BOD = 180° − {a}° − {c}° = {bod}°.",
            f"Reflex ∠BOD = 360° − {bod}° = {ans}°.",
        ],
    }


def _build_equal_angles(g: dict) -> dict:
    r, b = g["r"], g["b"]  # reflex ∠AOD, ∠BOC
    ans = (360 - r - b) // 2  # ∠AOB = ∠COD
    start = 90 + (360 - r) / 2  # A, then B, C, D clockwise, the minor angle AOD on top
    coords = _rays(
        {
            "A": (start, 5),
            "B": (start - ans, 5),
            "C": (start - ans - b, 5),
            "D": (start - 2 * ans - b, 5),
        }
    )
    angles = [
        _angle("A-O-D", r),
        _angle("B-O-C", b),
        # ∠AOB is not marked: its arc would run into the arc of ∠BOC and read as one.
    ]
    return {
        "coords": coords,
        "segments": _segs("O-A", "O-B", "O-C", "O-D"),
        "angles": angles,
        "answer": ans,
        "text": (
            f"In the figure, ∠AOB = ∠COD. The reflex angle AOD is {r}° and ∠BOC = {b}°. "
            f"Find ∠AOB. {_NOTE}"
        ),
        "steps": [
            f"∠AOD = 360° − {r}° = {360 - r}° (angles at a point).",
            f"∠AOB + ∠COD = {360 - r}° − {b}° = {360 - r - b}°, "
            f"so ∠AOB = {360 - r - b}° ÷ 2 = {ans}°.",
        ],
    }


def _build_crossing_lines(g: dict) -> dict:
    a = g["a"]  # ∠AOC
    boc = 180 - a
    ans = 360 - boc  # reflex ∠BOC
    coords = _rays({"A": (180, 5), "B": (0, 5), "C": (180 - a, 5), "D": (360 - a, 5)})
    angles = [_angle("A-O-C", a), _angle("B-O-C", ans, unknown=True)]
    return {
        "coords": coords,
        "segments": _segs("A-O", "O-B", "C-O", "O-D"),
        "angles": angles,
        "answer": ans,
        "text": (
            f"In the figure, the straight lines AB and CD cross at O. ∠AOC = {a}°. "
            f"Find the reflex angle BOC. {_NOTE}"
        ),
        "steps": [
            f"AOB is a straight line, so ∠BOC = 180° − {a}° = {boc}°.",
            f"Reflex ∠BOC = 360° − {boc}° = {ans}°.",
        ],
    }


_REFLEX = {
    "straight_line": _build_straight_line,
    "equal_angles": _build_equal_angles,
    "crossing_lines": _build_crossing_lines,
}


def _build_reflex(params: dict) -> dict:
    return _REFLEX[params["template"]](params["givens"])


class GeometryAngleReflexSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(list(_REFLEX))
        if template == "straight_line":
            while True:
                a, c = rng.randint(30, 80), rng.randint(30, 80)
                if 180 - a - c >= 30:
                    break
            givens = {"a": a, "c": c}
        elif template == "equal_angles":
            while True:
                r, b = rng.randrange(200, 291, 2), rng.randrange(30, 81, 2)
                if 360 - r - b >= 40:
                    break
            givens = {"r": r, "b": b}
        else:
            givens = {"a": rng.choice([x for x in range(35, 146) if abs(x - 90) > 10])}
        built = _REFLEX[template](givens)
        return {"template": template, "givens": givens, "angles": _given_map(built["angles"])}

    def solve(self, params: dict) -> dict:
        return _single_answer(_build_reflex(params))

    def distractors(self, params: dict, solution: dict) -> list[tuple[int | Fraction, str]]:
        g, template = params["givens"], params["template"]
        if template == "straight_line":
            a, c = g["a"], g["c"]
            return [
                (180 - a - c, "found ∠BOD, not the reflex angle"),
                (360 - a - c, "subtracted from 360° instead of using the straight line"),
                (180 + a, "left out ∠COD"),
                (180 + c, "left out ∠AOC"),
            ]
        if template == "equal_angles":
            r, b = g["r"], g["b"]
            return [
                (360 - r - b, "forgot to halve"),
                (Fraction(360 - r, 2), "left out ∠BOC"),
                (Fraction(r - b, 2), "used the reflex angle as if it were ∠AOD"),
            ]
        a = g["a"]
        return [
            (180 - a, "found ∠BOC, not the reflex angle"),
            (360 - a, "found the reflex angle AOC"),
            (a, "took ∠BOC equal to ∠AOC"),
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        g, template = params["givens"], params["template"]
        ans = solution["answer"]["value"]
        if template == "straight_line":
            rule = g["a"] + g["c"] + (360 - ans) == 180
        elif template == "equal_angles":
            rule = g["r"] + g["b"] + 2 * ans == 360
        else:
            rule = g["a"] + (360 - ans) == 180
        reflex = template != "equal_angles"
        checks = {
            "rule": rule,
            "in_range": (180 < ans < 360) if reflex else (0 < ans < 180),
            "unit_degrees": solution["answer"]["unit"] == _UNIT,
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _figure(_build_reflex(params))


# --------------------------------------------------------------------------- structured


def _build_structured(g: dict) -> dict:
    b = g["d"]  # ∠ADC, and so ∠ABC (opposite angles)
    abe = b - 60
    bae = (180 - abe) // 2  # (a)
    dab = 180 - b
    dae = dab - bae  # (b)
    s = 6.0
    ux, uy = _dir(b)  # BA leaves B at ∠ABC above BC
    ex, ey = _dir(60)
    coords = {
        "A": (s * ux, s * uy),
        "B": (0.0, 0.0),
        "C": (s, 0.0),
        "D": (s + s * ux, s * uy),
        "E": (s * ex, s * ey),
    }
    angles = [
        # ∠ADC is given, not ∠ABC: at B the ray BE crowds the angle's value.
        _angle("A-D-C", b),
        # Only (a)'s angle is marked: two unlabelled arcs side by side at A would read as one.
        _angle("B-A-E", bae, unknown=True, part="a"),
    ]
    sides = ("A-B", "B-C", "C-D", "D-A", "B-E", "C-E")
    return {
        "coords": coords,
        "segments": _segs(*sides, "A-E", ticks=sides),
        "angles": angles,
        "answers": [bae, dae],
        "intermediates": {"b": b, "abe": abe, "bae": bae, "dab": dab, "dae": dae},
    }


class GeometryAngleStructuredSolver:
    def sample(self, schema: dict, rng: random.Random) -> dict:
        # Away from 60° and 120° E would crowd AD; 90° would make the rhombus a square.
        d = rng.choice([x for x in range(76, 101, 2) if x != 90])
        return {
            "template": "rhombus_equilateral_inside",
            "givens": {"d": d},
            "angles": {"A-D-C": d},
        }

    def solve(self, params: dict) -> dict:
        built = _build_structured(params["givens"])
        return {
            "answers": [{"type": "integer", "value": v, "unit": _UNIT} for v in built["answers"]],
            "intermediates": built["intermediates"],
        }

    def validate(self, params: dict, solution: dict) -> dict:
        b = params["givens"]["d"]
        bae, dae = (a["value"] for a in solution["answers"])
        checks = {
            "e_inside_rhombus": 60 < b < 120,
            # isosceles ABE (AB = BC = BE): apex ∠ABE = b − 60, two equal base angles
            "rule_a": (b - 60) + 2 * bae == 180,
            # ∠DAB + ∠ABC = 180 (AD ∥ BC), split by AE
            "rule_b": bae + dae + b == 180,
            "in_range": all(0 < v < 180 for v in (bae, dae)),
        }
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        return _figure(_build_structured(params["givens"]))


register("geometry_angle_folded", GeometryAngleFoldedSolver())
register("geometry_angle_composite", GeometryAngleCompositeSolver())
register("geometry_angle_reflex", GeometryAngleReflexSolver())
register("geometry_angle_structured", GeometryAngleStructuredSolver())
