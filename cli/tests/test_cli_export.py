"""KAN-152 — behavioural tests for `mathgen export`.

`preview` renders worksheet HTML (no browser; always runs). `worksheet` and
`answer-key` render to PDF via headless Chromium, so those are skipped cleanly when
Chromium is not installed (CI installs it, mirroring the V5 api export test).
"""

from __future__ import annotations

import json

import pytest
from mathgen.__main__ import main


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


requires_chromium = pytest.mark.skipif(
    not _chromium_available(),
    reason="headless Chromium not installed (run: playwright install chromium)",
)


def _gen_file(capsys, tmp_path, code, seed):
    out = tmp_path / f"{code}_{seed}.json"
    main(["generate", code, "--seed", str(seed), "--out", str(out)])
    capsys.readouterr()
    return out


def _plain_prefix(obj: dict) -> str:
    """First plain-text chunk of the question (before any KaTeX ``\\(``/``$``)."""
    text = obj["question"]["parts"][0]["text"]
    for delim in ("\\(", "$"):
        text = text.split(delim, 1)[0]
    return text.strip()


def test_preview_renders_html_with_both_questions(capsys, tmp_path):
    f1 = _gen_file(capsys, tmp_path, "ratio_medium", 1)
    f2 = _gen_file(capsys, tmp_path, "fractions_easy", 2)

    rc = main(["export", "preview", str(f1), str(f2), "--title", "Mixed Set"])
    assert rc == 0
    html = capsys.readouterr().out
    assert "Mixed Set" in html
    assert html.count('class="question"') == 2
    # each question's plain stem text is present
    assert _plain_prefix(json.loads(f1.read_text())) in html
    assert _plain_prefix(json.loads(f2.read_text())) in html


def test_preview_to_out_file(capsys, tmp_path):
    f1 = _gen_file(capsys, tmp_path, "ratio_medium", 1)
    out = tmp_path / "preview.html"
    rc = main(["export", "preview", str(f1), "--out", str(out)])
    assert rc == 0
    assert "sheet-title" in out.read_text()


def test_tampered_object_exits_nonzero(capsys, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "canonical"}))
    rc = main(["export", "preview", str(bad)])
    assert rc != 0
    assert "invalid canonical object" in capsys.readouterr().err


@requires_chromium
def test_worksheet_writes_pdf(capsys, tmp_path):
    f1 = _gen_file(capsys, tmp_path, "ratio_medium", 1)
    f2 = _gen_file(capsys, tmp_path, "fractions_easy", 2)
    out = tmp_path / "worksheet.pdf"
    rc = main(["export", "worksheet", str(f1), str(f2), "--title", "Set A", "--out", str(out)])
    assert rc == 0
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


@requires_chromium
def test_answer_key_writes_pdf(capsys, tmp_path):
    f1 = _gen_file(capsys, tmp_path, "ratio_medium", 1)
    out = tmp_path / "answers.pdf"
    rc = main(["export", "answer-key", str(f1), "--out", str(out)])
    assert rc == 0
    data = out.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
