"""mathgen — a headless CLI that drives the exam engine directly (KAN-152, V7).

No web, no API server: the tool imports :mod:`exam_engine` and nothing from the
FastAPI layer. This is the engine-agnostic proof — the same deterministic engine
that powers the HTTP API also powers a plain command line. The one impurity, the
headless-Chromium HTML->PDF step needed by ``export``, lives in this package's own
:mod:`mathgen._pdf` (a small mirror of ``api/app/export.py``), lazy-importing
Playwright so non-PDF subcommands need no browser (decision C1).
"""
