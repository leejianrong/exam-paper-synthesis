"""Pydantic envelopes for the API boundary only (ADR-0016).

These wrap canonical objects (plain dicts, jsonschema-gated in the engine); they
do not re-describe the canonical schema.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    blueprint_code: str = "ratio_medium"
    seed: int | None = None
    count: int = Field(default=1, ge=1, le=50)


class GenerateResponse(BaseModel):
    questions: list[dict]


class EditRequest(BaseModel):
    question: dict
    seed: int | None = None
    # Only for `set-cosmetic` (W1a): {param: new value(s)}, e.g. {"names": ["Ann", "Ben"]}.
    changes: dict | None = None


class EditResponse(BaseModel):
    question: dict


class ExportRequest(BaseModel):
    title: str = "worksheet"
    questions: list[dict]


class CreateDocumentRequest(BaseModel):
    title: str | None = None
    # P8a: start from a paper template (its sections and time, no questions).
    template: str | None = None
    # O2: file the new paper in one of the caller's folders (404 if foreign or unknown).
    folder_id: str | None = None


class GeneratePaperRequest(BaseModel):
    """P8a: fill a paper template's slots from the blueprints (one paper per call)."""

    template: str
    level: Literal["P5", "P6"] = "P6"
    seed: int | None = Field(default=None, ge=1, lt=2**31)
    folder_id: str | None = None  # O2


class SwapQuestionRequest(BaseModel):
    """P8d: replace one question of a paper (another like this / another topic / my own)."""

    block_id: str = Field(min_length=1, max_length=64)
    mode: Literal["like", "topic", "own"]
    base_version: int
    level: Literal["P5", "P6"] | None = None  # None = the paper's own (cover, else questions)
    seed: int | None = Field(default=None, ge=1, lt=2**31)


class RegeneratePaperRequest(BaseModel):
    """P8d: refill every unlocked generated question and empty placeholder."""

    base_version: int
    level: Literal["P5", "P6"] | None = None
    seed: int | None = Field(default=None, ge=1, lt=2**31)


class SaveDocumentRequest(BaseModel):
    document: dict
    base_version: int


class RenderQuestionRequest(BaseModel):
    question: dict
    mode: Literal["student", "key"] = "student"
    number: int | None = None
    placement: Literal["question", "answer", "both"] | None = None
    answer_area: bool = True


class RenderDiagramRequest(BaseModel):
    diagram: dict


class ConvertFreeformRequest(BaseModel):
    question: dict


class BankReviewRequest(BaseModel):
    reviewed: bool


class BankImportRequest(BaseModel):
    objects: list[Any]  # per-item validation happens in the route, so one bad item is reported
    replace: bool = False


class FolderRequest(BaseModel):
    """O2: create or rename a folder. The store trims and checks 1-80 characters."""

    name: str = Field(max_length=1000)


class MoveDocumentRequest(BaseModel):
    """O2: file a paper in a folder, or ``null`` to unfile it (not an edit: no new version)."""

    folder_id: str | None
