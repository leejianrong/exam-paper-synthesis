"""T2 — the ``solid`` diagram (schema 1.8.0): cuboid / container with a fill level."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object
from exam_engine.solid import (
    check_solid_consistency,
    fill_volume,
    leaked_hidden_values,
    solid_volume,
)

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
NAMES = ("tank", "cuboid", "level")


def _obj(name: str) -> dict:
    return json.loads((SOURCED / f"standin_solid_{name}.json").read_text("utf-8"))


def _spec(name: str) -> dict:
    return _obj(name)["question"]["diagram"]


@pytest.mark.parametrize("name", NAMES)
def test_fixture_loads_is_consistent_and_renders_deterministically(name):
    canonical.load(_obj(name))
    spec = _spec(name)
    assert all(check_solid_consistency(spec).values())
    assert check_consistency(spec, {}, {}) == check_solid_consistency(spec)
    svg = render_svg(spec)
    assert svg == render_svg(copy.deepcopy(spec))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert set(re.findall(r'font-family="([^"]*)"', svg)) == {"Inter, system-ui, sans-serif"}


def test_the_answers_in_the_fixtures_follow_from_the_dims():
    tank = _spec("tank")
    assert solid_volume(tank) == 30000 and fill_volume(tank) == 12000
    assert (solid_volume(tank) - fill_volume(tank)) / 1000 == 18  # part (b), litres
    cuboid = _spec("cuboid")
    assert solid_volume(cuboid) == 1800  # the stem's volume
    level = _spec("level")
    assert 9000 / (level["dims"]["length"] * level["dims"]["width"]) == level["fill"]["height"]
    assert fill_volume({"dims": level["dims"]}) == 0  # no fill -> empty


def test_labels_show_the_dims_and_the_fill():
    text = " ".join(re.findall(r">([^<]*)<", render_svg(_spec("tank"))))
    for expected in ("40 cm", "25 cm", "30 cm", "12 cm"):
        assert expected in text


def test_hidden_dimension_and_fill_print_as_question_marks_but_are_drawn_true():
    cuboid, level = _spec("cuboid"), _spec("level")
    svg = render_svg(cuboid)
    assert leaked_hidden_values(cuboid, svg) == []
    assert "?" in svg and "10 cm" not in svg
    # the hidden height still sets the drawn height: 10 vs 15 changes the figure
    taller = copy.deepcopy(cuboid)
    taller["dims"]["height"] = 15
    assert render_svg(taller) != svg

    svg = render_svg(level)
    assert leaked_hidden_values(level, svg) == [] and ">?<" in svg
    # a deeper fill moves the water line
    deeper = copy.deepcopy(level)
    deeper["fill"]["height"] = 20
    assert render_svg(deeper) != svg


def test_guard_detects_a_leak_and_tolerates_equal_shown_values():
    cuboid = _spec("cuboid")
    assert leaked_hidden_values(cuboid, "<svg><text>10 cm</text></svg>") == ["10"]
    cube = {"kind": "cuboid", "dims": {"length": 10, "width": 10, "height": 10}, "unit": "cm"}
    cube["hidden_dims"] = ["height"]
    assert leaked_hidden_values(cube, "<svg><text>10 cm</text><text>10 cm</text></svg>") == []
    assert leaked_hidden_values(
        cube, "<svg><text>10 cm</text><text>10 cm</text><text>10 cm</text></svg>"
    ) == ["10"]


def test_aria_label_carries_no_data():
    svg = render_svg(_spec("cuboid"))
    label = re.search(r'aria-label="([^"]*)"', svg).group(1)
    assert label == "cuboid" and not re.search(r"\d", label)


@pytest.mark.parametrize(
    ("mutate", "failing"),
    [
        (lambda s: s["dims"].update(length=0), "dims_positive"),
        (lambda s: s["dims"].update(width=float("inf")), "dims_positive"),
        (lambda s: s["dims"].update(height=12.3456), "dims_print_exactly"),
        (lambda s: s["fill"].update(height=31), "fill_within_height"),
        (lambda s: s["fill"].update(height=2.0001), "fill_prints_exactly"),
        (lambda s: s.update(kind="cuboid"), "fill_only_on_container"),
        (lambda s: s.update(hidden_dims=["height", "height"]), "hidden_dims_unique"),
    ],
)
def test_corruptions_are_caught(mutate, failing):
    spec = _spec("tank")
    mutate(spec)
    checks = check_solid_consistency(spec)
    assert checks[failing] is False


def test_schema_rejects_malformed_solids():
    def bad(**changes):
        obj = _obj("tank")
        obj["question"]["diagram"].update(changes)
        return validate_object(obj)

    assert bad(kind="sphere") != []
    assert bad(dims={"length": 1, "width": 1}) != []
    assert bad(dims={"length": 1, "width": 1, "height": -1}) != []
    assert bad(hidden_dims=["depth"]) != []
    assert bad(fill={"height": -1}) != []
    assert bad(fill={"depth": 1}) != []
    assert bad(radius=3) != []
    assert bad() == []


def test_load_gate_rejects_a_fill_above_the_rim():
    obj = _obj("tank")
    obj["question"]["diagram"]["fill"]["height"] = 35
    assert validate_object(obj) == []  # schema-valid...
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)  # ...but the gate points at it
    assert "question.diagram: solid inconsistent: fill_within_height" in str(exc.value)


def test_load_gate_checks_solid_options_of_an_mcq():
    obj = _obj("tank")
    good = obj["question"]["diagram"]
    bad = copy.deepcopy(good)
    bad["fill"]["height"] = 99
    obj["question"]["diagram"] = None
    obj["question"]["parts"][0]["answer"] = {
        "type": "choice",
        "correct": "A",
        "options": [{"label": "A", "diagram": good}, {"label": "B", "diagram": bad}],
    }
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)
    assert "options[1].diagram: solid inconsistent: fill_within_height" in str(exc.value)


def test_earlier_schema_objects_still_load_under_1_8_0():
    for name in ("psle_2023_table", "standin_chart_pie"):
        data = json.loads((SOURCED / f"{name}.json").read_text("utf-8"))
        assert data["schema_version"] in ("1.6.0", "1.7.0")
        canonical.load(data)


@pytest.mark.parametrize("name", NAMES)
def test_worksheet_and_key_render_the_solid_as_a_stem_figure(name):
    obj = canonical.load(_obj(name))
    sheet = render_worksheet_html("Solids", [obj])
    key = render_answer_key_html("Solids", [obj])
    assert '<figure class="diagram"><svg' in sheet and '<figure class="diagram"><svg' in key
    assert "Answer:" in key and "Answer:" not in sheet
