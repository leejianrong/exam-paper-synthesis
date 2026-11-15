"""Print golden fixtures as the engine prints them: question, worked steps, answer.

For the human golden check (CLAUDE.md: goldens are verified by a person, never a model).
Usage: uv run python scripts/show_goldens.py [prefix ...]   e.g.  ... decimals rate
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.pipeline import build_from_params
from exam_engine.render import _fmt_answer

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"


def plain(text: str) -> str:
    """Readable in a terminal: \\(5n - 7\\) -> 5n - 7, \\frac{a}{b} -> (a)/(b), \\times -> ×."""
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", text)
    return text.replace("\\(", "").replace("\\)", "").replace("\\times", "×").replace("\\div", "÷")


def main(prefixes: list[str]) -> None:
    n = 0
    for path in sorted(GOLDEN.glob("*.jsonl")):
        code = path.stem
        if prefixes and not code.startswith(tuple(prefixes)):
            continue
        spec, solver = load_blueprint(code), get_solver(code)
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            n += 1
            g = json.loads(line)
            q = build_from_params(spec, solver, 0, g["params"])["question"]
            print(f"\n#{n}  [{code}]")
            if q.get("stem"):
                print("   " + plain(q["stem"]))
            for p in q["parts"]:
                label = f"({p['label']}) " if len(q["parts"]) > 1 else ""
                print(f"   {label}{plain(p['text'])}")
                for s in p.get("solution_steps", []):
                    print(f"      · {plain(s['text'])}")
                marks = f"{p['marks']} mark{'' if p['marks'] == 1 else 's'}"
                print(f"   => {label}{plain(_fmt_answer(p['answer']))}   [{marks}]")


if __name__ == "__main__":
    main(sys.argv[1:])
