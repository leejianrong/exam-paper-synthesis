"""Independent correctness authority for the P6 Circles ladder (EXA-149).

Two re-derivations per question, neither calling the solver:

1. **From the printed stem** (exact ``Fraction`` arithmetic, π as stated): the numbers are
   parsed out of the question text and the answer is recomputed by a *different
   decomposition* from the solver's (circumference as π × d where the solver doubles the
   radius; the leaf as two quarter circles less the square, not twice "quarter less
   triangle"; the gap between two quarter circles in a rectangle as the rectangle less one
   semicircle; and so on).
2. **From the drawn figure**: every shaded region is traced from the figure spec (straight
   edges and SVG-style arcs, by ``from``/``to``/``center``/``sweep``) into a dense polygon,
   and its area (shoelace) or outline length is measured numerically with the true π. The
   printed answer, which uses π = 3.14 or 22/7, must agree within the error that the π
   approximation alone explains, and every distractor the hook offers must not. An answer
   "in terms of π" is evaluated with the true π and must match the traced outline closely.
   So the shading on the page is exactly the region the answer measures.

Unshaded easy figures are measured from their arcs (a full, half or quarter turn).
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

import pytest
from exam_engine import canonical, expression, mcq
from exam_engine.edits import available_ops
from exam_engine.pipeline import generate
from invariants import single_part_answer

SEEDS = range(1, 301)
CODES = ["circles_easy", "circles_medium", "circles_hard"]
MARKS = {"circles_easy": 1, "circles_medium": 2, "circles_hard": 3}
TEMPLATES = {
    "circles_easy": {
        "circle_area",
        "circle_circumference",
        "quarter_circle_area",
        "semicircle_area",
    },
    "circles_medium": {
        "quarter_circle_perimeter",
        "rectangle_cutout_area",
        "rectangle_cutout_perimeter",
        "square_semicircle_area",
        "square_semicircle_perimeter",
    },
    "circles_hard": {
        "leaf_area",
        "quarter_semicircle_area",
        "quarter_semicircle_perimeter",
        "rectangle_quarters_area",
        "rectangle_quarters_perimeter",
    },
}
# π = 3.14 or 22/7 differs from π by < 0.0016, i.e. < 0.051% of π. Every answer here is
# (positive π part) ± (whole part) with the π part at most ~2.4x the answer (the leaf), so
# the printed answer may differ from the true-π figure by at most ~0.13%.
_PI_TOL = 0.002
_TRACE_STEPS = 720  # polygon points per arc


# ------------------------------------------------------------------ the printed stem


def _pi(text: str) -> Fraction | None:
    m = re.search(r"Take π = (3\.14|22/7)", text)
    if m is None:
        assert "in terms of π" in text, text
        return None
    return Fraction(22, 7) if m[1] == "22/7" else Fraction(314, 100)


def _num(pattern: str, text: str) -> int:
    m = re.search(pattern, text)
    assert m, (pattern, text)
    return int(m[1])


def _from_stem(text: str) -> tuple[Fraction, str] | None:
    """(answer, unit) recomputed from the question as printed; None for "in terms of π"."""
    p = _pi(text)
    if p is None:
        return None
    if text.startswith("The figure shows a circle"):
        d = (
            2 * _num(r"radius (\d+) cm", text)
            if "radius" in text
            else _num(r"diameter (\d+) cm", text)
        )
        if "circumference" in text:
            return p * d, "cm"
        return p * Fraction(d, 2) ** 2, "cm^2"
    if text.startswith("The figure shows a semicircle"):
        d = (
            2 * _num(r"radius (\d+) cm", text)
            if "radius" in text
            else _num(r"diameter (\d+) cm", text)
        )
        return p * d * d / 8, "cm^2"
    if text.startswith("The figure shows a quarter circle"):
        r = _num(r"radius (\d+) cm", text)
        if "perimeter" in text:  # a quarter of the circumference π × 2r, plus two radii
            return p * (2 * r) / 4 + r + r, "cm"
        return (p * r * r) / 4, "cm^2"
    if "made up of a square" in text:
        s = _num(r"square of side (\d+) cm", text)
        if "perimeter" in text:  # half the circumference of a circle of diameter s
            return s + s + s + (p * s) / 2, "cm"
        return s * s + (p * Fraction(s, 2) ** 2) / 2, "cm^2"
    if "cut out of a rectangle" in text:
        m = re.search(r"measuring (\d+) cm by (\d+) cm", text)
        L, W = int(m[1]), int(m[2])
        if "perimeter" in text:  # the rectangle's perimeter, less the cut side, plus the arc
            return 2 * (L + W) - W + (p * W) / 2, "cm"
        return L * W - (p * Fraction(W, 2) ** 2) / 2, "cm^2"
    if "ABCD is a rectangle" in text:
        s = _num(r"AD = (\d+) cm", text)
        assert _num(r"DC = (\d+) cm", text) == 2 * s
        # The two quarter circles of radius s make one semicircle of radius s.
        if "perimeter" in text:
            return 2 * s + (2 * p * s) / 2, "cm"
        return 2 * s * s - (p * s * s) / 2, "cm^2"
    s = _num(r"square of side (\d+) cm", text)
    if "centre A and one with centre C" in text:  # leaf: both quarter circles less the square
        return 2 * (p * s * s / 4) - s * s, "cm^2"
    if "semicircle with diameter AB" in text:  # shaded = square − (quarter − semicircle)
        return s * s - (p * s * s / 4 - p * Fraction(s, 2) ** 2 / 2), "cm^2"
    raise AssertionError(f"unrecognised stem: {text}")


def _terms_from_stem(text: str) -> tuple[Fraction, Fraction]:
    """(π coefficient, number) of a perimeter asked in terms of π, from the printed question:
    each curved edge as its fraction of a whole circumference π × d, plus the straight edges."""
    assert "Leave your answer in terms of π." in text and "perimeter" in text, text
    if text.startswith("The figure shows a quarter circle"):
        r = _num(r"radius (\d+) cm", text)
        return Fraction(2 * r, 4), Fraction(r + r)  # a quarter of π × 2r; two radii
    if "made up of a square" in text:
        s = _num(r"square of side (\d+) cm", text)
        return Fraction(s, 2), Fraction(s + s + s)  # half of π × s; three sides
    if "semicircle with diameter AB" in text:
        s = _num(r"square of side (\d+) cm", text)
        # a quarter of π × 2s (centre A), half of π × s (diameter AB), and the side AD
        return Fraction(2 * s, 4) + Fraction(s, 2), Fraction(s)
    raise AssertionError(f"unrecognised stem: {text}")


def _pi_answer(a: Fraction, b: Fraction) -> dict:
    terms = [{"coefficient": float(a), "symbol": "π"}]
    if b:
        terms.append({"coefficient": float(b), "symbol": None})
    return {"type": "expression", "terms": terms, "unit": "cm"}


# ------------------------------------------------------------------ the drawn figure


def _arc_points(p, q, c, sweep: int, large: int) -> list[tuple[float, float]]:
    """Points from p to q along the circle centred c (y down, as SVG: sweep 1 = increasing
    angle). Asserts the endpoints lie on that circle and the large-arc flag agrees."""
    r1 = math.dist(p, c)
    assert abs(r1 - math.dist(q, c)) < 1e-6, (p, q, c)
    a1 = math.atan2(p[1] - c[1], p[0] - c[0])
    a2 = math.atan2(q[1] - c[1], q[0] - c[0])
    delta = (a2 - a1) % (2 * math.pi) if sweep else -((a1 - a2) % (2 * math.pi))
    assert (abs(delta) > math.pi) == bool(large), (delta, large)
    return [
        (
            c[0] + r1 * math.cos(a1 + delta * k / _TRACE_STEPS),
            c[1] + r1 * math.sin(a1 + delta * k / _TRACE_STEPS),
        )
        for k in range(1, _TRACE_STEPS + 1)
    ]


def _trace(region: dict, pts: dict) -> list[tuple[float, float]]:
    boundary = region["boundary"]
    arcs = {(a["from"], a["to"]): a for a in region.get("arcs") or []}
    out = [pts[boundary[0]]]
    for i, a in enumerate(boundary):
        b = boundary[(i + 1) % len(boundary)]
        arc = arcs.get((a, b))
        if arc is None:
            out.append(pts[b])
        else:
            assert math.isclose(math.dist(pts[a], pts[arc["center"]]), float(arc["radius"]))
            out += _arc_points(
                pts[a],
                pts[b],
                pts[arc["center"]],
                int(arc.get("sweep", 0)),
                int(arc.get("large", 0)),
            )
    return out


def _area(poly: list[tuple[float, float]]) -> float:
    return (
        abs(
            sum(
                x1 * y2 - x2 * y1
                for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1], strict=True)
            )
        )
        / 2
    )


def _length(poly: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(poly, poly[1:] + poly[:1], strict=True))


def _from_figure(fig: dict, unit: str) -> float:
    """The measured area / perimeter of the shaded part(s), or of the single arc shape."""
    pts = {p["id"]: (float(p["x"]), float(p["y"])) for p in fig["points"]}
    if fig["shaded"]:
        polys = [_trace(r, pts) for r in fig["shaded"]]
        if unit == "cm^2":
            return sum(_area(p) for p in polys)
        assert len(polys) == 1
        return _length(polys[0])
    # An unshaded easy figure: one shape centred on its arcs' common centre.
    turn = sum(a["end_deg"] - a["start_deg"] for a in fig["arcs"]) / 360
    (r,) = {float(a["radius"]) for a in fig["arcs"]}
    assert turn in (1, 0.5, 0.25), turn
    return turn * math.pi * r * r if unit == "cm^2" else turn * 2 * math.pi * r


def _value(answer: dict) -> Fraction:
    return Fraction(str(answer["value"]))


# ------------------------------------------------------------------ the sweeps


@pytest.mark.parametrize("code", CODES)
def test_every_answer_is_rederived_from_the_stem_and_the_figure(code):
    templates = set()
    for seed in SEEDS:
        obj = generate(code, seed)
        canonical.load(obj)
        where = (code, seed)
        part = obj["question"]["parts"][0]
        answer = single_part_answer(obj)
        templates.add(obj["parameters"]["template"])
        assert obj["question"]["total_marks"] == MARKS[code], where
        assert obj["syllabus"]["level"] == "P6" and obj["syllabus"]["topic"] == "Circles"
        fig = part["diagram"]
        assert fig and fig["type"] == "geometry_figure", where
        assert "toggle-diagram" not in available_ops(obj)  # the figure is mandatory

        text = part["text"]
        unit = answer["unit"]
        assert unit in ("cm", "cm^2"), where
        assert ("perimeter" in text or "circumference" in text) == (unit == "cm"), where
        measured = _from_figure(fig, unit)

        stem = _from_stem(text)
        if stem is None:  # in terms of π
            assert answer["type"] == "expression", where
            assert all(expression.check_expression_consistency(answer).values()), where
            assert expression.expressions_equal(answer, _pi_answer(*_terms_from_stem(text)))
            assert math.isclose(expression.evaluate(answer), measured, rel_tol=1e-5), where
            # every named wrong answer is an expression the figure tells apart (EXA-155)
            slips = mcq.expression_wrong_answers(obj)
            assert len(slips) >= 3, where
            for wrong, why in slips:
                assert not expression.expressions_equal(wrong, answer), (where, why)
                assert not math.isclose(expression.evaluate(wrong), measured, rel_tol=1e-3), (
                    where,
                    why,
                )
            continue
        exact, stem_unit = stem
        assert stem_unit == unit, where
        assert _value(answer) == exact, (where, answer, exact)
        # whole, or exactly 2 decimal places (the π choice keeps answers tidy)
        assert (exact * 100).denominator == 1, where
        assert answer["type"] == ("integer" if exact.denominator == 1 else "decimal"), where
        assert math.isclose(float(exact), measured, rel_tol=_PI_TOL), (where, exact, measured)
        # The figure tells every named wrong answer apart from the right one.
        for wrong, why in mcq.common_wrong_answers(obj):
            assert wrong != exact, (where, why)
            assert not math.isclose(float(wrong), measured, rel_tol=_PI_TOL), (where, why)
    assert templates == TEMPLATES[code]


def test_pi_is_stated_and_mostly_three_point_one_four():
    """Real papers say "Take π = 3.14" about 7 times for each 22/7; both appear here, and
    the medium (EXA-155) and hard rungs leave some answers in terms of π."""
    seen = {"3.14": 0, "22/7": 0, "terms": 0}
    terms = {code: 0 for code in CODES}
    for code in CODES:
        for seed in SEEDS:
            pi = generate(code, seed)["parameters"]["pi"]
            seen[pi] += 1
            terms[code] += pi == "terms"
    assert seen["3.14"] > seen["22/7"] > 0 and seen["terms"] > 0, seen
    assert terms["circles_easy"] == 0 and terms["circles_medium"] > 0 < terms["circles_hard"]
