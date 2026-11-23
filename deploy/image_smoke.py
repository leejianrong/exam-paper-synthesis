"""Smoke test for the production image (EXA-179): the browser the image ships can print a paper.

Run inside the image, where the API is installed (the script is piped in; it is not in the image):
    docker run --rm -i <image> uv run --no-sync python - < deploy/image_smoke.py
Pass a directory (``python - /out``) to also write the PDFs there, e.g. to compare two builds.

Generates Paper 2 (P6, seed 7), renders the student paper and the key through the same
``html_to_pdf`` the export endpoints use, and checks each is a multi-page PDF. A missing system
library or browser build fails here instead of on a teacher's first export.
"""

import sys
from pathlib import Path

sys.path.insert(0, "api")

from app.export import html_to_pdf  # noqa: E402
from exam_engine.paper import generate_paper  # noqa: E402
from exam_engine.render import render_document_html  # noqa: E402


def main() -> None:
    doc, _ = generate_paper("p2", "P6", 7)
    for mode in ("student", "key"):
        pdf = html_to_pdf(render_document_html("Smoke test", doc, mode=mode))
        pages = pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")
        assert pdf.startswith(b"%PDF") and pages >= 2, f"{mode}: {len(pdf)} bytes, {pages} pages"
        if len(sys.argv) > 1:
            Path(sys.argv[1], f"{mode}.pdf").write_bytes(pdf)
        print(f"{mode}: {pages} pages, {len(pdf)} bytes")


if __name__ == "__main__":
    main()
