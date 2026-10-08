"""W1d — the owner's question bank for the editor's "From my bank" tab.

Read-only here: content gets in through ``mathgen bank import`` (an in-editor import screen
is deferred to W2). Every query is scoped to the authenticated owner (ADR-0022), so sourced
and hand-authored questions never leak between teachers.
"""

from __future__ import annotations

from contextlib import closing
from typing import Annotated

from exam_engine.bank import open_bank
from fastapi import APIRouter, Depends

from .auth import current_owner

router = APIRouter()

Owner = Annotated[str, Depends(current_owner)]


@router.get("/bank")
def list_bank(
    owner: Owner,
    topic: str | None = None,
    level: str | None = None,
    difficulty: str | None = None,
    source_type: str | None = None,
    reviewed: bool | None = None,
) -> dict:
    """The owner's bank questions, oldest first, optionally filtered."""
    with closing(open_bank(owner_id=owner)) as bank:
        objects = bank.search(
            topic=topic,
            level=level,
            difficulty=difficulty,
            source_type=source_type,
            reviewed=reviewed,
        )
    return {
        "items": [
            {
                "id": obj["id"],
                "topic": obj.get("syllabus", {}).get("topic"),
                "level": obj.get("syllabus", {}).get("level"),
                "difficulty": obj.get("cognitive", {}).get("difficulty"),
                "source_type": obj["source_type"],
                "reviewed": bool(obj.get("validation", {}).get("checks", {}).get("human_reviewed")),
                "question": obj,
            }
            for obj in objects
        ]
    }
