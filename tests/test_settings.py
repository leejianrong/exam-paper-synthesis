"""O1 — account settings (EXA-125): the store contract (SQLite and, when configured, Postgres)
and the API. Settings are per owner, known keys only, defaults merged on read."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from app.main import app
from app.settings import DEFAULTS, SqliteSettingsStore, UnknownSetting, merged
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


ON = {**DEFAULTS, "classic_generator": True}


def test_update_is_per_owner_and_partial(store):
    assert store.update("alice", {"classic_generator": True}) == ON
    assert store.get("alice") == ON
    assert store.get("bob") == DEFAULTS
    assert store.update("alice", {}) == ON  # nothing to change
    assert store.update("alice", {"classic_generator": False})["classic_generator"] is False


def test_unknown_keys_and_wrong_types_are_refused_and_change_nothing(store):
    store.update("alice", {"classic_generator": True})
    bad_values = (
        {"theme": "dark"},
        {"classic_generator": "yes"},
        {"classic_generator": 1},
        {"answer_key_style": "fancy"},
        {"answer_key_style": True},
    )
    for bad in bad_values:
        with pytest.raises(UnknownSetting):
            store.update("alice", bad)
    assert store.get("alice") == ON


def test_erase_owner_removes_only_that_owner(store):
    store.update("alice", {"classic_generator": True})
    store.update("bob", {"classic_generator": True})
    store.erase_owner("alice")
    assert store.get("alice") == DEFAULTS
    assert store.get("bob") == ON


def test_sqlite_settings_persist_across_instances(tmp_path):
    SqliteSettingsStore(tmp_path / "s.sqlite3").update("alice", {"classic_generator": True})
    assert SqliteSettingsStore(tmp_path / "s.sqlite3").get("alice")["classic_generator"] is True


# --- API ---------------------------------------------------------------------------------


def test_settings_need_auth(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/settings").status_code == 401
    assert client.put("/settings", json={"classic_generator": True}).status_code == 401


def test_get_and_put_settings():
    assert client.get("/settings", headers=ALICE).json() == DEFAULTS
    resp = client.put("/settings", json={"classic_generator": True}, headers=ALICE)
    assert resp.status_code == 200 and resp.json() == ON
    assert client.get("/settings", headers=ALICE).json() == ON
    assert client.get("/settings", headers=BOB).json() == DEFAULTS


@pytest.mark.parametrize(
    "body", [{"nope": True}, {"classic_generator": "on"}, {"answer_key_style": "fancy"}]
)
def test_bad_settings_are_a_422_with_a_reason(body):
    resp = client.put("/settings", json=body, headers=ALICE)
    assert resp.status_code == 422
    assert next(iter(body)) in resp.text


def test_stored_values_that_are_no_longer_allowed_fall_back_to_the_default():
    assert merged({"answer_key_style": "fancy", "gone": 1}) == DEFAULTS


# --- answer key style (EXA-159) ------------------------------------------------------------


def _key_options(record: dict) -> dict:
    return record["document"]["settings"]["key_options"]


def test_new_papers_take_the_accounts_answer_key_style():
    assert DEFAULTS["answer_key_style"] == "school"
    blank = client.post("/documents", json={"title": "Blank"}, headers=ALICE).json()
    assert _key_options(blank)["layout"] == "compact"
    assert _key_options(blank)["show_scheme"] is False

    assert (
        client.put("/settings", json={"answer_key_style": "worked"}, headers=ALICE).json()[
            "answer_key_style"
        ]
        == "worked"
    )
    for req in (
        client.post("/documents", json={"title": "Blank"}, headers=ALICE),
        client.post("/documents", json={"template": "p2"}, headers=ALICE),
        client.post(
            "/documents/generate",
            json={"template": "p1_booklet_b", "level": "P6", "seed": 3},
            headers=ALICE,
        ),
    ):
        assert req.status_code == 201, req.text
        assert _key_options(req.json()) == {
            "layout": "full",
            "show_question": True,
            "show_scheme": True,
        }
    # Bob kept the default; Alice's saved papers keep the key they were made with
    generated = client.post(
        "/documents/generate", json={"template": "p2", "level": "P6", "seed": 3}, headers=BOB
    ).json()
    assert _key_options(generated)["layout"] == "compact"
    assert (
        _key_options(client.get(f"/documents/{blank['id']}", headers=ALICE).json())["layout"]
        == "compact"
    )


def test_account_export_includes_settings_and_delete_erases_them():
    client.put("/settings", json={"classic_generator": True}, headers=ALICE)
    zf = zipfile.ZipFile(io.BytesIO(client.get("/account/export", headers=ALICE).content))
    assert json.loads(zf.read("settings.json")) == ON
    assert (
        client.request("DELETE", "/account", json={"confirm": "DELETE"}, headers=ALICE).status_code
        == 204
    )
    assert client.get("/settings", headers=ALICE).json() == DEFAULTS
