"""Independent correctness authority for the Geometry (Angles) ladder (KAN-229).

A seed-sweep that re-derives each template's *defining angle relationship*
independently of ``solve()`` — "what must be true" of the given angles + the
solved unknown — and asserts every generated object also schema-validates, that
the mandatory ``geometry_figure`` marks the unknown as exactly the answer, and
that every given angle drawn equals the stored parameter.

Exact integer arithmetic only (angles are whole degrees) — the checks are
provable, not approximate. The golden fixtures pin one figure per rung; this
sweep is the independent guard against a solver that is self-consistent but wrong.
"""

from __future__ import annotations

from exam_engine import generate
from exam_engine.schema import validate_object

SWEEP = range(1, 400)


def _figure_facts(obj: dict) -> tuple[dict, int, list[dict]]:
    """Return (params, answer_value, diagram angle marks) with basic invariants
    that hold for EVERY geometry_angle object, independent of the template."""
    assert validate_object(obj) == [], validate_object(obj)
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
    given = obj["parameters"]["angles"]
    for key, val in given.items():
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


def test_easy_invariant_one_rule_one_step():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_angle_easy", seed)
        params, ans, _ = _figure_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
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
    assert seen == {"straight_line", "at_point", "triangle_sum"}


def test_medium_invariant_two_step_property():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_angle_medium", seed)
        params, ans, _ = _figure_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
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
    assert seen == {"isosceles_apex", "isosceles_base", "exterior"}


def test_hard_invariant_composite_two_properties():
    seen: set[str] = set()
    for seed in SWEEP:
        obj = generate("geometry_angle_hard", seed)
        params, ans, _ = _figure_facts(obj)
        g = params["givens"]
        template = params["template"]
        seen.add(template)
        if template == "parallelogram":
            # corresponding angles give angle CBE = DAB = a; triangle BCE sum.
            assert g["a"] + g["e"] + ans == 180
        elif template == "rhombus":
            # equal sides -> isosceles triangle ABC; base angles equal.
            assert g["b"] + 2 * ans == 180
        else:
            raise AssertionError(f"unexpected template {template!r}")
    assert seen == {"parallelogram", "rhombus"}
