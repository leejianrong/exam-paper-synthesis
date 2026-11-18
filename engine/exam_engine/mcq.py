"""P8b — multiple choice from constructed-response questions (Paper 1 Booklet A).

``to_mcq(obj, seed)`` turns a generated question with a numeric answer into a four-option
multiple-choice question. The correct option is the engine's own answer, formatted exactly as
the answer key prints it; the three distractors are plausible wrong answers:

1. **Common wrong answers** — the solver's own ``distractors(params, solution)`` hook, when it
   has one: wrong answers pupils really give, in the answer's own quantity and unit, each
   with the reason it is tempting (shown in the answer key's marking scheme).
2. **Stopping early** — otherwise, the worked solution's intermediate values (e.g. "the value
   of one unit" in a ratio question).
3. **Common slips** — a near miss one "step" away, doubling / halving, ×10 / ÷10.

The answer is never left exactly between two other options, evenly (``7 / 8 / 9``) or by a
factor (``14 / 28 / 56``), when the candidates allow another choice.

The options print in ascending order, as real papers list numeric options (EXA-141); the seed
picks the last wrong option so the answer's place in that order varies. A solver whose answer
is an extreme of the options ("which is the greatest?") opts out with ``mcq_ascending = False``
and gets a seeded order instead.

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

from .blueprints.registry import get_solver
from .errors import EditNotApplicable
from .units import printed_unit

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


def legacy_answer_text(answer: dict) -> str:
    """The option text a paper saved before litres printed as ``ℓ`` carries (``18 l``)."""
    return answer_text(answer).replace("mℓ", "ml").replace("ℓ", "l")


def answer_text(answer: dict) -> str:
    """How an answer reads as an option: ``$344``, ``$12.50``, ``53 kg``, ``45%``, ``95°``,
    ``297 cm³``, or a KaTeX fraction. The document check uses the same function on the
    re-solved answer, so an option and the proof can never disagree on format."""
    unit = answer.get("unit") or ""
    if answer["type"] == "fraction":
        body = rf"\(\frac{{{answer['numerator']}}}{{{answer['denominator']}}}\)"
        return f"{body} {printed_unit(unit)}".strip() if unit != "$" else f"${body}"
    value = answer["value"]
    if unit == "$":
        return f"${value:.2f}" if answer["type"] == "decimal" else f"${value}"
    if unit == "%":
        return f"{value}%"
    if unit == "degrees":
        return f"{value}°"
    return f"{value} {printed_unit(unit)}".strip()


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
        # the answer's declared places (money: dp 2, so 5.25 is never shown as 5.2 -> $5.20)
        dp = answer.get("dp")
        own = next((k for k in range(4) if (value * 10**k).denominator == 1), 2)
        places = dp if isinstance(dp, int) else max(_places(answer.get("value")), own)
        out["type"] = "decimal" if answer["type"] != "quantity" else "quantity"
        out["value"] = round(float(value), places)
        if value.denominator == 1 and _kind(answer) != "money":
            out["value"] = int(value)  # a whole wrong answer reads "100 cm²", not "100.0 cm²"
        elif _kind(answer) == "money" and value.denominator != 1:
            # cents on a whole-dollar answer: a 2-dp amount ("$19.80", never "$19.8")
            out["type"], out["dp"], out["value"] = "decimal", 2, round(float(value), 2)
    else:
        out["value"] = int(value)
    return out


def _places(v: object) -> int:
    s = str(v)
    return len(s.split(".")[1]) if "." in s else 0


# Units of a measure, where a whole answer may still be met by a 1-dp wrong answer (2.5 h,
# 52.5°); a plain count ("", items, people, ...) keeps whole-number distractors.
_MEASURES = frozenset(
    {"cm", "m", "km", "mm", "cm^2", "m^2", "cm^3", "m^3", "ml", "l", "g", "kg", "s", "min", "h"}
    | {"km/h", "m/s", "m/min", "degrees", "%"}
)


def _plausible(v: Fraction, answer: Fraction, *, fraction: bool = False, kind: str = "") -> bool:
    """``kind``: ``"money"`` (2 dp always fine), ``"measure"`` (a whole answer allows 1 dp),
    ``"vouched"`` (a unitless number the solver's hook offers: up to 3 dp), else a count or
    plain number (a whole answer gets whole distractors)."""
    if v <= 0 or v == answer:
        return False
    if fraction:  # first: a fraction option is a proper-looking fraction, never "4/1" (EXA-133)
        return v.denominator != 1 and v.denominator <= 100
    if kind == "vouched":  # a solver's own decimal slip (1.984 for 19.84): up to 3 dp
        return (v * 1000).denominator == 1
    if answer.denominator == 1 and v.denominator != 1:
        if kind == "money":
            return (v * 100).denominator == 1
        if kind == "measure":
            return (v * 10).denominator == 1
        return False
    return (v * 100).denominator == 1


def _kind(answer: dict) -> str:
    unit = answer.get("unit") or ""
    if unit == "$":  # whole dollars or cents: a wrong answer may have cents, never 3 dp
        return "money"
    return "measure" if unit in _MEASURES else ""


def common_wrong_answers(obj: dict) -> list[tuple[Fraction, str]]:
    """The solver's own "common wrong answers" (an optional ``distractors(params, solution)``
    hook, see ``blueprints.base.Solver``): ``(value, why)`` pairs, best first. Each is a
    wrong answer a pupil really gives *in the answer's own quantity and unit*: forgetting a
    step, using the wrong total, the other person's share. ``[]`` when the solver has none."""
    try:
        solver = get_solver(obj.get("blueprint_code") or "")
    except Exception:  # a sourced or unknown blueprint: no hook
        return []
    hook = getattr(solver, "distractors", None)
    params = obj.get("parameters")
    if hook is None or not isinstance(params, dict):
        return []
    out = []
    for value, why in hook(params, solver.solve(params)):
        out.append((value if isinstance(value, Fraction) else Fraction(str(value)), str(why)))
    return out


def hook_value_prints(v: Fraction, answer_obj: dict) -> bool:
    """Whether :func:`distractor_candidates` keeps a solver hook's value ``v`` for this answer:
    plausible, and (unless a fraction) within 20 times of it. ``blueprints.base.spread`` uses
    it to balance only the slips that will print."""
    answer = _value(answer_obj)
    is_fraction = answer_obj["type"] == "fraction"
    kind = _kind(answer_obj)
    # a solver's own hook vouches for a decimal slip on a whole answer (7.4 × 30: "22.2"); a
    # real slip far off the answer is a giveaway (24000 ℓ for 24 ℓ), 20x still keeps "the
    # distance in 1 hour" for a 12-hour journey
    near = is_fraction or answer / 20 <= v <= answer * 20
    return near and _plausible(v, answer, fraction=is_fraction, kind=kind or "vouched")


def distractor_candidates(obj: dict) -> list[tuple[Fraction, str]]:
    """Candidate wrong answers with the reason each is tempting, best first.

    1. The solver's common wrong answers (its hook), when it has one.
    2. Otherwise, stopping early: the worked solution's intermediate values within 8x of
       the answer (farther ones are usually another quantity).
    3. Near misses, doubling / halving, place value: the generic fallback, never short.
    """
    part = obj["question"]["parts"][0]
    answer_obj = part["answer"]
    answer = _value(answer_obj)
    is_fraction = answer_obj["type"] == "fraction"
    kind = _kind(answer_obj)
    whole_only = _solver_flag(obj, "mcq_whole", False)
    out: list[tuple[Fraction, str]] = []

    def add(v: Fraction | None, why: str, *, vouched: bool = False) -> None:
        # a solver's own hook vouches for a decimal slip on a whole answer (7.4 × 30: "22.2")
        if v is None or not _plausible(
            v, answer, fraction=is_fraction, kind="vouched" if vouched and not kind else kind
        ):
            return
        if whole_only and v.denominator != 1:  # e.g. whole hours of rental: never "3.5 h"
            return
        if all(v != have for have, _ in out):
            out.append((v, why))

    hooked = common_wrong_answers(obj)
    for v, why in hooked:
        if hook_value_prints(v, answer_obj) and all(v != have for have, _ in out):
            out.append((v, why))

    if is_fraction:
        n, d = answer.numerator, answer.denominator
        add(Fraction(d - n, d) if d > n else None, "the other part of the whole")
        add(Fraction(n, d - n) if d > n else None, "part : rest read as a fraction")
        add(Fraction(n + 1, d), "numerator one out")
        add(Fraction(n, d + 1), "denominator one out")
        add(Fraction(max(n - 1, 1), d), "numerator one out")
        add(Fraction(n + 1, d + 1), "one added to both")
        for k in range(2, 30):
            add(Fraction(n, d + k), "a near miss")
            if len(out) >= 8:
                break
        return out

    if not hooked:
        steps = part.get("solution_steps") or []
        for i in range(len(steps) - 2, -1, -1):  # the latest intermediate first
            mid = _eval(steps[i].get("expr") or "")
            if mid is not None and answer / 8 <= mid <= answer * 8:
                add(mid, f"stopped after step {i + 1}")
    step = max(Fraction(1), Fraction(10) ** (len(str(int(answer))) - 2))
    for v, why in (
        (answer + step, "a near miss"),
        (answer - step, "a near miss"),
        (answer * 2, "doubled"),
        (answer / 2, "halved"),
        (answer * 10, "a place-value slip"),
        (answer / 10, "a place-value slip"),
    ):
        add(v, why)
    for k in range(2, 50):  # never short of options, on both sides
        add(answer + k * step, "a near miss")
        add(answer - k * step, "a near miss")
        if len(out) >= 10:
            break
    return out


def distractor_values(obj: dict) -> list[Fraction]:
    """Candidate wrong answers, best first (the values of :func:`distractor_candidates`)."""
    return [v for v, _ in distractor_candidates(obj)]


def _gives_it_away(answer: Fraction, chosen: list[Fraction]) -> bool:
    """Guessable without the maths: the answer sits exactly between two other options,
    evenly (``7 / 8 / 9``) or by a factor (``14 / 28 / 56``), or it is the odd one out (the
    only whole number among decimals, or the only decimal)."""
    between = any(
        answer - a == b - answer or answer / a == b / answer
        for a in chosen
        for b in chosen
        if 0 < a < answer < b
    )
    # the odd one out: the only whole number among decimals, or the only decimal
    whole = answer.denominator == 1
    odd = len(chosen) == len(LABELS) - 1 and all((c.denominator == 1) != whole for c in chosen)
    return between or odd


def _solver_flag(obj: dict, name: str, default: bool) -> bool:
    """A solver's optional multiple-choice setting (``default`` for a sourced question)."""
    try:
        solver = get_solver(obj.get("blueprint_code") or "")
    except Exception:  # a sourced or unknown blueprint
        return default
    return bool(getattr(solver, name, default))


def _ascending(obj: dict) -> bool:
    """Options print in ascending order unless the solver opts out (``mcq_ascending = False``:
    "which is the greatest?", whose answer would then always be (1) or (4))."""
    return _solver_flag(obj, "mcq_ascending", True)


def _last_pick(
    answer: Fraction,
    chosen: list[Fraction],
    fits: list[tuple[Fraction, str, str]],
    rng: random.Random,
) -> tuple[Fraction, str, str]:
    """The last wrong option, picked so the answer's place in the ascending list varies.

    Options print in ascending order, so a solver whose common wrong answers all lie on one
    side of the answer would always put it first or last (a rate's "the amount in 1 unit" is
    always smaller). The first wrong options stay the best candidates; for the last one the
    seed picks one of the places the remaining candidates allow, then the best candidate that
    puts the answer there."""
    below = sum(c < answer for c in chosen)
    places = sorted({below + (v < answer) for v, _, _ in fits})
    place = rng.choice(places)
    return next(f for f in fits if below + (f[0] < answer) == place)


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
    value = _value(answer)

    rng = random.Random(f"mcq|{obj['id']}|{seed}")
    ascending = _ascending(obj)
    texts = [correct_text]
    why: dict[str, str] = {}
    chosen: list[Fraction] = []
    candidates = distractor_candidates(obj)
    for strict in (True, False):  # avoid a give-away set when the candidates allow it
        fits: list[tuple[Fraction, str, str]] = []
        for v, reason in candidates:
            shown = _with_value(answer, v)
            if _value(shown) != v:  # printed rounded: its reason would not match what is shown
                continue
            t = answer_text(shown)
            if t in texts or (strict and _gives_it_away(value, [*chosen, v])):
                continue
            if len(texts) < len(LABELS) - 1:
                texts.append(t)
                why[t] = reason
                chosen.append(v)
            elif all(t != have for _, _, have in fits):
                fits.append((v, reason, t))
        if fits:  # the last wrong option: see _last_pick
            v, reason, t = _last_pick(value, chosen, fits, rng) if ascending else fits[0]
            texts.append(t)
            why[t] = reason
            chosen.append(v)
        if len(texts) == len(LABELS):
            break
    assert len(texts) == len(LABELS), texts

    if ascending:
        # as real papers list numeric options (about 36 of 40 in the 2025 prelims): every
        # option here is a number in the answer's own unit and form
        texts = [t for _, t in sorted(zip([value, *chosen], texts, strict=True))]
    else:
        rng.shuffle(texts)
    options = [{"label": label, "text": text} for label, text in zip(LABELS, texts, strict=True)]
    correct = LABELS[texts.index(correct_text)]
    part["answer"] = {"type": "choice", "options": options, "correct": correct}
    marks = part["marks"]
    wrong = "; ".join(f"({o['label']}) {why[o['text']]}" for o in options if o["text"] in why)
    part["marking_scheme"] = [
        {
            "mark": marks,
            "type": "A",
            "description": f"Correct option ({correct}). Wrong options: {wrong}.",
        }
    ]
    return out


def correct_option_text(answer: dict) -> str | None:
    """The text of a choice answer's correct option (exact, as stored)."""
    return next(
        (o.get("text") for o in answer.get("options", []) if o.get("label") == answer["correct"]),
        None,
    )
