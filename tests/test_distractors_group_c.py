"""EXA-122 — the "common wrong answers" hooks of the whole_numbers, decimals, rate and algebra
ladders.

For every rung, over many seeds through the real ``generate()``: the hook offers named
mistakes, most of the multiple-choice copy's wrong options come from it, and the copy stays
engine-proven. Then, per rung, at least one named mistake is re-derived *independently* from
the printed question text (numbers parsed out of the stem — never the solver or its
intermediates) and must be among the hook's values.
"""

from __future__ import annotations

import re
from fractions import Fraction

import pytest
from exam_engine import mcq
from exam_engine.document import verify_snapshot
from exam_engine.pipeline import generate

CODES = [
    f"{family}_{rung}"
    for family in ("whole_numbers", "decimals", "rate", "algebra")
    for rung in ("easy", "medium", "hard")
]
SEEDS = range(1, 101)


def _text(obj: dict) -> str:
    q = obj["question"]
    return " ".join(t for t in (q.get("stem"), q["parts"][0].get("text")) if t)


def _hook_values(obj: dict) -> list[Fraction]:
    return [v for v, _ in mcq.common_wrong_answers(obj)]


def _whole_dollars(answer: dict) -> bool:
    """A money answer that happens to be whole dollars ($7.00). mcq's plausibility filter
    reads its value as a whole number and drops every distractor with cents, so most
    money mistakes (the cost of one, $5.25 + ...) cannot be offered: the generic near
    misses fill in. Those seeds are left out of the ratio (a framework limitation)."""
    return answer.get("unit") == "$" and float(answer["value"]).is_integer()


@pytest.mark.parametrize("code", CODES)
def test_the_hook_supplies_most_wrong_options(code):
    from_hook = counted = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        hooked = mcq.common_wrong_answers(obj)
        assert hooked, (code, seed)
        assert all(isinstance(why, str) and why.strip() for _, why in hooked), (code, seed)
        answer = obj["question"]["parts"][0]["answer"]
        hook_texts = {mcq.answer_text(mcq._with_value(answer, v)) for v, _ in hooked}
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == [], (code, seed)
        choice = m["question"]["parts"][0]["answer"]
        wrong = [o["text"] for o in choice["options"] if o["label"] != choice["correct"]]
        assert len(wrong) == 3
        if answer["type"] == "decimal" and _whole_dollars(answer):
            continue
        counted += 1
        if sum(t in hook_texts for t in wrong) >= 2:
            from_hook += 1
    assert counted >= 0.6 * len(SEEDS), (code, counted)
    assert from_hook >= 0.9 * counted, (code, from_hook, counted)


# ------------------------------------------------------------------ independent re-derivations

_NUM = r"(\d+(?:\.\d+)?)"


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", text)]


def _expr_value(expr: str) -> Fraction:
    """Evaluate ``a + b × (c − d)`` exactly with the usual precedence (a tiny parser)."""
    tokens = re.findall(r"\d+|[()+\-×÷]", expr.replace("−", "-"))
    pos = 0

    def atom() -> Fraction:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        if tok == "(":
            v = add()
            pos += 1  # ")"
            return v
        return Fraction(int(tok))

    def mul() -> Fraction:
        nonlocal pos
        v = atom()
        while pos < len(tokens) and tokens[pos] in "×÷":
            op = tokens[pos]
            pos += 1
            v = v * atom() if op == "×" else v / atom()
        return v

    def add() -> Fraction:
        nonlocal pos
        v = mul()
        while pos < len(tokens) and tokens[pos] in "+-":
            op = tokens[pos]
            pos += 1
            v = v + mul() if op == "+" else v - mul()
        return v

    return add()


def _left_to_right(expr: str) -> Fraction:
    tokens = re.findall(r"\d+|[+\-×÷]", expr.replace("−", "-"))
    v = Fraction(int(tokens[0]))
    for op, n in zip(tokens[1::2], tokens[2::2], strict=True):
        v = {"+": v + int(n), "-": v - int(n), "×": v * int(n), "÷": v / int(n)}[op]
    return v


def whole_numbers_easy(text: str) -> Fraction:
    """No brackets: worked left to right. Brackets: ignored them (usual precedence)."""
    expr = re.search(r"value of (.*)\.", text).group(1)
    if "(" in expr:
        return _expr_value(expr.replace("(", "").replace(")", ""))
    return _left_to_right(expr)


def whole_numbers_medium(text: str) -> Fraction:
    """Gave the remainder."""
    pens = re.search(r"costs \$(\d+)\..*with \$(\d+)\?", text)
    n, d = (int(pens.group(2)), int(pens.group(1))) if pens else _ints(text)[:2]
    return Fraction(n % d)


def whole_numbers_hard(text: str) -> Fraction:
    """Forgot the leftover: shares × pupils only."""
    m = re.search(
        r"gets (\d+) \w+, there will be (\d+) \w+ left over\. "
        r"If each pupil gets (\d+) \w+, .* short of (\d+)",
        text,
    )
    a, left, b, short = (int(g) for g in m.groups())
    return Fraction(a * (left + short), b - a)


def decimals_easy(text: str) -> Fraction:
    """The decimal point one place too far right."""
    m = re.search(rf"value of {_NUM} ([×÷]) (\d+)", text)
    a, f = Fraction(m.group(1)), int(m.group(3))
    return (a * f if m.group(2) == "×" else a / f) * 10


def decimals_medium(text: str) -> Fraction:
    """Gave the cost of one."""
    m = re.search(rf"(\d+) .*? cost \${_NUM}\.", text)
    return Fraction(m.group(2)) / int(m.group(1))


def decimals_hard(text: str) -> Fraction:
    """Gave the total spent instead of the change."""
    bought = re.findall(rf"(\d+) [^$]*? at \${_NUM}", text)
    assert len(bought) == 2, text
    return sum((int(q) * Fraction(p) for q, p in bought), Fraction(0))


def rate_easy(text: str) -> Fraction:
    """Added the rate and the time instead of multiplying."""
    rate = int(re.search(r" (\d+) [\w ]+ (?:per minute|every hour)", text).group(1))
    time = int(re.search(r" in (\d+) (?:minute|hour)", text).group(1))
    return Fraction(rate + time)


def rate_medium(text: str) -> Fraction:
    """Gave the number in one time unit."""
    m = re.search(r" (\d+) [\w ]+? in (\d+) (?:minute|hour)", text)
    return Fraction(int(m.group(1)), int(m.group(2)))


def _minutes(text: str) -> int:
    hours = re.search(r"for (\d+) hours?\.", text)
    if hours:
        return 60 * int(hours.group(1))
    m = re.search(r"for (?:(\d+) h)? ?(?:(\d+) min)?\.", text)
    return 60 * int(m.group(1) or 0) + int(m.group(2) or 0)


def rate_hard(text: str) -> Fraction:
    """Left out the first-hour charge: only the additional blocks."""
    m = re.search(rf"\${_NUM} for each additional (half hour|hour)", text)
    extra, block = Fraction(m.group(1)), 30 if m.group(2) == "half hour" else 60
    return extra * (_minutes(text) - 60) / block


def algebra_easy(text: str) -> Fraction | None:
    """``5n − 7`` read as ``57 − 7`` (only the ``an ± b`` forms)."""
    m = re.search(r"\\\((\d+)([a-z]) ([+-]) (\d+)\\\) when \\\(\2 = (\d+)\\\)", text)
    if m is None:
        return None
    joined, b = int(m.group(1) + m.group(5)), int(m.group(4))
    return Fraction(joined + b if m.group(3) == "+" else joined - b)


def algebra_medium(text: str) -> Fraction:
    """Used the first item's price for both."""
    k1, k2 = (int(g) for g in re.search(r"buys (\d+) [\w-]+ and (\d+) ", text).groups())
    p = int(re.search(r"when \\\([a-z] = (\d+)\\\)", text).group(1))
    return Fraction((k1 + k2) * p)


def algebra_hard(text: str) -> Fraction:
    """Gave the other person's number at first (x found by trying every value)."""
    times = re.search(r"has (\d+) times as many", text)
    more = re.search(r"has (\d+) more \w+ than", text)
    give = re.search(r"gives away (\d+)", text)
    get = re.search(r"gets (\d+) more", text)
    total = int(re.search(r"now have (\d+)", text).group(1))
    change = -int(give.group(1)) if give else int(get.group(1))
    for x in range(1, total + 1):
        other = x * int(times.group(1)) if times else x + int(more.group(1))
        if x + other + change == total:
            return Fraction(other)
    raise AssertionError(text)


DERIVE = {
    "whole_numbers_easy": whole_numbers_easy,
    "whole_numbers_medium": whole_numbers_medium,
    "whole_numbers_hard": whole_numbers_hard,
    "decimals_easy": decimals_easy,
    "decimals_medium": decimals_medium,
    "decimals_hard": decimals_hard,
    "rate_easy": rate_easy,
    "rate_medium": rate_medium,
    "rate_hard": rate_hard,
    "algebra_easy": algebra_easy,
    "algebra_medium": algebra_medium,
    "algebra_hard": algebra_hard,
}


@pytest.mark.parametrize("code", CODES)
def test_a_named_mistake_is_rederived_from_the_printed_question(code):
    checked = 0
    for seed in SEEDS:
        obj = generate(code, seed)
        text = _text(obj)
        mistake = DERIVE[code](text)
        if mistake is None:  # this form has no such mistake (algebra_easy: a bracket form)
            continue
        checked += 1
        assert mistake in _hook_values(obj), (code, seed, text, mistake)
    assert checked >= len(SEEDS) // 3, (code, checked)
