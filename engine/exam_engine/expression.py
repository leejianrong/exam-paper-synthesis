"""T5 — the ``expression`` answer (schema 1.11.0): answers "in terms of π / n".

A *collected* sum of terms ``coefficient * symbol^power`` (symbol ``null`` = the
constant), so ``(42π + 42) m`` and ``$17n`` are structured data, not free text.
Two equal expressions have one representation (like terms collected, a fixed term
order), which is what makes them comparable.

* :func:`check_expression_consistency` — the load-gate checks.
* :func:`to_latex` — the print form (KaTeX), unit included.
* :func:`evaluate` / :func:`expressions_equal` — for solvers and invariant tests.

Limit (deliberate): one symbol per term, so ``πr²`` is not expressible, but
``42π`` and ``2n + 3`` are. No FastAPI/Pydantic (ADR-0016).
"""

from __future__ import annotations

import math
import re
from fractions import Fraction

_SYMBOL = re.compile(r"^(π|[A-Za-z])$")
_MAX = 1_000_000


def _is_num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) <= _MAX


def _order_key(term: dict) -> tuple:
    sym = term.get("symbol")
    return (sym is None, -(term.get("power") or 1), sym or "")


def check_expression_consistency(answer: dict) -> dict[str, bool]:
    terms = answer.get("terms") or []
    coeffs = [t.get("coefficient") for t in terms]
    syms = [t.get("symbol") for t in terms]
    keys = [(t.get("symbol"), (t.get("power") or 1) if t.get("symbol") else 0) for t in terms]
    return {
        "has_terms": len(terms) >= 1,
        "coefficients_finite_nonzero": all(_is_num(c) and c != 0 for c in coeffs),
        "coefficients_print_exactly": all(
            _is_num(c) and abs(round(c, 3) - c) < 1e-9 for c in coeffs
        ),
        "symbols_valid": all(s is None or bool(_SYMBOL.match(str(s))) for s in syms),
        "constant_has_no_power": all(t.get("symbol") or (t.get("power") or 1) == 1 for t in terms),
        "like_terms_collected": len(set(keys)) == len(keys),
        "terms_in_canonical_order": [_order_key(t) for t in terms]
        == sorted(_order_key(t) for t in terms),
    }


def _num(c: float) -> str:
    s = f"{abs(c):.3f}".rstrip("0").rstrip(".")
    return s


def _term_latex(term: dict, *, first: bool) -> str:
    c = term["coefficient"]
    sym, power = term.get("symbol"), term.get("power") or 1
    sign = "-" if c < 0 else ("" if first else "+")
    mag = _num(c)
    if sym is None:
        body = mag
    else:
        body = (mag if mag != "1" else "") + ("\\pi" if sym == "π" else sym)
        if power != 1:
            body += f"^{{{power}}}"
    if first:
        return f"{sign}{body}"
    return f"{sign or '+'} {body}" if sign != "-" else f"- {body}"


def to_latex(answer: dict) -> str:
    """KaTeX source for the answer, unit included: ``42\\pi + 84\\ \\text{m}``,
    ``\\$17n``, ``(2n + 3)\\ \\text{cm}``."""
    terms = answer["terms"]
    parts = [_term_latex(t, first=i == 0) for i, t in enumerate(terms)]
    body = " ".join(parts)
    unit = answer.get("unit") or ""
    if unit == "$":
        return rf"\${'(' + body + ')' if len(terms) > 1 else body}"
    if unit == "%":
        return rf"{'(' + body + ')' if len(terms) > 1 else body}\%"
    if unit:
        shown = rf"\left({body}\right)" if len(terms) > 1 else body
        return rf"{shown}\ \text{{{unit}}}"
    return body


def evaluate(answer: dict, values: dict[str, float] | None = None) -> float:
    """Numeric value; ``π`` is ``math.pi`` unless overridden, other symbols come from
    ``values``."""
    env = {"π": math.pi, **(values or {})}
    total = 0.0
    for t in answer["terms"]:
        sym = t.get("symbol")
        total += t["coefficient"] * (1.0 if sym is None else env[sym] ** (t.get("power") or 1))
    return total


def expressions_equal(a: dict, b: dict) -> bool:
    """Same collected expression (exact, via rationals), regardless of term order."""

    def norm(ans: dict) -> dict:
        out: dict = {}
        for t in ans["terms"]:
            key = (t.get("symbol"), (t.get("power") or 1) if t.get("symbol") else 0)
            out[key] = out.get(key, Fraction(0)) + Fraction(str(t["coefficient"]))
        return {k: v for k, v in out.items() if v != 0}

    return norm(a) == norm(b) and (a.get("unit") or "") == (b.get("unit") or "")
