"""Hypothesis strategies + object builder for the property-based invariant suite.

KAN-237 graduates the KAN-236 seed sweeps to real property-based testing. This
module is **not** a test module (no ``test_`` functions) — it is an importable
helper that provides:

* :func:`build_object` — assemble one canonical object from *externally supplied*
  params (the pipeline steps, minus the internal sampler), so an ``@given`` test
  can drive the engine with Hypothesis-generated params instead of integer seeds.
* one ``@composite`` **param strategy per blueprint rung** that generates valid
  parameter sets directly, with numeric bounds derived from the same ranges the
  YAML param schema / solver documents. Hypothesis explores this space far more
  richly than ``range(1, 400)`` and **shrinks** any failure to a minimal
  counterexample.

The strategies build params the same "by construction" way each solver's
``sample`` does (ADR-0014: constraints satisfied by construction), so the pipeline
never has to reject them. That construction is *input* generation only — the
mathematical **answer** is still produced by ``solve`` and re-derived a different
way by the per-rung invariant test, which stays the independent correctness
authority. The golden fixtures remain the pure regression anchor.
"""

from __future__ import annotations

from math import gcd

from exam_engine.blueprints.base import validate_params
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.blueprints.solvers import geometry_angle_easy as _ga_easy
from exam_engine.blueprints.solvers import geometry_angle_hard as _ga_hard
from exam_engine.blueprints.solvers import geometry_angle_medium as _ga_medium
from exam_engine.blueprints.solvers import geometry_area_easy as _ar_easy
from exam_engine.blueprints.solvers import geometry_area_hard as _ar_hard
from exam_engine.blueprints.solvers import geometry_area_medium as _ar_medium
from exam_engine.canonical import assemble
from exam_engine.diagram import check_consistency
from exam_engine.pipeline import build_part_diagram
from exam_engine.schema import validate_object
from hypothesis import assume
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Object builder — the pipeline, minus the internal sampler.
# ---------------------------------------------------------------------------


def build_object(blueprint_code: str, params: dict, *, seed: int = 0) -> dict:
    """Assemble + schema-validate a canonical object from supplied ``params``.

    Mirrors :func:`exam_engine.pipeline.run_pipeline` but takes the params from a
    Hypothesis strategy instead of the solver's RNG sampler. The params must be a
    valid domain input (asserted); a rare degenerate combination the strategy did
    not exclude is discarded with :func:`assume` rather than reported as a
    correctness failure (the by-construction strategies make this essentially a
    no-op). A diagram/consistency or schema failure is an engine bug and surfaces
    loudly, exactly as in the real pipeline.
    """
    spec = load_blueprint(blueprint_code)
    solver = get_solver(blueprint_code)

    param_errors = validate_params(params, spec.parameter_schema)
    assert param_errors == [], (blueprint_code, param_errors, params)

    solution = solver.solve(params)
    report = solver.validate(params, solution)
    assume(report.get("ok"))

    diagram = build_part_diagram(solver, params, solution)
    if diagram is not None:
        dchecks = check_consistency(diagram, params, solution)
        assert all(dchecks.values()), (blueprint_code, dchecks)

    obj = assemble(
        spec, seed=seed, params=params, solution=solution, report=report, diagram=diagram
    )
    errors = validate_object(obj)
    assert errors == [], (blueprint_code, errors)
    return obj


# ---------------------------------------------------------------------------
# Shared building blocks.
# ---------------------------------------------------------------------------

# Simple, str.format-safe label strings (letters only — no ``{`` / ``}``).
_NAME = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6)


def _distinct_names(n: int) -> st.SearchStrategy[list[str]]:
    return st.lists(_NAME, min_size=n, max_size=n, unique=True)


# ---------------------------------------------------------------------------
# Ratio ladder.
# ---------------------------------------------------------------------------


@st.composite
def ratio_easy_params(draw: st.DrawFn) -> dict:
    names = draw(_distinct_names(2))
    r0 = draw(st.integers(min_value=1, max_value=9))
    r1 = draw(st.integers(min_value=1, max_value=9))
    assume(r0 != r1)
    unit_value = draw(st.integers(min_value=2, max_value=50))
    total = (r0 + r1) * unit_value
    return {"names": names, "ratio": [r0, r1], "total": total}


@st.composite
def ratio_medium_params(draw: st.DrawFn) -> dict:
    names = draw(_distinct_names(3))
    ratio = [draw(st.integers(min_value=1, max_value=9)) for _ in range(3)]
    assume(len(set(ratio)) > 1)
    unit_value = draw(st.integers(min_value=3, max_value=60))
    total = sum(ratio) * unit_value
    return {"names": names, "ratio": ratio, "total": total}


@st.composite
def ratio_hard_params(draw: st.DrawFn) -> dict:
    names = draw(_distinct_names(2))
    a = draw(st.integers(min_value=1, max_value=9))
    b = draw(st.integers(min_value=1, max_value=9))
    c = draw(st.integers(min_value=1, max_value=9))
    d = draw(st.integers(min_value=1, max_value=9))
    ga, gc = gcd(a, b), gcd(c, d)
    a, b = a // ga, b // ga
    c, d = c // gc, d // gc
    assume(b != d)  # LCM step must be non-trivial
    assume(a * d > c * b)  # A strictly shrinks
    lcm = b * d // gcd(b, d)
    delta_units = a * lcm // b - c * lcm // d
    assume(delta_units > 0)
    unit_value = draw(st.integers(min_value=5, max_value=40))
    spent = delta_units * unit_value
    b_amount = lcm * unit_value
    # spent in [1, 2000] is the schema bound; b_amount <= 2000 is the solver's
    # within-level cap. (The real sampler leaves an out-of-range `spent` to be
    # rejected by the pipeline's param-schema gate + retried; here we exclude it.)
    assume(1 <= spent <= 2000 and b_amount <= 2000)
    return {"names": names, "ratio_before": [a, b], "ratio_after": [c, d], "spent": spent}


# ---------------------------------------------------------------------------
# Percentage ladder.
# ---------------------------------------------------------------------------


@st.composite
def percentage_easy_params(draw: st.DrawFn) -> dict:
    name = draw(_NAME)
    percent = 5 * draw(st.integers(min_value=1, max_value=19))  # 5..95
    whole = 20 * draw(st.integers(min_value=1, max_value=100))  # 20..2000
    return {"name": name, "percent": percent, "whole": whole}


@st.composite
def percentage_medium_params(draw: st.DrawFn, direction: str) -> dict:
    context = draw(_NAME)
    percent = 5 * draw(st.integers(min_value=1, max_value=18))  # 5..90
    original = 20 * draw(st.integers(min_value=1, max_value=100))  # 20..2000
    return {"context": context, "original": original, "percent": percent, "direction": direction}


@st.composite
def percentage_hard_params(draw: st.DrawFn, direction: str) -> dict:
    context = draw(_NAME)
    percent = 5 * draw(st.integers(min_value=1, max_value=16))  # 5..80
    original = 20 * draw(st.integers(min_value=1, max_value=75))  # 20..1500
    factor = 100 + percent if direction == "increase" else 100 - percent
    new_value = original * factor // 100
    return {"context": context, "percent": percent, "direction": direction, "new_value": new_value}


# ---------------------------------------------------------------------------
# Fractions ladder.
# ---------------------------------------------------------------------------


@st.composite
def fractions_easy_params(draw: st.DrawFn) -> dict:
    shape = draw(st.sampled_from(["rectangle", "circle", "bar"]))
    denominator = draw(st.integers(min_value=2, max_value=12))
    numerator = draw(st.integers(min_value=1, max_value=denominator - 1))
    assume(gcd(numerator, denominator) == 1)  # proper fraction in lowest terms
    return {"shape": shape, "numerator": numerator, "denominator": denominator}


@st.composite
def _fraction_pair(draw: st.DrawFn) -> tuple[int, int]:
    d = draw(st.integers(min_value=2, max_value=6))
    n = draw(st.integers(min_value=1, max_value=d - 1))
    return n, d


@st.composite
def fractions_medium_params(draw: st.DrawFn) -> dict:
    name = draw(_NAME)
    n1, d1 = draw(_fraction_pair())
    n2, d2 = draw(_fraction_pair())
    k = draw(st.integers(min_value=2, max_value=15))
    whole = d1 * d2 * k
    return {"name": name, "whole": whole, "n1": n1, "d1": d1, "n2": n2, "d2": d2}


@st.composite
def fractions_hard_params(draw: st.DrawFn) -> dict:
    name = draw(_NAME)
    n1, d1 = draw(_fraction_pair())
    n2, d2 = draw(_fraction_pair())
    k = draw(st.integers(min_value=2, max_value=15))
    left = k * (d1 - n1) * (d2 - n2)
    return {"name": name, "n1": n1, "d1": d1, "n2": n2, "d2": d2, "left": left}


# ---------------------------------------------------------------------------
# Speed ladder.
# ---------------------------------------------------------------------------


@st.composite
def speed_easy_params(draw: st.DrawFn) -> dict:
    name = draw(_NAME)
    speed = draw(st.integers(min_value=10, max_value=120))
    time = draw(st.integers(min_value=1, max_value=12))
    return {"name": name, "speed": speed, "time": time}


@st.composite
def speed_medium_params(draw: st.DrawFn) -> dict:
    name = draw(_NAME)
    # Distinct leg times so the true average never coincides with the mean of the
    # two leg speeds (the misconception the invariant guards).
    t1, t2 = draw(
        st.lists(st.integers(min_value=1, max_value=4), min_size=2, max_size=2, unique=True)
    )
    j = draw(st.integers(min_value=1, max_value=4))  # >= 1 keeps leg speeds unequal
    s2 = draw(st.integers(min_value=20, max_value=50))
    s1 = s2 + (t1 + t2) * j
    return {"name": name, "d1": s1 * t1, "t1": t1, "d2": s2 * t2, "t2": t2}


@st.composite
def speed_hard_params(draw: st.DrawFn) -> dict:
    names = draw(_distinct_names(2))
    s1 = draw(st.integers(min_value=10, max_value=90))
    s2 = draw(st.integers(min_value=10, max_value=90))
    t_meet = draw(st.integers(min_value=1, max_value=6))
    gap = (s1 + s2) * t_meet
    return {"name1": names[0], "name2": names[1], "s1": s1, "s2": s2, "gap": gap}


# ---------------------------------------------------------------------------
# Geometry (Angles) ladder — givens per template; contract map from the builder.
# ---------------------------------------------------------------------------

GEOMETRY_ANGLE_EASY_TEMPLATES = ("straight_line", "at_point", "triangle_sum")
GEOMETRY_ANGLE_MEDIUM_TEMPLATES = ("isosceles_apex", "isosceles_base", "exterior")
GEOMETRY_ANGLE_HARD_TEMPLATES = ("parallelogram", "rhombus", "trapezium")


def _angle_params(mod: object, template: str, givens: dict) -> dict:
    built = mod._BUILDERS[template](givens)  # type: ignore[attr-defined]
    return {"template": template, "givens": givens, "angles": built["given_map"]}


@st.composite
def geometry_angle_easy_params(draw: st.DrawFn, template: str) -> dict:
    if template == "straight_line":
        p = draw(st.integers(min_value=30, max_value=80))
        q = draw(st.integers(min_value=30, max_value=80))
        assume(180 - p - q >= 20)
        givens = {"p": p, "q": q}
    elif template == "at_point":
        a = draw(st.integers(min_value=110, max_value=150))
        c = draw(st.integers(min_value=110, max_value=150))
        assume(40 <= 360 - a - c <= 150)
        givens = {"a": a, "c": c}
    else:  # triangle_sum
        a = draw(st.integers(min_value=35, max_value=80))
        b = draw(st.integers(min_value=35, max_value=80))
        assume(180 - a - b >= 20)
        givens = {"a": a, "b": b}
    return _angle_params(_ga_easy, template, givens)


@st.composite
def geometry_angle_medium_params(draw: st.DrawFn, template: str) -> dict:
    if template == "isosceles_apex":
        apex = 2 * draw(st.integers(min_value=15, max_value=70))  # even -> whole base angle
        givens = {"apex": apex}
    elif template == "isosceles_base":
        givens = {"base": draw(st.integers(min_value=25, max_value=75))}
    else:  # exterior
        b = draw(st.integers(min_value=30, max_value=60))
        ext = draw(st.integers(min_value=80, max_value=150))
        assume(25 <= ext - b <= 130 and 180 - ext >= 20)
        givens = {"b": b, "ext": ext}
    return _angle_params(_ga_medium, template, givens)


@st.composite
def geometry_angle_hard_params(draw: st.DrawFn, template: str) -> dict:
    if template == "parallelogram":
        a = draw(st.integers(min_value=55, max_value=110))
        e = draw(st.integers(min_value=30, max_value=70))
        assume(180 - a - e >= 20)
        givens = {"a": a, "e": e}
    elif template == "rhombus":
        b = 2 * draw(st.integers(min_value=20, max_value=70))  # even -> whole base angle
        givens = {"b": b}
    else:  # trapezium: obtuse a, smaller e -> whole ans = a - e > 0
        a = draw(st.integers(min_value=100, max_value=140))
        e = draw(st.integers(min_value=30, max_value=60))
        givens = {"a": a, "e": e}
    return _angle_params(_ga_hard, template, givens)


# ---------------------------------------------------------------------------
# Geometry (Area) ladder — givens per template; contract maps from the builder.
# ---------------------------------------------------------------------------

GEOMETRY_AREA_EASY_TEMPLATES = ("rectangle", "square", "triangle")
GEOMETRY_AREA_MEDIUM_TEMPLATES = (
    "L_shape",
    "rectangle_plus_triangle",
    "semicircle_area",
    "semicircle_perimeter",
    "inverse_rectangle",
)
GEOMETRY_AREA_HARD_TEMPLATES = (
    "square_minus_quarter",
    "rectangle_with_semicircle_ends",
    "triangle_with_semicircle",
)

# Radii mixing the 22/7 (multiple-of-7) and 3.14 paths, mirroring the samplers.
_SEMICIRCLE_RADII = st.sampled_from([7, 14, 4, 5, 6, 8, 9, 10, 11, 12, 13])


def _area_params(mod: object, template: str, givens: dict) -> dict:
    built = mod._BUILDERS[template](givens)  # type: ignore[attr-defined]
    out = {"template": template, "givens": givens, "lengths": built["lengths"]}
    if built.get("radii"):
        out["radii"] = built["radii"]
    return out


@st.composite
def geometry_area_easy_params(draw: st.DrawFn, template: str) -> dict:
    if template == "rectangle":
        givens = {
            "w": draw(st.integers(min_value=4, max_value=18)),
            "h": draw(st.integers(min_value=3, max_value=15)),
        }
    elif template == "square":
        givens = {"s": draw(st.integers(min_value=3, max_value=15))}
    else:  # triangle — even height keeps 1/2 base*height whole
        givens = {
            "base": draw(st.integers(min_value=5, max_value=18)),
            "height": 2 * draw(st.integers(min_value=2, max_value=7)),
        }
    return _area_params(_ar_easy, template, givens)


@st.composite
def geometry_area_medium_params(draw: st.DrawFn, template: str) -> dict:
    if template == "L_shape":
        big_w = draw(st.integers(min_value=12, max_value=20))
        big_h = draw(st.integers(min_value=9, max_value=14))
        notch_w = draw(st.integers(min_value=3, max_value=big_w - 5))
        notch_h = draw(st.integers(min_value=3, max_value=big_h - 4))
        givens = {"W": big_w, "H": big_h, "w": notch_w, "h": notch_h}
    elif template == "rectangle_plus_triangle":
        givens = {
            "W": draw(st.integers(min_value=6, max_value=14)),
            "H": draw(st.integers(min_value=4, max_value=10)),
            "h": 2 * draw(st.integers(min_value=2, max_value=5)),  # even -> 1/2 W*h whole
        }
    elif template == "inverse_rectangle":
        givens = {
            "length": draw(st.integers(min_value=4, max_value=15)),
            "width": draw(st.integers(min_value=3, max_value=14)),
        }
    else:  # semicircle_area / semicircle_perimeter
        givens = {"r": draw(_SEMICIRCLE_RADII)}
    return _area_params(_ar_medium, template, givens)


@st.composite
def geometry_area_hard_params(draw: st.DrawFn, template: str) -> dict:
    if template == "square_minus_quarter":
        givens = {"s": draw(st.sampled_from([14, 28, 8, 10, 12, 16, 18, 20]))}
    elif template == "rectangle_with_semicircle_ends":
        givens = {
            "L": draw(st.integers(min_value=10, max_value=25)),
            "r": draw(st.sampled_from([7, 14, 4, 5, 6, 8, 9, 10])),
        }
    else:  # triangle_with_semicircle
        givens = {
            "b": draw(st.sampled_from([14, 28, 6, 8, 10, 12, 16])),  # even diameter
            "H": draw(st.integers(min_value=5, max_value=14)),
        }
    return _area_params(_ar_hard, template, givens)
