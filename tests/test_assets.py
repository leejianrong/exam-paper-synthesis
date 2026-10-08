"""W2b — asset store contract + upload gate + /assets API (ADR-0022).

The store tests are parametrised over implementations so W3/W4's object-storage store must
pass the identical suite, including tenant isolation.
"""

from __future__ import annotations

import pytest
from app import assets as assets_mod
from app.assets import AssetNotFound, InvalidImage, SqliteAssetStore, sniff_image
from app.main import app
from fastapi.testclient import TestClient
from images import jpeg, png

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(autouse=True)
def _dev_env(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")


@pytest.fixture(params=["sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteAssetStore(tmp_path / "contract.sqlite3")
    if request.param == "postgres":
        from app.pgstores import PgAssetStore

        return PgAssetStore(request.getfixturevalue("pg_db"))
    raise AssertionError(request.param)  # pragma: no cover


# --- store contract ------------------------------------------------------------------


def test_put_get_delete_roundtrip(store):
    data = png()
    meta = store.put("alice", data, "image/png", "fig.png", (2, 3))
    assert meta["bytes"] == len(data) and meta["mime"] == "image/png"
    got = store.get("alice", meta["id"])
    assert got["data"] == data and got["filename"] == "fig.png"
    assert (got["width"], got["height"]) == (2, 3)
    store.delete("alice", meta["id"])
    with pytest.raises(AssetNotFound):
        store.get("alice", meta["id"])
    with pytest.raises(AssetNotFound):
        store.delete("alice", meta["id"])


def test_owner_isolation(store):
    meta = store.put("alice", png(), "image/png", "a.png", (2, 3))
    with pytest.raises(AssetNotFound):
        store.get("bob", meta["id"])
    with pytest.raises(AssetNotFound):
        store.delete("bob", meta["id"])
    assert store.owned("bob", [meta["id"]]) == set()
    assert store.owned("alice", [meta["id"], "nope"]) == {meta["id"]}
    assert store.get("alice", meta["id"])["data"]  # bob's failed delete changed nothing


def test_usage_sums_per_owner(store):
    a = png(2, 3)
    b = png(5, 5)
    store.put("alice", a, "image/png", "a", (2, 3))
    store.put("alice", b, "image/png", "b", (5, 5))
    store.put("bob", a, "image/png", "c", (2, 3))
    assert store.usage("alice") == len(a) + len(b)
    assert store.usage("bob") == len(a)
    assert store.usage("nobody") == 0
    assert store.owned("alice", []) == set()


# --- upload gate (magic bytes) ---------------------------------------------------------


def test_sniff_accepts_png_and_jpeg_and_reads_size():
    assert sniff_image(png(7, 9)).width == 7
    info = sniff_image(jpeg(11, 13))
    assert (info.mime, info.width, info.height) == ("image/jpeg", 11, 13)
    assert sniff_image(png(7, 9)).mime == "image/png"


@pytest.mark.parametrize(
    "data",
    [
        b"GIF89a\x01\x00\x01\x00\x00\x00\x00;",
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b"<html><script>alert(1)</script></html>",
        b"",
        b"\x89PNG\r\n\x1a\n",  # signature only
        png()[:-20],  # truncated PNG
        jpeg()[:-2],  # truncated JPEG (no EOI)
        b"\xff\xd8\xff\xd9",  # JPEG with no frame header
        png(4097, 1),  # too wide (header-only check)
        png(1, 4097),
        b"%PDF-1.7 ...",
    ],
)
def test_sniff_rejects(data):
    with pytest.raises(InvalidImage):
        sniff_image(data)


def test_sniff_rejects_oversize():
    big = png()[:-12] + b"\x00" * assets_mod.MAX_ASSET_BYTES + png()[-12:]
    with pytest.raises(InvalidImage):
        sniff_image(big)


# --- API ----------------------------------------------------------------------------------


def _upload(data: bytes, headers=ALICE, name: str | None = "fig.png"):
    h = dict(headers)
    if name:
        h["X-Filename"] = name
    return client.post("/assets", content=data, headers={**h, "Content-Type": "image/png"})


def test_upload_then_fetch_with_fixed_type_and_nosniff():
    data = png(6, 4)
    resp = _upload(data)
    assert resp.status_code == 201
    meta = resp.json()
    assert (meta["mime"], meta["width"], meta["height"], meta["bytes"]) == (
        "image/png",
        6,
        4,
        len(data),
    )
    got = client.get(f"/assets/{meta['id']}", headers=ALICE)
    assert got.status_code == 200 and got.content == data
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in got.headers["cache-control"]


def test_jpeg_served_as_jpeg_whatever_the_client_said():
    meta = client.post(
        "/assets", content=jpeg(), headers={**ALICE, "Content-Type": "image/png"}
    ).json()
    assert meta["mime"] == "image/jpeg"
    got = client.get(f"/assets/{meta['id']}", headers=ALICE)
    assert got.headers["content-type"] == "image/jpeg"


@pytest.mark.parametrize(
    "data",
    [b"<html><script>alert(1)</script></html>", b"GIF89a....", b"<svg></svg>", png()[:-5]],
)
def test_renamed_non_images_are_refused(data):
    resp = _upload(data, name="x.png")
    assert resp.status_code == 422
    assert client.get("/assets/anything", headers=ALICE).status_code == 404


def test_foreign_asset_is_404():
    meta = _upload(png()).json()
    assert client.get(f"/assets/{meta['id']}", headers=BOB).status_code == 404
    assert client.get(f"/assets/{meta['id']}", headers=ALICE).status_code == 200


def test_oversize_upload_is_413(monkeypatch):
    monkeypatch.setattr(assets_mod, "MAX_ASSET_BYTES", 100)
    monkeypatch.setattr("app.routes_assets.MAX_ASSET_BYTES", 100)
    assert _upload(png(40, 40)).status_code == 413


def test_owner_quota_is_enforced(monkeypatch):
    size = len(png())
    monkeypatch.setattr("app.routes_assets.MAX_OWNER_BYTES", size * 2)
    assert _upload(png()).status_code == 201
    assert _upload(png()).status_code == 201
    over = _upload(png())
    assert over.status_code == 413 and "storage" in over.json()["detail"]
    assert _upload(png(), headers=BOB).status_code == 201  # quotas are per owner


def test_requires_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.post("/assets", content=png()).status_code == 401
    assert client.get("/assets/x").status_code == 401


def test_filename_is_sanitised():
    meta = _upload(png(), name="../../etc/<b>pass wd.png").json()
    from app.assets import get_asset_store

    stored = get_asset_store().get("alice", meta["id"])
    assert "/" not in stored["filename"] and "<" not in stored["filename"]
