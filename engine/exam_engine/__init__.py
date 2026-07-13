"""Exam Paper Synthesis engine — the product.

Public entry point is :func:`exam_engine.pipeline.generate`. The canonical
question object (a plain dict gated by JSON Schema, ADR-0016) is the single
source of truth; everything else is a view of it.
"""

from .canonical import SCHEMA_VERSION, CanonicalValidationError
from .errors import EngineError, InfeasibleConstraints, UnknownBlueprint
from .pipeline import generate

__all__ = [
    "generate",
    "SCHEMA_VERSION",
    "CanonicalValidationError",
    "EngineError",
    "InfeasibleConstraints",
    "UnknownBlueprint",
]
