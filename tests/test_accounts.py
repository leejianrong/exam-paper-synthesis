"""W3 — account-store contract (ADR-0022). Parametrised so the Postgres store (W3b) must pass
the identical suite: identity lookup, link-by-verified-email only, sessions."""

from __future__ import annotations

from datetime import timedelta

import pytest
from app import accounts as accounts_mod
from app.accounts import Profile, SqliteAccountStore, hash_token


@pytest.fixture(params=["sqlite"])
def store(request, tmp_path):
    if request.param == "sqlite":
        return SqliteAccountStore(tmp_path / "accounts.sqlite3")
    raise AssertionError(request.param)  # pragma: no cover


def P(provider="google", subject="g-1", email="ann@example.com", verified=True, name="Ann"):
    return Profile(provider, subject, email, verified, name)


def test_first_login_creates_a_user_and_the_same_identity_returns_it(store):
    a = store.login(P())
    assert a["email"] == "ann@example.com" and a["email_verified"] and a["name"] == "Ann"
    assert store.login(P(name="Ann Renamed"))["id"] == a["id"]
    assert store.get_user(a["id"]) == a
    assert store.get_user("nope") is None


def test_different_subjects_are_different_users(store):
    assert (
        store.login(P(subject="g-1"))["id"] != store.login(P(subject="g-2", email="b@x.com"))["id"]
    )


def test_second_provider_links_only_through_a_verified_email_on_both_sides(store):
    google = store.login(P("google", "g-1", "Ann@Example.com", True))
    github = store.login(P("github", "42", "ann@example.com", True))
    assert github["id"] == google["id"]  # case-insensitive, both verified
    # …and signing in again through either gives the same account
    assert store.login(P("github", "42", None, False))["id"] == google["id"]


def test_an_unverified_email_never_links_or_claims(store):
    google = store.login(P("google", "g-1", "ann@example.com", True))
    ms = store.login(P("microsoft", "m-1", "ann@example.com", False))
    assert ms["id"] != google["id"] and ms["email_verified"] is False
    # an unverified account does not become linkable by someone else's verified login either
    other = store.login(P("github", "7", "ann@example.com", True))
    assert other["id"] == google["id"]
    assert other["id"] != ms["id"]


def test_unverified_email_cannot_pre_claim_an_address(store):
    squatter = store.login(P("github", "9", "victim@example.com", False))
    victim = store.login(P("google", "g-9", "victim@example.com", True))
    assert victim["id"] != squatter["id"]


def test_email_becomes_verified_when_a_later_login_proves_it(store):
    first = store.login(P("github", "5", "z@example.com", False))
    assert first["email_verified"] is False
    again = store.login(P("github", "5", "z@example.com", True))
    assert again["id"] == first["id"] and again["email_verified"] is True


def test_user_without_email(store):
    u = store.login(P("github", "11", None, False, None))
    assert u["email"] is None and u["email_verified"] is False


def test_sessions_resolve_expire_and_end(store, monkeypatch):
    user = store.login(P())
    token = store.create_session(user["id"])
    assert store.user_for_session(token)["id"] == user["id"]
    assert store.user_for_session("not-a-token") is None
    assert store.create_session(user["id"]) != token

    store.delete_session(token)
    assert store.user_for_session(token) is None

    live = store.create_session(user["id"])
    real_now = accounts_mod._now
    monkeypatch.setattr(
        accounts_mod, "_now", lambda: real_now() + accounts_mod.SESSION_TTL + timedelta(seconds=1)
    )
    assert store.user_for_session(live) is None


def test_tokens_are_stored_hashed(store, tmp_path):
    import sqlite3

    user = store.login(P())
    token = store.create_session(user["id"])
    rows = (
        sqlite3.connect(tmp_path / "accounts.sqlite3")
        .execute("SELECT token_hash FROM sessions")
        .fetchall()
    )
    assert rows == [(hash_token(token),)] and token not in rows[0][0]
