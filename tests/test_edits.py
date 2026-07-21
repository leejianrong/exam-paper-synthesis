"""V3 — edit-operation transforms (ADR-0004/0009).

Every edit returns a NEW schema-valid object with stamped lineage and leaves the
source object untouched (deep-copy semantics)."""

from __future__ import annotations

import copy
import re

import pytest
from exam_engine import edits
from exam_engine.errors import EditNotApplicable
from exam_engine.pipeline import generate
from exam_engine.schema import validate_object


def _lineage_ok(child: dict, source: dict) -> None:
    prov = child["provenance"]
    assert prov["parent_id"] == source["id"]
    assert prov["version"] == source["provenance"]["version"] + 1
    assert prov["created_by"] == "engine"
    assert prov["llm_used"] is False
    assert prov["created_at"] is None
    assert child["id"] != source["id"]
    assert validate_object(child) == []


@pytest.mark.parametrize("op", ["regenerate", "make-harder", "make-easier"])
def test_resample_ops_lineage_and_unmutated(op):
    source = generate("ratio_medium", 42)
    before = copy.deepcopy(source)
    child = edits.apply(op, source, seed=99)
    _lineage_ok(child, source)
    assert source == before  # source never mutated


def test_regenerate_keeps_blueprint():
    source = generate("ratio_medium", 42)
    child = edits.apply("regenerate", source, seed=7)
    assert child["blueprint_code"] == "ratio_medium"


def test_make_harder_climbs():
    source = generate("ratio_medium", 42)
    child = edits.apply("make-harder", source, seed=7)
    assert child["blueprint_code"] == "ratio_hard"


def test_make_easier_descends():
    source = generate("ratio_medium", 42)
    child = edits.apply("make-easier", source, seed=7)
    assert child["blueprint_code"] == "ratio_easy"


def test_available_ops_at_ladder_ends():
    hard = generate("ratio_hard", 3)
    easy = generate("ratio_easy", 3)
    assert "make-harder" not in edits.available_ops(hard)
    assert "make-easier" in edits.available_ops(hard)
    assert "make-easier" not in edits.available_ops(easy)
    assert "make-harder" in edits.available_ops(easy)


def test_apply_unavailable_op_raises():
    hard = generate("ratio_hard", 3)
    with pytest.raises(EditNotApplicable):
        edits.apply("make-harder", hard, seed=1)
    easy = generate("ratio_easy", 3)
    with pytest.raises(EditNotApplicable):
        edits.apply("make-easier", easy, seed=1)


@pytest.mark.parametrize("code", ["ratio_easy", "ratio_medium", "ratio_hard"])
def test_change_to_decimals(code):
    source = generate(code, 5)
    before = copy.deepcopy(source)
    child = edits.apply("change-to-decimals", source)
    _lineage_ok(child, source)
    assert source == before

    ans = child["question"]["parts"][0]["answer"]
    assert ans["type"] == "decimal"
    # Money declares 2 dp so every surface renders it as currency (KAN-309).
    assert ans["dp"] == 2
    assert ans["unit"] == "$"
    src_value = source["question"]["parts"][0]["answer"]["value"]
    assert ans["value"] == src_value / 10

    # parameters remain the original integer sample (no floats stored).
    assert child["parameters"] == source["parameters"]
    ratio_key = "ratio" if "ratio" in child["parameters"] else "ratio_before"
    assert all(isinstance(v, int) for v in child["parameters"][ratio_key])

    # The story text carries $ amounts at exactly 2 dp (e.g. "$20.00", not "$20.0").
    text = child["question"]["parts"][0]["text"]
    assert re.search(r"\$\d+\.\d{2}\b", text)
    assert not re.search(r"\$\d+\.\d(?!\d)", text)  # never a bare 1-dp money amount

    assert child["validation"]["checks"]["representation"] == "decimals"


@pytest.mark.parametrize(
    "code", ["ratio_easy", "ratio_medium", "ratio_hard", "percentage_easy", "percentage_hard"]
)
def test_change_to_decimals_money_is_2dp_everywhere(code):
    # Every $ surface the decimals view produces — story text, worked steps, and
    # bar-model labels — must show exactly 2 dp (KAN-309), never a bare 1 dp.
    source = generate(code, 11)
    child = edits.apply("change-to-decimals", source)
    part = child["question"]["parts"][0]

    bare_1dp = re.compile(r"\$\d+\.\d(?!\d)")
    two_dp = re.compile(r"\$\d+\.\d{2}\b")

    surfaces = [part["text"]]
    surfaces += [s["text"] for s in part["solution_steps"]]
    surfaces += [s["expr"] for s in part["solution_steps"] if s.get("expr")]

    diagram = part["diagram"]
    if diagram is not None:
        labels = _diagram_money_labels(diagram)
        assert labels  # the ratio ladder's aid bars carry $ labels
        surfaces += labels

    joined = " ".join(surfaces)
    assert two_dp.search(joined)  # at least one $ amount is shown
    for surface in surfaces:
        assert not bare_1dp.search(surface), f"1-dp money leaked: {surface!r}"


def _diagram_money_labels(diagram: dict) -> list[str]:
    """Collect every ``$``-bearing label from a bar-model diagram spec."""
    labels: list[str] = []
    for ann in diagram.get("annotations", []):
        labels.append(ann.get("label", ""))
    bracket = diagram.get("total_bracket")
    if bracket:
        labels.append(bracket.get("label", ""))
    return [ell for ell in labels if "$" in ell]


@pytest.mark.parametrize("code", ["ratio_easy", "ratio_medium", "ratio_hard"])
def test_available_ops_offers_toggle_for_aid_diagrams(code):
    # The ratio blueprints declare aid diagram families (bar_model /
    # bar_model_before_after), so toggle-diagram must be offered.
    obj = generate(code, 3)
    assert "toggle-diagram" in edits.available_ops(obj)


def test_available_ops_hides_toggle_for_mandatory_shaded_fraction(monkeypatch):
    # A shaded_fraction figure is *mandatory* (carries the answer), not an aid, so
    # toggle-diagram must NOT be offered. Simulate a blueprint that declares it.
    obj = generate("ratio_medium", 3)

    class _Stub:
        diagram = "shaded_fraction"

    monkeypatch.setattr(edits, "load_blueprint", lambda code: _Stub())
    ops = edits.available_ops(obj)
    assert "toggle-diagram" not in ops
    assert "regenerate" in ops  # other ops unaffected


@pytest.mark.parametrize(
    "code,dtype",
    [
        ("ratio_easy", "bar_model"),
        ("ratio_medium", "bar_model"),
        ("ratio_hard", "bar_model_before_after"),
    ],
)
def test_toggle_diagram_both_directions(code, dtype):
    source = generate(code, 8)
    before = copy.deepcopy(source)
    assert source["question"]["parts"][0]["diagram"] is not None  # generated with a diagram

    # present -> null
    off = edits.apply("toggle-diagram", source, seed=1)
    _lineage_ok(off, source)
    assert off["question"]["parts"][0]["diagram"] is None
    assert source == before

    # null -> rebuilt (correct diagram type)
    back = edits.apply("toggle-diagram", off, seed=1)
    diagram = back["question"]["parts"][0]["diagram"]
    assert diagram is not None
    assert diagram["type"] == dtype
