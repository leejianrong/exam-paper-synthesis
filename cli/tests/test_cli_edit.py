"""KAN-152 — behavioural tests for `mathgen edit`.

The edit reads a canonical object (file or stdin), applies an op, and writes the
lineage-stamped child. An unavailable op must exit non-zero, name the available
ops, and write nothing.
"""

from __future__ import annotations

import io
import json

from exam_engine import canonical
from mathgen.__main__ import main


def _generate(capsys, code, seed):
    main(["generate", code, "--seed", str(seed)])
    return json.loads(capsys.readouterr().out)


def test_make_harder_produces_hard_child_from_file(capsys, tmp_path):
    parent = _generate(capsys, "ratio_medium", 1)
    src = tmp_path / "parent.json"
    src.write_text(json.dumps(parent))

    rc = main(["edit", "make-harder", str(src), "--seed", "5"])
    assert rc == 0
    child = json.loads(capsys.readouterr().out)
    canonical.load(child)
    assert child["blueprint_code"] == "ratio_hard"
    assert child["provenance"]["parent_id"] == parent["id"]
    assert child["provenance"]["version"] == parent["provenance"]["version"] + 1


def test_edit_reads_from_stdin(capsys, monkeypatch, tmp_path):
    parent = _generate(capsys, "ratio_medium", 2)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(parent)))
    rc = main(["edit", "make-harder", "-"])
    assert rc == 0
    child = json.loads(capsys.readouterr().out)
    assert child["blueprint_code"] == "ratio_hard"


def test_make_harder_on_hard_rung_fails_and_writes_nothing(capsys, tmp_path):
    parent = _generate(capsys, "ratio_hard", 1)
    src = tmp_path / "hard.json"
    src.write_text(json.dumps(parent))
    out = tmp_path / "child.json"

    rc = main(["edit", "make-harder", str(src), "--out", str(out)])
    assert rc != 0
    captured = capsys.readouterr()
    assert "not available" in captured.err
    # lists the ops that ARE available
    assert "make-easier" in captured.err
    assert not out.exists()  # nothing written


def test_tampered_object_exits_nonzero(capsys, tmp_path):
    src = tmp_path / "bad.json"
    src.write_text(json.dumps({"not": "canonical"}))
    rc = main(["edit", "regenerate", str(src)])
    assert rc != 0
    assert "invalid canonical object" in capsys.readouterr().err


def test_set_cosmetic_renames_via_set_flag(capsys, tmp_path):
    parent = _generate(capsys, "ratio_medium", 3)
    src = tmp_path / "parent.json"
    src.write_text(json.dumps(parent))

    rc = main(["edit", "set-cosmetic", str(src), "--set", "names=Ann,Ben,Cal"])
    assert rc == 0
    child = json.loads(capsys.readouterr().out)
    canonical.load(child)
    assert child["parameters"]["names"] == ["Ann", "Ben", "Cal"]
    assert child["question"]["parts"][0]["answer"] == parent["question"]["parts"][0]["answer"]
    assert child["provenance"]["parent_id"] == parent["id"]


def test_set_cosmetic_refuses_a_numeric_param(capsys, tmp_path):
    parent = _generate(capsys, "ratio_medium", 3)
    src = tmp_path / "parent.json"
    src.write_text(json.dumps(parent))

    rc = main(["edit", "set-cosmetic", str(src), "--set", "total=99"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "changes the maths" in captured.err
