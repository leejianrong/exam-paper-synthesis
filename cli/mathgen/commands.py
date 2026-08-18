"""Subcommand implementations — thin marshalling over the engine (KAN-152).

Each ``cmd_*`` takes the parsed argparse ``Namespace`` and returns a process exit
code (0 on success, non-zero on a handled error). The heavy lifting stays in the
engine: :func:`exam_engine.pipeline.generate`, :mod:`exam_engine.edits`,
:mod:`exam_engine.canonical`, :mod:`exam_engine.render`, and :mod:`exam_engine.bank`.
JSON in / JSON out
(contract C3); every object crosses :func:`canonical.load` before it is written or
rendered, so a tampered or invalid object fails loudly with a path-pointed error.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from exam_engine import canonical, edits, pipeline
from exam_engine.bank import open_bank
from exam_engine.errors import EditNotApplicable, EngineError
from exam_engine.render import render_answer_key_html, render_worksheet_html


def _err(msg: str) -> None:
    print(f"mathgen: error: {msg}", file=sys.stderr)


def _write_text(text: str, out: str | None) -> None:
    if out is None:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    else:
        Path(out).write_text(text, encoding="utf-8")


def _read_object(source: str) -> dict:
    """Read one canonical object from a file path or ``-`` (stdin)."""
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    return json.loads(raw)


def _load_questions(files: list[str]) -> list[dict]:
    """Read canonical objects from files (each a single object or a JSON array).

    Every object is passed through the schema gate; a bad one raises
    :class:`canonical.CanonicalValidationError` with a path-pointed message.
    """
    questions: list[dict] = []
    for f in files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        for obj in items:
            questions.append(canonical.load(obj))
    return questions


# --- generate ---------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    base_seed = args.seed if args.seed is not None else random.randrange(1, 2**31)
    count = args.count
    if count < 1:
        _err("--count must be >= 1")
        return 2

    objects = [canonical.load(pipeline.generate(args.code, base_seed + i)) for i in range(count)]
    if count > 1:
        text = json.dumps(objects, ensure_ascii=False, indent=2)
    else:
        text = canonical.to_json(objects[0], indent=2)
    _write_text(text, args.out)
    return 0


# --- edit -------------------------------------------------------------------


def cmd_edit(args: argparse.Namespace) -> int:
    obj = canonical.load(_read_object(args.source))
    available = edits.available_ops(obj)
    if args.op not in available:
        _err(
            f"edit {args.op!r} is not available for {obj['blueprint_code']!r}; "
            f"available: {', '.join(sorted(available))}"
        )
        return 2

    child = edits.apply(args.op, obj, seed=args.seed)
    _write_text(canonical.to_json(child, indent=2), args.out)
    return 0


# --- export -----------------------------------------------------------------


def cmd_export(args: argparse.Namespace) -> int:
    questions = _load_questions(args.files)
    title = args.title or "Worksheet"

    if args.export_cmd == "preview":
        _write_text(render_worksheet_html(title, questions), args.out)
        return 0

    from ._pdf import html_to_pdf  # lazy: only the PDF subcommands touch the browser

    if args.export_cmd == "worksheet":
        html = render_worksheet_html(title, questions)
    else:  # answer-key
        html = render_answer_key_html(title, questions)

    Path(args.out).write_bytes(html_to_pdf(html))
    return 0


# --- bank ---------------------------------------------------------------


def _print_bank_table(objects: list[dict]) -> None:
    print(f"{'id':<40} {'source_type':<10} {'topic':<20} {'level':<6} {'difficulty':<10} reviewed")
    for obj in objects:
        reviewed = "yes" if obj["validation"].get("checks", {}).get("human_reviewed") else "no"
        topic = obj.get("syllabus", {}).get("topic") or ""
        level = obj.get("syllabus", {}).get("level") or ""
        difficulty = obj.get("cognitive", {}).get("difficulty") or ""
        print(
            f"{obj['id']:<40} {obj['source_type']:<10} {topic:<20} "
            f"{level:<6} {difficulty:<10} {reviewed}"
        )


def cmd_bank_import(args: argparse.Namespace) -> int:
    bank = open_bank()
    for obj in _load_questions([args.file]):
        stored = bank.add(obj, overwrite=args.overwrite)
        print(stored["id"])
    return 0


def cmd_bank_list(args: argparse.Namespace) -> int:
    _print_bank_table(open_bank().search())
    return 0


def cmd_bank_search(args: argparse.Namespace) -> int:
    reviewed = None if args.reviewed is None else args.reviewed == "true"
    objects = open_bank().search(
        topic=args.topic,
        difficulty=args.difficulty,
        level=args.level,
        source_type=args.source_type,
        reviewed=reviewed,
    )
    _print_bank_table(objects)
    return 0


def cmd_bank_review(args: argparse.Namespace) -> int:
    bank = open_bank()
    obj = bank.get(args.id)

    did_edit = False
    if not args.no_edit:
        editor = args.editor or os.environ.get("EDITOR")
        if not editor:
            _err("no editor available: set $EDITOR, or pass --no-edit / --editor")
            return 2
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(canonical.to_json(obj, indent=2))
            tmp_path = tf.name
        try:
            subprocess.run([*shlex.split(editor), tmp_path], check=True)
            obj = json.loads(Path(tmp_path).read_text(encoding="utf-8"))
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        did_edit = True

    if args.mark_reviewed:
        obj.setdefault("validation", {}).setdefault("checks", {})["human_reviewed"] = True

    if did_edit or args.mark_reviewed:
        obj = bank.update(obj)

    print(canonical.to_json(obj, indent=2))
    return 0


def cmd_bank(args: argparse.Namespace) -> int:
    handlers = {
        "import": cmd_bank_import,
        "list": cmd_bank_list,
        "search": cmd_bank_search,
        "review": cmd_bank_review,
    }
    return handlers[args.bank_cmd](args)


def dispatch(args: argparse.Namespace) -> int:
    """Route to the selected subcommand, converting engine errors to exit codes."""
    handlers = {
        "generate": cmd_generate,
        "edit": cmd_edit,
        "export": cmd_export,
        "bank": cmd_bank,
    }
    try:
        return handlers[args.command](args)
    except canonical.CanonicalValidationError as e:
        _err(f"invalid canonical object: {e}")
        return 2
    except EditNotApplicable as e:
        _err(str(e))
        return 2
    except FileNotFoundError as e:
        _err(f"no such file: {e.filename}")
        return 2
    except json.JSONDecodeError as e:
        _err(f"could not parse JSON: {e}")
        return 2
    except EngineError as e:
        _err(str(e))
        return 2
