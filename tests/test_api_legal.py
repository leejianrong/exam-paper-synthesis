"""EXA-185: the privacy notice and terms are readable signed out, script-free, with the contact."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "heading"), [("/privacy", "Privacy notice"), ("/terms", "Terms of use")]
)
def test_pages_load_signed_out(client: TestClient, path: str, heading: str) -> None:
    res = client.get(path)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert f"<h1>{heading}</h1>" in res.text
    assert "<script" not in res.text
    assert "Content-Security-Policy" in res.headers


def test_privacy_names_what_is_kept_and_the_ways_out(client: TestClient) -> None:
    text = client.get("/privacy").text
    for phrase in (
        "never see or store a password",
        "Download my data",
        "Delete my account",
        "Singapore",
        "Backups are kept for 14 days",
    ):
        assert phrase in text


def test_contact_address_is_escaped_into_both_pages(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EXAM_CONTACT_EMAIL", 'help@example.org"><b>')
    for path in ("/privacy", "/terms"):
        text = client.get(path).text
        assert 'href="mailto:help@example.org&quot;&gt;&lt;b&gt;"' in text
        assert "<b>" not in text


def test_without_a_contact_address_the_pages_say_so(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EXAM_CONTACT_EMAIL", raising=False)
    assert "A contact address will be published here" in client.get("/privacy").text
