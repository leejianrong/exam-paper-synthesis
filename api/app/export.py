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
