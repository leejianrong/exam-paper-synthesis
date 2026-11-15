"""P8b — multiple choice from constructed-response questions (Paper 1 Booklet A).

``to_mcq(obj, seed)`` turns a generated question with a numeric answer into a four-option
multiple-choice question. The correct option is the engine's own answer, formatted exactly as
the answer key prints it; the three distractors are plausible wrong answers:

1. **Stopping early** — the values of the worked solution's intermediate steps (e.g. "the value
   of one unit" in a ratio question), the classic wrong answer.
2. **Common slips** — ×10 / ÷10 (place value), and a near miss one "step" away.

Pure and deterministic: the same ``(obj, seed)`` gives the same options in the same order.
``document.verify_snapshot`` re-solves the blueprint and checks the correct option's text
equals the proven answer, so a converted question stays engine-proven.
"""

from __future__ import annotations

import ast
import copy
import operator
import random
from fractions import Fraction

from .errors import EditNotApplicable

LABELS = ("1", "2", "3", "4")  # PSLE Booklet A numbers its options (1)–(4)
NUMERIC = ("integer", "decimal", "quantity")
CONVERTIBLE = (*NUMERIC, "fraction")

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval(expr: str) -> Fraction | None:
    """Exactly evaluate a step's arithmetic (numbers, + - * / and brackets), else ``None``."""

    def ev(n: ast.AST) -> Fraction:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int | float):
            return Fraction(str(n.value))
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        raise ValueError("unsupported")

    try:
        return ev(ast.parse(expr.replace("×", "*").replace("÷", "/"), mode="eval"))
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None


def convertible(obj: dict) -> bool:
    """A generated, single-part question with a numeric answer."""
    parts = obj["question"]["parts"]
    return (
        obj.get("source_type") == "generated"
        and len(parts) == 1
        and parts[0]["answer"].get("type") in CONVERTIBLE
    )


_UNIT_TEXT = {"cm^2": "cm²", "m^2": "m²", "cm^3": "cm³", "m^3": "m³"}


def answer_text(answer: dict) -> str:
    """How an answer reads as an option: ``$344``, ``$12.50``, ``53 kg``, ``45%``, ``95°``,
    ``297 cm³``, or a KaTeX fraction. The document check uses the same function on the
    re-solved answer, so an option and the proof can never disagree on format."""
    unit = answer.get("unit") or ""
    if answer["type"] == "fraction":
        body = rf"\(\frac{{{answer['numerator']}}}{{{answer['denominator']}}}\)"
        return f"{body} {_UNIT_TEXT.get(unit, unit)}".strip() if unit != "$" else f"${body}"
    value = answer["value"]
    if unit == "$":
        return f"${value:.2f}" if answer["type"] == "decimal" else f"${value}"
    if unit == "%":
        return f"{value}%"
    if unit == "degrees":
        return f"{value}°"
    return f"{value} {_UNIT_TEXT.get(unit, unit)}".strip()


def _value(answer: dict) -> Fraction:
    if answer["type"] == "fraction":
        return Fraction(answer["numerator"], answer["denominator"])
    return Fraction(str(answer["value"]))


def _with_value(answer: dict, value: Fraction) -> dict:
    """``answer`` carrying another value, kept in the same representation."""
    out = dict(answer)
    if answer["type"] == "fraction":
        out["numerator"], out["denominator"] = value.numerator, value.denominator
        return out
    if answer["type"] == "decimal" or value.denominator != 1:
        places = max(_places(answer.get("value")), 1 if value.denominator != 1 else 0)
        out["type"] = "decimal" if answer["type"] != "quantity" else "quantity"
        out["value"] = round(float(value), places)
    else:
        out["value"] = int(value)
    return out


def _places(v: object) -> int:
    s = str(v)
    return len(s.split(".")[1]) if "." in s else 0


def _plausible(v: Fraction, answer: Fraction, *, fraction: bool = False) -> bool:
    if v <= 0 or v == answer:
        return False
    if fraction:
        return v.denominator != 1 and v.denominator <= 100
    if v.denominator != 1 and answer.denominator == 1:
        # a whole-number answer gets whole-number distractors (2 dp at most otherwise)
        return False
    return (v * 100).denominator == 1


def distractor_values(obj: dict) -> list[Fraction]:
    """Candidate wrong answers, best first."""
    part = obj["question"]["parts"][0]
    answer_obj = part["answer"]
    answer = _value(answer_obj)
    is_fraction = answer_obj["type"] == "fraction"
    out: list[Fraction] = []

    def add(v: Fraction | None) -> None:
        if v is not None and _plausible(v, answer, fraction=is_fraction) and v not in out:
            out.append(v)

    if is_fraction:
        n, d = answer.numerator, answer.denominator
        # the unshaded part, shaded : unshaded read as a fraction, and off-by-one slips
        add(Fraction(d - n, d) if d > n else None)
        add(Fraction(n, d - n) if d > n else None)
        add(Fraction(n + 1, d))
        add(Fraction(n, d + 1))
        add(Fraction(max(n - 1, 1), d))
        add(Fraction(n + 1, d + 1))
        for k in range(2, 30):
            add(Fraction(n, d + k))
            if len(out) >= 6:
                break
        return out

    # 1. stopping early: the latest intermediate value first (one step short)
    steps = part.get("solution_steps") or []
    for step in reversed(steps[:-1]):
        v = _eval(step.get("expr") or "")
        # far-off intermediates are usually another quantity (km vs h, units vs $): skip them
        if v is not None and answer / 8 <= v <= answer * 8:
            add(v)
    # 2. near misses, then halving/doubling, then place value (most guessable last)
    step = max(Fraction(1), Fraction(10) ** (len(str(int(answer))) - 2))
    for v in (answer + step, answer - step, answer * 2, answer / 2, answer * 10, answer / 10):
        add(v)
    for k in range(2, 50):  # never short of options
        add(answer + k * step)
        if len(out) >= 6:
            break
    return out


def to_mcq(obj: dict, seed: int) -> dict:
    """A four-option multiple-choice copy of ``obj`` (see the module docstring)."""
    if not convertible(obj):
        raise EditNotApplicable("to-mcq", "only a generated question with a numeric answer")
    if obj.get("validation", {}).get("checks", {}).get("representation") == "decimals":
        raise EditNotApplicable("to-mcq", "not a question shown in decimals")
    out = copy.deepcopy(obj)
    part = out["question"]["parts"][0]
    answer = part["answer"]
    correct_text = answer_text(answer)

    texts = [correct_text]
    for v in distractor_values(obj):
        t = answer_text(_with_value(answer, v))
        if t not in texts:
            texts.append(t)
        if len(texts) == len(LABELS):
            break
    assert len(texts) == len(LABELS), texts

    rng = random.Random(f"mcq|{obj['id']}|{seed}")
    rng.shuffle(texts)
    options = [{"label": label, "text": text} for label, text in zip(LABELS, texts, strict=True)]
    correct = LABELS[texts.index(correct_text)]
    part["answer"] = {"type": "choice", "options": options, "correct": correct}
    marks = part["marks"]
    part["marking_scheme"] = [
        {"mark": marks, "type": "A", "description": f"Correct option ({correct})."}
    ]
    return out


def correct_option_text(answer: dict) -> str | None:
    """The text of a choice answer's correct option (exact, as stored)."""
    return next(
        (o.get("text") for o in answer.get("options", []) if o.get("label") == answer["correct"]),
        None,
    )
