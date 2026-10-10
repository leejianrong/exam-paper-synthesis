"""T4 — the ``panels`` diagram wrapper (schema 1.10.0)."""

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

SOURCED = Path(__file__).parent / "fixtures" / "sourced"


def _obj() -> dict:
    return json.loads((SOURCED / "standin_panels_before_after.json").read_text("utf-8"))


def _spec() -> dict:
    return _obj()["question"]["diagram"]


def test_fixture_loads_renders_deterministically_and_answer_follows():
    obj = canonical.load(_obj())
    spec = obj["question"]["diagram"]
    assert all(check_consistency(spec, {}, {}).values())
    svg = render_svg(spec)
    assert svg == render_svg(copy.deepcopy(spec))
    assert set(re.findall(r'font-family="([^"]*)"', svg)) == {"Inter, system-ui, sans-serif"}
    a, b = (p["figure"] for p in spec["panels"])
    d = a["dims"]
    rise = b["fill"]["height"] - a["fill"]["height"]
    assert d["length"] * d["width"] * rise == obj["question"]["parts"][0]["answer"]["value"]


def test_each_panel_is_a_nested_svg_with_title_and_arrow():
    svg = render_svg(_spec())
    assert svg.count("<svg") == 3 and svg.count("</svg>") == 3
    text = re.findall(r"<text[^>]*>([^<]+)</text>", svg)
    assert "Before" in text and "After" in text and "12 cm" in text and "15 cm" in text
    assert svg.count("<path") == 1  # the one arrow between two panels
    no_arrow = _spec() | {"arrows": False}
    assert "<path" not in render_svg(no_arrow)


def test_children_stay_inside_the_viewbox():
    svg = render_svg(_spec())
    outer = re.match(r'<svg[^>]*viewBox="0 0 (\d+) (\d+)"', svg)
    w, h = int(outer.group(1)), int(outer.group(2))
    for x, y, cw, ch in re.findall(
        r'<svg x="([\d.]+)" y="([\d.]+)"[^>]*width="(\d+)" height="(\d+)"', svg
    ):
        assert float(x) + float(cw) <= w and float(y) + float(ch) <= h


def test_schema_rejects_malformed_panels():
    def bad(**changes):
        obj = _obj()
        obj["question"]["diagram"].update(changes)
        return validate_object(obj)

    one = [_spec()["panels"][0]]
    assert bad(panels=one) != [] and bad(panels=one * 5) != []
    assert bad(panels=[{"title": "x"}, {"title": "y"}]) != []
    assert bad(extra=1) != [] and bad() == []


@pytest.mark.parametrize(
    ("mutate", "failing"),
    [
        (lambda s: s["panels"][1].update(title="Before"), "panel_titles_unique"),
        (
            lambda s: s["panels"][1].update(
                figure={"type": "panels", "panels": copy.deepcopy(s["panels"])}
            ),
            "no_nested_panels",
        ),
        (
            lambda s: s["panels"][1].update(
                figure={"type": "raster", "asset_ref": "data:image/png;base64,AA", "alt_text": "x"}
            ),
            "panels_are_vector",
        ),
        (lambda s: s["panels"][1]["figure"]["fill"].update(height=99), "panel2_fill_within_height"),
    ],
)
def test_corruptions_are_caught_and_gate_points_at_the_panel(mutate, failing):
    obj = _obj()
    mutate(obj["question"]["diagram"])
    assert check_consistency(obj["question"]["diagram"], {}, {})[failing] is False
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)
    assert f"panels inconsistent: {failing}" in str(exc.value)


def test_worksheet_and_key_render_the_panels():
    obj = canonical.load(_obj())
    assert '<figure class="diagram"><svg' in render_worksheet_html("P", [obj])
    assert "Answer:" in render_answer_key_html("P", [obj])
