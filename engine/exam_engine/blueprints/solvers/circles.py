"""Solvers for the P6 ``circles`` ladder (P8e, EXA-149), each with a ``geometry_figure``.

* easy (1 mark)   — the circumference or area of a circle, the area of a semicircle or a
                    quarter circle, from its radius or diameter.
* medium (2 marks) — a composite: a square with a semicircle on one side, a rectangle with
                    a semicircle cut out, a quarter circle (perimeter or area of the whole
                    shaded figure, so the straight edges count only when they bound it).
* hard (3 marks)  — a shaded region made by quarter circles and semicircles inside a square
                    or rectangle: the leaf of two quarter circles, a quarter circle less a
                    semicircle (area, or perimeter "in terms of π" as an ``expression``
                    answer), the gap between two quarter circles in a rectangle.

π is stated in the stem: ``3.14`` (the usual choice in real papers) or ``22/7``, and the
dimensions are drawn so the answer is whole or ends within 2 decimal places (22/7 only
with lengths that are multiples of 7). The ``terms`` template asks for the answer in terms
of π instead. Every shaded region is traced on the figure (``shaded[].arcs``) exactly as
the question measures it, so the invariant test can recompute the answer from the figure
by numerical integration. Exact ``Fraction`` arithmetic throughout (no LLM).
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from fractions import Fraction

from ..registry import register
from .geometry_area_common import AREA_UNIT, LEN_UNIT, _labels, _pt, format_measure

PIS = ("3.14", "22/7")
TERMS = "terms"  # the answer is left in terms of π


def pi_of(pi: str) -> Fraction:
    return Fraction(22, 7) if pi == "22/7" else Fraction(314, 100)


def _n(x: Fraction | int) -> str:
    """A whole or 2-dp exact value as printed (``154``, ``78.5``)."""
    return str(format_measure(Fraction(x), "")["value"])


def _pick_pi(rng: random.Random) -> str:
    return "3.14" if rng.random() < 0.6 else "22/7"


def _take(pi: str) -> str:
    return f"Take π = {pi}."


Distractors = list[tuple[Fraction, str]]


def _fig(**kw: object) -> dict:
    base: dict = {"angles": [], "shaded": [], "lengths": {}, "radii": {}, "labels": []}
    base.update(kw)
    return base


# ====================================================================== easy


def _circle_points(r: int) -> list[dict]:
    return [_pt("O", r, r), _pt("P", 0, r), _pt("Q", 2 * r, r), _pt("T", r, 0)]


def _easy_dimension(given_as: str, r: int, *, full: bool) -> tuple[list, dict, str]:
    """The labelled radius (dashed, from the centre) or diameter of a circle/semicircle."""
    if given_as == "radius":
        seg = {"from": "O", "to": "Q" if full else "T", "label": f"{r} cm", "dashed": True}
        return [seg], {f"O-{seg['to']}": r}, f"radius {r} cm"
    if full:
        seg = {"from": "P", "to": "Q", "label": f"{2 * r} cm", "dashed": True}
        return [seg], {"P-Q": 2 * r}, f"diameter {2 * r} cm"
    return [], {"P-Q": 2 * r}, f"diameter {2 * r} cm"


def _easy_circle(g: dict, pi: str, given_as: str, *, area: bool) -> dict:
    r = g["r"]
    p = pi_of(pi)
    segs, lengths, dim = _easy_dimension(given_as, r, full=True)
    arcs = [
        {"center": "O", "radius": r, "start_deg": 0, "end_deg": 180, "label": None},
        {"center": "O", "radius": r, "start_deg": 180, "end_deg": 360, "label": None},
    ]
    d = 2 * r
    if area:
        exact = p * r * r
        what = "area"
        half = f"Radius = {d} ÷ 2 = {r} cm. " if given_as == "diameter" else ""
        steps = [
            f"{_take(pi)} {half}Area of a circle = π × r × r.",
            f"Area = {pi} × {r} × {r} = {_n(exact)} cm².",
        ]
        if given_as == "diameter":
            wrong: Distractors = [
                (p * d * d, "used the diameter as the radius"),
                (2 * p * r, "the circumference, not the area"),
                (p * r * r / 2, "halved the area (a semicircle)"),
            ]
        else:
            wrong = [
                (2 * p * r, "multiplied the radius by 2 instead of by itself"),
                (p * d * d, "doubled the radius before squaring"),
                (p * r * r / 2, "halved the area (a semicircle)"),
            ]
        unit = AREA_UNIT
    else:
        exact = 2 * p * r
        what = "circumference"
        if given_as == "radius":
            steps = [
                f"{_take(pi)} Circumference = 2 × π × r.",
                f"Circumference = 2 × {pi} × {r} = {_n(exact)} cm.",
            ]
            wrong = [
                (p * r, "used the radius as the diameter (π × r)"),
                (p * r * r, "the area, not the circumference"),
                (4 * p * r, "doubled the radius twice"),
            ]
        else:
            steps = [
                f"{_take(pi)} Circumference = π × d.",
                f"Circumference = {pi} × {d} = {_n(exact)} cm.",
            ]
            wrong = [
                (2 * p * d, "used the diameter as the radius (2 × π × d)"),
                (p * r, "halved the circumference (a semicircle's curved edge)"),
                (p * r * r, "the area, not the circumference"),
            ]
        unit = LEN_UNIT
    text = (
        f"The figure shows a circle with centre O and {dim}. {_take(pi)} "
        f"Find the {what} of the circle."
    )
    return _fig(
        points=_circle_points(r),
        segments=segs,
        arcs=arcs,
        labels=_labels(["O"]),
        lengths=lengths,
        radii={"O": r},
        answer=format_measure(exact, unit),
        text=text,
        steps=steps,
        wrong=wrong,
    )


def _easy_semicircle(g: dict, pi: str, given_as: str) -> dict:
    r = g["r"]
    p = pi_of(pi)
    d = 2 * r
    segs, lengths, dim = _easy_dimension(given_as, r, full=False)
    edge = {"from": "P", "to": "Q"}
    if given_as == "diameter":
        edge["label"] = f"{d} cm"
    exact = p * r * r / 2
    first = f"{_take(pi)} " + (f"Radius = {d} ÷ 2 = {r} cm. " if given_as == "diameter" else "")
    steps = [
        first + "Area of a semicircle = ½ × π × r × r.",
        f"Area = ½ × {pi} × {r} × {r} = {_n(exact)} cm².",
    ]
    wrong: Distractors = [
        (p * r * r, "the whole circle (forgot to halve)"),
        (p * d * d / 2, "used the diameter as the radius"),
        (p * r + d, "the perimeter, not the area"),
        (p * r * r / 4, "a quarter circle"),
    ]
    return _fig(
        points=_circle_points(r),
        segments=[edge, *segs],
        arcs=[{"center": "O", "radius": r, "start_deg": 180, "end_deg": 360, "label": None}],
        labels=_labels(["O"]),
        lengths=lengths,
        radii={"O": r},
        answer=format_measure(exact, AREA_UNIT),
        text=f"The figure shows a semicircle with centre O and {dim}. {_take(pi)} "
        "Find the area of the semicircle.",
        steps=steps,
        wrong=wrong,
    )


def _quarter_figure(r: int, *, shaded: bool) -> dict:
    """Quarter circle, centre O at the bottom left, radius OA (across) and OB (up)."""
    return {
        "points": [_pt("O", 0, r), _pt("A", r, r), _pt("B", 0, 0)],
        "segments": [{"from": "O", "to": "A", "label": f"{r} cm"}, {"from": "O", "to": "B"}],
        "arcs": [{"center": "O", "radius": r, "start_deg": -90, "end_deg": 0, "label": None}],
        "angles": [{"at": "O", "from": "A", "to": "B", "right": True}],
        "shaded": (
            [
                {
                    "boundary": ["O", "A", "B"],
                    "arcs": [{"from": "A", "to": "B", "center": "O", "radius": r, "sweep": 0}],
                }
            ]
            if shaded
            else []
        ),
        "labels": _labels(["O"]),
        "lengths": {"O-A": r},
        "radii": {"O": r},
    }


def _easy_quarter(g: dict, pi: str, given_as: str) -> dict:
    r = g["r"]
    p = pi_of(pi)
    exact = p * r * r / 4
    return {
        **_quarter_figure(r, shaded=False),
        "answer": format_measure(exact, AREA_UNIT),
        "text": f"The figure shows a quarter circle with centre O and radius {r} cm. "
        f"{_take(pi)} Find the area of the quarter circle.",
        "steps": [
            f"{_take(pi)} Area of a quarter circle = ¼ × π × r × r.",
            f"Area = ¼ × {pi} × {r} × {r} = {_n(exact)} cm².",
        ],
        "wrong": [
            (p * r * r, "the whole circle (forgot to take a quarter)"),
            (p * r * r / 2, "a semicircle, not a quarter circle"),
            (p * r / 2, "the curved edge, not the area"),
        ],
    }


EASY: dict[str, Callable[[dict, str, str], dict]] = {
    "circle_circumference": lambda g, pi, a: _easy_circle(g, pi, a, area=False),
    "circle_area": lambda g, pi, a: _easy_circle(g, pi, a, area=True),
    "semicircle_area": _easy_semicircle,
    "quarter_circle_area": _easy_quarter,
}


def _easy_radius(template: str, pi: str, given_as: str, rng: random.Random) -> int:
    if pi == "22/7":
        return 7 * rng.randint(1, 3)
    if template == "quarter_circle_area":
        return rng.choice([4, 6, 8, 10, 12, 16, 20])  # even: ¼ × 3.14 × r × r has 2 dp
    return (
        rng.choice([3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 15])
        if given_as == "radius"
        else (rng.choice([3, 4, 5, 6, 8, 9, 10, 12]))
    )


# ====================================================================== medium


def _square_semicircle(s: int) -> dict:
    """Square of side s with a semicircle on its right side BC, bulging out."""
    h = Fraction(s, 2)
    return {
        "points": [
            _pt("A", 0, 0),
            _pt("B", s, 0),
            _pt("C", s, s),
            _pt("D", 0, s),
            _pt("M", s, float(h)),
        ],
        "segments": [
            {"from": "A", "to": "B", "label": f"{s} cm"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "D"},
            {"from": "D", "to": "A"},
        ],
        "arcs": [
            {"center": "M", "radius": float(h), "start_deg": -90, "end_deg": 90, "label": None}
        ],
        "angles": [{"at": "D", "from": "A", "to": "C", "right": True}],
        "shaded": [
            {
                "boundary": ["A", "B", "C", "D"],
                "arcs": [{"from": "B", "to": "C", "center": "M", "radius": float(h), "sweep": 1}],
            }
        ],
        "labels": [],
        "lengths": {"A-B": s},
        "radii": {"M": float(h)},
    }


def _medium_square_semicircle(g: dict, pi: str, *, area: bool) -> dict:
    s = g["s"]
    p = pi_of(pi)
    lead = (
        f"The figure is made up of a square of side {s} cm and a semicircle. "
        f"The side of the square is the diameter of the semicircle. {_take(pi)} "
    )
    if area:
        semi = p * s * s / 8
        exact = s * s + semi
        steps = [
            f"{_take(pi)} Area of the square = {s} × {s} = {s * s} cm².",
            f"Radius = {s} ÷ 2 = {_n(Fraction(s, 2))} cm. Area of the semicircle = "
            f"½ × {pi} × {_n(Fraction(s, 2))} × {_n(Fraction(s, 2))} = {_n(semi)} cm².",
            f"Area of the figure = {s * s} + {_n(semi)} = {_n(exact)} cm².",
        ]
        wrong: Distractors = [
            (s * s + 2 * semi, "a whole circle, not a semicircle"),
            (s * s + 4 * semi, "used the side as the radius of the semicircle"),
            (Fraction(s * s), "the square only"),
            (s * s - semi, "took the semicircle away instead of adding it"),
        ]
        return {
            **_square_semicircle(s),
            "answer": format_measure(exact, AREA_UNIT),
            "text": lead + "Find the area of the figure.",
            "steps": steps,
            "wrong": wrong,
        }
    arc = p * s / 2
    exact = 3 * s + arc
    steps = [
        f"{_take(pi)} Curved edge = ½ × {pi} × {s} = {_n(arc)} cm.",
        f"Straight edges = 3 × {s} = {3 * s} cm (the side inside the figure is not part of "
        "its perimeter).",
        f"Perimeter = {3 * s} + {_n(arc)} = {_n(exact)} cm.",
    ]
    wrong = [
        (4 * s + arc, "added the side inside the figure too"),
        (3 * s + 2 * arc, "a whole circle's circumference, not a semicircle's"),
        (3 * s + 4 * arc, "used the side as the radius of a whole circle"),
        (2 * s + arc, "counted only two sides of the square"),
    ]
    return {
        **_square_semicircle(s),
        "answer": format_measure(exact, LEN_UNIT),
        "text": lead + "Find the perimeter of the figure.",
        "steps": steps,
        "wrong": wrong,
    }


def _medium_quarter_perimeter(g: dict, pi: str) -> dict:
    r = g["r"]
    p = pi_of(pi)
    arc = p * r / 2
    exact = 2 * r + arc
    return {
        **_quarter_figure(r, shaded=True),
        "answer": format_measure(exact, LEN_UNIT),
        "text": f"The figure shows a quarter circle with centre O and radius {r} cm. "
        f"{_take(pi)} Find the perimeter of the figure.",
        "steps": [
            f"{_take(pi)} Curved edge = ¼ × 2 × {pi} × {r} = {_n(arc)} cm.",
            f"The two radii = 2 × {r} = {2 * r} cm.",
            f"Perimeter = {_n(arc)} + {2 * r} = {_n(exact)} cm.",
        ],
        "wrong": [
            (arc, "the curved edge only (forgot the two straight edges)"),
            (r + arc, "added only one radius"),
            (2 * r + 2 * arc, "used a semicircle's curved edge"),
            (p * r * r / 4, "the area, not the perimeter"),
        ],
    }


def _rect_cutout(L: int, W: int) -> dict:
    """Rectangle L × W with a semicircle (diameter W) cut out of its right side BC."""
    h = Fraction(W, 2)
    return {
        "points": [
            _pt("A", 0, 0),
            _pt("B", L, 0),
            _pt("C", L, W),
            _pt("D", 0, W),
            _pt("M", L, float(h)),
        ],
        "segments": [
            {"from": "A", "to": "B", "label": f"{L} cm"},
            {"from": "C", "to": "D"},
            {"from": "D", "to": "A", "label": f"{W} cm"},
        ],
        "arcs": [
            {"center": "M", "radius": float(h), "start_deg": 90, "end_deg": 270, "label": None}
        ],
        "angles": [{"at": "D", "from": "A", "to": "C", "right": True}],
        "shaded": [
            {
                "boundary": ["A", "B", "C", "D"],
                "arcs": [{"from": "B", "to": "C", "center": "M", "radius": float(h), "sweep": 0}],
            }
        ],
        "labels": [],
        "lengths": {"A-B": L, "D-A": W},
        "radii": {"M": float(h)},
    }


def _medium_rect_cutout(g: dict, pi: str, *, area: bool) -> dict:
    L, W = g["L"], g["W"]
    p = pi_of(pi)
    lead = (
        f"A semicircle is cut out of a rectangle measuring {L} cm by {W} cm, as shown. "
        f"The diameter of the semicircle is the {W}-cm side of the rectangle. {_take(pi)} "
    )
    rw = _n(Fraction(W, 2))
    if area:
        semi = p * W * W / 8
        exact = L * W - semi
        return {
            **_rect_cutout(L, W),
            "answer": format_measure(exact, AREA_UNIT),
            "text": lead + "Find the area of the shaded figure.",
            "steps": [
                f"{_take(pi)} Area of the rectangle = {L} × {W} = {L * W} cm².",
                f"Radius = {W} ÷ 2 = {rw} cm. Area of the semicircle = ½ × {pi} × {rw} × {rw} "
                f"= {_n(semi)} cm².",
                f"Shaded area = {L * W} − {_n(semi)} = {_n(exact)} cm².",
            ],
            "wrong": [
                (L * W - 2 * semi, "took away a whole circle"),
                (L * W + semi, "added the semicircle instead of taking it away"),
                (Fraction(L * W), "the rectangle only"),
                (L * W - 4 * semi, "used the diameter as the radius"),
                (L * W - p * W / 2, "took away the curved edge's length, not its area"),
                (2 * L + W + p * W / 2, "the perimeter, not the area"),
            ],
        }
    arc = p * W / 2
    exact = 2 * L + W + arc
    return {
        **_rect_cutout(L, W),
        "answer": format_measure(exact, LEN_UNIT),
        "text": lead + "Find the perimeter of the shaded figure.",
        "steps": [
            f"{_take(pi)} Curved edge = ½ × {pi} × {W} = {_n(arc)} cm.",
            f"Straight edges = {L} + {L} + {W} = {2 * L + W} cm (the side that was cut out is "
            "not an edge).",
            f"Perimeter = {2 * L + W} + {_n(arc)} = {_n(exact)} cm.",
        ],
        "wrong": [
            (2 * L + 2 * W + arc, "added the side that was cut out"),
            (2 * L + 2 * W, "the rectangle's perimeter"),
            (2 * L + W + 2 * arc, "a whole circle's circumference, not a semicircle's"),
            (2 * L + arc, "left out the other short side"),
        ],
    }


MEDIUM: dict[str, Callable[[dict, str], dict]] = {
    "square_semicircle_perimeter": lambda g, pi: _medium_square_semicircle(g, pi, area=False),
    "square_semicircle_area": lambda g, pi: _medium_square_semicircle(g, pi, area=True),
    "quarter_circle_perimeter": _medium_quarter_perimeter,
    "rectangle_cutout_area": lambda g, pi: _medium_rect_cutout(g, pi, area=True),
    "rectangle_cutout_perimeter": lambda g, pi: _medium_rect_cutout(g, pi, area=False),
}


def _medium_givens(template: str, pi: str, rng: random.Random) -> dict:
    sevens = pi == "22/7"
    if template == "square_semicircle_perimeter":
        return {"s": 7 * rng.randint(1, 3) if sevens else rng.randint(6, 20)}
    if template == "square_semicircle_area":  # radius s ÷ 2 must be whole (22/7: a 7s)
        return {"s": 14 * rng.randint(1, 2) if sevens else 2 * rng.randint(3, 10)}
    if template == "quarter_circle_perimeter":
        return {"r": 7 * rng.randint(1, 3) if sevens else rng.randint(5, 20)}
    if template == "rectangle_cutout_area":
        W = 14 * rng.randint(1, 2) if sevens else 2 * rng.randint(3, 10)
    else:
        W = 7 * rng.randint(1, 3) if sevens else rng.randint(6, 20)
    # long enough to hold the semicircle, and never a square
    return {"L": rng.choice([x for x in range(W // 2 + 4, W // 2 + 19) if x != W]), "W": W}


# ====================================================================== hard


def _square(s: int, extra: list[dict]) -> tuple[list[dict], list[dict]]:
    pts = [_pt("A", 0, 0), _pt("B", s, 0), _pt("C", s, s), _pt("D", 0, s), *extra]
    segs = [
        {"from": "A", "to": "B", "label": f"{s} cm"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ]
    return pts, segs


def _hard_leaf(g: dict, pi: str) -> dict:
    """Square ABCD; quarter circles centred A and C (radius s) overlap in a leaf B–D."""
    s = g["s"]
    p = pi_of(pi)
    # E, the middle of arc BD (centre A), only splits the leaf's outline into three points.
    e = s * math.sqrt(0.5)
    pts, segs = _square(s, [{"id": "E", "x": e, "y": e}])
    quarter = p * s * s / 4
    tri = Fraction(s * s, 2)
    half = quarter - tri
    exact = 2 * half
    return _fig(
        points=pts,
        segments=segs,
        arcs=[
            {"center": "A", "radius": s, "start_deg": 0, "end_deg": 90, "label": None},
            {"center": "C", "radius": s, "start_deg": 180, "end_deg": 270, "label": None},
        ],
        shaded=[
            {
                "boundary": ["B", "E", "D"],
                "arcs": [
                    {"from": "B", "to": "E", "center": "A", "radius": s, "sweep": 1},
                    {"from": "E", "to": "D", "center": "A", "radius": s, "sweep": 1},
                    {"from": "D", "to": "B", "center": "C", "radius": s, "sweep": 1},
                ],
            }
        ],
        labels=_labels(["A", "B", "C", "D"]),
        lengths={"A-B": s},
        radii={"A": s, "C": s},
        answer=format_measure(exact, AREA_UNIT),
        text=f"ABCD is a square of side {s} cm. Two quarter circles are drawn inside it, "
        f"one with centre A and one with centre C. {_take(pi)} "
        "Find the area of the shaded part.",
        steps=[
            f"{_take(pi)} Area of one quarter circle = ¼ × {pi} × {s} × {s} = {_n(quarter)} cm².",
            f"Area of triangle ABD = ½ × {s} × {s} = {_n(tri)} cm². Half of the shaded part = "
            f"{_n(quarter)} − {_n(tri)} = {_n(half)} cm².",
            f"Shaded area = 2 × {_n(half)} = {_n(exact)} cm².",
        ],
        wrong=[
            (half, "found only half of the shaded part"),
            (2 * quarter, "added the two quarter circles without taking away the square"),
            (s * s - exact, "the unshaded part of the square"),
            (s * s - quarter, "the square minus one quarter circle"),
        ],
    )


def _quarter_semi(s: int, *, area: bool) -> dict:
    """Square ABCD; a quarter circle centre A (arc BD) and a semicircle on AB inside it.

    Perimeter: the shaded part lies inside the quarter circle and outside the semicircle
    (bounded by AD, arc DB and the semicircle). Area: two shaded parts, the corner of the
    square outside the quarter circle and the semicircle itself. F, the bottom of the
    semicircle, is the centre of the square."""
    h = Fraction(s, 2)
    pts, segs = _square(s, [_pt("M", float(h), 0), _pt("F", float(h), float(h))])
    semi_arc = {"center": "M", "radius": float(h), "sweep": 1}
    if area:
        shaded = [
            {
                "boundary": ["B", "C", "D"],
                "arcs": [{"from": "D", "to": "B", "center": "A", "radius": s, "sweep": 0}],
            },
            {
                "boundary": ["A", "B", "F"],
                "arcs": [
                    {"from": "B", "to": "F", **semi_arc},
                    {"from": "F", "to": "A", **semi_arc},
                ],
            },
        ]
    else:
        shaded = [
            {
                "boundary": ["A", "D", "B"],
                "arcs": [
                    {"from": "D", "to": "B", "center": "A", "radius": s, "sweep": 0},
                    {"from": "B", "to": "A", **semi_arc},
                ],
            }
        ]
    return {
        "points": pts,
        "segments": segs,
        "arcs": [
            {"center": "A", "radius": s, "start_deg": 0, "end_deg": 90, "label": None},
            {"center": "M", "radius": float(h), "start_deg": 0, "end_deg": 180, "label": None},
        ],
        "angles": [],
        "shaded": shaded,
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"A-B": s},
        "radii": {"A": s, "M": float(h)},
    }


_QS_LEAD = (
    "ABCD is a square of side {s} cm. A quarter circle with centre A and a semicircle "
    "with diameter AB are drawn inside it. "
)


def _hard_quarter_semi_area(g: dict, pi: str) -> dict:
    s = g["s"]
    p = pi_of(pi)
    h = Fraction(s, 2)
    quarter = p * s * s / 4
    corner = s * s - quarter
    semi = p * h * h / 2
    exact = corner + semi
    return {
        **_quarter_semi(s, area=True),
        "answer": format_measure(exact, AREA_UNIT),
        "text": _QS_LEAD.format(s=s) + f"{_take(pi)} Find the total area of the shaded parts.",
        "steps": [
            f"{_take(pi)} Area of the quarter circle = ¼ × {pi} × {s} × {s} = {_n(quarter)} cm². "
            f"Shaded corner = {s} × {s} − {_n(quarter)} = {_n(corner)} cm².",
            f"Radius of the semicircle = {s} ÷ 2 = {_n(h)} cm. Area of the semicircle = "
            f"½ × {pi} × {_n(h)} × {_n(h)} = {_n(semi)} cm².",
            f"Total shaded area = {_n(corner)} + {_n(semi)} = {_n(exact)} cm².",
        ],
        "wrong": [
            (corner, "the shaded corner only (left out the semicircle)"),
            (corner - semi, "took the semicircle away instead of adding it"),
            (corner + 2 * semi, "a whole circle instead of the semicircle"),
            (s * s - exact, "the unshaded part of the square"),
        ],
    }


def _hard_quarter_semi_perimeter(g: dict, pi: str) -> dict:
    """In terms of π: AD + quarter arc DB + semicircle arc BA = sπ + s."""
    s = g["s"]
    h = s // 2
    return {
        **_quarter_semi(s, area=False),
        "answer": {
            "type": "expression",
            "terms": [{"coefficient": s, "symbol": "π"}, {"coefficient": s, "symbol": None}],
            "unit": LEN_UNIT,
        },
        "text": _QS_LEAD.format(s=s) + "Find the perimeter of the shaded part. "
        "Leave your answer in terms of π.",
        "steps": [
            f"Curved edge of the quarter circle = ¼ × 2 × π × {s} = {h}π cm.",
            f"Curved edge of the semicircle = ½ × π × {s} = {h}π cm.",
            f"The shaded part is bounded by the two curved edges and AD, so its perimeter = "
            f"{h}π + {h}π + {s} = ({s}π + {s}) cm.",
        ],
        "wrong": [],  # no multiple-choice copy of an answer in terms of π
    }


def _rect_two_quarters(s: int) -> dict:
    """Rectangle ABCD, AB = 2s, AD = s; quarter circles centred D and C (radius s) meet at
    M, the midpoint of DC. The shaded part lies between the arcs and AB."""
    pts = [
        _pt("A", 0, 0),
        _pt("B", 2 * s, 0),
        _pt("C", 2 * s, s),
        _pt("D", 0, s),
        _pt("M", s, s),
    ]
    segs = [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "D", "to": "C", "label": f"{2 * s} cm"},
        {"from": "D", "to": "A", "label": f"{s} cm"},
    ]
    return {
        "points": pts,
        "segments": segs,
        "arcs": [
            {"center": "D", "radius": s, "start_deg": -90, "end_deg": 0, "label": None},
            {"center": "C", "radius": s, "start_deg": 180, "end_deg": 270, "label": None},
        ],
        "angles": [],
        "shaded": [
            {
                "boundary": ["A", "B", "M"],
                "arcs": [
                    {"from": "B", "to": "M", "center": "C", "radius": s, "sweep": 0},
                    {"from": "M", "to": "A", "center": "D", "radius": s, "sweep": 0},
                ],
            }
        ],
        "labels": _labels(["A", "B", "C", "D"]),
        "lengths": {"D-C": 2 * s, "D-A": s},
        "radii": {"D": s, "C": s},
    }


_RQ_LEAD = (
    "ABCD is a rectangle with DC = {d} cm and AD = {s} cm. Two quarter circles with centres "
    "D and C are drawn inside it. They meet at the midpoint of DC. {take} "
)


def _hard_rect_two_quarters(g: dict, pi: str, *, area: bool) -> dict:
    s = g["s"]
    p = pi_of(pi)
    lead = _RQ_LEAD.format(d=2 * s, s=s, take=_take(pi))
    if area:
        quarter = p * s * s / 4
        rect = 2 * s * s
        exact = rect - 2 * quarter
        return {
            **_rect_two_quarters(s),
            "answer": format_measure(exact, AREA_UNIT),
            "text": lead + "Find the area of the shaded part.",
            "steps": [
                f"{_take(pi)} Area of the rectangle = {2 * s} × {s} = {rect} cm².",
                f"Area of one quarter circle = ¼ × {pi} × {s} × {s} = {_n(quarter)} cm². "
                f"Two quarter circles = {_n(2 * quarter)} cm².",
                f"Shaded area = {rect} − {_n(2 * quarter)} = {_n(exact)} cm².",
            ],
            "wrong": [
                (rect - quarter, "took away only one quarter circle"),
                (2 * quarter, "the two quarter circles, not the shaded part"),
                (rect - 4 * quarter, "took away two semicircles"),
                (s * s - quarter, "half of the shaded part"),
            ],
        }
    arc = p * s / 2
    exact = 2 * s + 2 * arc
    return {
        **_rect_two_quarters(s),
        "answer": format_measure(exact, LEN_UNIT),
        "text": lead + "Find the perimeter of the shaded part.",
        "steps": [
            f"{_take(pi)} Curved edge of one quarter circle = ¼ × 2 × {pi} × {s} = {_n(arc)} cm.",
            f"The shaded part is bounded by the two curved edges and AB = {2 * s} cm.",
            f"Perimeter = {_n(arc)} + {_n(arc)} + {2 * s} = {_n(exact)} cm.",
        ],
        "wrong": [
            (2 * arc, "the two curved edges only (forgot AB)"),
            (2 * s + arc, "counted only one curved edge"),
            (6 * s + 2 * arc, "added AD, BC and AB"),
            (2 * s + 4 * arc, "used semicircles instead of quarter circles"),
        ],
    }


HARD: dict[str, Callable[[dict, str], dict]] = {
    "leaf_area": _hard_leaf,
    "quarter_semicircle_area": _hard_quarter_semi_area,
    "quarter_semicircle_perimeter": _hard_quarter_semi_perimeter,
    "rectangle_quarters_area": lambda g, pi: _hard_rect_two_quarters(g, pi, area=True),
    "rectangle_quarters_perimeter": lambda g, pi: _hard_rect_two_quarters(g, pi, area=False),
}


def _hard_givens(template: str, pi: str, rng: random.Random) -> dict:
    sevens = pi == "22/7"
    if template == "leaf_area":  # ¼ × 3.14 × s × s ends in 2 dp when s is even
        return {"s": 7 * rng.randint(1, 3) if sevens else 2 * rng.randint(3, 10)}
    if template == "quarter_semicircle_area":  # the semicircle's radius s ÷ 2 is whole
        return {"s": 14 * rng.randint(1, 2) if sevens else 2 * rng.randint(3, 10)}
    if template == "quarter_semicircle_perimeter":
        return {"s": 2 * rng.randint(3, 10)}
    if template == "rectangle_quarters_area":
        return {"s": 7 * rng.randint(1, 3) if sevens else 2 * rng.randint(3, 10)}
    return {"s": 7 * rng.randint(1, 3) if sevens else rng.randint(5, 20)}


# ====================================================================== solvers


def _step_keys(n: int) -> list[str]:
    return [f"step{i + 1}" for i in range(n)]


class _CirclesSolver:
    """Shared solve / validate / diagram / distractors; a rung supplies ``_build`` + sampling."""

    TEMPLATES: dict

    def _build(self, params: dict) -> dict:  # pragma: no cover - overridden
        raise NotImplementedError

    def _out(self, template: str, pi: str, givens: dict, built: dict, **extra: str) -> dict:
        out = {"template": template, "pi": pi, "givens": givens, **extra}
        out["lengths"] = built["lengths"]
        if built["radii"]:
            out["radii"] = built["radii"]
        return out

    def solve(self, params: dict) -> dict:
        built = self._build(params)
        inter = {"question_text": built["text"]}
        inter.update(zip(_step_keys(len(built["steps"])), built["steps"], strict=True))
        return {"answer": built["answer"], "intermediates": inter}

    def distractors(self, params: dict, solution: dict) -> Distractors:
        """Common wrong answers in the answer's own unit, best first (EXA-122)."""
        built = self._build(params)
        right = built["answer"].get("value")
        return [
            (Fraction(v), why)
            for v, why in built["wrong"]
            if v > 0 and (right is None or Fraction(v) != Fraction(str(right)))
        ]

    def validate(self, params: dict, solution: dict) -> dict:
        built = self._build(params)
        answer = solution["answer"]
        checks: dict[str, bool] = {
            "template_known": params["template"] in self.TEMPLATES,
            "answer_matches_figure": answer == built["answer"],
            "answer_independent": answer == _expected(params),
        }
        if answer["type"] != "expression":
            checks["positive"] = Fraction(str(answer["value"])) > 0
        return {"ok": all(checks.values()), "checks": checks}

    def diagram(self, params: dict, solution: dict) -> dict:
        built = self._build(params)
        return {
            "type": "geometry_figure",
            "unit": "cm",
            "points": built["points"],
            "segments": built["segments"],
            "arcs": built["arcs"],
            "angles": built["angles"],
            "shaded": built["shaded"],
            "labels": built["labels"],
        }


def _expected(params: dict) -> dict:
    """The answer from one closed formula per template (a second path to ``_build``)."""
    t, g, pi = params["template"], params["givens"], params["pi"]
    if t == "quarter_semicircle_perimeter":
        s = g["s"]
        return {
            "type": "expression",
            "terms": [{"coefficient": s, "symbol": "π"}, {"coefficient": s, "symbol": None}],
            "unit": LEN_UNIT,
        }
    p = pi_of(pi)
    r = g.get("r", 0)
    s = g.get("s", 0)
    L, W = g.get("L", 0), g.get("W", 0)
    formulas: dict[str, tuple[Fraction, str]] = {
        "circle_circumference": (2 * p * r, LEN_UNIT),
        "circle_area": (p * r * r, AREA_UNIT),
        "semicircle_area": (p * r * r / 2, AREA_UNIT),
        "quarter_circle_area": (p * r * r / 4, AREA_UNIT),
        "square_semicircle_perimeter": (3 * s + p * s / 2, LEN_UNIT),
        "square_semicircle_area": (s * s + p * s * s / 8, AREA_UNIT),
        "quarter_circle_perimeter": (2 * r + p * r / 2, LEN_UNIT),
        "rectangle_cutout_area": (L * W - p * W * W / 8, AREA_UNIT),
        "rectangle_cutout_perimeter": (2 * L + W + p * W / 2, LEN_UNIT),
        "leaf_area": (s * s * (p / 2 - 1), AREA_UNIT),
        "quarter_semicircle_area": (s * s - p * s * s / 8, AREA_UNIT),
        "rectangle_quarters_area": (s * s * (2 - p / 2), AREA_UNIT),
        "rectangle_quarters_perimeter": (2 * s + p * s, LEN_UNIT),
    }
    value, unit = formulas[t]
    return format_measure(value, unit)


class CirclesEasySolver(_CirclesSolver):
    TEMPLATES = EASY

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(EASY))
        pi = _pick_pi(rng)
        given_as = (
            "radius" if template == "quarter_circle_area" else rng.choice(["radius", "diameter"])
        )
        givens = {"r": _easy_radius(template, pi, given_as, rng)}
        built = EASY[template](givens, pi, given_as)
        return self._out(template, pi, givens, built, given_as=given_as)

    def _build(self, params: dict) -> dict:
        return EASY[params["template"]](params["givens"], params["pi"], params["given_as"])


class CirclesMediumSolver(_CirclesSolver):
    TEMPLATES = MEDIUM

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(MEDIUM))
        pi = _pick_pi(rng)
        givens = _medium_givens(template, pi, rng)
        return self._out(template, pi, givens, MEDIUM[template](givens, pi))

    def _build(self, params: dict) -> dict:
        return MEDIUM[params["template"]](params["givens"], params["pi"])


class CirclesHardSolver(_CirclesSolver):
    TEMPLATES = HARD

    def sample(self, schema: dict, rng: random.Random) -> dict:
        template = rng.choice(sorted(HARD))
        pi = TERMS if template == "quarter_semicircle_perimeter" else _pick_pi(rng)
        givens = _hard_givens(template, pi, rng)
        return self._out(template, pi, givens, HARD[template](givens, pi))

    def _build(self, params: dict) -> dict:
        return HARD[params["template"]](params["givens"], params["pi"])


register("circles_easy", CirclesEasySolver())
register("circles_medium", CirclesMediumSolver())
register("circles_hard", CirclesHardSolver())
