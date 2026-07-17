"""V3 — explicit topic difficulty ladders + sibling lookup (ADR-0009).

The ladder is data, not inferred from ``cognitive.difficulty``: an edit op
("make it harder/easier") is a deterministic hop to the adjacent blueprint code.
Extend :data:`LADDERS` when a topic gains more rungs (V6 adds more topics).
"""

from __future__ import annotations

RATIO = ["ratio_easy", "ratio_medium", "ratio_hard"]
PERCENTAGE = ["percentage_easy", "percentage_medium", "percentage_hard"]
FRACTIONS = ["fractions_easy", "fractions_medium", "fractions_hard"]
SPEED = ["speed_easy", "speed_medium", "speed_hard"]
GEOMETRY_ANGLE = ["geometry_angle_easy", "geometry_angle_medium", "geometry_angle_hard"]
GEOMETRY_AREA = ["geometry_area_easy", "geometry_area_medium", "geometry_area_hard"]

# Keyed by topic; each value is the ordered list of rungs, easiest first.
LADDERS: dict[str, list[str]] = {
    "Ratio": RATIO,
    "Percentage": PERCENTAGE,
    "Fractions": FRACTIONS,
    "Speed": SPEED,
    "Geometry (Angles)": GEOMETRY_ANGLE,
    "Geometry (Area & Perimeter)": GEOMETRY_AREA,
}


def ladder_for(code: str) -> list[str] | None:
    """Return the ladder (list of codes) that contains ``code``, else ``None``."""
    for ladder in LADDERS.values():
        if code in ladder:
            return ladder
    return None


def sibling(code: str, direction: int) -> str | None:
    """Return the adjacent code on ``code``'s ladder.

    ``direction`` is ``+1`` for harder, ``-1`` for easier. Returns ``None`` at the
    ends of the ladder or when ``code`` is not on any ladder.
    """
    ladder = ladder_for(code)
    if ladder is None:
        return None
    idx = ladder.index(code) + direction
    if 0 <= idx < len(ladder):
        return ladder[idx]
    return None
