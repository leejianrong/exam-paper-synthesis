"""EXA-130 — every glyph a paper prints comes from the embedded faces: Inter for text (with
one-glyph Inter faces for ℓ and π, and KaTeX_Main's ∠) and KaTeX's own fonts for maths. Before
this, every KaTeX @font-face had `format("woff2")` twice, the browser dropped the src, and all
maths printed in the host's Times; ∠ and π fell back to whatever Noto the host had."""

from __future__ import annotations

import re

import pytest
from exam_engine import render
from exam_engine.pipeline import generate

FACE = re.compile(r"@font-face\{[^}]*\}")
SRC = re.compile(r'src:url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\) format\("woff2"\)[;}]')


def test_every_katex_font_face_has_one_valid_src():
    faces = FACE.findall(render._KATEX_CSS)
    assert len(faces) == 20
    for face in faces:
        assert 'format("woff2") format("woff2")' not in face
        assert len(SRC.findall(face)) == 1, face[:160]
        assert "url(fonts/" not in face  # every font inlined, no dangling relative refs


def test_the_text_faces_cover_the_symbols_papers_print():
    css = render.font_css()
    for rng in ("U+2113", "U+03C0", "U+2220,U+2225"):
        assert css.count(f"unicode-range:{rng};") == 4  # one per weight/style
    for face in FACE.findall(css):
        assert len(SRC.findall(face)) == 1


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_available(), reason="headless Chromium not installed")
def test_a_real_pdf_embeds_only_inter_and_katex_fonts():
    """Print a fraction, algebra, ∠ (geometry angles), π (circles) and ℓ (volume) through
    real Chromium: the PDF may embed Inter and KaTeX faces only — no host fallback fonts."""
    from app.export import html_to_pdf

    questions = [
        generate("fractions_medium", 3),
        generate("algebra_easy", 1),
        generate("geometry_angle_medium", 2),
        *[generate("geometry_angle_hard", s) for s in range(6)],  # "AD ∥ BC" in the steps
        generate("geometry_area_hard", 3),
        generate("volume_medium", 4),
    ]
    html = render.render_answer_key_html("Fonts", questions)
    for symbol in ("∠", "∥", "π", "ℓ"):
        assert symbol in html, symbol
    pdf = html_to_pdf(html)
    fonts = set(re.findall(rb"/BaseFont\s*/[A-Z]{6}\+([A-Za-z0-9_-]+)", pdf))
    assert fonts, "no embedded fonts found"
    others = {f for f in fonts if not (f.startswith(b"Inter") or f.startswith(b"KaTeX"))}
    assert not others, f"fell back to host fonts: {sorted(others)}"
    assert any(f.startswith(b"KaTeX") for f in fonts)  # the maths really is in KaTeX's face
