"""T6 — the ``cube_stack`` diagram (schema 1.12.0): heightmap and derived views."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.cube_stack import (
    check_cube_stack_consistency,
    cube_count,
    front_view,
    side_view,
    top_view,
    view_key,
)
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.schema import validate_diagram

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
H = [[2, 1, 0], [1, 3, 1]]  # back row first, front row last


def _fixture(name: str) -> dict:
    return json.loads((SOURCED / f"standin_cubestack_{name}.json").read_text("utf-8"))


def _spec(view: str = "iso", heights=H) -> dict:
    return {"type": "cube_stack", "heights": copy.deepcopy(heights), "view": view}


def test_views_are_derived_from_the_heightmap():
    assert cube_count(H) == 8
    assert front_view(H) == [2, 3, 1]
    assert side_view(H) == [3, 2]  # from the right: front row on the left
    assert top_view(H) == [[True, True, False], [True, True, True]]


def test_front_view_ignores_cubes_hidden_behind_taller_stacks():
    assert view_key([[1, 1], [3, 1]], "front") == view_key([[3, 1], [3, 1]], "front")
    assert view_key([[1, 1], [3, 1]], "iso") != view_key([[3, 1], [3, 1]], "iso")


def test_fixtures_load_and_the_answers_follow_from_the_heightmap():
    count = canonical.load(_fixture("count"))
    assert (
        cube_count(count["question"]["diagram"]["heights"])
        == (count["question"]["parts"][0]["answer"]["value"])
    )
    mcq = canonical.load(_fixture("view"))
    heights = mcq["question"]["diagram"]["heights"]
    answer = mcq["question"]["parts"][0]["answer"]
    matching = [
        o["label"]
        for o in answer["options"]
        if view_key(o["diagram"]["heights"], o["diagram"]["view"]) == view_key(heights, "front")
    ]
    assert matching == [answer["correct"]]  # exactly one option is the front view
    # every option is a different picture
    drawn = {render_svg(o["diagram"]) for o in answer["options"]}
    assert len(drawn) == len(answer["options"])


def test_render_is_deterministic_inter_only_and_draws_every_cube():
    svg = render_svg(_spec())
    assert svg == render_svg(_spec())
    assert set(re.findall(r'font-family="([^"]*)"', svg)) == {"Inter, system-ui, sans-serif"}
    assert svg.count("<polygon") == 3 * cube_count(H)
    assert render_svg(_spec("front")).count("<rect") == sum(front_view(H))
    assert render_svg(_spec("side")).count("<rect") == sum(side_view(H))
    assert render_svg(_spec("top")).count("<rect") == sum(map(sum, top_view(H)))


def test_a_view_never_shows_more_than_the_stack_has():
    for view in ("front", "side", "top"):
        assert 0 < render_svg(_spec(view)).count("<rect") <= cube_count(H)


@pytest.mark.parametrize(
    "mutate,failing",
    [
        (lambda s: s.update(heights=[[1, 2], [1]]), "heights_rectangular"),
        (lambda s: s.update(heights=[[0, 0]]), "has_cubes"),
        (lambda s: s.update(heights=[[9]]), "heights_in_range"),
        (lambda s: s.update(heights=[[True]]), "heights_in_range"),
        (lambda s: s.update(heights=[]), "heights_rectangular"),
        (lambda s: s.update(view="back"), "view_known"),
    ],
)
def test_consistency_catches_bad_specs(mutate, failing):
    s = _spec()
    mutate(s)
    assert check_cube_stack_consistency(s)[failing] is False


def test_consistency_is_total_on_garbage():
    for junk in ({}, {"heights": None}, {"heights": "x"}, {"heights": [None]}):
        assert isinstance(check_cube_stack_consistency(junk), dict)


def test_schema_rejects_oversize_and_negative():
    assert not validate_diagram(_spec())
    assert validate_diagram(_spec(heights=[[1] * 7]))
    assert validate_diagram(_spec(heights=[[1]] * 7))
    assert validate_diagram(_spec(heights=[[-1]]))
    assert validate_diagram(_spec(view="bottom"))


def test_load_gate_rejects_an_all_empty_stack_and_a_ragged_grid():
    obj = _fixture("count")
    obj["question"]["diagram"]["heights"] = [[0, 0], [0, 0]]
    with pytest.raises(CanonicalValidationError, match="has_cubes"):
        canonical.load(obj)
    obj["question"]["diagram"]["heights"] = [[1, 1], [1]]
    with pytest.raises(CanonicalValidationError, match="heights_rectangular"):
        canonical.load(obj)


def test_check_consistency_dispatches_and_panels_can_hold_a_stack():
    assert all(check_consistency(_spec(), {}, {}).values())
    panels = {
        "type": "panels",
        "panels": [{"title": "Front", "figure": _spec("front")}, {"figure": _spec("top")}],
    }
    assert all(check_consistency(panels, {}, {}).values())
    panels["panels"][0]["figure"]["heights"] = [[0]]
    assert not all(check_consistency(panels, {}, {}).values())
    assert render_svg(panels).startswith("<svg")
