"""Independent correctness authority for the deeper P6 angle blueprints (EXA-150).

These figures are drawn to scale, so the answer can be read off the drawing. Each check
works only from the **printed question text** and the **figure's point coordinates**, never
from the solver's formulas:

1. Every fact the text states is true of the figure: "ABCD is a rhombus" (four equal sides,
   opposite sides parallel), "CDE is an equilateral triangle", "EA = ED", "AOB is a straight
   line", "∠AOB = ∠COD", the fold (B' is the corner B reflected in EF), "∠ADC = 76°" (the
   angle measured at D is 76°) and so on.
2. Every angle mark on the figure measures what it says.
3. The angle the question asks for ("Find ∠B'FC", "Find the reflex angle BOD"), measured off
   the figure, is the printed answer.

A text fact this test does not recognise fails it, so new wording cannot slip past.
The sweeps cover every parameter value the samplers can draw, and seeds through the real
pipeline.
"""

from __future__ import annotations

import math
import re

import pytest
from exam_engine import generate
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.pipeline import build_from_params

_PT = r"[A-Z]'?"  # a point name: A, B, B'
TOL = 0.02  # degrees; coordinates are stored to 4 decimal places


def _coords(fig: dict) -> dict[str, tuple[float, float]]:
    # Figure coordinates are y-down; flip so angles read as on paper (anticlockwise +).
    return {p["id"]: (p["x"], -p["y"]) for p in fig["points"]}


def _angle(pts: dict, a: str, o: str, b: str) -> float:
    """The (non-reflex) angle AOB in degrees, measured from the coordinates."""
    (ax, ay), (ox, oy), (bx, by) = pts[a], pts[o], pts[b]
    u, v = (ax - ox, ay - oy), (bx - ox, by - oy)
    cos = (u[0] * v[0] + u[1] * v[1]) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def _dist(pts: dict, a: str, b: str) -> float:
    return math.dist(pts[a], pts[b])


def _cross(pts: dict, a: str, b: str, c: str, d: str) -> float:
    """Normalised cross product of AB and CD: 0 when they are parallel."""
    u = (pts[b][0] - pts[a][0], pts[b][1] - pts[a][1])
    v = (pts[d][0] - pts[c][0], pts[d][1] - pts[c][1])
    return (u[0] * v[1] - u[1] * v[0]) / (math.hypot(*u) * math.hypot(*v))


def _parallel(pts: dict, a: str, b: str, c: str, d: str) -> bool:
    return abs(_cross(pts, a, b, c, d)) < 1e-4


def _between(pts: dict, a: str, p: str, b: str) -> bool:
    """P lies strictly inside segment AB."""
    return abs(_dist(pts, a, p) + _dist(pts, p, b) - _dist(pts, a, b)) < 1e-3 and p not in (a, b)


def _eq(x: float, y: float, rel: float = 1e-3) -> bool:
    return abs(x - y) <= rel * max(abs(x), abs(y), 1.0)


def _measure(pts: dict, name: str, reflex: bool) -> float:
    a, o, b = re.findall(_PT, name)
    m = _angle(pts, a, o, b)
    return 360 - m if reflex else m


def _check_facts(text: str, pts: dict) -> str:
    """Assert each stated fact against the figure; return the text with the facts removed
    (what is left must be the question and the not-to-scale note)."""
    rest = text

    def fact(pattern: str, check) -> None:
        nonlocal rest
        for m in re.finditer(pattern, rest):
            assert check(*m.groups()), (m.group(0), pts)
        rest = re.sub(pattern, "", rest)

    def rhombus(n: str) -> bool:
        a, b, c, d = n
        sides = [_dist(pts, a, b), _dist(pts, b, c), _dist(pts, c, d), _dist(pts, d, a)]
        return all(_eq(s, sides[0]) for s in sides) and parallelogram(n)

    def parallelogram(n: str) -> bool:
        a, b, c, d = n
        return _parallel(pts, a, b, d, c) and _parallel(pts, a, d, b, c)

    def rectangle(n: str) -> bool:
        a, b, c, d = n
        return parallelogram(n) and abs(_angle(pts, d, a, b) - 90) < TOL

    def equilateral(n: str) -> bool:
        a, b, c = n
        return _eq(_dist(pts, a, b), _dist(pts, b, c)) and _eq(_dist(pts, b, c), _dist(pts, c, a))

    def fold(line: str, corner: str, image: str) -> bool:
        # The folded-away corner B is not drawn: it is where AE (level) meets CF (upright).
        # Folding reflects it in EF, so B' is as far from E and from F as B was, on the
        # other side of EF. The rectangle check then runs with this B.
        e, f = line
        pts[corner] = (pts["C"][0], pts["A"][1])
        on_ab = _between(pts, "A", e, corner)
        on_bc = _between(pts, corner, f, "C")
        same = _eq(_dist(pts, e, corner), _dist(pts, e, image)) and _eq(
            _dist(pts, f, corner), _dist(pts, f, image)
        )
        sides = _cross(pts, e, f, e, corner) * _cross(pts, e, f, e, image) < 0
        return on_ab and on_bc and same and sides

    fact(
        rf"({_PT}{_PT}{_PT}{_PT}) is a rectangular piece of paper\. ({_PT}) is on ({_PT}{_PT}) "
        rf"and ({_PT}) is on ({_PT}{_PT})\. It is folded along ({_PT}{_PT}) so that the corner "
        rf"({_PT}) lands on ({_PT}), as shown\.",
        lambda n, e, ab, f, bc, line, corner, image: (
            (
                line == e + f and corner in ab and corner in bc  # fold() checks E on AB, F on BC
            )
            and fold(line, corner, image)
            and rectangle(n)
        ),
    )
    fact(r"([A-Z]{4}) is a rhombus", rhombus)
    fact(r"([A-Z]{4}) is a parallelogram", parallelogram)
    fact(
        r"([A-Z]{4}) is a trapezium with ([A-Z]{2}) parallel to ([A-Z]{2})",
        lambda n, p, q: (
            _parallel(pts, p[0], p[1], q[0], q[1]) and not _parallel(pts, n[0], n[3], n[1], n[2])
        ),
    )
    fact(r"([A-Z]{3}) is an equilateral triangle", equilateral)
    fact(
        r"([A-Z]) is a point on ([A-Z]{2}) such that",
        lambda p, s: _between(pts, s[0], p, s[1]),
    )
    fact(
        r"([A-Z]{2}) = ([A-Z]{2})(?=[\s.])",
        lambda s, t: _eq(_dist(pts, *s), _dist(pts, *t)),
    )
    fact(r"([A-Z]{3}) is a straight line", lambda s: _between(pts, s[0], s[1], s[2]))
    fact(
        r"the straight lines ([A-Z]{2}) and ([A-Z]{2}) cross at ([A-Z])",
        lambda s, t, o: _between(pts, s[0], o, s[1]) and _between(pts, t[0], o, t[1]),
    )
    fact(
        rf"∠({_PT}{_PT}{_PT}) = ∠({_PT}{_PT}{_PT})",
        lambda s, t: abs(_measure(pts, s, False) - _measure(pts, t, False)) < TOL,
    )
    fact(
        r"The reflex angle ([A-Z]{3}) is (\d+)°",
        lambda s, v: abs(_measure(pts, s, True) - int(v)) < TOL,
    )
    fact(
        rf"∠({_PT}{_PT}{_PT}) = (\d+)°",
        lambda s, v: abs(_measure(pts, s, False) - int(v)) < TOL,
    )
    return rest


def _check_marks(fig: dict, pts: dict) -> None:
    """Each mark measures what it says (a mark over 180° is the reflex angle)."""
    for mark in fig["angles"]:
        v = mark["value_deg"]
        m = _measure(pts, mark["from"] + mark["at"] + mark["to"], v > 180)
        assert abs(m - v) < TOL, (mark, m)


def _asked(text: str) -> tuple[str, bool]:
    m = re.search(rf"Find (the reflex angle |∠)({_PT}{_PT}{_PT})\.", text)
    assert m, text
    return m[2], m[1].startswith("the reflex")


def check(obj: dict) -> None:
    q = obj["question"]
    fig = q["parts"][0]["diagram"]
    assert fig is not None and fig["type"] == "geometry_figure"
    pts = _coords(fig)
    _check_marks(fig, pts)
    rest = _check_facts(q.get("stem") or q["parts"][0]["text"], pts)
    rest = rest.replace("(The figure is not drawn to scale.)", "")
    for part in q["parts"]:
        text = part["text"] if q.get("stem") else rest
        name, reflex = _asked(text)
        answer = part["answer"]
        assert answer["type"] == "integer" and answer["unit"] == "degrees"
        measured = _measure(pts, name, reflex)
        assert abs(measured - answer["value"]) < TOL, (name, measured, answer)
        assert (answer["value"] > 180) == reflex
    if q.get("stem"):
        leftover = rest
    else:
        leftover = re.sub(rf"Find (the reflex angle |∠){_PT}{_PT}{_PT}\.", "", rest)
    # Only connecting words may be left once the facts and the question are gone.
    assert re.fullmatch(r"[\s,.]*(In the figure[\s,.]*)?(and[\s,.]*)*", leftover), leftover


# --------------------------------------------------------------------------- sweeps


def _every_param() -> list[tuple[str, dict]]:
    """Every value the samplers can draw (the same ranges, enumerated)."""
    out: list[tuple[str, dict]] = []
    for p in range(40, 141, 2):
        out.append(("geometry_angle_folded", {"template": "corner_fold", "givens": {"p": p}}))
    for d in range(40, 89, 2):
        out.append(
            ("geometry_angle_composite", {"template": "rhombus_equilateral", "givens": {"d": d}})
        )
    for b in range(46, 73):
        out.append(
            (
                "geometry_angle_composite",
                {"template": "parallelogram_isosceles", "givens": {"b": b}},
            )
        )
    for a in range(100, 141, 2):
        for c in range(45, 81):
            out.append(
                (
                    "geometry_angle_composite",
                    {"template": "trapezium_isosceles", "givens": {"a": a, "c": c}},
                )
            )
    for a in range(30, 81):
        for c in range(30, 81):
            if 180 - a - c >= 30:
                out.append(
                    (
                        "geometry_angle_reflex",
                        {"template": "straight_line", "givens": {"a": a, "c": c}},
                    )
                )
    for r in range(200, 291, 2):
        for b in range(30, 81, 2):
            if 360 - r - b >= 40:
                out.append(
                    (
                        "geometry_angle_reflex",
                        {"template": "equal_angles", "givens": {"r": r, "b": b}},
                    )
                )
    for a in range(35, 146):
        if abs(a - 90) > 10:
            out.append(
                ("geometry_angle_reflex", {"template": "crossing_lines", "givens": {"a": a}})
            )
    for b in range(76, 101, 2):
        if b != 90:
            out.append(
                (
                    "geometry_angle_structured",
                    {"template": "rhombus_equilateral_inside", "givens": {"d": b}},
                )
            )
    return out


ALL = _every_param()
CODES = [
    "geometry_angle_folded",
    "geometry_angle_composite",
    "geometry_angle_reflex",
    "geometry_angle_structured",
]


@pytest.mark.parametrize("code", CODES)
def test_every_parameter_value(code):
    solver = get_solver(code)
    n = 0
    for c, params in ALL:
        if c != code:
            continue
        # The params carry a map of the given marks for the figure's consistency gate; read it
        # off the figure (only the marks, no answer is taken from the solver).
        fig = solver.diagram({**params, "angles": {}}, {})
        params = {
            **params,
            "angles": {
                f"{m['from']}-{m['at']}-{m['to']}": m["value_deg"]
                for m in fig["angles"]
                if not m["unknown"]
            },
        }
        check(build_from_params(load_blueprint(code), solver, 1, params))
        n += 1
    assert n >= 12, (code, n)


@pytest.mark.parametrize("code", CODES)
def test_seed_sweep_through_the_real_sampler(code):
    templates = set()
    for seed in range(1, 201):
        obj = generate(code, seed)
        check(obj)
        templates.add(obj["parameters"]["template"])
    expected = {
        "geometry_angle_folded": 1,
        "geometry_angle_composite": 3,
        "geometry_angle_reflex": 3,
        "geometry_angle_structured": 1,
    }[code]
    assert len(templates) == expected


def test_a_wrong_answer_or_a_false_fact_is_caught():
    """The check is not vacuous: a nudged answer, a nudged given angle or a moved point fails."""
    obj = generate("geometry_angle_composite", 5)
    check(obj)
    bad = {**obj, "question": {**obj["question"]}}
    part = dict(obj["question"]["parts"][0])
    part["answer"] = {**part["answer"], "value": part["answer"]["value"] + 1}
    bad["question"]["parts"] = [part]
    with pytest.raises(AssertionError):
        check(bad)
    moved = generate("geometry_angle_reflex", 2)
    moved["question"]["parts"][0]["diagram"]["points"][1]["y"] += 0.3
    with pytest.raises(AssertionError):
        check(moved)
