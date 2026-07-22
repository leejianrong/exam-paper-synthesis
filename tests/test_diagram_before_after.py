"""A5 — before-after bar-model diagram: consistency check (honest spec passes,
each corruption rejected), spec → SVG render smoke, and determinism (R3.3, R3.4)."""

from __future__ import annotations

import copy

from exam_engine.blueprints.registry import get_solver
from exam_engine.diagram import (
    check_bar_model_before_after_consistency,
    check_consistency,
    render_svg,
)

PARAMS = {
    "names": ["Aisha", "Ben"],
    "ratio_before": [2, 3],
    "ratio_after": [1, 2],
    "spent": 20,
}


def _built(params: dict = PARAMS) -> tuple[dict, dict]:
    """Return (solution, diagram) for a params set via the real solver."""
    solver = get_solver("ratio_hard")
    solution = solver.solve(params)
    diagram = solver.diagram(params, solution)
    return solution, diagram


# --- consistency check (R3.3) ----------------------------------------------


def test_consistency_passes_for_built_spec():
    solution, diagram = _built()
    checks = check_consistency(diagram, PARAMS, solution)
    assert all(checks.values()), checks


def test_consistency_rejects_corrupted_units():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["stages"][0]["bars"][0]["units"] += 1  # A's before-units no longer match
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["before_bars"] is False
    assert not all(checks.values())


def test_consistency_rejects_broken_invariant():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["stages"][1]["bars"][1]["units"] += 1  # after.B != before.B → invariant broken
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["invariant"] is False
    assert not all(checks.values())


def test_consistency_rejects_corrupted_annotation():
    solution, diagram = _built()
    bad = copy.deepcopy(diagram)
    bad["annotations"][0]["label"] = "1 unit = $999"
    checks = check_bar_model_before_after_consistency(bad, PARAMS, solution)
    assert checks["unit_annotation"] is False
    assert not all(checks.values())


# --- SVG render (R3.4) ------------------------------------------------------


def test_svg_render_smoke():
    _, diagram = _built()
    svg = render_svg(diagram)

    assert svg
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "viewBox" in svg
    for name in PARAMS["names"]:
        assert name in svg
    assert "Before" in svg
    assert "After" in svg
    # v=20, spent=20, B=$120 (see golden fixture 1)
    assert "1 unit = $20" in svg
    assert "Aisha spent = $20" in svg
    assert "Ben = $120" in svg
    assert "<path" in svg  # the invariant brace is a path


def test_svg_is_deterministic():
    _, diagram = _built()
    assert render_svg(diagram) == render_svg(diagram)


# --- KAN-310: two view modes on the explosion case (before 7:1 → after 8:9) --
# L = lcm(1, 9) = 9; A's before-units = 7·9 = 63 (the "segment explosion"),
# after-units = 8. spent = (63 − 8)·10 = 550, b_amount = 9·10 = 90.
EXPLODE = {
    "names": ["Aisha", "Ben"],
    "ratio_before": [7, 1],
    "ratio_after": [8, 9],
    "spent": 550,
}


def _count(haystack: str, needle: str) -> int:
    return haystack.count(needle)


def test_default_view_mode_is_grouped():
    _, diagram = _built(EXPLODE)
    assert diagram["view_mode"] == "grouped"
    # parts carry the original ratio terms (a, b) / (c, d).
    assert [b["parts"] for b in diagram["stages"][0]["bars"]] == [7, 1]
    assert [b["parts"] for b in diagram["stages"][1]["bars"]] == [8, 9]


def test_both_modes_pass_consistency():
    solution, diagram = _built(EXPLODE)
    grouped = {**diagram, "view_mode": "grouped"}
    sliced = {**diagram, "view_mode": "sliced"}
    assert all(check_consistency(grouped, EXPLODE, solution).values())
    assert all(check_consistency(sliced, EXPLODE, solution).values())


def test_grouped_mode_does_not_explode():
    """Grouped draws O(ratio-terms) dividers + a unit-worth label — never the
    common-unit LCM (which would be 62 sub-dividers on A's before bar alone)."""
    _, diagram = _built(EXPLODE)
    svg = render_svg({**diagram, "view_mode": "grouped"})
    # Dividers = (parts-1) per bar: (7-1)+(1-1)+(8-1)+(9-1) = 21 — bounded, small.
    assert _count(svg, "<line") == 21
    assert _count(svg, "<rect") == 4
    # A segment's unit-worth label: before parts = 9 common-units, after = 1.
    assert "= 9u" in svg
    assert "= 1u" in svg
    # Grouped uses only the heavy divider weight (no fine sub-unit grid).
    assert 'stroke-width="0.75"' not in svg


def test_sliced_mode_has_heavy_and_light_dividers():
    """Sliced keeps the full common-unit grid but marks the original-ratio
    boundaries with a heavier stroke than the sub-unit dividers."""
    _, diagram = _built(EXPLODE)
    svg = render_svg({**diagram, "view_mode": "sliced"})
    # Both stroke weights present: heavy (ratio boundaries) + light (sub-units).
    assert 'stroke-width="2"' in svg
    assert 'stroke-width="0.75"' in svg
    # Far more dividers than grouped (the full LCM grid): 62+0+7+8 = 77 inner
    # dividers, plus the two heavy end-boundaries fold into those counts.
    assert _count(svg, "<line") > 21
    # Heavy boundaries: A-before has 7 groups → 6 heavy inner dividers, etc. The
    # count of heavy dividers equals Σ(parts-1) = 21 (same boundaries grouped draws).
    assert _count(svg, 'stroke-width="2"') == 21


def test_grouped_is_narrower_than_sliced():
    """The whole point: grouped never blows up the canvas width."""
    _, diagram = _built(EXPLODE)

    def _width(svg: str) -> int:
        return int(svg.split('width="', 1)[1].split('"', 1)[0])

    g = _width(render_svg({**diagram, "view_mode": "grouped"}))
    s = _width(render_svg({**diagram, "view_mode": "sliced"}))
    assert g < s
    assert s > 2000  # the explosion the sliced grid inevitably carries


def test_absent_view_mode_defaults_to_grouped_render():
    """A spec without view_mode renders identically to an explicit grouped spec."""
    _, diagram = _built(EXPLODE)
    no_mode = {k: v for k, v in diagram.items() if k != "view_mode"}
    assert render_svg(no_mode) == render_svg({**diagram, "view_mode": "grouped"})
