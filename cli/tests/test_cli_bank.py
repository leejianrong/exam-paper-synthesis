"""KAN-663 E1 — behavioural tests for `mathgen bank`."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from exam_engine.bank import default_path
from mathgen.__main__ import main

FIXTURE = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "fixtures"
    / "sourced"
    / "psle_2023_ratio.json"
)
FIXTURE_ID = "sourced:rosyth-2023-prelim-p2-q12"


def _run(capsys, argv):
    rc = main(argv)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _row_for(out: str, id_: str) -> list[str]:
    for line in out.strip().splitlines():
        if line.startswith(id_):
            return line.split()
    raise AssertionError(f"{id_!r} not found in output:\n{out}")


def test_import_then_list(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))

    rc, out, _ = _run(capsys, ["bank", "import", str(FIXTURE)])
    assert rc == 0
    assert out.strip() == FIXTURE_ID

    rc, out, _ = _run(capsys, ["bank", "list"])
    assert rc == 0
    assert _row_for(out, FIXTURE_ID)[-1] == "no"


def test_persists_across_invocations(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))

    rc, _, _ = _run(capsys, ["bank", "import", str(FIXTURE)])
    assert rc == 0

    # A fresh `main()` call, as a fresh process would see it, against the same path.
    rc, out, _ = _run(capsys, ["bank", "list"])
    assert rc == 0
    assert _row_for(out, FIXTURE_ID)


def test_search_by_reviewed(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))
    _run(capsys, ["bank", "import", str(FIXTURE)])

    rc, out, _ = _run(capsys, ["bank", "search", "--reviewed", "false"])
    assert rc == 0
    assert _row_for(out, FIXTURE_ID)[-1] == "no"

    rc, out, _ = _run(capsys, ["bank", "search", "--reviewed", "true"])
    assert rc == 0
    assert FIXTURE_ID not in out

    rc, _, _ = _run(capsys, ["bank", "review", FIXTURE_ID, "--mark-reviewed", "--no-edit"])
    assert rc == 0

    rc, out, _ = _run(capsys, ["bank", "search", "--reviewed", "true"])
    assert rc == 0
    assert _row_for(out, FIXTURE_ID)[-1] == "yes"

    rc, out, _ = _run(capsys, ["bank", "search", "--reviewed", "false"])
    assert rc == 0
    assert FIXTURE_ID not in out


def test_review_with_editor(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))
    _run(capsys, ["bank", "import", str(FIXTURE)])

    stub = tmp_path / "fake_editor.py"
    stub.write_text(
        "import json, sys\n"
        "path = sys.argv[1]\n"
        "obj = json.load(open(path))\n"
        "obj['validation']['checks']['note'] = 'edited-by-stub'\n"
        "json.dump(obj, open(path, 'w'))\n"
    )
    editor = f"{shlex.quote(sys.executable)} {shlex.quote(str(stub))}"

    rc, out, _ = _run(capsys, ["bank", "review", FIXTURE_ID, "--editor", editor])
    assert rc == 0
    result = json.loads(out)
    assert result["validation"]["checks"]["note"] == "edited-by-stub"
    assert result["provenance"]["version"] == 2

    rc, out, _ = _run(capsys, ["bank", "list"])
    assert rc == 0
    assert _row_for(out, FIXTURE_ID)[-1] == "no"  # editing alone doesn't mark reviewed


def test_import_duplicate_without_overwrite_fails(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_BANK_PATH", str(tmp_path / "bank.sqlite3"))
    _run(capsys, ["bank", "import", str(FIXTURE)])

    rc, _, err = _run(capsys, ["bank", "import", str(FIXTURE)])
    assert rc == 2
    assert "already has an object" in err

    rc, out, _ = _run(capsys, ["bank", "import", str(FIXTURE), "--overwrite"])
    assert rc == 0
    assert out.strip() == FIXTURE_ID


def test_bank_path_resolution(monkeypatch):
    monkeypatch.delenv("EXAM_BANK_PATH", raising=False)
    assert default_path() == Path.home() / ".exam_engine" / "bank.sqlite3"
