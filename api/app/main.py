"""A9 — FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
