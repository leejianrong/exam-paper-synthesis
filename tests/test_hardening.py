"""W4 — production configuration guard, security headers, readiness, static web serving."""

from __future__ import annotations

import pytest
from app import config, export
from app.main import app, mount_web
from fastapi import FastAPI
from fastapi.testclient import TestClient

GOOD_ENV = {
    "EXAM_ENV": "production",
    "EXAM_DATABASE_URL": "postgresql://u:p@db.example/neon",
    "EXAM_PUBLIC_URL": "https://exams.example",
    "EXAM_WEB_URL": "https://exams.example",
    "EXAM_OAUTH_GOOGLE_CLIENT_ID": "id",
    "EXAM_OAUTH_GOOGLE_CLIENT_SECRET": "secret",
}


@pytest.fixture
def prod(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH", raising=False)
    for k, v in GOOD_ENV.items():
        monkeypatch.setenv(k, v)
    return monkeypatch


# --- production guard ------------------------------------------------------------------------


def test_a_correct_production_environment_has_no_problems(prod):
    assert config.production_problems() == []
    config.check_production()  # does not raise


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        ({"EXAM_DEV_AUTH": "1"}, "EXAM_DEV_AUTH"),
        ({"EXAM_DATABASE_URL": ""}, "EXAM_DATABASE_URL"),
        ({"EXAM_PUBLIC_URL": "http://exams.example"}, "EXAM_PUBLIC_URL"),
        ({"EXAM_WEB_URL": "http://localhost:5173"}, "EXAM_WEB_URL"),
        ({"EXAM_OAUTH_GOOGLE_CLIENT_SECRET": ""}, "no sign-in provider"),
    ],
)
def test_each_unsafe_setting_is_named(prod, change, needle):
    for k, v in change.items():
        prod.setenv(k, v)
    problems = config.production_problems()
    assert any(needle in p for p in problems), problems
    with pytest.raises(RuntimeError, match=needle):
        config.check_production()


def test_the_app_refuses_to_boot_when_production_is_unsafe(prod):
    prod.setenv("EXAM_DEV_AUTH", "1")
    with pytest.raises(RuntimeError, match="unsafe production configuration"), TestClient(app):
        pass


def test_outside_production_nothing_is_enforced(monkeypatch):
    monkeypatch.delenv("EXAM_ENV", raising=False)
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    config.check_production()
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_dev_stub_flag_cannot_authenticate_in_a_correct_production_setup(prod):
    # Even if someone sets the flag after boot, there is still no session => no identity
    # unless the flag is on; the guard above is what keeps it off. Anonymous stays 401.
    with TestClient(app) as client:
        assert client.get("/documents").status_code == 401


# --- headers, readiness ----------------------------------------------------------------------


def test_security_headers_on_every_response(monkeypatch):
    monkeypatch.setenv("EXAM_PUBLIC_URL", "https://exams.example")
    resp = TestClient(app).get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
    assert "camera=()" in resp.headers["permissions-policy"]
    assert resp.headers["strict-transport-security"].startswith("max-age=")


def test_no_hsts_on_plain_http_dev(monkeypatch):
    monkeypatch.setenv("EXAM_PUBLIC_URL", "http://localhost:8000")
    assert "strict-transport-security" not in TestClient(app).get("/health").headers


def test_ready_is_ok_on_sqlite_and_503_when_the_database_is_down(monkeypatch):
    assert TestClient(app).get("/ready").json() == {"status": "ready"}

    class Dead:
        def connection(self):
            raise RuntimeError("connection refused to db.internal:5432")

    from app import pgstores

    monkeypatch.setenv("EXAM_DATABASE_URL", "postgresql://x/y")
    monkeypatch.setattr(pgstores, "get_database", lambda _u: Dead())
    resp = TestClient(app).get("/ready")
    assert resp.status_code == 503
    assert "db.internal" not in resp.text  # no internals leak


# --- static web ------------------------------------------------------------------------------


def test_the_built_web_app_is_served_from_the_same_origin_and_the_api_still_wins(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>app</title>")
    (dist / "app.js").write_text("console.log(1)")
    target = FastAPI()

    @target.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    assert mount_web(target, dist) is True
    client = TestClient(target)
    assert "<title>app</title>" in client.get("/").text
    assert client.get("/app.js").text == "console.log(1)"
    assert client.get("/health").json() == {"status": "ok"}  # mounted last: API first


def test_no_build_means_nothing_is_mounted(tmp_path):
    assert mount_web(FastAPI(), tmp_path) is False
    assert mount_web(FastAPI(), None) is False


# --- export timeouts -------------------------------------------------------------------------


def test_export_timeout_and_sandbox_flags(monkeypatch):
    assert export._timeout_ms() == 30000
    monkeypatch.setenv("EXAM_EXPORT_TIMEOUT_MS", "5000")
    assert export._timeout_ms() == 5000
    monkeypatch.setenv("EXAM_EXPORT_TIMEOUT_MS", "junk")
    assert export._timeout_ms() == 30000
    monkeypatch.setenv("EXAM_EXPORT_TIMEOUT_MS", "5")
    assert export._timeout_ms() == 1000  # floor: never a zero/negative timeout
    assert export._launch_args() == []
    monkeypatch.setenv("EXAM_CHROMIUM_NO_SANDBOX", "1")
    assert export._launch_args() == ["--no-sandbox"]
