"""Shared helpers for the ``geometry_area_*`` ladder (KAN-230).

The maths of the area/perimeter/shaded/inverse-length templates lives in the
three rung solvers; this module holds only the pieces they all share:

* ``_pt`` / ``_labels`` — tiny figure-spec builders (mirrors the angle ladder).
* **π auto-selection (G4)** — ``pi_str_for`` picks ``22/7`` when the radius is a
  multiple of 7 (so the exact answer stays a whole number), else ``3.14``;
  ``pi_value`` returns that π as an exact :class:`~fractions.Fraction`.
* **answer formatting** — ``format_measure`` turns an exact ``Fraction`` measure
  into a canonical answer object: an ``integer`` when the value is whole (the
  22/7 path, by construction), else a 2-dp ``decimal`` (the 3.14 path). Radii are
  chosen upstream so the 3.14 value terminates at 2 dp, so the conversion is
  exact — no floating-point rounding enters the printed key.

All arithmetic is exact rational (``Fraction``) — mathematical truth is the
deterministic solver, so the printed answer is provably the figure's solution.
"""

from __future__ import annotations

from fractions import Fraction

AREA_UNIT = "cm^2"
LEN_UNIT = "cm"


def _pt(pid: str, x: float, y: float) -> dict:
    return {"id": pid, "x": float(x), "y": float(y)}


def _labels(point_ids: list[str]) -> list[dict]:
    return [{"at": pid, "text": pid} for pid in point_ids]


def pi_str_for(r: int) -> str:
    """π auto-select (G4): ``22/7`` when ``r`` is a multiple of 7, else ``3.14``."""
    return "22/7" if r % 7 == 0 else "3.14"


def pi_value(pi_str: str) -> Fraction:
    """The exact rational value of the printed π string."""
    return Fraction(22, 7) if pi_str == "22/7" else Fraction(314, 100)


def format_measure(exact: Fraction, unit: str) -> dict:
    """Exact measure → canonical answer: whole → integer, else a 2-dp decimal.

    ``exact`` must be a value that either is whole or terminates at 2 dp (the
    samplers guarantee this by construction — 22/7 with a multiple-of-7 radius is
    whole; 3.14 yields hundredths). The assertion makes a violated assumption a
    loud engine bug rather than a silently mis-rounded key.
    """
    if exact.denominator == 1:
        return {"type": "integer", "value": int(exact), "unit": unit}
    cents = exact * 100
    assert cents.denominator == 1, f"non-2dp measure {exact}"
    return {"type": "decimal", "value": int(cents) / 100, "dp": 2, "unit": unit}
