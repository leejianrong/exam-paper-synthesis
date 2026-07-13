"""Solver plugins. Importing this package registers every solver."""

from . import (
    ratio_easy,  # noqa: F401
    ratio_hard,  # noqa: F401
    ratio_medium,  # noqa: F401
)

__all__ = ["ratio_easy", "ratio_hard", "ratio_medium"]
