"""D1 — shaded_fraction figure: consistency check (valid passes, corrupt spec
flips a check to False) + spec → SVG render (non-empty, right number of filled
cells) + determinism. The figure is a *mandatory* Fractions figure: it must
provably equal the answer fraction (num/den = shaded/total)."""

from __future__ import annotations

import re

import pytest
from exam_engine.diagram import (
    check_consistency,
    check_shaded_fraction_consistency,
    render_svg,
)

# A solution whose answer is the fraction 3/8.
SOLUTION = {"answer": {"type": "fraction", "numerator": 3, "denominator": 8}}


def _spec(shape: str = "rectangle", total: int = 8, shaded: int = 3) -> dict:
    return {
        "type": "shaded_fraction",
        "shape": shape,
        "total_parts": total,
        "shaded_parts": shaded,
    }


# --- consistency check ------------------------------------------------------


@pytest.mark.parametrize("shape", ["rectangle", "circle", "bar"])
def test_consistency_passes_for_matching_spec(shape: str):
    checks = check_shaded_fraction_consistency(_spec(shape=shape), {}, SOLUTION)
    assert all(checks.values()), checks


def test_consistency_dispatches_via_check_consistency():
    checks = check_consistency(_spec(), {}, SOLUTION)
    assert all(checks.values()), checks


def test_consistency_rejects_wrong_total_parts():
    bad = _spec(total=9)  # denominator is 8
    checks = check_shaded_fraction_consistency(bad, {}, SOLUTION)
    assert checks["total_matches_denominator"] is False
    assert not all(checks.values())


def test_consistency_rejects_wrong_shaded_parts():
    bad = _spec(shaded=4)  # numerator is 3
    checks = check_shaded_fraction_consistency(bad, {}, SOLUTION)
    assert checks["shaded_matches_numerator"] is False


def test_consistency_rejects_unknown_shape():
    bad = _spec(shape="hexagon")
    checks = check_shaded_fraction_consistency(bad, {}, SOLUTION)
    assert checks["shape_valid"] is False


def test_consistency_rejects_shaded_out_of_range():
    # shaded 3 > total 2 (and denominator mismatch too, but range is the point).
    sol = {"answer": {"numerator": 3, "denominator": 2}}
    checks = check_shaded_fraction_consistency(_spec(total=2, shaded=3), {}, sol)
    assert checks["shaded_in_range"] is False


# --- SVG render -------------------------------------------------------------

_SHADE = 'fill="#93b8f2"'  # light-blue shaded fill (distinct from the outline)
_STROKE = 'stroke="#2f5fe0"'  # darker-blue segment outline
_EMPTY = 'fill="#eef2fb"'  # pale empty fill


def _filled_cells(svg: str) -> int:
    return svg.count(_SHADE)


@pytest.mark.parametrize("shape", ["rectangle", "bar", "circle"])
def test_render_non_empty_and_right_number_of_filled_cells(shape: str):
    svg = render_svg(_spec(shape=shape, total=8, shaded=3))
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "viewBox" in svg
    assert _filled_cells(svg) == 3


def test_render_rectangle_has_one_rect_per_part():
    svg = render_svg(_spec(shape="rectangle", total=5, shaded=2))
    assert svg.count("<rect") == 5
    assert _filled_cells(svg) == 2


def test_render_bar_has_one_rect_per_part():
    svg = render_svg(_spec(shape="bar", total=4, shaded=1))
    assert svg.count("<rect") == 4
    assert _filled_cells(svg) == 1


def test_render_circle_has_one_sector_per_part():
    svg = render_svg(_spec(shape="circle", total=6, shaded=5))
    assert svg.count("<path") == 6
    assert _filled_cells(svg) == 5


def test_render_circle_single_part_is_a_whole_circle():
    svg = render_svg(_spec(shape="circle", total=1, shaded=1))
    assert svg.count("<circle") == 1
    assert svg.count("<path") == 0
    assert _filled_cells(svg) == 1


def test_render_none_shaded_has_no_filled_cells():
    svg = render_svg(_spec(shape="rectangle", total=4, shaded=0))
    assert _filled_cells(svg) == 0


@pytest.mark.parametrize("shape", ["rectangle", "bar", "circle"])
def test_render_outline_distinct_from_fills(shape: str):
    # KAN-311: the segment outline must be a different colour from both the
    # shaded and the empty fill, so every segment border (shaded and unshaded)
    # stays visible in the card, preview, and PDF.
    assert _SHADE != _STROKE
    assert _EMPTY != _STROKE
    svg = render_svg(_spec(shape=shape, total=4, shaded=2))
    assert _SHADE in svg  # a shaded segment
    assert _EMPTY in svg  # an unshaded segment
    assert svg.count(_STROKE) == 4  # a visible outline on every one of them


def test_render_circle_sector_vertices_within_canvas():
    # Circle sectors are drawn as <path> elements; their vertices (in the `d`
    # attribute) must stay inside the declared square canvas.
    svg = render_svg(_spec(shape="circle", total=7, shaded=4))
    size = int(re.search(r'width="(\d+)"', svg).group(1))
    ds = re.findall(r'd="([^"]+)"', svg)
    assert ds
    coords = [float(v) for d in ds for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
    assert coords
    assert all(0 <= c <= size for c in coords)


def test_render_rejects_unknown_shape():
    with pytest.raises(ValueError):
        render_svg(
            {"type": "shaded_fraction", "shape": "hexagon", "total_parts": 3, "shaded_parts": 1}
        )


# --- determinism ------------------------------------------------------------


@pytest.mark.parametrize("shape", ["rectangle", "bar", "circle"])
def test_render_is_deterministic(shape: str):
    a = render_svg(_spec(shape=shape, total=8, shaded=3))
    b = render_svg(_spec(shape=shape, total=8, shaded=3))
    assert a == b
