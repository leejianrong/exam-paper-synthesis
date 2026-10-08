"""V5 — the impure HTML -> PDF boundary (ADR-0008).

This is the ONE place a browser (headless Chromium via Playwright) is used. The
engine renderers produce a complete, self-contained HTML document whose inlined
bootstrap runs KaTeX auto-render and, when done, sets
``document.documentElement[data-katex-rendered="true"]`` (see
``engine/exam_engine/render.py``). We wait for that flag before snapshotting so
the PDF captures fully typeset math.
"""

from __future__ import annotations

import os

from exam_engine.render import font_css
from playwright.sync_api import sync_playwright

# The renderer flags typesetting completion on the root element; wait for it so
# the PDF is taken only after KaTeX has finished laying out every math atom.
_KATEX_DONE_SELECTOR = "html[data-katex-rendered='true']"


def _timeout_ms() -> int:
    """Per-operation browser timeout (a stuck render must free its slot, W4)."""
    try:
        return max(1000, int(os.environ.get("EXAM_EXPORT_TIMEOUT_MS", "30000")))
    except ValueError:
        return 30000


def _launch_args() -> list[str]:
    """Chromium's sandbox needs user namespaces most container hosts do not grant; the
    container image sets ``EXAM_CHROMIUM_NO_SANDBOX=1``. The only HTML rendered is the
    engine's own, with user text escaped and no remote content."""
    return ["--no-sandbox"] if os.environ.get("EXAM_CHROMIUM_NO_SANDBOX") == "1" else []


def html_to_pdf(html: str) -> bytes:
    """Render a self-contained HTML document to A4 PDF bytes via headless Chromium.

    Impure: launches/tears down a browser. Waits for the KaTeX bootstrap to flag
    completion (``data-katex-rendered``) before snapshotting, and prints
    backgrounds so answer-space borders and diagram fills appear.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(args=_launch_args())
        try:
            page = browser.new_page()
            page.set_default_timeout(_timeout_ms())
            page.set_content(html, wait_until="load")
            page.wait_for_selector(_KATEX_DONE_SELECTOR, state="attached")
            return page.pdf(format="A4", print_background=True)
        finally:
            browser.close()


def html_to_png_many(svgs: list[str], *, scale: int = 2) -> list[bytes | None]:
    """Rasterise each SVG string to PNG bytes via headless Chromium (W2c).

    One browser for the whole batch; ``None`` for any figure that fails to render, so one bad
    diagram never loses the others. White background (print), ``scale``x for crisp edges.
    """
    out: list[bytes | None] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=_launch_args())
        try:
            page = browser.new_page(device_scale_factor=scale)
            page.set_default_timeout(_timeout_ms())
            for svg in svgs:
                try:
                    page.set_content(
                        f"<style>{font_css()}</style>"
                        f'<body style="margin:0;background:#fff;display:inline-block">{svg}</body>',
                        wait_until="load",
                    )
                    out.append(page.locator("svg").first.screenshot(type="png"))
                except Exception:
                    out.append(None)
        finally:
            browser.close()
    return out
