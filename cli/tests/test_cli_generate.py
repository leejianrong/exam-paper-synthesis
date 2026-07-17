"""KAN-152 — behavioural tests for `mathgen generate` (the test is the proof).

We drive the real argv path via ``mathgen.__main__.main`` and assert the emitted
JSON is schema-valid, correctly shaped, and deterministic. A guard test asserts the
CLI never pulls in FastAPI/the API app — the engine-agnostic proof (decision C1).
"""

from __future__ import annotations

import json

from exam_engine import canonical
from mathgen.__main__ import main


def _run(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


def test_generate_single_is_schema_valid_and_generated(capsys):
    rc, out = _run(capsys, ["generate", "ratio_medium", "--seed", "1"])
    assert rc == 0
    obj = json.loads(out)
    canonical.load(obj)  # accepts it -> schema-valid
    assert obj["source_type"] == "generated"
    assert obj["blueprint_code"] == "ratio_medium"


def test_generate_is_deterministic(capsys):
    _, out1 = _run(capsys, ["generate", "ratio_medium", "--seed", "1"])
    _, out2 = _run(capsys, ["generate", "ratio_medium", "--seed", "1"])
    a, b = json.loads(out1), json.loads(out2)
    assert a["id"] == b["id"]
    assert a["parameters"] == b["parameters"]


def test_generate_count_gives_distinct_valid_array(capsys):
    rc, out = _run(capsys, ["generate", "ratio_medium", "--seed", "1", "--count", "3"])
    assert rc == 0
    arr = json.loads(out)
    assert isinstance(arr, list) and len(arr) == 3
    for obj in arr:
        canonical.load(obj)
    ids = [obj["id"] for obj in arr]
    assert len(set(ids)) == 3


def test_generate_writes_to_out_file(capsys, tmp_path):
    out = tmp_path / "q.json"
    rc, stdout = _run(capsys, ["generate", "fractions_easy", "--seed", "7", "--out", str(out)])
    assert rc == 0
    assert stdout == ""  # nothing to stdout when --out given
    obj = json.loads(out.read_text())
    canonical.load(obj)
    assert obj["blueprint_code"] == "fractions_easy"


def test_unknown_blueprint_exits_nonzero(capsys):
    rc = main(["generate", "does_not_exist", "--seed", "1"])
    assert rc != 0
    assert "unknown blueprint" in capsys.readouterr().err.lower()


def test_cli_does_not_import_fastapi_or_app():
    """The engine-agnostic proof: importing mathgen must not pull in FastAPI/app.

    Runs in a fresh interpreter so it is not confused by the rest of the test
    session (the api tests import FastAPI, polluting this process's sys.modules).
    """
    import subprocess
    import sys

    probe = (
        "import mathgen, mathgen.__main__, mathgen.commands, sys; "
        "bad = [m for m in sys.modules if m == 'fastapi' or m == 'app' "
        "or m.startswith('fastapi.') or m.startswith('app.')]; "
        "print(bad); "
        "assert not bad, bad"
    )
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert result.returncode == 0, f"CLI imported forbidden modules: {result.stdout}{result.stderr}"
