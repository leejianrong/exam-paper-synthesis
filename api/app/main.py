"""A9 — FastAPI app entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_assets import router as assets_router
from .routes_auth import router as auth_router
from .routes_bank import router as bank_router
from .routes_convert import router as convert_router
from .routes_documents import router as documents_router
from .routes_edit import router as edit_router
from .routes_export import router as export_router
from .routes_generate import router
from .routes_render import router as render_router

app = FastAPI(title="Exam Paper Synthesis API", version="0.1.0")


# The SPA is a different origin (Vite on :5173 in dev), so CORS must name it and allow the
# session cookie. Origins: EXAM_CORS_ORIGINS (comma-separated), defaulting to EXAM_WEB_URL.
def _cors_origins() -> list[str]:
    raw = os.environ.get("EXAM_CORS_ORIGINS") or os.environ.get(
        "EXAM_WEB_URL", "http://localhost:5173"
    )
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(edit_router)
app.include_router(export_router)
app.include_router(documents_router)
app.include_router(bank_router)
app.include_router(assets_router)
app.include_router(convert_router)
app.include_router(render_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
