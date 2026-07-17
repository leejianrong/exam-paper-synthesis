"""Independent correctness authority for the Geometry (Area & Perimeter) ladder.

For area/perimeter figures there is no unknown *angle*, so the diagram
consistency check does NOT verify the numeric answer — this seed-sweep is the
primary guard that the printed key is right. Per template it **recomputes** the
area / perimeter / length independently of ``solve()``: via the mensuration
formula from the figure's labelled dimensions, using the SAME π the stem states
but a DIFFERENT arithmetic path (integer ``//`` on the 22/7 path; float ``round``
on the 3.14 path — the solver uses exact ``Fraction``). It also asserts every
object schema-validates and that the figure's labelled dims equal the params.

Exact integer arithmetic on the whole-number paths; a small tolerance on the
2-dp decimal (3.14) path (the ticket sanctions comparing rounded values).
"""

from __future__ import annotations

from exam_engine import generate
from exam_engine.diagram import _leading_number
from exam_engine.schema import validate_object

SWEEP = range(1, 400)
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
    assert validate_object(obj) == [], validate_object(obj)
    part = obj["question"]["parts"][0]
    answer = part["answer"]
    assert answer["type"] in {"integer", "decimal"}
    assert answer["unit"] in (_AREA_UNITS | _LEN_UNITS)
    assert float(answer["value"]) > 0

    fig = part["diagram"]
    assert fig is not None, "geometry figure is mandatory"
    assert fig["type"] == "geometry_figure"

    params = obj["parameters"]
    # Every labelled length in params is drawn on the figure with that value.
    for key, val in params.get("lengths", {}).items():
        assert _seg_len(fig, key) == float(val), (key, val, fig["segments"])
    # Every param radius is an arc centred there with that radius.
    for center, val in params.get("radii", {}).items():
        arcs = [a for a in fig["arcs"] if a["center"] == center]
        assert any(float(a["radius"]) == float(val) for a in arcs), (center, val, fig["arcs"])
    return params, answer, fig


def _no_toggle_and_mandatory(obj: dict) -> None:
    from exam_engine.edits import available_ops

    assert "toggle-diagram" not in available_ops(obj)


def test_easy_invariant_single_shape_area():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_area_easy", seed)
        params, answer, _ = _area_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
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
    assert seen == {"rectangle", "square", "triangle"}
    _no_toggle_and_mandatory(generate("geometry_area_easy", 1))


def test_medium_invariant_composite_and_circle():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_area_medium", seed)
        params, answer, _ = _area_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
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
    assert seen == {"L_shape", "rectangle_plus_triangle", "semicircle_area", "semicircle_perimeter"}


def test_hard_invariant_shaded_and_inverse():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_area_hard", seed)
        params, answer, _ = _area_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
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
    assert seen == {
        "square_minus_quarter",
        "rectangle_with_semicircle_ends",
        "triangle_with_semicircle",
        "inverse_rectangle",
    }
