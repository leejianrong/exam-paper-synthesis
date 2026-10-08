"""V5 — the impure HTML -> PDF boundary (ADR-0008).

This is the ONE place a browser (headless Chromium via Playwright) is used. The
engine renderers produce a complete, self-contained HTML document whose inlined
bootstrap runs KaTeX auto-render and, when done, sets
``document.documentElement[data-katex-rendered="true"]`` (see
``engine/exam_engine/render.py``). We wait for that flag before snapshotting so
the PDF captures fully typeset math.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

# The renderer flags typesetting completion on the root element; wait for it so
# the PDF is taken only after KaTeX has finished laying out every math atom.
_KATEX_DONE_SELECTOR = "html[data-katex-rendered='true']"


def html_to_pdf(html: str) -> bytes:
    """Render a self-contained HTML document to A4 PDF bytes via headless Chromium.

    Impure: launches/tears down a browser. Waits for the KaTeX bootstrap to flag
    completion (``data-katex-rendered``) before snapshotting, and prints
    backgrounds so answer-space borders and diagram fills appear.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
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
        browser = p.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=scale)
            for svg in svgs:
                try:
                    page.set_content(
                        f'<body style="margin:0;background:#fff;display:inline-block">{svg}</body>',
                        wait_until="load",
                    )
                    out.append(page.locator("svg").first.screenshot(type="png"))
                except Exception:
                    out.append(None)
        finally:
            browser.close()
    return out
