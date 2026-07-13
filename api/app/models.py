"""Pydantic envelopes for the API boundary only (ADR-0016).

These wrap canonical objects (plain dicts, jsonschema-gated in the engine); they
do not re-describe the canonical schema.
"""

from __future__ import annotations

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


class EditResponse(BaseModel):
    question: dict


class ExportRequest(BaseModel):
    title: str = "worksheet"
    questions: list[dict]
