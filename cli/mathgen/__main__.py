"""Sole CLI entry point: argparse wiring + dispatch (KAN-152).

    mathgen generate <code> [--seed N] [--count K] [--out FILE]
    mathgen edit <op> [<FILE>|-] [--seed N] [--out FILE]
    mathgen export {preview|worksheet|answer-key} <FILES...> [--title T] [--out FILE]

Only stdlib ``argparse`` is used (no dependency beyond Playwright, which the
non-PDF paths never import). ``main`` returns a process exit code, so the console
script wrapper does the right thing (``sys.exit(main())``).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from exam_engine import edits

from .commands import dispatch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mathgen",
        description="Drive the exam engine directly: generate/edit/export (no web, no API).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate canonical question object(s)")
    gen.add_argument("code", help="blueprint code, e.g. ratio_medium")
    gen.add_argument("--seed", type=int, default=None, help="base seed (default: random)")
    gen.add_argument("--count", type=int, default=1, help="how many (fresh distinct seeds)")
    gen.add_argument("--out", default=None, help="write to FILE instead of stdout")

    ed = sub.add_parser("edit", help="apply an edit op to a canonical object")
    ed.add_argument("op", choices=sorted(edits.KNOWN_OPS), help="edit operation")
    ed.add_argument("source", nargs="?", default="-", help="input FILE or '-' for stdin")
    ed.add_argument("--seed", type=int, default=None, help="seed for resample ops")
    ed.add_argument("--out", default=None, help="write to FILE instead of stdout")

    exp = sub.add_parser("export", help="render a worksheet/answer-key from objects")
    exp_sub = exp.add_subparsers(dest="export_cmd", required=True)
    for name, needs_out in (("preview", False), ("worksheet", True), ("answer-key", True)):
        p = exp_sub.add_parser(name)
        p.add_argument("files", nargs="+", help="canonical object files (or JSON arrays)")
        p.add_argument("--title", default=None, help="worksheet title")
        p.add_argument(
            "--out",
            required=needs_out,
            default=None,
            help="output FILE" + (" (required, PDF)" if needs_out else " (default: stdout)"),
        )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
