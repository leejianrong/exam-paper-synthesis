"""The one impure boundary: HTML -> PDF via headless Chromium (decision C1).

A deliberate ~15-line mirror of ``api/app/export.py::html_to_pdf`` so the CLI owns
its own PDF step and depends only on ``exam-engine`` (+ Playwright), never on the
FastAPI ``exam-api`` package. Playwright is imported *inside* the function so that
non-PDF subcommands (generate/edit/export preview) need no browser installed.
"""

from __future__ import annotations

# The renderer flags typesetting completion on the root element (see
# ``exam_engine.render``); wait for it so the PDF is taken only after KaTeX has
# finished laying out every math atom.
_KATEX_DONE_SELECTOR = "html[data-katex-rendered='true']"


def html_to_pdf(html: str) -> bytes:
    """Render a self-contained HTML document to A4 PDF bytes via headless Chromium.

    Impure: launches/tears down a browser. Waits for the KaTeX bootstrap to flag
    completion (``data-katex-rendered``) before snapshotting, and prints
    backgrounds so answer-space borders and diagram fills appear.
    """
    from playwright.sync_api import sync_playwright  # lazy: no browser for non-PDF cmds

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.wait_for_selector(_KATEX_DONE_SELECTOR, state="attached")
            return page.pdf(format="A4", print_background=True)
        finally:
            browser.close()
