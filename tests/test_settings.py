"""O1 — account settings (EXA-125): the store contract (SQLite and, when configured, Postgres)
and the API. Settings are per owner, known keys only, defaults merged on read."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from app.main import app
from app.settings import DEFAULTS, SqliteSettingsStore, UnknownSetting
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(params=["sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteSettingsStore(tmp_path / "docs.sqlite3")
    from app.pgstores import PgSettingsStore

    return PgSettingsStore(request.getfixturevalue("pg_db"))


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))


# --- store contract ----------------------------------------------------------------------


def test_defaults_until_something_is_stored(store):
    assert store.get("alice") == DEFAULTS
    assert DEFAULTS["classic_generator"] is False  # the Classic generator starts hidden


def test_update_is_per_owner_and_partial(store):
    assert store.update("alice", {"classic_generator": True}) == {"classic_generator": True}
    assert store.get("alice") == {"classic_generator": True}
    assert store.get("bob") == DEFAULTS
    assert store.update("alice", {}) == {"classic_generator": True}  # nothing to change
    assert store.update("alice", {"classic_generator": False})["classic_generator"] is False


def test_unknown_keys_and_wrong_types_are_refused_and_change_nothing(store):
    store.update("alice", {"classic_generator": True})
    for bad in ({"theme": "dark"}, {"classic_generator": "yes"}, {"classic_generator": 1}):
        with pytest.raises(UnknownSetting):
            store.update("alice", bad)
    assert store.get("alice") == {"classic_generator": True}


def test_erase_owner_removes_only_that_owner(store):
    store.update("alice", {"classic_generator": True})
    store.update("bob", {"classic_generator": True})
    store.erase_owner("alice")
    assert store.get("alice") == DEFAULTS
    assert store.get("bob") == {"classic_generator": True}


def test_sqlite_settings_persist_across_instances(tmp_path):
    SqliteSettingsStore(tmp_path / "s.sqlite3").update("alice", {"classic_generator": True})
    assert SqliteSettingsStore(tmp_path / "s.sqlite3").get("alice")["classic_generator"] is True


# --- API ---------------------------------------------------------------------------------


def test_settings_need_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/settings").status_code == 401
    assert client.put("/settings", json={"classic_generator": True}).status_code == 401


def test_get_and_put_settings():
    assert client.get("/settings", headers=ALICE).json() == {"classic_generator": False}
    resp = client.put("/settings", json={"classic_generator": True}, headers=ALICE)
    assert resp.status_code == 200 and resp.json() == {"classic_generator": True}
    assert client.get("/settings", headers=ALICE).json() == {"classic_generator": True}
    assert client.get("/settings", headers=BOB).json() == {"classic_generator": False}


@pytest.mark.parametrize("body", [{"nope": True}, {"classic_generator": "on"}])
def test_bad_settings_are_a_422_with_a_reason(body):
    resp = client.put("/settings", json=body, headers=ALICE)
    assert resp.status_code == 422
    assert ("nope" in resp.text) if "nope" in body else ("classic_generator" in resp.text)


def test_account_export_includes_settings_and_delete_erases_them():
    client.put("/settings", json={"classic_generator": True}, headers=ALICE)
    zf = zipfile.ZipFile(io.BytesIO(client.get("/account/export", headers=ALICE).content))
    assert json.loads(zf.read("settings.json")) == {"classic_generator": True}
    assert (
        client.request("DELETE", "/account", json={"confirm": "DELETE"}, headers=ALICE).status_code
        == 204
    )
    assert client.get("/settings", headers=ALICE).json() == {"classic_generator": False}
