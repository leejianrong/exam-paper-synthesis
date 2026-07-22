"""V7 A1 — the sourced-object interchange proof (KAN-153).

A hand-authored PAST-PAPER question that the engine did NOT generate must be
*interchange-grade*: it validates against the SAME v1.4.0 schema as generated
questions, joins a worksheet next to them, and renders (raster figure included)
in the preview / PDF path. This test IS the proof (project verification policy);
it is not a golden regression anchor.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exam_engine import canonical, generate
from exam_engine.canonical import CanonicalValidationError
from exam_engine.render import render_answer_key_html, render_worksheet_html

FIXTURE = Path(__file__).parent / "fixtures" / "sourced" / "psle_2023_ratio.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# --- the sourced object validates on the same gate as generated ones ---------


def test_sourced_fixture_loads_against_canonical_schema():
    obj = _load_fixture()
    loaded = canonical.load(obj)  # raises CanonicalValidationError if invalid
    assert loaded["source_type"] == "sourced"
    assert loaded["blueprint_code"] is None
    assert loaded["parameters"] is None
    assert loaded["seed"] is None
    assert loaded["provenance"]["created_by"] == "ingested"
    # It carries a raster diagram (the interchange figure format).
    assert obj["question"]["parts"][0]["diagram"]["type"] == "raster"


# --- negative controls: assert the ACTUAL schema contract --------------------
# The top-level `allOf` for `source_type: "sourced"` requires BOTH `source` and
# `license`. It does NOT forbid a stray `blueprint_code`/`seed`/`parameters` on a
# sourced object (there is no such constraint in the schema) — so we assert only
# what the contract truly enforces, and document the gap it does not close.


def test_sourced_without_source_is_rejected():
    obj = _load_fixture()
    del obj["source"]
    with pytest.raises(CanonicalValidationError) as excinfo:
        canonical.load(obj)
    assert "source" in str(excinfo.value)


def test_sourced_without_license_is_rejected():
    obj = _load_fixture()
    del obj["license"]
    with pytest.raises(CanonicalValidationError) as excinfo:
        canonical.load(obj)
    assert "license" in str(excinfo.value)


def test_schema_does_not_forbid_stray_blueprint_code_on_sourced():
    # Documenting reality (not endorsing it): the schema requires source+license
    # for sourced questions but has no rule forbidding a non-null blueprint_code,
    # so this still validates. If that ever becomes undesirable it needs a new
    # schema rule + its own test — this asserts the contract as it stands today.
    obj = _load_fixture()
    obj["blueprint_code"] = "ratio_medium"
    canonical.load(obj)  # does not raise


# --- mixed worksheet: generated + sourced render side by side ----------------


def test_mixed_worksheet_renders_generated_and_sourced():
    generated = generate("ratio_medium", 42)
    sourced = canonical.load(_load_fixture())
    questions = [generated, sourced]

    html = render_worksheet_html("Mixed", questions)

    # Both questions are present, in order.
    assert html.count('<li class="question">') == 2
    # The sourced stem appears.
    assert "shared some stickers in the ratio" in html
    # The generated question's text appears too.
    assert generated["question"]["parts"][0]["text"][:20] in html
    # The raster figure renders as an <img> wrapped in the diagram figure.
    assert '<figure class="diagram"><img src="data:image/png;base64,' in html
    assert 'alt="Bar model:' in html


def test_mixed_answer_key_shows_sourced_answers_and_marks():
    generated = generate("ratio_medium", 42)
    sourced = canonical.load(_load_fixture())
    ak = render_answer_key_html("Mixed", [generated, sourced])

    # Part (a): integer total 96. Part (b): the fraction 3/8.
    assert r"Answer: \(96\)" in ak
    assert r"\frac{3}{8}" in ak
    # The hand-authored M/A/B marking scheme is present.
    assert '<span class="mark-type mark-M">M1</span>' in ak
    assert '<span class="mark-type mark-A">A1</span>' in ak
    assert '<span class="mark-type mark-B">B1</span>' in ak
    # The raster figure also renders in the answer key.
    assert '<figure class="diagram"><img src="data:image/png;base64,' in ak


# --- PDF smoke (Chromium required; skips cleanly when absent) ----------------
# Mirrors the guard in tests/test_export_api.py so this adds no hard dependency.


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


requires_chromium = pytest.mark.skipif(
    not _chromium_available(),
    reason="headless Chromium not installed (run: playwright install chromium)",
)


@requires_chromium
def test_mixed_worksheet_exports_pdf():
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    generated = _load_via_api("ratio_medium", 42, client)
    sourced = _load_fixture()
    resp = client.post(
        "/export/worksheet", json={"title": "Mixed", "questions": [generated, sourced]}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


def _load_via_api(blueprint_code: str, seed: int, client: object) -> dict:
    resp = client.post(  # type: ignore[attr-defined]
        "/generate", json={"blueprint_code": blueprint_code, "seed": seed, "count": 1}
    )
    assert resp.status_code == 200
    return resp.json()["questions"][0]
