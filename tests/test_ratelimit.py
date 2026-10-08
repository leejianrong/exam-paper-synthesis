"""W5 — /auth/* rate limiting: window, per-address keys, sign-in attempts, failure lockout."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from app import ratelimit
from app.main import app
from app.ratelimit import SlidingWindow
from fastapi.testclient import TestClient
from test_auth_api import GOOGLE_OK, make_client, sign_in


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(ratelimit.limiter, "_clock", lambda: now[0])
    return now


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH", raising=False)
    monkeypatch.delenv("EXAM_CLIENT_IP_HEADER", raising=False)
    monkeypatch.setenv("EXAM_PUBLIC_URL", "http://localhost:8000")
    monkeypatch.setenv("EXAM_WEB_URL", "http://localhost:5173")
    monkeypatch.setenv("EXAM_OAUTH_GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("EXAM_OAUTH_GOOGLE_CLIENT_SECRET", "secret")


# --- the window ----------------------------------------------------------------------------


def test_window_allows_up_to_the_limit_then_names_the_wait():
    now = [0.0]
    w = SlidingWindow(lambda: now[0])
    assert [w.hit("k", 3, 60) for _ in range(3)] == [0, 0, 0]
    now[0] = 10
    wait = w.hit("k", 3, 60)
    assert 49 <= wait <= 52  # the oldest event (t=0) ages out at t=60
    assert w.hit("other", 3, 60) == 0  # keys are independent
    now[0] = 61
    assert w.hit("k", 3, 60) == 0


def test_a_refused_hit_is_not_counted_and_zero_means_unlimited():
    now = [0.0]
    w = SlidingWindow(lambda: now[0])
    for _ in range(2):
        w.hit("k", 2, 60)
    for _ in range(50):
        assert w.hit("k", 2, 60) > 0  # hammering while refused does not extend the lockout
    now[0] = 61
    assert w.hit("k", 2, 60) == 0
    assert all(w.hit("free", 0, 60) == 0 for _ in range(100))


def test_memory_is_bounded(monkeypatch):
    monkeypatch.setattr(ratelimit, "_MAX_KEYS", 50)
    now = [0.0]
    w = SlidingWindow(lambda: now[0])
    for i in range(50):
        w.hit(f"k{i}", 1, 60)
    now[0] = 7200  # everything is stale
    w.hit("new", 1, 60)
    assert len(w._events) < 50


# --- the routes ----------------------------------------------------------------------------


def test_all_auth_routes_share_a_per_address_ceiling(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_LIMIT_PER_MINUTE", "5")
    client = TestClient(app)
    assert [client.get("/auth/providers").status_code for _ in range(5)] == [200] * 5
    resp = client.get("/auth/me")
    assert resp.status_code == 429 and int(resp.headers["retry-after"]) >= 1


def test_sign_in_attempts_are_limited_and_bounce_back_to_the_login_page(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_ATTEMPTS_PER_MINUTE", "3")
    client = TestClient(app, follow_redirects=False)
    for _ in range(3):
        assert "accounts.google.com" in client.get("/auth/google/login").headers["location"]
    resp = client.get("/auth/google/login")
    assert resp.status_code == 302 and int(resp.headers["retry-after"]) >= 1
    url = urlparse(resp.headers["location"])
    assert url.netloc == "localhost:5173" and parse_qs(url.fragment.split("?")[1])["error"] == [
        "rate_limited"
    ]
    assert 'exam_oauth_state=""' in resp.headers["set-cookie"]  # cleared, not issued


def test_repeated_failed_sign_ins_lock_the_address_out_until_the_window_passes(monkeypatch, clock):
    monkeypatch.setenv("EXAM_AUTH_FAILURES_PER_15_MIN", "3")
    client = make_client(GOOGLE_OK)
    for _ in range(3):  # a callback with no matching state cookie is a failed sign-in
        resp = client.get("/auth/google/callback", params={"code": "x", "state": "forged"})
        assert "error=state" in resp.headers["location"]
    locked = client.get("/auth/google/login")
    assert "error=rate_limited" in locked.headers["location"]
    assert 800 <= int(locked.headers["retry-after"]) <= 901
    blocked = client.get("/auth/google/callback", params={"code": "x", "state": "forged"})
    assert "error=rate_limited" in blocked.headers["location"]
    clock[0] += 901
    assert (
        sign_in(client, "google").headers["location"].endswith("/#/")
    )  # a real sign-in works again


def test_cancelling_at_the_provider_is_not_a_failure(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_FAILURES_PER_15_MIN", "2")
    client = TestClient(app, follow_redirects=False)
    for _ in range(5):
        assert (
            "error=denied"
            in client.get("/auth/google/callback", params={"error": "x"}).headers["location"]
        )


def test_successful_sign_ins_do_not_lock_anyone_out(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_FAILURES_PER_15_MIN", "2")
    client = make_client(GOOGLE_OK)
    for _ in range(4):
        assert sign_in(client, "google").headers["location"].endswith("/#/")


def test_addresses_are_independent_and_the_ip_header_only_counts_when_configured(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_LIMIT_PER_MINUTE", "2")
    client = TestClient(app)
    # unset: the header is attacker-controlled, so it must NOT buy a fresh allowance
    for n in range(2):
        assert (
            client.get("/auth/providers", headers={"Fly-Client-IP": f"9.9.9.{n}"}).status_code
            == 200
        )
    assert client.get("/auth/providers", headers={"Fly-Client-IP": "9.9.9.9"}).status_code == 429
    ratelimit.limiter.reset()
    monkeypatch.setenv("EXAM_CLIENT_IP_HEADER", "Fly-Client-IP")
    a, b = {"Fly-Client-IP": "1.1.1.1"}, {"Fly-Client-IP": "2.2.2.2"}
    assert [client.get("/auth/providers", headers=a).status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]
    assert client.get("/auth/providers", headers=b).status_code == 200


def test_zero_disables_a_limit(monkeypatch):
    monkeypatch.setenv("EXAM_AUTH_LIMIT_PER_MINUTE", "0")
    client = TestClient(app)
    assert all(client.get("/auth/providers").status_code == 200 for _ in range(40))
