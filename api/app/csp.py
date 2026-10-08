"""W5 — Content-Security-Policy for the app and the print preview it embeds.

Scripts are the part that matters: ``script-src`` is ``'self'`` plus the SHA-256 of each of the
engine's three inline print scripts (KaTeX, auto-render, bootstrap). Hashes rather than a nonce
because the SPA is a static file (no per-request HTML to stamp a nonce into) and those scripts are
identical for every document; and because the preview is a ``srcdoc``/``blob:`` document, which
*inherits* this policy — a hash lets it run exactly its own scripts and nothing else. No
``'unsafe-inline'`` and no ``'unsafe-eval'`` for scripts.

Styles keep ``'unsafe-inline'``: the print HTML carries three inline ``<style>`` blocks, TipTap and
the diagrams set ``style`` attributes, and CSS injection cannot execute code. Fonts and images
are first-party or ``data:`` (the print HTML inlines Inter and uploaded images as data URIs).
"""

from __future__ import annotations

from functools import lru_cache

from exam_engine.render import inline_script_hashes

# Paths that legitimately need more (Swagger UI loads a CDN script) and only exist in development.
EXEMPT_PATHS = frozenset({"/docs", "/redoc"})


@lru_cache(maxsize=1)
def content_security_policy() -> str:
    directives = {
        "default-src": ["'self'"],
        "script-src": ["'self'", *inline_script_hashes()],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "frame-src": ["'self'", "blob:"],
        "object-src": ["'none'"],
        "base-uri": ["'none'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'self'"],
    }
    return "; ".join(f"{name} {' '.join(sources)}" for name, sources in directives.items())
