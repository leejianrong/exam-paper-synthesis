"""A2 — blueprint content loader + solver registry."""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import yaml

from ..errors import UnknownBlueprint
from ..schema import repo_root
from .base import BlueprintSpec, Solver

_SOLVERS: dict[str, Solver] = {}


def content_dir() -> Path:
    env = os.environ.get("EXAM_CONTENT_DIR")
    if env:
        return Path(env)
    return repo_root() / "content"


def register(code: str, solver: Solver) -> None:
    _SOLVERS[code] = solver


def _ensure_solvers_loaded() -> None:
    if not _SOLVERS:
        # Importing the package triggers each solver module's register() call.
        from . import solvers  # noqa: F401


def get_solver(code: str) -> Solver:
    _ensure_solvers_loaded()
    try:
        return _SOLVERS[code]
    except KeyError:
        raise UnknownBlueprint(code) from None


@cache
def load_blueprint(code: str) -> BlueprintSpec:
    path = content_dir() / "blueprints" / f"{code}.yaml"
    if not path.exists():
        raise UnknownBlueprint(code)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("code") != code:
        raise UnknownBlueprint(code)
    return BlueprintSpec.from_dict(data)
