"""A1 — canonical schema loading + validation.

The hand-written JSON Schema at ``schemas/canonical-question.schema.json`` is the
authoritative contract (ADR-0014/0016). This module is the only place objects are
gated. Errors are path-pointed so bad data never enters silently (R6.2).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator


def repo_root() -> Path:
    """Resolve the monorepo root.

    Override with ``EXAM_REPO_ROOT`` if the engine is ever used outside the repo.
    Layout: ``engine/exam_engine/schema.py`` → ``parents[2]`` is the repo root.
    """
    env = os.environ.get("EXAM_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def schema_path() -> Path:
    env = os.environ.get("EXAM_SCHEMA_PATH")
    if env:
        return Path(env)
    return repo_root() / "schemas" / "canonical-question.schema.json"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_object(obj: dict) -> list[str]:
    """Return a list of path-pointed error strings; empty means valid."""
    errors: list[str] = []
    for err in sorted(_validator().iter_errors(obj), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def validate_against(instance: object, subschema: dict) -> list[str]:
    """Validate an arbitrary instance against an ad-hoc subschema (e.g. a
    blueprint's declared parameter schema, ADR-0014)."""
    validator = Draft202012Validator(subschema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors
