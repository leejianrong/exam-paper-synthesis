"""V5 — pure HTML renderers for the printable worksheet + answer key (ADR-0008).

Two pure functions turn a list of canonical question objects (plain ``dict``s)
into complete, self-contained HTML documents:

* :func:`render_worksheet_html` — the student sheet (questions, ``[n]`` marks,
  blank answer spaces, inline bar-model SVGs). No answers.
* :func:`render_answer_key_html` — the same questions plus worked
  ``solution_steps``, the typed final answer, and the M/A/B ``marking_scheme``.

Both share one markup/CSS/KaTeX core, so the on-screen preview and the Chromium
PDF (KAN-147) are produced from the *same* document — "preview matches print" is
structural, not a per-change claim.

Purity (ADR-0016): no clock, no RNG, no network, no per-call disk I/O. The
vendored KaTeX + print CSS/JS are read **once at import** and cached in module
globals; every ``render_*`` call is a deterministic function of ``(title,
questions)`` — same inputs give byte-identical HTML. Diagrams are reused verbatim
from :func:`exam_engine.diagram.render_svg`; nothing is re-rendered here.

Math convention: ``\\(…\\)`` inline, ``\\[…\\]`` display; ``$`` is currency
(never a KaTeX delimiter), so dollar amounts inside math are written ``\\$``.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from . import diagram

# ---------------------------------------------------------------------------
# Vendored assets — read ONCE at import (no per-call I/O; keeps render_* pure).
# ---------------------------------------------------------------------------

_ASSETS = Path(__file__).resolve().parent / "assets"
_KATEX = _ASSETS / "katex"

# The woff/ttf fallbacks reference files we do not vendor (woff2 only); strip
# them so the emitted CSS has no dangling external refs.
_FONT_FALLBACK_RE = re.compile(r',url\(fonts/[^)]+\.(?:woff|ttf)\) format\("[^"]+"\)')
_FONT_WOFF2_RE = re.compile(r"url\(fonts/([^)]+\.woff2)\)")


def _inline_katex_css() -> str:
    """Load ``katex.min.css`` with every WOFF2 font inlined as a ``data:`` URI.

    Makes the document truly host-free: it typesets offline and inside a
    cross-origin iframe with no font requests.
    """
    css = (_KATEX / "katex.min.css").read_text(encoding="utf-8")
    css = _FONT_FALLBACK_RE.sub("", css)

    cache: dict[str, str] = {}

    def _to_data_uri(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in cache:
            raw = (_KATEX / "fonts" / name).read_bytes()
            cache[name] = base64.b64encode(raw).decode("ascii")
        return f'url(data:font/woff2;base64,{cache[name]}) format("woff2")'

    return _FONT_WOFF2_RE.sub(_to_data_uri, css)


def _read_js(name: str) -> str:
    """Read a vendored script, neutralising any ``</script>`` so it can be inlined."""
    text = (_KATEX / name).read_text(encoding="utf-8")
    return text.replace("</script>", "<\\/script>")


_KATEX_CSS = _inline_katex_css()
_PRINT_CSS = (_ASSETS / "print.css").read_text(encoding="utf-8")
_KATEX_JS = _read_js("katex.min.js")
_AUTORENDER_JS = _read_js("auto-render.min.js")

# Inline bootstrap: run KaTeX auto-render over the body once the DOM is parsed,
# then flag completion so the PDF step (KAN-147) can wait for typesetting.
_BOOTSTRAP_JS = r"""
(function () {
  function run() {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true }
      ],
      throwOnError: false
    });
    document.documentElement.setAttribute("data-katex-rendered", "true");
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
"""


# ---------------------------------------------------------------------------
# Text helpers (pure).
# ---------------------------------------------------------------------------


def _esc(text: object) -> str:
    """Minimal HTML text escaping (order-fixed, deterministic)."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# A ratio (``2 : 3`` / ``5 : 9 : 8``) and a currency amount (``$204``/``$3.50``)
# are the math atoms the ratio blueprints emit; wrap each in inline delimiters so
# KaTeX typesets them while surrounding prose stays plain text.
_RATIO_RE = re.compile(r"\d+(?:\s*:\s*\d+)+")
_MONEY_RE = re.compile(r"\$(\d+(?:\.\d+)?)")


def _mathify(text: str) -> str:
    """HTML-escape prose, then wrap math atoms in ``\\(…\\)`` (``$`` → ``\\$``)."""
    out = _esc(text)
    out = _RATIO_RE.sub(lambda m: rf"\({m.group(0)}\)", out)
    out = _MONEY_RE.sub(lambda m: rf"\(\${m.group(1)}\)", out)
    return out


def _fmt_answer(answer: dict) -> str:
    """Format the typed canonical answer as a KaTeX-delimited string."""
    atype = answer.get("type")
    if atype in ("integer", "decimal", "quantity"):
        unit = answer.get("unit") or ""
        value = answer.get("value")
        if unit == "$":
            return rf"\(\${value}\)"
        if unit:
            return rf"\({value}\ \text{{{_esc(unit)}}}\)"
        return rf"\({value}\)"
    if atype == "fraction":
        body = rf"\frac{{{answer['numerator']}}}{{{answer['denominator']}}}"
        unit = answer.get("unit") or ""
        if unit == "$":
            return rf"\(\${body}\)"
        if unit:
            return rf"\({body}\ \text{{{_esc(unit)}}}\)"
        return rf"\({body}\)"
    if atype == "ratio":
        return r"\(" + " : ".join(str(p) for p in answer.get("parts", [])) + r"\)"
    if atype == "set":
        return r"\(" + ", ".join(_esc(v) for v in answer.get("values", [])) + r"\)"
    if atype == "text":
        return _esc(answer.get("text", ""))
    return _esc(str(answer))


# ---------------------------------------------------------------------------
# Fragment builders (pure).
# ---------------------------------------------------------------------------


def _render_part_head(part: dict, *, multipart: bool) -> list[str]:
    """The ``.part`` block (optional label, text, right-aligned marks) + diagram."""
    out: list[str] = ['<div class="part">']
    if multipart and part.get("label"):
        out.append(f'<span class="part-label">({_esc(part["label"])})</span>')
    out.append(f'<div class="part-text">{_mathify(part["text"])}</div>')
    out.append(f'<span class="marks">[{part["marks"]}]</span>')
    out.append("</div>")

    spec = part.get("diagram")
    if spec is not None:
        out.append(f'<figure class="diagram">{diagram.render_svg(spec)}</figure>')
    return out


def _render_solution(part: dict) -> list[str]:
    """Answer-key-only: worked steps + final answer + M/A/B marking scheme."""
    out: list[str] = ['<div class="solution">']

    out.append('<ol class="solution-steps">')
    for step in part.get("solution_steps", []):
        out.append(f'<li class="step">{_mathify(step["text"])}</li>')
    out.append("</ol>")

    out.append(f'<p class="final-answer">Answer: {_fmt_answer(part["answer"])}</p>')

    out.append('<ul class="marking-scheme">')
    for mark in part.get("marking_scheme", []):
        mtype = mark["type"]
        out.append(
            '<li class="mark">'
            f'<span class="mark-type mark-{mtype}">{mtype}{mark["mark"]}</span>'
            f'<span class="mark-desc">{_esc(mark["description"])}</span>'
            "</li>"
        )
    out.append("</ul>")

    out.append("</div>")
    return out


def _render_questions(questions: list[dict], *, answer_key: bool) -> str:
    """The ``<ol class="questions">`` body, in the given (tray) order."""
    out: list[str] = ['<ol class="questions">']
    for obj in questions:
        parts = obj["question"]["parts"]
        multipart = len(parts) > 1
        out.append('<li class="question">')
        stem = obj["question"].get("stem")
        if stem:
            out.append(f'<p class="question-stem">{_mathify(stem)}</p>')
        for part in parts:
            out.extend(_render_part_head(part, multipart=multipart))
            if answer_key:
                out.extend(_render_solution(part))
            else:
                out.append(
                    '<div class="answer-space" aria-hidden="true" '
                    f'style="--marks:{part["marks"]}"></div>'
                )
        out.append("</li>")
    out.append("</ol>")
    return "".join(out)


def _total_marks(questions: list[dict]) -> int:
    """Sheet total = sum of each question's ``total_marks`` (settled default)."""
    return sum(obj["question"]["total_marks"] for obj in questions)


def _document(*, root_class: str, title: str, header_html: str, body_html: str) -> str:
    """Assemble the shared self-contained HTML shell around a rendered body."""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_esc(title)}</title>\n"
        f"<style>{_KATEX_CSS}</style>\n"
        f"<style>{_PRINT_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f'<main class="{root_class}">\n'
        f"{header_html}\n"
        f"{body_html}\n"
        "</main>\n"
        f"<script>{_KATEX_JS}</script>\n"
        f"<script>{_AUTORENDER_JS}</script>\n"
        f"<script>{_BOOTSTRAP_JS}</script>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def render_worksheet_html(title: str, questions: list[dict]) -> str:
    """Render the printable student worksheet as a self-contained HTML document."""
    header = (
        '<header class="sheet-header">'
        f'<h1 class="sheet-title">{_esc(title)}</h1>'
        '<p class="sheet-meta">'
        '<span class="field-name">Name: ______________</span>'
        f'<span class="field-marks">Total: {_total_marks(questions)} marks</span>'
        "</p>"
        "</header>"
    )
    body = _render_questions(questions, answer_key=False)
    return _document(root_class="sheet worksheet", title=title, header_html=header, body_html=body)


def render_answer_key_html(title: str, questions: list[dict]) -> str:
    """Render the answer key (questions + worked solutions) as self-contained HTML."""
    key_title = f"{title} — Answer Key"
    header = (
        '<header class="sheet-header">'
        f'<h1 class="sheet-title">{_esc(key_title)}</h1>'
        '<p class="sheet-meta">'
        f'<span class="field-marks">Total: {_total_marks(questions)} marks</span>'
        "</p>"
        "</header>"
    )
    body = _render_questions(questions, answer_key=True)
    return _document(
        root_class="sheet answer-key", title=key_title, header_html=header, body_html=body
    )
