"""Independent correctness authority for the Geometry (Area & Perimeter) ladder.

KAN-230 / KAN-237. For area/perimeter figures there is no unknown *angle*, so the
diagram consistency check does NOT verify the numeric answer — these property
tests are the primary guard that the printed key is right. Per template they
**recompute** the area / perimeter / length independently of ``solve()``: via the
mensuration formula from the figure's labelled dimensions, using the SAME π the
stem states but a DIFFERENT arithmetic path (integer ``//`` on the 22/7 path;
float ``round`` on the 3.14 path — the solver uses exact ``Fraction``). Every
template is exercised via parametrisation, over givens generated directly from the
template's parameter space with shrinking. Each object also schema-validates and
the figure's labelled dims equal the params.

Exact integer arithmetic on the whole-number paths; a small tolerance on the
2-dp decimal (3.14) path (the ticket sanctions comparing rounded values).
"""

from __future__ import annotations

import pytest
from exam_engine.diagram import _leading_number
from exam_engine.edits import available_ops
from hypothesis import given
from hypothesis import strategies as st
from strategies import (
    GEOMETRY_AREA_EASY_TEMPLATES,
    GEOMETRY_AREA_HARD_TEMPLATES,
    GEOMETRY_AREA_MEDIUM_TEMPLATES,
    build_object,
    geometry_area_easy_params,
    geometry_area_hard_params,
    geometry_area_medium_params,
)

_TOL = 1e-9

_AREA_UNITS = {"cm^2", "m^2"}
_LEN_UNITS = {"cm", "m"}


def _dp_ok(answer: dict) -> bool:
    """A 3.14-path answer is either a 2-dp decimal or (when whole) a plain integer."""
    if answer["type"] == "integer":
        return True
    return answer["type"] == "decimal" and answer["dp"] == 2


def _seg_len(fig: dict, key: str) -> float | None:
    """Leading number of the labelled segment whose endpoints match ``key``."""
    fr, to = key.split("-")
    for seg in fig["segments"]:
        if {seg["from"], seg["to"]} == {fr, to}:
            return _leading_number(seg.get("label"))
    return None


def _area_facts(obj: dict) -> tuple[dict, dict, dict]:
    """Return (params, answer, figure) with the invariants that hold for EVERY
    geometry_area object, independent of the template."""
    part = obj["question"]["parts"][0]
    answer = part["answer"]
    assert answer["type"] in {"integer", "decimal"}
    assert answer["unit"] in (_AREA_UNITS | _LEN_UNITS)
    assert float(answer["value"]) > 0

    fig = part["diagram"]
    assert fig is not None, "geometry figure is mandatory"
    assert fig["type"] == "geometry_figure"
    # The aid figure is mandatory, so it can never be toggled off.
    assert "toggle-diagram" not in available_ops(obj)

    params = obj["parameters"]
    # Every labelled length in params is drawn on the figure with that value.
    for key, val in params.get("lengths", {}).items():
        assert _seg_len(fig, key) == float(val), (key, val, fig["segments"])
    # Every param radius is an arc centred there with that radius.
    for center, val in params.get("radii", {}).items():
        arcs = [a for a in fig["arcs"] if a["center"] == center]
        assert any(float(a["radius"]) == float(val) for a in arcs), (center, val, fig["arcs"])
    return params, answer, fig


@pytest.mark.parametrize("template", GEOMETRY_AREA_EASY_TEMPLATES)
@given(data=st.data())
def test_easy_invariant_single_shape_area(template: str, data: st.DataObject):
    params = data.draw(geometry_area_easy_params(template))
    obj = build_object("geometry_area_easy", params)
    _, answer, _ = _area_facts(obj)
    g = params["givens"]
    ans = answer["value"]
    assert answer["type"] == "integer" and answer["unit"] == "cm^2"
    if template == "rectangle":
        assert ans == g["w"] * g["h"]
    elif template == "square":
        assert ans == g["s"] * g["s"]
    elif template == "triangle":
        assert g["base"] * g["height"] % 2 == 0
        assert ans == g["base"] * g["height"] // 2
    else:
        raise AssertionError(f"unexpected template {template!r}")
    assert ans > 0


@pytest.mark.parametrize("template", GEOMETRY_AREA_MEDIUM_TEMPLATES)
@given(data=st.data())
def test_medium_invariant_composite_and_circle(template: str, data: st.DataObject):
    params = data.draw(geometry_area_medium_params(template))
    obj = build_object("geometry_area_medium", params)
    _, answer, _ = _area_facts(obj)
    g = params["givens"]
    ans = answer["value"]
    if template == "L_shape":
        assert 0 < g["w"] < g["W"] and 0 < g["h"] < g["H"]
        expected = g["W"] * g["H"] - g["w"] * g["h"]
        assert expected > 0
        assert answer["type"] == "integer" and answer["unit"] == "cm^2"
        assert ans == expected
    elif template == "rectangle_plus_triangle":
        # house = rectangle + triangle; base×height must stay even (whole ½·b·h).
        assert (g["W"] * g["h"]) % 2 == 0
        expected = g["W"] * g["H"] + g["W"] * g["h"] // 2
        assert expected > 0
        assert answer["type"] == "integer" and answer["unit"] == "cm^2"
        assert ans == expected
    elif template == "semicircle_area":
        r = g["r"]
        assert answer["unit"] == "cm^2"
        if r % 7 == 0:  # 22/7 path -> exact whole answer by construction
            assert answer["type"] == "integer"
            assert ans == 22 * r * r // (7 * 2)
        else:  # 3.14 path -> 2-dp value (whole values collapse to integer)
            assert abs(ans - round(3.14 * r * r / 2, 2)) < _TOL
            assert _dp_ok(answer)
    elif template == "semicircle_perimeter":
        r = g["r"]
        assert answer["unit"] == "cm"
        if r % 7 == 0:  # 22/7 path -> exact whole answer by construction
            assert answer["type"] == "integer"
            assert ans == 22 * r // 7 + 2 * r
        else:  # 3.14 path -> 2-dp value (whole values collapse to integer)
            assert abs(ans - round(3.14 * r + 2 * r, 2)) < _TOL
            assert _dp_ok(answer)
    else:
        raise AssertionError(f"unexpected template {template!r}")
    assert ans > 0


@pytest.mark.parametrize("template", GEOMETRY_AREA_HARD_TEMPLATES)
@given(data=st.data())
def test_hard_invariant_shaded_and_inverse(template: str, data: st.DataObject):
    params = data.draw(geometry_area_hard_params(template))
    obj = build_object("geometry_area_hard", params)
    _, answer, _ = _area_facts(obj)
    g = params["givens"]
    ans = answer["value"]
    if template == "square_minus_quarter":
        s = g["s"]
        outer = s * s
        assert answer["unit"] == "cm^2"
        if s % 7 == 0:  # 22/7 path (side is a multiple of 14) -> whole
            quarter = 22 * s * s // (7 * 4)
            shaded = outer - quarter
            assert shaded > 0  # region is non-negative
            assert answer["type"] == "integer"
            assert ans == shaded
        else:  # 3.14 path -> 2-dp value (whole values collapse to integer)
            shaded = round(outer - 3.14 * s * s / 4, 2)
            assert shaded > 0
            assert abs(ans - shaded) < _TOL
            assert _dp_ok(answer)
    elif template == "rectangle_with_semicircle_ends":
        # running track: perimeter = 2·L + 2·π·r (two ends form one full circle).
        L, r = g["L"], g["r"]
        assert answer["unit"] == "cm"
        if r % 7 == 0:  # 22/7 path -> exact whole answer by construction
            assert answer["type"] == "integer"
            assert ans == 2 * L + 2 * 22 * r // 7
        else:  # 3.14 path -> 2-dp value (whole values collapse to integer)
            assert abs(ans - round(2 * L + 2 * 3.14 * r, 2)) < _TOL
            assert _dp_ok(answer)
    elif template == "triangle_with_semicircle":
        # total area = triangle (½·b·H) + semicircle (½·π·r²), r = b/2.
        b, height = g["b"], g["H"]
        assert b % 2 == 0
        r = b // 2
        triangle = b * height // 2
        assert answer["unit"] == "cm^2"
        if r % 7 == 0:  # 22/7 path -> exact whole answer by construction
            assert answer["type"] == "integer"
            assert ans == triangle + 22 * r * r // (7 * 2)
        else:  # 3.14 path -> 2-dp value (whole values collapse to integer)
            assert abs(ans - round(triangle + 3.14 * r * r / 2, 2)) < _TOL
            assert _dp_ok(answer)
    elif template == "inverse_rectangle":
        length, width = g["length"], g["width"]
        area = length * width  # the area stated in the stem
        assert answer["type"] == "integer" and answer["unit"] == "cm"
        # Forward-apply: the recovered width times the length is exactly the area.
        assert ans * length == area
        assert ans == width
    else:
        raise AssertionError(f"unexpected template {template!r}")
    assert ans > 0
