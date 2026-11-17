"""EXA-135: the printed paper is black on white, like a photocopied school paper.

Every colour in a rendered paper, answer key, question fragment or figure must be a neutral grey
(r == g == b): no blue strokes, no red marks, no green key panels, and no chart told apart only by
hue. The scan covers the stylesheet and every inline SVG; script bodies (KaTeX) and ``data:``
URIs (fonts, images) are not colours we draw, so they are stripped first.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from documents import make_doc, question_block
from exam_engine import canonical, generate, palette
from exam_engine.blueprints.registry import content_dir
from exam_engine.diagram import render_svg
from exam_engine.paper import generate_paper
from exam_engine.render import fragment_css, render_document_html, render_question_fragment

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
CODES = sorted(p.stem for p in (content_dir() / "blueprints").glob("*.yaml"))

# Every diagram type with an SVG renderer except ``raster`` (an uploaded picture, not drawn).
DRAWN_TYPES = {
    "bar_model",
    "bar_model_before_after",
    "shaded_fraction",
    "geometry_figure",
    "chart",
    "solid",
    "number_line",
    "panels",
    "cube_stack",
}

_HEX = re.compile(r"(?<![&\w])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
_RGB = re.compile(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)")
_NAMED = re.compile(
    r"""(?:fill|stroke|color|background(?:-color)?|border(?:-\w+)?)\s*[:=]\s*["']?[^;"'>]*?"""
    r"""\b(red|green|blue|navy|teal|orange|purple|crimson|magenta|pink|yellow)\b""",
    re.IGNORECASE,
)


def _scannable(html: str) -> str:
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.DOTALL)
    return re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", "", html)


def non_grey_colours(html: str) -> list[str]:
    """Every colour in ``html`` whose channels differ (a hue), as written."""
    text = _scannable(html)
    bad = []
    for m in _HEX.finditer(text):
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
        if not r == g == b:
            bad.append(m.group(0))
    for m in _RGB.finditer(text):
        if len({float(v) for v in m.groups()}) > 1:
            bad.append(m.group(0))
    bad += [m.group(0) for m in _NAMED.finditer(text)]
    return bad


def _diagram_types(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        if node.get("type") in DRAWN_TYPES:
            found.add(node["type"])
        for v in node.values():
            found |= _diagram_types(v)
    elif isinstance(node, list):
        for v in node:
            found |= _diagram_types(v)
    return found


def _all_questions() -> list[dict]:
    objs = [canonical.load(json.loads(p.read_text("utf-8"))) for p in sorted(SOURCED.glob("*"))]
    return objs + [generate(code, seed) for code in CODES for seed in (1, 2)]


def test_the_scanner_catches_hues_and_passes_greys():
    assert non_grey_colours('<rect fill="#2f5fe0"/><b style="color: rgb(181, 58, 34)">') == [
        "#2f5fe0",
        "rgb(181, 58, 34",
    ]
    assert non_grey_colours('<line stroke="red"/>') == ['stroke="red']
    assert non_grey_colours('<rect fill="#1a1a1a" stroke="#fff"/> &#8217; url(#p1)') == []


def test_the_palette_is_grey():
    values = [v for k, v in vars(palette).items() if k.isupper() and isinstance(v, str)]
    assert non_grey_colours(" ".join(values + list(palette.SERIES))) == []


def test_every_drawn_diagram_type_is_covered():
    assert _diagram_types(_all_questions()) == DRAWN_TYPES


@pytest.mark.parametrize("mode", ["student", "key", "full"])
def test_a_paper_of_every_question_and_figure_is_monochrome(mode):
    doc = make_doc(*[question_block(o) for o in _all_questions()])
    assert non_grey_colours(render_document_html("Mono", doc, mode=mode)) == []


@pytest.mark.parametrize("template", ["p1_booklet_a", "p1_booklet_b", "p2"])
@pytest.mark.parametrize("mode", ["student", "key"])
def test_a_generated_paper_is_monochrome(template, mode):
    doc, _ = generate_paper(template, "P6", 3)
    assert non_grey_colours(render_document_html(doc["title"], doc, mode=mode)) == []


def test_the_editor_fragment_and_its_stylesheet_are_monochrome():
    assert non_grey_colours(fragment_css()) == []
    for obj in _all_questions():
        for mode in ("student", "key"):
            assert non_grey_colours(render_question_fragment(obj, mode=mode, number=1)) == []


def test_charts_tell_series_apart_without_hue():
    pie = json.loads((SOURCED / "standin_chart_pie.json").read_text("utf-8"))
    spec = pie["question"]["diagram"]
    svg = render_svg(spec)
    sectors = re.findall(r'<path d="M[^"]*" fill="([^"]+)" stroke="([^"]+)"', svg)
    assert len(sectors) == len(spec["sectors"])
    assert set(sectors) == {(palette.PAPER, palette.INK)}  # white, outlined
    for sector in spec["sectors"]:
        assert f">{sector['label']}" in svg  # each sector carries its label

    two = {
        "type": "chart",
        "kind": "bar",
        "x_axis": {"categories": ["A", "B"]},
        "y_axis": {"min": 0, "max": 10, "step": 5},
        "series": [{"name": "X", "values": [4, 6]}, {"name": "Y", "values": [5, 3]}],
    }
    fills = re.findall(r'<rect [^>]*height="(?!12")[^"]*" fill="([^"]+)"', render_svg(two))
    assert len(set(fills)) == 2  # two series, two clearly different grey tones
