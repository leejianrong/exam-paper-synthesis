"""W2c — Convert to free-form: the pure engine conversion (sweep every blueprint and every
sourced fixture) and the API that rasterises figures into owner-scoped assets."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from app import export
from app.main import app
from documents import make_doc
from exam_engine import generate
from exam_engine.convert import answer_inline, figures, to_freeform
from exam_engine.document import validate_document
from fastapi.testclient import TestClient
from images import png
from test_export_api import requires_chromium

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}
SOURCED = sorted((Path(__file__).parent / "fixtures" / "sourced").glob("*.json"))
CODES = sorted(
    p.stem
    for p in (
        Path(__file__).parent.parent / "engine" / "exam_engine" / "content" / "blueprints"
    ).glob("*.yaml")
)


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")


def _texts(blocks) -> str:
    out: list[str] = []

    def walk(n):
        if n.get("type") == "text":
            out.append(n["text"])
        if n.get("type") == "math":
            out.append(n["attrs"]["latex"])
        for c in n.get("content", []):
            walk(c)

    for b in blocks:
        walk(b)
    return " ".join(out)


def _as_document(draft: dict, *, figure_to_image: bool = True) -> dict:
    """The draft wrapped as a free-form block, figures swapped for a dummy image."""

    def swap(blocks):
        return [
            {"type": "image", "attrs": {"asset_id": "asset_0001", "alt": b["alt"]}}
            if b["type"] == "figure"
            else b
            for b in blocks
        ]

    return make_doc(
        {
            "type": "freeformQuestion",
            "attrs": {
                "block_id": "ff_convert_1",
                "marks": draft["marks"],
                "answer": {"type": "doc", "content": swap(draft["answer"])},
            },
            "content": swap(draft["body"]),
        }
    )


# --- pure conversion ---------------------------------------------------------------


@pytest.mark.parametrize("code", CODES)
def test_every_blueprint_converts_to_a_valid_free_form_block(code):
    for seed in range(1, 9):
        obj = generate(code, seed)
        draft = to_freeform(obj)
        q = obj["question"]
        assert draft["marks"] == q["total_marks"], (code, seed)
        body = _texts(draft["body"])
        # the question's text is preserved, part by part
        for part in q["parts"]:
            assert part["text"] in body, (code, seed)
        if q.get("stem"):
            assert q["stem"] in body
        # the answer carries the printed answer and every worked step
        answer = _texts(draft["answer"])
        assert "Answer:" in answer
        for part in q["parts"]:
            for step in part.get("solution_steps", []):
                assert step["text"] in answer, (code, seed)
        # figures survive as placeholders, in the right place
        n_diagrams = sum(
            1 for d in [q.get("diagram"), *[p.get("diagram") for p in q["parts"]]] if d
        )
        assert len(figures(draft["body"])) >= n_diagrams
        assert validate_document(_as_document(draft)) == [], (code, seed)


@pytest.mark.parametrize("path", SOURCED, ids=lambda p: p.stem)
def test_sourced_fixtures_convert_too(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    draft = to_freeform(obj)
    assert validate_document(_as_document(draft)) == []
    assert draft["marks"] == obj["question"]["total_marks"]


def test_mcq_options_become_a_list_and_the_answer_names_the_correct_one():
    obj = json.loads((SOURCED[0].parent / "psle_2023_mcq.json").read_text(encoding="utf-8"))
    draft = to_freeform(obj)
    part = obj["question"]["parts"][0]
    options = part["answer"]["options"]
    listed = [b for b in draft["body"] if b["type"] in ("orderedList", "bulletList")]
    paragraphs = [b for b in draft["body"] if b["type"] == "paragraph"]
    if listed:
        assert len(listed[0]["content"]) == len(options)
    else:
        assert len(paragraphs) >= 1 + len(options)
    assert _texts(draft["answer"]).startswith("Answer:")
    correct = part["answer"]["correct"]
    assert f"({correct})" in _texts(draft["answer"])


def test_table_becomes_a_plain_text_grid_with_blanks():
    obj = json.loads((SOURCED[0].parent / "psle_2023_table.json").read_text(encoding="utf-8"))
    draft = to_freeform(obj)
    table = obj["question"]["table"]
    body = _texts(draft["body"])
    assert " | " in body
    for row in table["rows"]:
        for cell in row:
            if isinstance(cell, dict):
                assert "______" in body
            elif cell is not None:
                assert str(cell) in body


def test_construction_answer_is_a_figure():
    obj = json.loads(
        (SOURCED[0].parent / "psle_2023_construction.json").read_text(encoding="utf-8")
    )
    draft = to_freeform(obj)
    assert any(f["label"] == "answer figure" for f in figures(draft["answer"]))


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ({"type": "integer", "value": 7}, "7"),
        ({"type": "quantity", "value": 40, "unit": "$"}, "$40"),
        ({"type": "decimal", "value": 4.5, "unit": "$"}, "$4.50"),
        ({"type": "quantity", "value": 12, "unit": "cm"}, "12 cm"),
        ({"type": "quantity", "value": 25, "unit": "%"}, "25%"),
        ({"type": "ratio", "parts": [2, 3]}, "2 : 3"),
        ({"type": "set", "values": [1, 2]}, "1, 2"),
        ({"type": "text", "text": "yes"}, "yes"),
    ],
)
def test_answer_text(answer, expected):
    assert _texts([{"type": "paragraph", "content": answer_inline(answer)}]) == expected


def test_fraction_answer_is_a_math_node():
    inline = answer_inline({"type": "fraction", "numerator": 3, "denominator": 4})
    assert inline == [{"type": "math", "attrs": {"latex": r"\frac{3}{4}"}}]


# --- API ----------------------------------------------------------------------------------


def _fake_pngs(monkeypatch, *, fail: set[int] | None = None):
    calls: list[int] = []

    def fake(svgs, *, scale=2):
        calls.append(len(svgs))
        return [None if i in (fail or set()) else png(30 + i, 20) for i in range(len(svgs))]

    monkeypatch.setattr(export, "html_to_png_many", fake)
    return calls


def test_convert_stores_figures_as_the_owners_assets(monkeypatch):
    calls = _fake_pngs(monkeypatch)
    obj = generate("ratio_hard", 2)
    resp = client.post("/convert/freeform", json={"question": obj}, headers=ALICE)
    assert resp.status_code == 200
    out = resp.json()
    assert out["marks"] == obj["question"]["total_marks"] and out["dropped"] == []
    images = [b for b in out["content"] if b["type"] == "image"]
    assert len(images) == 1 and calls == [1]
    asset_id = images[0]["attrs"]["asset_id"]
    assert client.get(f"/assets/{asset_id}", headers=ALICE).status_code == 200
    assert client.get(f"/assets/{asset_id}", headers=BOB).status_code == 404
    # the converted block is a valid free-form question referencing a real asset
    block = {
        "type": "freeformQuestion",
        "attrs": {"block_id": "ff_api_1", "marks": out["marks"], "answer": out["answer"]},
        "content": out["content"],
    }
    assert validate_document(make_doc(block)) == []


def test_a_figure_that_cannot_be_drawn_is_named_and_the_rest_converts(monkeypatch):
    _fake_pngs(monkeypatch, fail={0})
    resp = client.post(
        "/convert/freeform", json={"question": generate("ratio_hard", 2)}, headers=ALICE
    )
    assert resp.status_code == 200
    out = resp.json()
    assert len(out["dropped"]) == 1 and "figure" in out["dropped"][0]
    assert not [b for b in out["content"] if b["type"] == "image"]
    assert out["content"]  # the text is still there


def test_text_only_question_needs_no_browser(monkeypatch):
    calls = _fake_pngs(monkeypatch)
    obj = generate("ratio_easy", 1)
    obj["question"]["parts"][0]["diagram"] = None
    out = client.post("/convert/freeform", json={"question": obj}, headers=ALICE).json()
    assert calls == [] and out["dropped"] == []


def test_raster_figures_are_stored_without_a_browser(monkeypatch):
    calls = _fake_pngs(monkeypatch)
    data = base64.b64encode(png(30, 20)).decode()
    obj = generate("ratio_easy", 1)
    obj["question"]["parts"][0]["diagram"] = {
        "type": "raster",
        "asset_ref": f"data:image/png;base64,{data}",
        "alt_text": "A scanned figure",
    }
    out = client.post("/convert/freeform", json={"question": obj}, headers=ALICE).json()
    assert calls == []  # decoded straight from the data URI
    images = [b for b in out["content"] if b["type"] == "image"]
    assert len(images) == 1 and out["dropped"] == []


def test_a_raster_that_is_not_an_embedded_image_is_dropped(monkeypatch):
    _fake_pngs(monkeypatch)
    obj = generate("ratio_easy", 1)
    obj["question"]["parts"][0]["diagram"] = {
        "type": "raster",
        "asset_ref": "scans/q1.png",
        "alt_text": "x",
    }
    out = client.post("/convert/freeform", json={"question": obj}, headers=ALICE).json()
    assert len(out["dropped"]) == 1 and not [b for b in out["content"] if b["type"] == "image"]


def test_invalid_question_is_422_and_auth_is_required(monkeypatch):
    assert client.post("/convert/freeform", json={"question": {}}, headers=ALICE).status_code == 422
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.post("/convert/freeform", json={"question": {}}).status_code == 401


def test_ui_hints_are_ignored(monkeypatch):
    _fake_pngs(monkeypatch)
    obj = generate("ratio_easy", 1)
    obj["available_ops"] = ["regenerate"]
    assert (
        client.post("/convert/freeform", json={"question": obj}, headers=ALICE).status_code == 200
    )


@requires_chromium
def test_real_chromium_rasterises_a_bar_model():
    obj = generate("ratio_medium", 3)
    out = client.post("/convert/freeform", json={"question": obj}, headers=ALICE).json()
    assert out["dropped"] == []
    asset_id = next(b for b in out["content"] if b["type"] == "image")["attrs"]["asset_id"]
    got = client.get(f"/assets/{asset_id}", headers=ALICE)
    assert got.headers["content-type"] == "image/png"
    assert got.content.startswith(b"\x89PNG") and len(got.content) > 1000
