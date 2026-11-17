"""EXA-151: every figure the web shows is drawn by the engine via ``POST /render/diagram``.

The web used to draw bar models, shaded fractions and geometry figures with a TypeScript
copy of the old renderer, so the editor showed label placement the engine had since fixed
(EXA-136). Now it fetches every figure from the engine: these tests pin that the endpoint
accepts each newly routed type and returns exactly ``render_svg``'s output, the drawing
``test_figure_labels`` checks for collisions.
"""

from __future__ import annotations

import copy

import pytest
from app.main import app
from exam_engine import generate
from exam_engine.blueprints.registry import content_dir
from exam_engine.diagram import render_svg
from fastapi.testclient import TestClient

client = TestClient(app)


def _shown_figures(obj: dict) -> list[dict]:
    """The question figures the web draws (stem and parts; key figures come as engine HTML)."""
    q = obj["question"]
    specs = [obj.get("diagram"), q.get("diagram"), *(p.get("diagram") for p in q["parts"])]
    return [s for s in specs if s]


ROUTED = {
    "bar_model": "ratio_easy",
    "bar_model_before_after": "ratio_hard",
    "shaded_fraction": "fractions_easy",
    "geometry_figure": "geometry_area_hard",
}


@pytest.mark.parametrize("kind", sorted(ROUTED))
def test_newly_routed_type_is_drawn_by_the_engine_renderer(kind):
    spec = next(s for s in _shown_figures(generate(ROUTED[kind], 3)) if s["type"] == kind)
    resp = client.post("/render/diagram", json={"diagram": spec})
    assert resp.status_code == 200, resp.text
    assert resp.json()["svg"] == render_svg(spec)
    assert resp.json()["svg"].startswith("<svg")


def test_before_after_view_modes_draw_differently():
    """The editor's toggle-bar-view edit flips view_mode; each mode is its own render."""
    spec = next(s for s in _shown_figures(generate("ratio_hard", 3)))
    svgs = set()
    for mode in ("grouped", "sliced"):
        resp = client.post("/render/diagram", json={"diagram": {**spec, "view_mode": mode}})
        assert resp.status_code == 200, resp.text
        svgs.add(resp.json()["svg"])
    assert len(svgs) == 2


def test_every_generated_figure_is_accepted():
    codes = sorted(p.stem for p in (content_dir() / "blueprints").glob("*.yaml"))
    seen = set()
    for code in codes:
        for spec in _shown_figures(generate(code, 1)):
            seen.add(spec["type"])
            resp = client.post("/render/diagram", json={"diagram": spec})
            assert resp.status_code == 200, (code, resp.text)
    assert set(ROUTED) <= seen


def test_an_invalid_routed_figure_is_rejected():
    spec = copy.deepcopy(next(s for s in _shown_figures(generate("geometry_area_hard", 3))))
    spec["points"] = "not a list"
    assert client.post("/render/diagram", json={"diagram": spec}).status_code == 422
    bad_bar = {"type": "bar_model", "bars": [{"label": "A", "units": "three"}]}
    assert client.post("/render/diagram", json={"diagram": bad_bar}).status_code == 422
