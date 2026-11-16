"""EXA-152: the editor shows each question's [n] by its section's placement, as the paper prints.

The engine is the authority. This test computes every question's effective placement for a
table of documents the way ``render._render_document_body`` does (the paper's placement until
the first section, then each section's ``paper_outline`` placement) and checks the result into
``web/src/lib/editor/placements.fixture.json``; the web unit test ``placements.test.ts`` asserts
the editor's ``blockPlacements`` gives the same answer for each document. Regenerate with
``EXAM_WRITE_FIXTURES=1 uv run pytest tests/test_editor_placement_fixture.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from exam_engine.document import QUESTION_TYPES, paper_outline, paper_placement

FIXTURE = Path(__file__).resolve().parents[1] / "web/src/lib/editor/placements.fixture.json"


def _q(marks: int = 2) -> dict:
    return {"type": "freeformQuestion", "attrs": {"marks": marks}, "content": []}


def _sec(mode: str | None = None, placement: str | None = None) -> dict:
    return {
        "type": "section",
        "attrs": {"title": "S", "mode": mode, "marks_placement": placement},
    }


def _para() -> dict:
    return {"type": "paragraph"}


def _doc(name: str, blocks: list[dict], placement: str | None = None) -> dict:
    settings = {} if placement is None else {"marks_placement": placement}
    return {"name": name, "settings": settings, "content": {"type": "doc", "content": blocks}}


CASES = [
    _doc("no sections, paper default", [_q(), _para(), _q()]),
    _doc("no sections, paper question", [_q(), _q()], "question"),
    _doc("before the first section uses the paper", [_q(), _sec("mcq"), _q()], "both"),
    _doc(
        "mode defaults: mcq and short none, structured and no mode the paper",
        [_sec("mcq"), _q(1), _sec("short"), _q(2), _sec("structured"), _q(4), _sec(None), _q(3)],
        "question",
    ),
    _doc(
        "an explicit choice wins over the mode",
        [_sec("mcq", "both"), _q(1), _sec("structured", "none"), _q(4), _sec("short", "answer")],
        "question",
    ),
    _doc("an unknown choice falls back to the mode", [_sec("structured", "margin"), _q()], "both"),
    _doc("an unknown paper setting is answer", [_q(), _sec(None), _q()], "nowhere"),
    _doc(
        "a real paper: Booklet A, Booklet B, Paper 2",
        [
            _sec("mcq"),
            _q(1),
            _q(1),
            _sec("mcq"),
            _q(2),
            _sec("short"),
            _q(2),
            _para(),
            _sec("structured"),
            _q(3),
            _q(5),
        ],
        "answer",
    ),
]


def _expected(case: dict) -> list[str]:
    """Each question's placement, in order: the engine's render loop, step for step."""
    placement = paper_placement(case)
    outline = iter(paper_outline(case))
    out = []
    for node in case["content"]["content"]:
        if node["type"] == "section":
            placement = next(outline)["marks_placement"]
        elif node["type"] in QUESTION_TYPES:
            out.append(placement)
    return out


def _fixture() -> str:
    rows = [{**case, "expected": _expected(case)} for case in CASES]
    return json.dumps(rows, indent=2) + "\n"


def test_editor_placement_fixture_matches_the_engine():
    text = _fixture()
    if os.environ.get("EXAM_WRITE_FIXTURES") == "1":
        FIXTURE.write_text(text, encoding="utf-8")
    assert FIXTURE.read_text(encoding="utf-8") == text, (
        "placements.fixture.json is stale: regenerate it (see this module's docstring)"
    )


def test_fixture_covers_every_placement():
    seen = {p for case in CASES for p in _expected(case)}
    assert seen == {"none", "question", "answer", "both"}
