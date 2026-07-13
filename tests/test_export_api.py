"""V5 thin API contract for POST /export/{preview|worksheet|answer-key}.

Logic (rendering, load gate, Chromium) lives elsewhere; this checks the wiring:
content-types, the 422 policy on tampered/empty sets, and that the PDF routes
emit a real ``%PDF`` attachment. The PDF cases need Chromium, so they are
guarded to skip cleanly when the browser is not installed locally; CI installs
it (``playwright install --with-deps chromium``) so they always run there."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _chromium_available() -> bool:
    """True when a headless Chromium can actually launch (skip PDF tests if not)."""
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


def _generate(blueprint_code: str, seed: int) -> dict:
    resp = client.post(
        "/generate", json={"blueprint_code": blueprint_code, "seed": seed, "count": 1}
    )
    assert resp.status_code == 200
    return resp.json()["questions"][0]


# --- Preview (no browser; always runs) -------------------------------------


def test_preview_returns_html_worksheet():
    q = _generate("ratio_medium", 42)
    resp = client.post("/export/preview", json={"title": "Ratio Practice", "questions": [q]})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    assert "sheet-title" in body
    assert "Ratio Practice" in body
    assert 'class="question"' in body


# --- 422 policy (no browser; always runs) ----------------------------------


def test_empty_questions_is_422():
    resp = client.post("/export/preview", json={"title": "Empty", "questions": []})
    assert resp.status_code == 422


def test_tampered_question_is_422_preview():
    resp = client.post(
        "/export/preview", json={"title": "Bad", "questions": [{"not": "canonical"}]}
    )
    assert resp.status_code == 422


def test_tampered_question_is_422_worksheet():
    resp = client.post(
        "/export/worksheet", json={"title": "Bad", "questions": [{"not": "canonical"}]}
    )
    assert resp.status_code == 422


def test_tampered_question_is_422_answer_key():
    resp = client.post(
        "/export/answer-key", json={"title": "Bad", "questions": [{"not": "canonical"}]}
    )
    assert resp.status_code == 422


# --- PDF smoke (Chromium required) -----------------------------------------


@requires_chromium
def test_worksheet_returns_pdf_attachment():
    q = _generate("ratio_medium", 42)
    resp = client.post("/export/worksheet", json={"title": "Ratio Practice", "questions": [q]})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('filename="ratio-practice.pdf"')
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


@requires_chromium
def test_answer_key_returns_pdf_attachment():
    q = _generate("ratio_medium", 42)
    resp = client.post("/export/answer-key", json={"title": "Ratio Practice", "questions": [q]})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('filename="ratio-practice-answers.pdf"')
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000
