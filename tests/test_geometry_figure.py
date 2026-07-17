"""A5 — geometry_figure diagram system: consistency check (valid passes, a
deliberately corrupted spec flips a check to False) + spec → SVG render
(non-empty, expected primitives) + determinism. Exercised with hand-crafted
specs (the two geometry ladders KAN-229/230 are separate tickets); see the
param/solution key contract documented on ``check_geometry_figure_consistency``.
"""

from __future__ import annotations

import copy

from exam_engine.diagram import (
    check_consistency,
    check_geometry_figure_consistency,
    render_svg,
)

# ---------------------------------------------------------------------------
# (a) Angle figure: a triangle with two given angles + one unknown (the answer).
#     50 + 60 + 70 = 180 (angle sum of a triangle).
# ---------------------------------------------------------------------------

ANGLE_SPEC = {
    "type": "geometry_figure",
    "unit": "cm",
    "points": [
        {"id": "A", "x": 0.0, "y": 0.0},
        {"id": "B", "x": 4.0, "y": 0.0},
        {"id": "C", "x": 2.0, "y": 3.0},
    ],
    "segments": [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "A"},
    ],
    "angles": [
        {"at": "A", "from": "B", "to": "C", "value_deg": 50, "unknown": False},
        {"at": "B", "from": "A", "to": "C", "value_deg": 60, "unknown": False},
        {"at": "C", "from": "A", "to": "B", "value_deg": 70, "unknown": True},
    ],
}
ANGLE_PARAMS = {"angles": {"B-A-C": 50, "A-B-C": 60}}
ANGLE_SOLUTION = {"answer": {"type": "integer", "value": 70, "unit": "degrees"}}


# ---------------------------------------------------------------------------
# (b) Area figure: a rectangle (8 x 6) with a quarter-circle (r = 4) and a
#     right-angle mark; the whole rectangle is the shaded region.
# ---------------------------------------------------------------------------

AREA_SPEC = {
    "type": "geometry_figure",
    "unit": "cm",
    "points": [
        {"id": "A", "x": 0.0, "y": 0.0},
        {"id": "B", "x": 8.0, "y": 0.0},
        {"id": "C", "x": 8.0, "y": 6.0},
        {"id": "D", "x": 0.0, "y": 6.0},
    ],
    "segments": [
        {"from": "A", "to": "B", "label": "8 cm", "ticks": 1},
        {"from": "B", "to": "C", "label": "6 cm"},
        {"from": "C", "to": "D"},
        {"from": "D", "to": "A"},
    ],
    "arcs": [
        {"center": "A", "radius": 4, "start_deg": 0, "end_deg": 90, "label": "4 cm"},
    ],
    "angles": [
        {"at": "B", "from": "A", "to": "C", "right": True},
    ],
    "shaded": [{"boundary": ["A", "B", "C", "D"], "arcs": []}],
    "labels": [{"at": "A", "text": "A"}],
}
AREA_PARAMS = {"lengths": {"A-B": 8, "B-C": 6}, "radii": {"A": 4}}
AREA_SOLUTION = {"answer": {"type": "decimal", "value": 35.44, "dp": 2, "unit": "cm^2"}}


# ---------------------------------------------------------------------------
# (c) Shaded polygon-minus-arc: a square (side 8) with a quarter circle (r = 8,
#     centred at A) removed. The shaded region is bounded by two square edges
#     (B->C->D) then closed D->B along the quarter-circle arc — the classic
#     "square minus quarter circle" shaded figure (KAN-242).
# ---------------------------------------------------------------------------

SHADED_ARC_SPEC = {
    "type": "geometry_figure",
    "unit": "cm",
    "points": [
        {"id": "A", "x": 0.0, "y": 0.0},
        {"id": "B", "x": 8.0, "y": 0.0},
        {"id": "C", "x": 8.0, "y": 8.0},
        {"id": "D", "x": 0.0, "y": 8.0},
    ],
    "segments": [
        {"from": "A", "to": "B", "label": "8 cm"},
        {"from": "A", "to": "D", "label": "8 cm"},
        {"from": "B", "to": "C"},
        {"from": "C", "to": "D"},
    ],
    "arcs": [{"center": "A", "radius": 8, "start_deg": 0, "end_deg": 90, "label": None}],
    "angles": [],
    "shaded": [
        {
            "boundary": ["B", "C", "D"],
            "arcs": [{"from": "D", "to": "B", "center": "A", "radius": 8, "large": 0, "sweep": 0}],
        }
    ],
    "labels": [],
}


# --- consistency: valid specs pass -----------------------------------------


def test_angle_consistency_passes():
    checks = check_geometry_figure_consistency(ANGLE_SPEC, ANGLE_PARAMS, ANGLE_SOLUTION)
    assert all(checks.values()), checks


def test_area_consistency_passes():
    checks = check_geometry_figure_consistency(AREA_SPEC, AREA_PARAMS, AREA_SOLUTION)
    assert all(checks.values()), checks


def test_consistency_dispatches_via_check_consistency():
    checks = check_consistency(ANGLE_SPEC, ANGLE_PARAMS, ANGLE_SOLUTION)
    assert all(checks.values()), checks


# --- consistency: corrupted specs flip a check -----------------------------


def test_corrupt_given_angle_flips_check():
    bad = copy.deepcopy(ANGLE_SPEC)
    bad["angles"][0]["value_deg"] = 55  # param says 50
    checks = check_geometry_figure_consistency(bad, ANGLE_PARAMS, ANGLE_SOLUTION)
    assert checks["given_angles_match"] is False
    assert not all(checks.values())


def test_corrupt_unknown_angle_flips_check():
    bad = copy.deepcopy(ANGLE_SPEC)
    bad["angles"][2]["value_deg"] = 80  # answer is 70
    checks = check_geometry_figure_consistency(bad, ANGLE_PARAMS, ANGLE_SOLUTION)
    assert checks["unknown_angle_matches_answer"] is False


def test_corrupt_segment_label_flips_check():
    bad = copy.deepcopy(AREA_SPEC)
    bad["segments"][0]["label"] = "9 cm"  # param says 8
    checks = check_geometry_figure_consistency(bad, AREA_PARAMS, AREA_SOLUTION)
    assert checks["segment_labels_match"] is False


def test_corrupt_arc_radius_flips_check():
    bad = copy.deepcopy(AREA_SPEC)
    bad["arcs"][0]["radius"] = 5  # param says 4
    checks = check_geometry_figure_consistency(bad, AREA_PARAMS, AREA_SOLUTION)
    assert checks["arc_radii_match"] is False


def test_duplicate_point_ids_flip_check():
    bad = copy.deepcopy(ANGLE_SPEC)
    bad["points"][1]["id"] = "A"  # two "A"s
    checks = check_geometry_figure_consistency(bad, {}, ANGLE_SOLUTION)
    assert checks["points_distinct"] is False


def test_non_positive_radius_flips_check():
    bad = copy.deepcopy(AREA_SPEC)
    bad["arcs"][0]["radius"] = 0
    checks = check_geometry_figure_consistency(bad, {}, AREA_SOLUTION)
    assert checks["radii_positive"] is False


def test_out_of_range_angle_flips_check():
    bad = copy.deepcopy(ANGLE_SPEC)
    bad["angles"][0]["value_deg"] = 200  # not in (0, 180)
    checks = check_geometry_figure_consistency(bad, {}, ANGLE_SOLUTION)
    assert checks["angle_values_in_range"] is False


def test_shaded_boundary_unknown_point_flips_check():
    bad = copy.deepcopy(AREA_SPEC)
    bad["shaded"][0]["boundary"] = ["A", "B", "Z"]  # Z is not a point
    checks = check_geometry_figure_consistency(bad, {}, AREA_SOLUTION)
    assert checks["shaded_boundary_valid"] is False


def test_shaded_arc_consistency_passes():
    checks = check_geometry_figure_consistency(SHADED_ARC_SPEC, {}, {"answer": {}})
    assert all(checks.values()), checks


def test_shaded_arc_bad_center_ref_flips_check():
    bad = copy.deepcopy(SHADED_ARC_SPEC)
    bad["shaded"][0]["arcs"][0]["center"] = "Z"  # Z is not a point
    checks = check_geometry_figure_consistency(bad, {}, {"answer": {}})
    assert checks["shaded_boundary_valid"] is False


# --- SVG render -------------------------------------------------------------


def test_angle_render_has_segments_and_angle_marks():
    svg = render_svg(ANGLE_SPEC)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "viewBox" in svg
    assert svg.count("<line") == 3  # three triangle edges
    assert svg.count("<path") == 3  # three angle-mark arcs
    assert "70°" not in svg  # the unknown angle's value is not drawn
    assert "50°" in svg and "60°" in svg  # given angles are labelled


def test_area_render_has_arc_shaded_and_right_angle():
    svg = render_svg(AREA_SPEC)
    assert svg.startswith("<svg")
    assert "viewBox" in svg
    assert svg.count("<line") >= 4  # four rectangle edges (+ tick marks)
    assert 'fill="#dbe4fb"' in svg  # shaded region fill
    assert "<polyline" in svg  # right-angle square
    assert " A " in svg  # an SVG arc path command (the quarter circle)
    assert ">8 cm</text>" in svg and ">6 cm</text>" in svg


def test_shaded_polygon_minus_arc_fills_with_arc_path():
    """A square-minus-quarter-circle region fills as one <path> whose boundary is
    closed by an SVG arc command (not just an unfilled outline)."""
    import re

    svg = render_svg(SHADED_ARC_SPEC)
    fills = re.findall(r'<path d="([^"]*)" fill="#dbe4fb" stroke="none"/>', svg)
    assert len(fills) == 1, svg
    d = fills[0]
    assert d.startswith("M ")
    assert " A " in d  # the boundary edge closed by the quarter-circle arc
    assert d.rstrip().endswith("Z")


def test_render_dispatches_via_render_svg():
    assert render_svg(ANGLE_SPEC).startswith("<svg")


# --- determinism ------------------------------------------------------------


def test_render_is_deterministic():
    assert render_svg(ANGLE_SPEC) == render_svg(ANGLE_SPEC)
    assert render_svg(AREA_SPEC) == render_svg(AREA_SPEC)


def test_render_coordinates_are_integers():
    # Every coordinate emitted must be an integer (byte-stable output). Check the
    # line endpoints, which are the scaled point coordinates.
    import re

    svg = render_svg(AREA_SPEC)
    for attr in re.findall(r'(?:x1|y1|x2|y2)="([^"]+)"', svg):
        assert re.fullmatch(r"-?\d+", attr), attr
