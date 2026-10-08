"""W3c — the per-account export allowance: ledger contract and the routes that spend it."""

from __future__ import annotations

import threading

import pytest
from app import export, usage
from app.main import app
from app.usage import Limits, SqliteUsageLedger
from documents import gen_block, make_doc
from fastapi.testclient import TestClient

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}


@pytest.fixture(params=["sqlite", "postgres"])
def ledger(request, tmp_path):
    if request.param == "sqlite":
        return SqliteUsageLedger(tmp_path / "ledger.sqlite3")
    if request.param == "postgres":
        from app.pgstores import PgUsageLedger

        return PgUsageLedger(request.getfixturevalue("pg_db"))
    raise AssertionError(request.param)  # pragma: no cover


@pytest.fixture
def clock(monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(usage, "_now", lambda: now[0])
    return now


# --- ledger contract ---------------------------------------------------------------------


def test_consumes_up_to_the_daily_limit_then_refuses_with_a_retry_time(ledger, clock):
    limits = Limits(per_day=3, per_minute=0)
    for _ in range(3):
        assert ledger.consume("alice", limits).allowed
        clock[0] += 100  # spread out; the minute window is off
    refused = ledger.consume("alice", limits)
    assert not refused.allowed and refused.reason == "day" and refused.ticket is None
    # the oldest of the three ages out 24 h after it happened (300 s ago)
    assert refused.retry_after == pytest.approx(usage.DAY_S - 300, abs=2)
    clock[0] += usage.DAY_S - 299
    assert ledger.consume("alice", limits).allowed


def test_minute_window_is_separate_and_frees_quickly(ledger, clock):
    limits = Limits(per_day=100, per_minute=2)
    assert ledger.consume("alice", limits).allowed
    assert ledger.consume("alice", limits).allowed
    refused = ledger.consume("alice", limits)
    assert not refused.allowed and refused.reason == "minute" and 1 <= refused.retry_after <= 61
    clock[0] += 61
    assert ledger.consume("alice", limits).allowed


def test_owners_are_independent(ledger, clock):
    limits = Limits(per_day=1, per_minute=0)
    assert ledger.consume("alice", limits).allowed
    assert not ledger.consume("alice", limits).allowed
    assert ledger.consume("bob", limits).allowed


def test_zero_means_unlimited_per_window(ledger, clock):
    limits = Limits(per_day=0, per_minute=0)
    assert all(ledger.consume("alice", limits).allowed for _ in range(50))


def test_refund_gives_the_export_back(ledger, clock):
    limits = Limits(per_day=1, per_minute=0)
    first = ledger.consume("alice", limits)
    assert not ledger.consume("alice", limits).allowed
    ledger.refund(first.ticket)
    assert ledger.consume("alice", limits).allowed
    ledger.refund(999_999)  # refunding something unknown is harmless


def test_used_counts_the_windows(ledger, clock):
    limits = Limits(per_day=0, per_minute=0)
    ledger.consume("alice", limits)
    clock[0] += 120
    ledger.consume("alice", limits)
    assert ledger.used("alice") == (2, 1)
    assert ledger.used("bob") == (0, 0)


def test_parallel_consumers_cannot_exceed_the_limit(ledger):
    limits = Limits(per_day=5, per_minute=0)
    results: list[bool] = []

    def go():
        results.append(ledger.consume("alice", limits).allowed)

    threads = [threading.Thread(target=go) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 5


def test_limits_from_env(monkeypatch):
    monkeypatch.delenv("EXAM_EXPORT_LIMIT_PER_DAY")
    monkeypatch.delenv("EXAM_EXPORT_LIMIT_PER_MINUTE")
    assert usage.limits_from_env() == Limits(30, 5)
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "7")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_MINUTE", "junk")
    assert usage.limits_from_env() == Limits(7, 5)


# --- routes ----------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _dev(monkeypatch):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "2")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_MINUTE", "0")


@pytest.fixture
def fake_pdf(monkeypatch):
    calls: list[int] = []

    def render(html: str) -> bytes:
        calls.append(1)
        return b"%PDF-fake"

    monkeypatch.setattr(export, "html_to_pdf", render)
    return calls


def _doc(headers) -> str:
    rec = client.post("/documents", json={"title": "Q"}, headers=headers).json()
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": make_doc(gen_block(), title="Q"), "base_version": rec["version"]},
        headers=headers,
    )
    assert saved.status_code == 200
    return rec["id"]


def test_document_exports_spend_the_allowance_then_429_with_retry_after(fake_pdf):
    doc = _doc(ALICE)
    url = f"/documents/{doc}/export/student"
    assert client.post(url, headers=ALICE).status_code == 200
    assert client.post(url, headers=ALICE).status_code == 200
    refused = client.post(url, headers=ALICE)
    assert refused.status_code == 429
    assert int(refused.headers["retry-after"]) > 0
    assert "Export limit reached" in refused.json()["detail"]
    assert len(fake_pdf) == 2  # the refused request never started a browser
    # previews are free, other accounts are untouched
    assert client.get(f"/documents/{doc}/preview/student", headers=ALICE).status_code == 200
    bob_doc = _doc(BOB)
    assert client.post(f"/documents/{bob_doc}/export/student", headers=BOB).status_code == 200


def test_a_failed_render_is_refunded(monkeypatch):
    doc = _doc(ALICE)

    def boom(html: str) -> bytes:
        raise RuntimeError("chromium crashed")

    monkeypatch.setattr(export, "html_to_pdf", boom)
    failing = TestClient(app, raise_server_exceptions=False)
    for _ in range(4):  # more failures than the allowance of 2
        assert failing.post(f"/documents/{doc}/export/student", headers=ALICE).status_code == 500
    monkeypatch.setattr(export, "html_to_pdf", lambda html: b"%PDF-ok")
    assert client.post(f"/documents/{doc}/export/student", headers=ALICE).status_code == 200


def test_the_classic_export_routes_need_an_owner_and_spend_the_allowance(fake_pdf, monkeypatch):
    from exam_engine import generate

    body = {"title": "W", "questions": [generate("ratio_easy", 1)]}
    assert client.post("/export/worksheet", json=body, headers=ALICE).status_code == 200
    assert client.post("/export/answer-key", json=body, headers=ALICE).status_code == 200
    assert client.post("/export/worksheet", json=body, headers=ALICE).status_code == 429
    assert client.post("/export/preview", json=body, headers=ALICE).status_code == 200  # free
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.post("/export/worksheet", json=body).status_code == 401
    assert client.post("/export/preview", json=body).status_code == 401


def test_quota_endpoint_reports_what_is_left(fake_pdf):
    doc = _doc(ALICE)
    before = client.get("/auth/quota", headers=ALICE).json()
    assert before == {"per_day": 2, "per_minute": 0, "used_day": 0, "used_minute": 0, "left_day": 2}
    client.post(f"/documents/{doc}/export/student", headers=ALICE)
    assert client.get("/auth/quota", headers=ALICE).json()["left_day"] == 1
    assert client.get("/auth/quota", headers=BOB).json()["left_day"] == 2


def test_unlimited_when_both_limits_are_zero(fake_pdf, monkeypatch):
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "0")
    doc = _doc(ALICE)
    for _ in range(5):
        assert client.post(f"/documents/{doc}/export/student", headers=ALICE).status_code == 200
    assert client.get("/auth/quota", headers=ALICE).json()["left_day"] is None


def test_quota_requires_sign_in(monkeypatch):
    monkeypatch.delenv("EXAM_DEV_AUTH")
    assert client.get("/auth/quota").status_code == 401


def test_erase_owner_forgets_only_that_owner(ledger, clock):
    limits = Limits(per_day=1, per_minute=0)
    assert ledger.consume("alice", limits).allowed
    assert ledger.consume("bob", limits).allowed
    ledger.erase_owner("alice")
    assert ledger.used("alice") == (0, 0)
    assert ledger.used("bob") == (1, 1)
    assert ledger.consume("alice", limits).allowed
