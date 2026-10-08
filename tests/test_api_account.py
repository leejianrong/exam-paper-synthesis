"""W5 — account data export and deletion (the privacy-policy promises), on every backend."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from app.bankstore import open_owner_bank
from app.main import app
from app.routes_auth import get_http_client
from fastapi.testclient import TestClient
from images import png
from test_auth_api import GOOGLE_OK, provider_transport

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}
SOURCED = Path(__file__).parent / "fixtures" / "sourced"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))


def _seed(headers: dict, owner: str) -> str:
    """One document, one image and one bank question for ``owner``; returns the document id."""
    doc = client.post("/documents", json={"title": f"{owner}'s paper"}, headers=headers).json()
    img = client.post("/assets", content=png(), headers={**headers, "X-Filename": "fig.png"})
    assert img.status_code == 201
    bank = open_owner_bank(owner)
    bank.add(json.loads((SOURCED / "psle_2023_mcq.json").read_text(encoding="utf-8")))
    bank.close()
    return doc["id"]


def _zip(resp: httpx.Response) -> zipfile.ZipFile:
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(resp.content))


def test_account_routes_require_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/account/export").status_code == 401
    assert client.request("DELETE", "/account", json={"confirm": "DELETE"}).status_code == 401


def test_export_is_a_zip_of_json_and_images_for_the_caller_only():
    doc_id = _seed(ALICE, "alice")
    _seed(BOB, "bob")
    zf = _zip(client.get("/account/export", headers=ALICE))
    names = zf.namelist()
    assert "account.json" in names and f"documents/{doc_id}.json" in names
    assert len([n for n in names if n.startswith("bank/")]) == 1
    meta = json.loads(zf.read("account.json"))
    assert meta["id"] == "alice"
    assert meta["counts"] == {"documents": 1, "bank_questions": 1, "images": 1}
    doc = json.loads(zf.read(f"documents/{doc_id}.json"))
    assert doc["document"]["title"] == "alice's paper"
    (entry,) = json.loads(zf.read("assets/index.json"))
    assert entry["filename"] == "fig.png" and "data" not in entry
    assert zf.read(f"assets/{entry['file']}") == png()  # original bytes, byte for byte
    assert all(
        "bob" not in zf.read(n).decode("utf-8", "ignore") for n in names if n.endswith(".json")
    )


def test_export_of_an_empty_account_is_still_a_valid_zip():
    zf = _zip(client.get("/account/export", headers=ALICE))
    assert json.loads(zf.read("account.json"))["counts"] == {
        "documents": 0,
        "bank_questions": 0,
        "images": 0,
    }


@pytest.mark.parametrize("body", [{}, {"confirm": ""}, {"confirm": "delete"}, {"confirm": "yes"}])
def test_delete_needs_the_exact_confirmation_and_changes_nothing(body):
    _seed(ALICE, "alice")
    resp = client.request("DELETE", "/account", json=body, headers=ALICE)
    assert resp.status_code == 422
    assert len(client.get("/documents", headers=ALICE).json()["documents"]) == 1


def test_delete_erases_everything_of_the_caller_and_nothing_of_anyone_else():
    _seed(ALICE, "alice")
    bob_doc = _seed(BOB, "bob")
    resp = client.request("DELETE", "/account", json={"confirm": "DELETE"}, headers=ALICE)
    assert resp.status_code == 204
    assert client.get("/documents", headers=ALICE).json()["documents"] == []
    assert client.get("/bank", headers=ALICE).json()["items"] == []
    assert _zip(client.get("/account/export", headers=ALICE)).read("assets/index.json") == b"[]"
    assert client.get(f"/documents/{bob_doc}", headers=BOB).status_code == 200
    assert len(client.get("/bank", headers=BOB).json()["items"]) == 1
    assert (
        len(json.loads(_zip(client.get("/account/export", headers=BOB)).read("assets/index.json")))
        == 1
    )


def test_a_signed_in_user_is_deleted_signed_out_and_can_start_over(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    monkeypatch.setenv("EXAM_PUBLIC_URL", "http://localhost:8000")
    monkeypatch.setenv("EXAM_WEB_URL", "http://localhost:5173")
    monkeypatch.setenv("EXAM_OAUTH_GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("EXAM_OAUTH_GOOGLE_CLIENT_SECRET", "secret")

    def override():
        with httpx.Client(transport=provider_transport(GOOGLE_OK)) as c:
            yield c

    app.dependency_overrides[get_http_client] = override
    try:
        c = TestClient(app, follow_redirects=False)

        def sign_in() -> None:
            from urllib.parse import parse_qs, urlparse

            start = c.get("/auth/google/login")
            state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
            assert (
                c.get("/auth/google/callback", params={"code": "x", "state": state}).status_code
                == 302
            )

        sign_in()
        me = c.get("/auth/me").json()
        assert c.post("/documents", json={"title": "Mine"}).status_code == 201
        exported = _zip(c.get("/account/export"))
        meta = json.loads(exported.read("account.json"))
        assert meta["email"] == "ann@example.com" and meta["id"] == me["id"]

        resp = c.request("DELETE", "/account", json={"confirm": "DELETE"})
        assert resp.status_code == 204
        assert (
            "exam_session=" in resp.headers["set-cookie"]
            and "Max-Age=0" in resp.headers["set-cookie"]
        )
        c.cookies.clear()
        assert c.get("/auth/me").status_code == 401

        sign_in()  # the same Google identity now starts a fresh, empty account
        again = c.get("/auth/me").json()
        assert again["id"] != me["id"]
        assert c.get("/documents").json()["documents"] == []
    finally:
        app.dependency_overrides.clear()
