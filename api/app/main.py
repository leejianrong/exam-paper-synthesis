"""A9 — FastAPI app entry point."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from . import config
from .csp import EXEMPT_PATHS, content_security_policy
from .routes_account import router as account_router
from .routes_assets import router as assets_router
from .routes_auth import router as auth_router
from .routes_bank import router as bank_router
from .routes_convert import router as convert_router
from .routes_documents import router as documents_router
from .routes_edit import router as edit_router
from .routes_export import router as export_router
from .routes_generate import router
from .routes_render import router as render_router


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    config.check_production()  # refuse to boot on an unsafe production configuration
    yield


app = FastAPI(
    title="Exam Paper Synthesis API",
    version="0.1.0",
    lifespan=_lifespan,
    # The interactive docs are for development; production does not advertise its surface.
    docs_url=None if config.is_production() else "/docs",
    redoc_url=None,
    openapi_url=None if config.is_production() else "/openapi.json",
)


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


@app.middleware("http")
async def _security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # The editor's print preview is a same-origin iframe; nothing else may frame the app.
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    if request.url.path not in EXEMPT_PATHS:
        response.headers.setdefault("Content-Security-Policy", content_security_policy())
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if os.environ.get("EXAM_PUBLIC_URL", "").startswith("https://"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


app.include_router(router)
app.include_router(auth_router)
app.include_router(account_router)
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


@app.get("/ready")
def ready() -> dict:
    """Readiness: the database answers (liveness is ``/health``, which never touches it)."""
    from . import pgstores

    if url := pgstores.database_url():
        try:
            with pgstores.get_database(url).connection() as conn:
                conn.execute("SELECT 1")
        except Exception:
            raise HTTPException(status_code=503, detail="database unavailable") from None
    return {"status": "ready"}


def mount_web(target: FastAPI, dist: Path | None = None) -> bool:
    """Serve the built web app from the API (one origin in production: first-party cookies,
    no CORS). Mounted last so every API route wins. Returns whether a build was found."""
    directory = dist or (
        Path(os.environ["EXAM_WEB_DIST"]) if os.environ.get("EXAM_WEB_DIST") else None
    )
    if directory is None or not (directory / "index.html").is_file():
        return False
    target.mount("/", StaticFiles(directory=directory, html=True), name="web")
    return True


mount_web(app)
