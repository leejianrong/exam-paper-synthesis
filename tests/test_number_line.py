"""T3 — the ``number_line`` diagram (schema 1.9.0) and answer-vs-givens key styling."""

from __future__ import annotations

import copy
import json
import re
from fractions import Fraction
from pathlib import Path

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.number_line import check_number_line_consistency, tick_value
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
NAMES = ("fraction", "decimal")


def _texts(svg: str) -> list[str]:
    return re.findall(r"<text[^>]*>([^<]+)</text>", svg)


def _obj(name: str) -> dict:
    return json.loads((SOURCED / f"standin_numberline_{name}.json").read_text("utf-8"))


def _spec(name: str) -> dict:
    return _obj(name)["question"]["diagram"]


@pytest.mark.parametrize("name", NAMES)
def test_fixture_loads_is_consistent_and_renders_deterministically(name):
    canonical.load(_obj(name))
    spec = _spec(name)
    assert all(check_number_line_consistency(spec).values())
    assert check_consistency(spec, {}, {}) == check_number_line_consistency(spec)
    svg = render_svg(spec)
    assert svg == render_svg(copy.deepcopy(spec))
    assert set(re.findall(r'font-family="([^"]*)"', svg)) == {"Inter, system-ui, sans-serif"}


def test_fixture_answers_follow_from_the_geometry():
    frac = _spec("fraction")
    point = Fraction(str(frac["marked_points"][0]["at"]))
    ans = _obj("fraction")["question"]["parts"][0]["answer"]
    assert point == Fraction(ans["numerator"], ans["denominator"]) == Fraction(5, 4)
    assert tick_value(frac, 1) == Fraction(1, 4)
    dec = _spec("decimal")
    assert (
        float(dec["marked_points"][0]["at"])
        == _obj("decimal")["question"]["parts"][0]["answer"]["value"]
    )


def test_unlabelled_ticks_and_the_marked_value_are_not_printed():
    svg = render_svg(_spec("decimal"))
    text = _texts(svg)
    assert sorted(text) == ["0", "0.5", "1", "A"]  # 0.7 is never printed
    assert svg.count("<line") == 1 + 11  # axis + one tick per division


def test_ticks_are_evenly_spaced():
    xs = [
        float(x)
        for x in re.findall(r'<line x1="([\d.]+)" y1="\d+" x2="\1"', render_svg(_spec("decimal")))
    ]
    gaps = {round(b - a, 2) for a, b in zip(xs, xs[1:], strict=False)}
    assert len(xs) == 11 and len(gaps) == 1


@pytest.mark.parametrize(
    ("mutate", "failing"),
    [
        (lambda s: s.update(start=2, end=1), "range_valid"),
        (lambda s: s.update(labelled=[0, 11]), "labelled_unique_and_on_line"),
        (lambda s: s["marked_points"][0].update(at=1.5), "points_within_range"),
        (lambda s: s["marked_points"][0].update(at=0.55), "points_on_ticks"),
        (lambda s: s["marked_points"][0].update(at=0.5), "unknown_points_not_on_labelled_ticks"),
        (
            lambda s: s["marked_points"].append(dict(s["marked_points"][0], at=0.2)),
            "point_labels_unique",
        ),
        (lambda s: s.update(end=0.0005, divisions=1), "labels_print_exactly"),
    ],
)
def test_corruptions_are_caught(mutate, failing):
    spec = _spec("decimal")
    mutate(spec)
    assert check_number_line_consistency(spec)[failing] is False


def test_a_known_point_may_sit_on_a_labelled_tick():
    spec = _spec("decimal")
    spec["marked_points"][0].update(at=0.5, known=True)
    assert all(check_number_line_consistency(spec).values())


def test_fraction_labels_stack_numerator_over_denominator():
    spec = {
        "type": "number_line",
        "start": 0,
        "end": 1,
        "divisions": 6,
        "label_style": "fraction",
        "labelled": [0, 1, 6],
    }
    text = _texts(render_svg(spec))
    assert text == ["0", "1", "6", "1"]  # 0, 1/6 stacked, 1
    mixed = dict(spec, end=2, divisions=4, labelled=[3])  # 1 1/2
    assert _texts(render_svg(mixed)) == ["1", "1", "2"]


def test_non_finite_and_huge_inputs_are_rejected_not_raised():
    obj = _obj("decimal")
    obj["question"]["diagram"]["end"] = 10**400
    assert validate_object(obj) != []
    spec = _spec("decimal")
    for bad in (1e300, float("inf")):
        spec["end"] = bad
        assert check_number_line_consistency(spec)["range_valid"] is False


def test_schema_rejects_malformed_number_lines():
    def bad(**changes):
        obj = _obj("decimal")
        obj["question"]["diagram"].update(changes)
        return validate_object(obj)

    assert bad(divisions=0) != [] and bad(divisions=101) != []
    assert bad(label_style="roman") != [] and bad(labelled=[1, 1]) != []
    assert bad(marked_points=[{"at": 1}]) != [] and bad(colour="red") != []
    assert bad() == []


def test_load_gate_points_at_a_leaking_point():
    obj = _obj("decimal")
    obj["question"]["diagram"]["marked_points"][0]["at"] = 0.5
    assert validate_object(obj) == []
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)
    assert "number_line inconsistent: unknown_points_not_on_labelled_ticks" in str(exc.value)


@pytest.mark.parametrize("name", NAMES)
def test_worksheet_and_key_render_the_number_line(name):
    obj = canonical.load(_obj(name))
    assert '<figure class="diagram"><svg' in render_worksheet_html("NL", [obj])
    assert "Answer:" in render_answer_key_html("NL", [obj])


# --- answer-vs-givens styling in the key (construction answers) -------------------------


def test_key_draws_what_the_student_adds_in_the_answer_accent():
    obj = canonical.load(json.loads((SOURCED / "psle_2023_construction.json").read_text("utf-8")))
    key = render_answer_key_html("K", [obj])
    accented = re.findall(r'<line [^>]*stroke="#d6336c"[^>]*/>', key)
    assert len(accented) == 2  # the two new edges CD and DA; AB and BC stay the given blue
    assert key.count('fill="#d6336c"') == 1  # the new point's label D
    assert "#d6336c" not in render_worksheet_html("K", [obj])  # student sheet has no answer


def test_a_figure_with_no_given_is_not_restyled():
    from exam_engine import diagram

    spec = json.loads((SOURCED / "psle_2023_construction.json").read_text("utf-8"))["question"][
        "parts"
    ][0]["answer"]["diagram"]
    assert "#d6336c" not in diagram.render_svg(spec)
