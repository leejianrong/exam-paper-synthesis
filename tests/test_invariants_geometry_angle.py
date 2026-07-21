"""Independent correctness authority for the Geometry (Angles) ladder (KAN-229, KAN-237).

Property-based (Hypothesis) tests that re-derive each template's *defining angle
relationship* independently of ``solve()`` — "what must be true" of the given
angles + the solved unknown — over givens generated directly from the template's
parameter space, shrinking failures to a minimal counterexample. Every template
is exercised via parametrisation. Each object also schema-validates, the mandatory
``geometry_figure`` marks the unknown as exactly the answer, and every given angle
drawn equals the stored parameter.

Exact integer arithmetic only (angles are whole degrees) — the checks are
provable, not approximate. The golden fixtures pin one figure per rung; these
tests are the independent guard against a solver that is self-consistent but wrong.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from strategies import (
    GEOMETRY_ANGLE_EASY_TEMPLATES,
    GEOMETRY_ANGLE_HARD_TEMPLATES,
    GEOMETRY_ANGLE_MEDIUM_TEMPLATES,
    build_object,
    geometry_angle_easy_params,
    geometry_angle_hard_params,
    geometry_angle_medium_params,
)


def _figure_facts(obj: dict) -> tuple[dict, int, list[dict]]:
    """Return (params, answer_value, diagram angle marks) with basic invariants
    that hold for EVERY geometry_angle object, independent of the template."""
    part = obj["question"]["parts"][0]
    answer = part["answer"]
    assert answer["type"] == "integer"
    assert answer["unit"] == "degrees"
    assert isinstance(answer["value"], int)
    assert 0 < answer["value"] < 180

    fig = part["diagram"]
    assert fig is not None, "geometry figure is mandatory"
    assert fig["type"] == "geometry_figure"

    marks = fig["angles"]
    unknowns = [m for m in marks if m.get("unknown")]
    assert len(unknowns) == 1, "exactly one unknown angle is marked"
    # The figure's unknown IS the answer (the printed figure is the printed key).
    assert unknowns[0]["value_deg"] == answer["value"]

    # Every stored given angle appears on the figure with the same value.
    given_angles = obj["parameters"]["angles"]
    for key, val in given_angles.items():
        fr, at, to = key.split("-")
        hit = [
            m
            for m in marks
            if not m.get("unknown")
            and m["at"] == at
            and {m["from"], m["to"]} == {fr, to}
            and m["value_deg"] == val
        ]
        assert hit, (key, val, marks)

    return obj["parameters"], answer["value"], marks


@pytest.mark.parametrize("template", GEOMETRY_ANGLE_EASY_TEMPLATES)
@given(data=st.data())
def test_easy_invariant_one_rule_one_step(template: str, data: st.DataObject):
    params = data.draw(geometry_angle_easy_params(template))
    obj = build_object("geometry_angle_easy", params)
    _, ans, _ = _figure_facts(obj)
    g = params["givens"]
    if template == "straight_line":
        # angles on a straight line sum to 180.
        assert g["p"] + g["q"] + ans == 180
    elif template == "at_point":
        # angles at a point sum to 360.
        assert g["a"] + g["c"] + ans == 360
    elif template == "triangle_sum":
        # interior angles of a triangle sum to 180.
        assert g["a"] + g["b"] + ans == 180
    else:
        raise AssertionError(f"unexpected template {template!r}")


@pytest.mark.parametrize("template", GEOMETRY_ANGLE_MEDIUM_TEMPLATES)
@given(data=st.data())
def test_medium_invariant_two_step_property(template: str, data: st.DataObject):
    params = data.draw(geometry_angle_medium_params(template))
    obj = build_object("geometry_angle_medium", params)
    _, ans, _ = _figure_facts(obj)
    g = params["givens"]
    if template == "isosceles_apex":
        # equal base angles + angle sum: apex + 2 * base = 180.
        assert g["apex"] + 2 * ans == 180
    elif template == "isosceles_base":
        # the two equal base angles + apex sum to 180.
        assert 2 * g["base"] + ans == 180
    elif template == "exterior":
        # interior angle at C = 180 - ext (straight line); triangle sum.
        interior_c = 180 - g["ext"]
        assert 0 < interior_c < 180
        assert g["b"] + interior_c + ans == 180
    else:
        raise AssertionError(f"unexpected template {template!r}")


@pytest.mark.parametrize("template", GEOMETRY_ANGLE_HARD_TEMPLATES)
@given(data=st.data())
def test_hard_invariant_composite_two_properties(template: str, data: st.DataObject):
    params = data.draw(geometry_angle_hard_params(template))
    obj = build_object("geometry_angle_hard", params)
    _, ans, _ = _figure_facts(obj)
    g = params["givens"]
    if template == "parallelogram":
        # corresponding angles give angle CBE = DAB = a; triangle BCE sum.
        assert g["a"] + g["e"] + ans == 180
    elif template == "rhombus":
        # equal sides -> isosceles triangle ABC; base angles equal.
        assert g["b"] + 2 * ans == 180
    elif template == "trapezium":
        # BAE straight line -> angle DAE = 180 - a; then triangle ADE angle sum.
        angle_dae = 180 - g["a"]
        assert 0 < angle_dae < 180
        assert angle_dae + g["e"] + ans == 180
        assert ans == g["a"] - g["e"]
    else:
        raise AssertionError(f"unexpected template {template!r}")
