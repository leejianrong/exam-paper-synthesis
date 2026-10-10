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


class SaveDocumentRequest(BaseModel):
    document: dict
    base_version: int


class RenderQuestionRequest(BaseModel):
    question: dict
    mode: Literal["student", "key"] = "student"
    number: int | None = None


class RenderDiagramRequest(BaseModel):
    diagram: dict


class ConvertFreeformRequest(BaseModel):
    question: dict


class BankReviewRequest(BaseModel):
    reviewed: bool


class BankImportRequest(BaseModel):
    objects: list[Any]  # per-item validation happens in the route, so one bad item is reported
    replace: bool = False
