"""T1 — the ``chart`` diagram (schema 1.7.0): consistency, rendering, the
hidden-value leak guard, the schema/load gates, and the sourced fixtures.

The fixtures are structural stand-ins (no third-party text or artwork); the
*correctness* authority here is the invariants below, not the fixtures.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from exam_engine import canonical
from exam_engine.canonical import CanonicalValidationError
from exam_engine.chart import check_chart_consistency, leaked_hidden_values
from exam_engine.diagram import check_consistency, render_svg
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

SOURCED = Path(__file__).parent / "fixtures" / "sourced"
FIXTURES = {k: SOURCED / f"standin_chart_{k}.json" for k in ("pie", "bar", "line")}


def _obj(kind: str) -> dict:
    return json.loads(FIXTURES[kind].read_text("utf-8"))


def _spec(kind: str) -> dict:
    return _obj(kind)["question"]["diagram"]


# ---------------------------------------------------------------------------
# Fixtures load, are consistent, and render deterministically
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["pie", "bar", "line"])
def test_fixture_loads_and_is_consistent(kind):
    obj = canonical.load(_obj(kind))
    assert obj["schema_version"] == "1.7.0"
    checks = check_consistency(obj["question"]["diagram"], {}, {})
    assert checks and all(checks.values()), checks


@pytest.mark.parametrize("kind", ["pie", "bar", "line"])
def test_render_is_deterministic_inter_only(kind):
    svg = render_svg(_spec(kind))
    assert svg == render_svg(copy.deepcopy(_spec(kind)))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert 'font-family="Inter, system-ui, sans-serif"' in svg
    assert svg.count("font-family=") == 1  # one typeface, declared once (EXA-94)


def test_bar_draws_one_rect_per_value_scaled_to_axis():
    svg = render_svg(_spec("bar"))
    assert svg.count("<rect") == 5  # 5 bars, single series => no legend swatch
    # The Friday bar (36 on a 0-40 axis) is taller than the Thursday bar (12).
    import re

    heights = [float(h) for h in re.findall(r'<rect [^>]*height="([\d.]+)"', svg)]
    assert heights[4] > heights[3] > 0
    assert heights[4] / heights[3] == pytest.approx(3.0, rel=0.01)


def test_line_breaks_at_null_and_dashes_second_series():
    spec = _spec("line")
    spec["series"][0]["values"][2] = None
    spec["series"][1]["show_values"] = True
    svg = render_svg(spec)
    assert svg.count("<polyline") == 3  # A: two runs (1-2, 4-5), B: one
    assert 'stroke-dasharray="7 4"' in svg  # series B is dashed, not just recoloured
    assert svg.count("<circle") == 9  # one marker per non-null value
    assert ">13<" in svg  # B's labels shown, A's not
    assert ">18<" not in svg


# ---------------------------------------------------------------------------
# Consistency: each corruption flips exactly the check that names it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate, failing",
    [
        (lambda s: s["series"][0]["values"].pop(), "series_align_with_categories"),
        (lambda s: s["series"][0]["values"].__setitem__(0, 41), "values_within_axis"),
        (lambda s: s["y_axis"].update(step=15), "step_divides_span"),
        (lambda s: s["y_axis"].update(min=40, max=0), "axis_range_valid"),
        (lambda s: s["x_axis"]["categories"].__setitem__(1, "Mon"), "categories_unique"),
    ],
)
def test_axes_chart_corruptions_are_caught(mutate, failing):
    spec = _spec("bar")
    mutate(spec)
    checks = check_chart_consistency(spec)
    assert checks[failing] is False
    assert not all(checks.values())


def test_percent_pie_must_sum_to_100():
    spec = _spec("pie")
    assert check_chart_consistency(spec)["percent_sums_to_100"] is True
    spec["sectors"][0]["value"] = 36
    assert check_chart_consistency(spec)["percent_sums_to_100"] is False
    spec["value_unit"] = None  # counts, not percentages: no 100 constraint
    assert "percent_sums_to_100" not in check_chart_consistency(spec)


# ---------------------------------------------------------------------------
# The leak guard: a hidden number never reaches the SVG text
# ---------------------------------------------------------------------------


def test_hidden_sector_is_drawn_at_true_size_but_never_printed():
    spec = _spec("pie")
    svg = render_svg(spec)
    assert "Oranges" in svg  # still labelled
    assert leaked_hidden_values(spec, svg) == []
    # 25% of the circle: the Oranges wedge ends exactly a quarter-turn round.
    assert "A 100 100 0 0 1" in svg


def test_hidden_value_equal_to_a_shown_value_is_not_a_false_positive():
    spec = _spec("pie")
    # Bananas shows 25% and the hidden Oranges is also 25: fine.
    assert [s["value"] for s in spec["sectors"]].count(25) == 2
    assert leaked_hidden_values(spec, render_svg(spec)) == []


def test_guard_actually_detects_a_leak():
    spec = _spec("pie")
    spec["title"] = "Oranges 25 pupils"  # a title that gives the number away
    assert leaked_hidden_values(spec, render_svg(spec)) == ["25"]
    leaky = render_svg(_spec("pie")).replace(">Oranges<", ">Oranges 25%<")
    assert leaked_hidden_values(_spec("pie"), leaky) == ["25"]


def test_aria_label_carries_no_data():
    svg = render_svg(_spec("bar"))
    label = svg.split('aria-label="')[1].split('"')[0]
    assert label == "Books borrowed"


def test_text_is_xml_escaped():
    spec = _spec("bar")
    spec["title"] = 'A & B <"x">'
    svg = render_svg(spec)
    assert "A &amp; B &lt;&quot;x&quot;&gt;" in svg
    assert '<"x">' not in svg


# ---------------------------------------------------------------------------
# Schema + load gate
# ---------------------------------------------------------------------------


def _with(fixture: str, **changes) -> dict:
    obj = _obj(fixture)
    obj["question"]["diagram"].update(changes)
    return obj


def test_schema_rejects_mixed_kind_fields():
    assert validate_object(_with("pie", series=[{"name": "x", "values": [1]}])) != []
    assert validate_object(_with("bar", sectors=_spec("pie")["sectors"])) != []
    assert validate_object(_with("bar", value_unit="%")) != []


def test_schema_requires_the_kind_specific_fields():
    obj = _obj("bar")
    del obj["question"]["diagram"]["y_axis"]
    assert validate_object(obj) != []
    obj = _obj("pie")
    del obj["question"]["diagram"]["sectors"]
    assert validate_object(obj) != []
    assert validate_object(_with("bar", kind="donut")) != []


def test_load_gate_rejects_numbers_that_disagree_with_the_axis():
    obj = _obj("bar")
    obj["question"]["diagram"]["series"][0]["values"][0] = 99  # off the 0-40 axis
    assert validate_object(obj) == []  # schema-valid...
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)  # ...but the load gate points at it
    assert "question.diagram: chart inconsistent: values_within_axis" in str(exc.value)


def test_load_gate_also_checks_chart_options_of_an_mcq():
    obj = _obj("pie")
    good = obj["question"]["diagram"]
    bad = copy.deepcopy(good)
    bad["sectors"][0]["value"] = 50  # sums to 115%
    obj["question"]["diagram"] = None
    part = obj["question"]["parts"][0]
    part["answer"] = {
        "type": "choice",
        "correct": "A",
        "options": [{"label": "A", "diagram": good}, {"label": "B", "diagram": bad}],
    }
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)
    assert "options[1].diagram: chart inconsistent: percent_sums_to_100" in str(exc.value)


def test_earlier_schema_objects_still_load_under_1_7_0():
    """Additive-only proof: E3's 1.6.0 fixtures load unmodified."""
    for name in ("psle_2023_table", "psle_2023_grid_net", "psle_2023_construction"):
        data = json.loads((SOURCED / f"{name}.json").read_text("utf-8"))
        assert data["schema_version"] == "1.6.0"
        canonical.load(data)


# ---------------------------------------------------------------------------
# End to end: student view hides what the key shows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["pie", "bar", "line"])
def test_worksheet_and_key_render_the_chart_as_a_stem_figure(kind):
    obj = canonical.load(_obj(kind))
    sheet = render_worksheet_html("Charts", [obj])
    key = render_answer_key_html("Charts", [obj])
    assert '<figure class="diagram"><svg' in sheet
    assert '<figure class="diagram"><svg' in key
    assert "Answer:" in key and "Answer:" not in sheet


def test_pie_answer_is_not_printed_on_the_student_sheet():
    obj = canonical.load(_obj("pie"))
    sheet = render_worksheet_html("Charts", [obj])
    assert "25% of 80" not in sheet  # working is key-only


# ---------------------------------------------------------------------------
# Review hardening (PR #156)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [float("inf"), float("nan")])
def test_non_finite_numbers_fail_checks_instead_of_raising(bad):
    bar = _spec("bar")
    bar["y_axis"]["max"] = bad
    assert check_chart_consistency(bar)["axis_range_valid"] is False
    bar = _spec("bar")
    bar["series"][0]["values"][0] = bad
    assert check_chart_consistency(bar)["values_within_axis"] is False
    pie = _spec("pie")
    pie["sectors"][0]["value"] = bad
    assert check_chart_consistency(pie)["values_positive"] is False


def test_load_gate_gives_a_422_style_error_for_infinity():
    obj = json.loads(json.dumps(_obj("bar")).replace("40,", "Infinity,", 1))
    assert obj["question"]["diagram"]["y_axis"]["max"] == float("inf")
    with pytest.raises(CanonicalValidationError):
        canonical.load(obj)


def test_bar_axis_must_start_at_zero_but_a_line_axis_may_not():
    bar = _spec("bar")
    bar["y_axis"].update(min=10, max=40, step=10)
    bar["series"][0]["values"] = [24, 18, 30, 12, 36]
    assert check_chart_consistency(bar)["bar_axis_starts_at_zero"] is False
    line = _spec("line")
    line["y_axis"].update(min=0)
    assert "bar_axis_starts_at_zero" not in check_chart_consistency(line)
    line["y_axis"].update(min=-5, max=20, step=5)
    assert all(check_chart_consistency(line).values())  # a line may use a negative range


def test_values_must_print_exactly():
    pie = _spec("pie")
    pie["value_unit"] = None
    pie["sectors"][0]["value"] = 33.3333  # would print as 33.333
    assert check_chart_consistency(pie)["values_print_exactly"] is False
    pie["sectors"][0]["value"] = 33.333
    assert check_chart_consistency(pie)["values_print_exactly"] is True


def _viewbox_width(svg: str) -> float:
    return float(svg.split('viewBox="0 0 ')[1].split()[0])


def test_long_legend_wraps_inside_the_figure():
    spec = _spec("line")
    spec["series"] = [{"name": f"Series number {i}", "values": [1, 2, 3, 4, 5]} for i in range(6)]
    svg = render_svg(spec)
    width = _viewbox_width(svg)
    import re

    # every legend swatch sits inside the figure, and the figure grew to hold a second row
    xs = [float(x) for x in re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="12"', svg)]
    assert len(xs) == 6 and max(xs) + 12 <= width
    assert float(svg.split('viewBox="0 0 ')[1].split()[1].rstrip('"')) > 320


def test_pie_labels_fit_in_the_viewbox():
    spec = _spec("pie")
    spec["sectors"] = [
        {"label": "Mathematics homework", "value": 25},
        {"label": "Science projects", "value": 25},
        {"label": "Mother Tongue", "value": 25},
        {"label": "English compositions", "value": 25},
    ]
    svg = render_svg(spec)
    width = _viewbox_width(svg)
    import re

    for x, anchor, text in re.findall(
        r'<text x="([\d.]+)" y="[\d.]+" text-anchor="(\w+)" fill="[^"]+">([^<]+)</text>', svg
    ):
        x, est = float(x), 7.0 * len(text)  # generous Inter 12px average glyph width
        if anchor == "start":
            assert x + est <= width, text
        elif anchor == "end":
            assert x - est >= 0, text


def test_chart_size_is_bounded_so_a_request_cannot_ask_for_a_huge_figure():
    obj = _obj("bar")
    d = obj["question"]["diagram"]
    d["x_axis"]["categories"] = [f"c{i}" for i in range(31)]
    d["series"][0]["values"] = [1] * 31
    assert validate_object(obj) != []
    pie = _obj("pie")
    pie["question"]["diagram"]["sectors"] = [{"label": f"s{i}", "value": 1} for i in range(13)]
    assert validate_object(pie) != []
    many = _obj("bar")
    many["question"]["diagram"]["series"] = [{"name": f"n{i}", "values": [1] * 5} for i in range(7)]
    assert validate_object(many) != []
