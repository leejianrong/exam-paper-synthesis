"""Pytest + Hypothesis configuration for the test suite (KAN-237).

Registers Hypothesis profiles so the property-based invariant tests
(``test_invariants_*.py``) stay **deterministic** and **fast** by default while a
larger budget is available on demand:

* ``ci`` / ``dev`` (the default) — a bounded ``max_examples`` with
  ``derandomize=True`` so example selection is a deterministic function of the
  test (a green run stays green on re-run with no code change, and a failure
  reproduces exactly). ``deadline=None`` deliberately removes Hypothesis's
  per-example wall-clock deadline: on shared CI runners a timing deadline is the
  one source of flakiness we must not introduce (dev-playbook: tests must be
  deterministic). Determinism of *example choice* comes from ``derandomize``, not
  from a clock.
* ``nightly`` — the same determinism with a much larger ``max_examples`` for a
  deeper nightly sweep.

Select a profile with ``HYPOTHESIS_PROFILE=<name>`` (e.g. ``HYPOTHESIS_PROFILE=nightly
uv run pytest``); the default is ``ci``.
"""

from __future__ import annotations

import os

from hypothesis import settings

settings.register_profile("ci", max_examples=50, deadline=None, derandomize=True)
settings.register_profile("dev", max_examples=50, deadline=None, derandomize=True)
settings.register_profile("nightly", max_examples=1000, deadline=None, derandomize=True)

settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_assets_store(monkeypatch, tmp_path):
    """Never let a test touch the real ~/.exam_engine asset / account stores (W2b, W3)."""
    monkeypatch.setenv("EXAM_ASSETS_PATH", str(tmp_path / "assets.sqlite3"))
    monkeypatch.setenv("EXAM_AUTH_PATH", str(tmp_path / "accounts.sqlite3"))
    monkeypatch.setenv("EXAM_USAGE_PATH", str(tmp_path / "usage.sqlite3"))


@pytest.fixture
def pg_db():
    """A fresh Postgres schema for one test (W3b); skipped unless EXAM_TEST_DATABASE_URL is set.

    Locally: ``docker run -d -p 55432:5432 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=exam
    postgres:16-alpine`` then ``EXAM_TEST_DATABASE_URL=postgresql://postgres:pw@localhost:55432/exam``.
    CI runs a Postgres service container and sets it.
    """
    url = os.environ.get("EXAM_TEST_DATABASE_URL")
    if not url:
        pytest.skip("EXAM_TEST_DATABASE_URL not set (Postgres contract tests)")
    import uuid

    from app.pgstores import Database

    db = Database(url, schema=f"t_{uuid.uuid4().hex[:12]}")
    try:
        yield db
    finally:
        db.drop_schema()


_API_MODULE_PREFIXES = (
    "test_api_",
    "test_auth_api",
    "test_convert",
    "test_export_api",
    "test_sourced_interchange",
    "test_assets",
    "test_usage",
)


@pytest.fixture(autouse=True)
def _postgres_backend(request, monkeypatch):
    """With ``EXAM_TEST_BACKEND=postgres`` the API tests run on a fresh Postgres schema.

    The same assertions then prove the whole API — not just the stores — behaves identically
    on Neon-style Postgres and on the SQLite used locally.
    """
    if os.environ.get("EXAM_TEST_BACKEND") != "postgres":
        return
    if not request.module.__name__.startswith(_API_MODULE_PREFIXES):
        return
    db = request.getfixturevalue("pg_db")
    monkeypatch.setenv("EXAM_DATABASE_URL", db.url)
    monkeypatch.setattr("app.pgstores.get_database", lambda _url: db)
