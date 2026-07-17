"""Solver plugins. Importing this package registers every solver."""

from . import (
    percentage_easy,  # noqa: F401
    percentage_hard,  # noqa: F401
    percentage_medium,  # noqa: F401
    ratio_easy,  # noqa: F401
    ratio_hard,  # noqa: F401
    ratio_medium,  # noqa: F401
)

__all__ = [
    "percentage_easy",
    "percentage_hard",
    "percentage_medium",
    "ratio_easy",
    "ratio_hard",
    "ratio_medium",
]
