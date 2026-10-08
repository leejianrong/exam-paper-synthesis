"""W5 — Content-Security-Policy: scripts only from self or by hash, and the hashes are exactly
the inline scripts the print HTML carries (the preview iframe inherits the policy)."""

from __future__ import annotations

import base64
import hashlib
import re

import pytest
from app.csp import content_security_policy
from app.main import app
from documents import gen_block, make_doc
from exam_engine import generate
from exam_engine.render import (
    inline_script_hashes,
    render_answer_key_html,
    render_document_html,
    render_worksheet_html,
)
from fastapi.testclient import TestClient

INLINE_SCRIPT = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.S)


def sources(directive: str) -> list[str]:
    for part in content_security_policy().split("; "):
        name, _, rest = part.partition(" ")
        if name == directive:
            return rest.split()
    raise AssertionError(f"no {directive}")


def sha(js: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(js.encode()).digest()).decode() + "'"


def test_scripts_are_never_unsafe():
    script = sources("script-src")
    assert "'self'" in script
    assert "'unsafe-inline'" not in script and "'unsafe-eval'" not in script
    assert not any(s in ("*", "data:", "blob:", "https:") for s in script)
    assert sources("object-src") == ["'none'"] and sources("base-uri") == ["'none'"]
    assert sources("frame-ancestors") == ["'self'"]


@pytest.mark.parametrize("kind", ["worksheet", "answer-key", "document"])
def test_every_inline_script_in_the_print_html_is_allowed_by_hash(kind):
    q = generate("ratio_medium", 3)
    html = {
        "worksheet": lambda: render_worksheet_html("T", [q]),
        "answer-key": lambda: render_answer_key_html("T", [q]),
        "document": lambda: render_document_html("T", make_doc(gen_block()), mode="full"),
    }[kind]()
    scripts = INLINE_SCRIPT.findall(html)
    assert len(scripts) == 3  # katex, auto-render, bootstrap — nothing else runs inline
    allowed = set(sources("script-src"))
    assert {sha(js) for js in scripts} <= allowed
    assert set(inline_script_hashes()) <= allowed


def test_the_policy_is_sent_on_api_responses():
    resp = TestClient(app).get("/health")
    assert resp.headers["content-security-policy"] == content_security_policy()


def test_swagger_docs_are_exempt_in_development(monkeypatch):
    # /docs loads Swagger UI from a CDN with an inline script; it only exists outside production.
    assert "content-security-policy" not in TestClient(app).get("/docs").headers
