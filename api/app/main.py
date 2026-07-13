"""A9 — FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_edit import router as edit_router
from .routes_export import router as export_router
from .routes_generate import router

app = FastAPI(title="Exam Paper Synthesis API", version="0.1.0")

# Dev SPA (Vite) runs on a different origin; allow it (single-user, no auth).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(edit_router)
app.include_router(export_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
