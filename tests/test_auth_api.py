"""W3 — the OAuth flow end to end against faked providers, plus session-backed ownership."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.main import app
from app.routes_auth import get_http_client
from fastapi.testclient import TestClient

WEB = "http://localhost:5173"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH", raising=False)
    monkeypatch.setenv("EXAM_PUBLIC_URL", "http://localhost:8000")
    monkeypatch.setenv("EXAM_WEB_URL", WEB)
    for p in ("GOOGLE", "MICROSOFT", "GITHUB"):
        monkeypatch.setenv(f"EXAM_OAUTH_{p}_CLIENT_ID", f"id-{p.lower()}")
        monkeypatch.setenv(f"EXAM_OAUTH_{p}_CLIENT_SECRET", f"secret-{p.lower()}")


def provider_transport(responses: dict[str, tuple[int, object]], seen: list | None = None):
    """A fake of every provider endpoint: path substring -> (status, json)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for key, (status, body) in responses.items():
            if key in str(request.url):
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


GOOGLE_OK = {
    "oauth2.googleapis.com/token": (200, {"access_token": "tok"}),
    "openidconnect.googleapis.com": (
        200,
        {"sub": "g-100", "email": "ann@example.com", "email_verified": True, "name": "Ann"},
    ),
}
GITHUB_OK = {
    "github.com/login/oauth/access_token": (200, {"access_token": "tok"}),
    "api.github.com/user/emails": (
        200,
        [
            {"email": "other@example.com", "primary": False, "verified": True},
            {"email": "ann@example.com", "primary": True, "verified": True},
        ],
    ),
    "api.github.com/user": (200, {"id": 4242, "login": "ann-gh", "name": None}),
}
MICROSOFT_OK = {
    "login.microsoftonline.com": (200, {"access_token": "tok"}),
    "graph.microsoft.com": (200, {"sub": "m-1", "email": "ann@example.com", "name": "Ann M"}),
}


def make_client(responses, seen=None) -> TestClient:
    def override():
        with httpx.Client(transport=provider_transport(responses, seen)) as c:
            yield c

    app.dependency_overrides[get_http_client] = override
    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def sign_in(client: TestClient, provider: str) -> httpx.Response:
    start = client.get(f"/auth/{provider}/login")
    assert start.status_code == 302
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    return client.get(f"/auth/{provider}/callback", params={"code": "abc", "state": state})


# --- start ---------------------------------------------------------------------------------


def test_providers_lists_only_configured_ones(monkeypatch):
    monkeypatch.delenv("EXAM_OAUTH_MICROSOFT_CLIENT_SECRET")
    body = TestClient(app).get("/auth/providers").json()
    assert [p["name"] for p in body["providers"]] == ["google", "github"]
    assert body["dev"] is False


@pytest.mark.parametrize(
    ("provider", "host"),
    [
        ("google", "accounts.google.com"),
        ("microsoft", "login.microsoftonline.com"),
        ("github", "github.com"),
    ],
)
def test_login_redirects_to_the_provider_with_state_and_pkce(provider, host):
    client = TestClient(app, follow_redirects=False)
    resp = client.get(f"/auth/{provider}/login")
    assert resp.status_code == 302
    url = urlparse(resp.headers["location"])
    assert url.netloc == host
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert q["client_id"] == f"id-{provider}" and q["response_type"] == "code"
    assert q["redirect_uri"] == f"http://localhost:8000/auth/{provider}/callback"
    assert q["code_challenge_method"] == "S256" and len(q["state"]) >= 24
    cookies = resp.headers.get_list("set-cookie")
    assert any(
        "exam_oauth_state=" in c and "HttpOnly" in c and "SameSite=lax" in c for c in cookies
    )
    assert any("exam_oauth_verifier=" in c and "HttpOnly" in c for c in cookies)
    assert "client_secret" not in resp.headers["location"]


def test_unknown_or_unconfigured_provider(monkeypatch):
    client = TestClient(app, follow_redirects=False)
    assert client.get("/auth/myspace/login").status_code == 404
    monkeypatch.delenv("EXAM_OAUTH_GOOGLE_CLIENT_ID")
    resp = client.get("/auth/google/login")
    assert resp.status_code == 302 and "error=not_configured" in resp.headers["location"]
    assert resp.headers["location"].startswith(WEB)


# --- callback ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("provider", "responses", "name"),
    [
        ("google", GOOGLE_OK, "Ann"),
        ("github", GITHUB_OK, "ann-gh"),
        ("microsoft", MICROSOFT_OK, "Ann M"),
    ],
)
def test_full_sign_in_creates_an_account_and_a_session(provider, responses, name):
    client = make_client(responses)
    done = sign_in(client, provider)
    assert done.status_code == 302 and done.headers["location"] == f"{WEB}/#/"
    cookie = next(c for c in done.headers.get_list("set-cookie") if c.startswith("exam_session="))
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=" in cookie
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == name and me.json()["dev"] is False


def test_the_token_request_carries_the_code_verifier_and_secret_server_side_only():
    seen: list[httpx.Request] = []
    client = make_client(GOOGLE_OK, seen)
    sign_in(client, "google")
    token_req = next(r for r in seen if "oauth2.googleapis.com/token" in str(r.url))
    body = parse_qs(token_req.content.decode())
    assert body["code"] == ["abc"] and body["client_secret"] == ["secret-google"]
    assert len(body["code_verifier"][0]) >= 43
    assert any(r.headers.get("authorization") == "Bearer tok" for r in seen)


def test_state_mismatch_is_refused_and_creates_no_session():
    client = make_client(GOOGLE_OK)
    client.get("/auth/google/login")
    bad = client.get("/auth/google/callback", params={"code": "abc", "state": "forged"})
    assert bad.status_code == 302 and "error=state" in bad.headers["location"]
    assert client.get("/auth/me").status_code == 401


def test_callback_without_the_cookies_is_refused():
    client = make_client(GOOGLE_OK)
    resp = TestClient(app, follow_redirects=False).get(
        "/auth/google/callback", params={"code": "abc", "state": "x"}
    )
    assert "error=state" in resp.headers["location"]
    del client


def test_provider_denial_and_failures_return_to_the_app_with_an_error():
    client = make_client(GOOGLE_OK)
    client.get("/auth/google/login")
    denied = client.get("/auth/google/callback", params={"error": "access_denied"})
    assert "error=denied" in denied.headers["location"]

    failing = make_client({"oauth2.googleapis.com/token": (400, {"error": "invalid_grant"})})
    assert "error=provider" in sign_in(failing, "google").headers["location"]
    assert failing.get("/auth/me").status_code == 401

    no_token = make_client({"oauth2.googleapis.com/token": (200, {"error": "bad_code"})})
    assert "error=provider" in sign_in(no_token, "google").headers["location"]


def test_redirects_only_go_to_the_configured_web_url():
    client = make_client(GOOGLE_OK)
    done = sign_in(client, "google")
    assert done.headers["location"].startswith(WEB + "/")


# --- linking & ownership -------------------------------------------------------------------


def test_signing_in_with_a_second_provider_reaches_the_same_account_when_verified():
    a = make_client(GOOGLE_OK)
    sign_in(a, "google")
    b = make_client(GITHUB_OK)
    sign_in(b, "github")
    assert a.get("/auth/me").json()["id"] == b.get("/auth/me").json()["id"]


def test_microsoft_email_never_links():
    a = make_client(GOOGLE_OK)
    sign_in(a, "google")
    b = make_client(MICROSOFT_OK)
    sign_in(b, "microsoft")
    assert a.get("/auth/me").json()["id"] != b.get("/auth/me").json()["id"]


def test_a_session_is_the_owner_for_every_resource_and_logout_ends_it():
    a = make_client(GOOGLE_OK)
    sign_in(a, "google")
    created = a.post("/documents", json={"title": "Mine"})
    assert created.status_code == 201
    doc_id = created.json()["id"]
    assert a.get("/documents").json()["documents"][0]["title"] == "Mine"

    other = make_client(
        {
            "oauth2.googleapis.com/token": (200, {"access_token": "t2"}),
            "openidconnect.googleapis.com": (
                200,
                {"sub": "g-200", "email": "bob@example.com", "email_verified": True},
            ),
        }
    )
    sign_in(other, "google")
    assert other.get("/documents").json()["documents"] == []
    assert other.get(f"/documents/{doc_id}").status_code == 404

    assert a.post("/auth/logout").status_code == 204
    assert a.get("/auth/me").status_code == 401
    assert a.get("/documents").status_code == 401


def test_anonymous_requests_are_401_without_the_dev_stub():
    anon = TestClient(app)
    for path in ("/documents", "/bank", "/auth/me"):
        assert anon.get(path).status_code == 401
    assert anon.post("/assets", content=b"x").status_code == 401


def test_a_forged_or_stale_cookie_is_not_identity():
    client = TestClient(app, cookies={"exam_session": "forged-token"})
    assert client.get("/documents").status_code == 401


def test_dev_stub_still_works_when_enabled_and_a_session_wins_over_it(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    anon = TestClient(app)
    assert anon.get("/auth/me").json() == {
        "id": "local",
        "email": None,
        "name": "Local development",
        "dev": True,
    }
    assert anon.get("/auth/providers").json()["dev"] is True
    a = make_client(GOOGLE_OK)
    sign_in(a, "google")
    real = a.get("/auth/me").json()["id"]
    assert real != "local"
    assert a.get("/documents", headers={"X-Dev-Owner": "mallory"}).status_code == 200
    assert a.get("/auth/me", headers={"X-Dev-Owner": "mallory"}).json()["id"] == real


def test_cors_allows_the_web_origin_with_credentials_only():
    client = TestClient(app)
    ok = client.options(
        "/documents",
        headers={"Origin": WEB, "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers["access-control-allow-origin"] == WEB
    assert ok.headers["access-control-allow-credentials"] == "true"
    evil = client.options(
        "/documents",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in evil.headers
