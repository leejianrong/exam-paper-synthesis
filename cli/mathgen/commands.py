"""Subcommand implementations — thin marshalling over the engine (KAN-152).

Each ``cmd_*`` takes the parsed argparse ``Namespace`` and returns a process exit
code (0 on success, non-zero on a handled error). The heavy lifting stays in the
engine: :func:`exam_engine.pipeline.generate`, :mod:`exam_engine.edits`,
:mod:`exam_engine.canonical`, and :mod:`exam_engine.render`. JSON in / JSON out
(contract C3); every object crosses :func:`canonical.load` before it is written or
rendered, so a tampered or invalid object fails loudly with a path-pointed error.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from exam_engine import canonical, edits, pipeline
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


def dispatch(args: argparse.Namespace) -> int:
    """Route to the selected subcommand, converting engine errors to exit codes."""
    handlers = {"generate": cmd_generate, "edit": cmd_edit, "export": cmd_export}
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
