"""Solver plugins. Importing this package registers every solver."""

from . import (
    fractions_easy,  # noqa: F401
    fractions_hard,  # noqa: F401
    fractions_medium,  # noqa: F401
    percentage_easy,  # noqa: F401
    percentage_hard,  # noqa: F401
    percentage_medium,  # noqa: F401
    ratio_easy,  # noqa: F401
    ratio_hard,  # noqa: F401
    ratio_medium,  # noqa: F401
    speed_easy,  # noqa: F401
    speed_hard,  # noqa: F401
    speed_medium,  # noqa: F401
)

__all__ = [
    "fractions_easy",
    "fractions_hard",
    "fractions_medium",
    "percentage_easy",
    "percentage_hard",
    "percentage_medium",
    "ratio_easy",
    "ratio_hard",
    "ratio_medium",
    "speed_easy",
    "speed_hard",
    "speed_medium",
]
