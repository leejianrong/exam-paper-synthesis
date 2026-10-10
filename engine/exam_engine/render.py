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
import hashlib
import html
import re
from collections.abc import Callable
from pathlib import Path

from . import diagram, expression

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


def _inline_font_css() -> str:
    """The one typeface (Inter, OFL) as ``@font-face`` rules with WOFF2 inlined as data URIs.

    Documents are self-contained, so the PDF and the print preview use exactly the font the
    editor does (EXA-94) with no font request and no dependence on the host's installed fonts.
    """
    faces = []
    for weight, style in ((400, "normal"), (400, "italic"), (600, "normal"), (700, "normal")):
        raw = (_ASSETS / "fonts" / f"inter-latin-{weight}-{style}.woff2").read_bytes()
        faces.append(
            '@font-face{font-family:"Inter";'
            f"font-style:{style};font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{base64.b64encode(raw).decode('ascii')}) "
            'format("woff2")}'
        )
    return "\n".join(faces)


_FONT_CSS = _inline_font_css()
_KATEX_CSS = _inline_katex_css()


def font_css() -> str:
    """``@font-face`` rules for the document typeface (for pages the API assembles itself)."""
    return _FONT_CSS


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


def _mathify(text: str) -> str:
    """HTML-escape prose. Authored ``\\(…\\)`` math passes through for KaTeX; ratios and money
    stay plain text so the page keeps one typeface (EXA-94) — only real maths is typeset."""
    return _esc(text)


def _fmt_answer(answer: dict) -> str:
    """Format the typed canonical answer: plain text, except a fraction (KaTeX-delimited)."""
    atype = answer.get("type")
    if atype in ("integer", "decimal", "quantity"):
        unit = answer.get("unit") or ""
        value = answer.get("value")
        if unit == "$":
            # Money renders at exactly 2 dp when it is a decimal amount
            # (change-to-decimals, KAN-309); integer money keeps its whole form.
            shown = f"{value:.2f}" if atype == "decimal" else value
            return f"${shown}"
        if unit == "%":
            return f"{value}%"
        return f"{value} {_esc(unit)}" if unit else f"{value}"
    if atype == "fraction":
        body = rf"\frac{{{answer['numerator']}}}{{{answer['denominator']}}}"
        unit = answer.get("unit") or ""
        if unit == "$":
            return rf"\(\${body}\)"
        if unit:
            return rf"\({body}\ {expression.unit_latex(_esc(unit))}\)"
        return rf"\({body}\)"
    if atype == "expression":
        return rf"\({expression.to_latex(answer)}\)"
    if atype == "ratio":
        return " : ".join(str(p) for p in answer.get("parts", []))
    if atype == "set":
        return ", ".join(_esc(v) for v in answer.get("values", []))
    if atype == "text":
        return _esc(answer.get("text", ""))
    if atype == "choice":
        correct = answer.get("correct")
        opt = next((o for o in answer.get("options", []) if o.get("label") == correct), None)
        label = _esc(correct)
        if opt and opt.get("text"):
            return f"({label}) {_mathify(opt['text'])}"
        return f"({label})"
    return _esc(str(answer))


def _render_options(answer: dict, *, reveal_correct: bool) -> list[str]:
    """The ``<ol class="options">`` block for an MCQ ``answer`` (A3).

    Options are question content (the choices themselves) — rendered on both the
    worksheet and the answer key. Only which one is ``correct`` is secret, so
    ``reveal_correct`` (the answer-key branch) is the sole gate on the
    ``option-correct`` class.
    """
    correct = answer.get("correct")
    out: list[str] = ['<ol class="options">']
    for opt in answer.get("options", []):
        is_correct = reveal_correct and opt.get("label") == correct
        cls = "option option-correct" if is_correct else "option"
        out.append(f'<li class="{cls}">')
        out.append(f'<span class="option-label">({_esc(opt["label"])})</span>')
        if opt.get("text"):
            out.append(f'<span class="option-text">{_mathify(opt["text"])}</span>')
        if opt.get("diagram"):
            out.append(f'<figure class="diagram">{diagram.render_svg(opt["diagram"])}</figure>')
        out.append("</li>")
    out.append("</ol>")
    return out


# ---------------------------------------------------------------------------
# Fragment builders (pure).
# ---------------------------------------------------------------------------


def _render_part_head(part: dict, *, multipart: bool, answer_key: bool) -> list[str]:
    """The ``.part`` block (optional label, text, right-aligned marks) + diagram.

    ``marks`` is optional (A5): the ``[n]`` bracket is emitted only when present,
    never fabricated. ``answer_key`` gates whether an MCQ's ``options`` (A3)
    reveal the ``correct`` one.
    """
    out: list[str] = ['<div class="part">']
    if multipart and part.get("label"):
        out.append(f'<span class="part-label">({_esc(part["label"])})</span>')
    out.append(f'<div class="part-text">{_mathify(part["text"])}</div>')
    marks = part.get("marks")
    if marks is not None:
        out.append(f'<span class="marks">[{marks}]</span>')
    out.append("</div>")

    answer = part.get("answer") or {}
    if answer.get("type") == "choice":
        out.extend(_render_options(answer, reveal_correct=answer_key))

    spec = part.get("diagram")
    if spec is not None:
        out.append(f'<figure class="diagram">{diagram.render_svg(spec)}</figure>')
    return out


def _render_solution(part: dict, q_diagram: dict | None = None) -> list[str]:
    """Answer-key-only: worked steps + final answer + M/A/B marking scheme."""
    out: list[str] = ['<div class="solution">']

    out.append('<ol class="solution-steps">')
    for step in part.get("solution_steps", []):
        out.append(f'<li class="step">{_mathify(step["text"])}</li>')
    out.append("</ol>")

    answer = part["answer"]
    if answer["type"] == "construction":
        # The answer *is* a figure: draw the completed construction.
        # Anything the student had to add is drawn in the answer accent.
        svg = diagram.render_svg(answer["diagram"], given=part.get("diagram") or q_diagram)
        out.append(f'<figure class="diagram answer-diagram">{svg}</figure>')
    else:
        out.append(f'<p class="final-answer">Answer: {_fmt_answer(answer)}</p>')

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


def _render_table_cell(cell: object, parts: list[dict], *, answer_key: bool) -> str:
    if isinstance(cell, dict):  # {"answer_for": part.label}
        if not answer_key:
            return '<span class="table-blank" aria-hidden="true"></span>'
        part = next((p for p in parts if p["label"] == cell["answer_for"]), None)
        return _fmt_answer(part["answer"]) if part else ""
    if cell is None:
        return ""
    return _mathify(str(cell))


def _render_table(table: dict, parts: list[dict], *, answer_key: bool) -> str:
    """A real ``<table>``; ``answer_for`` cells are blank on the worksheet and
    filled with the bound part's answer in the answer key (A6)."""
    out = ['<table class="content-table">']
    if table.get("caption"):
        out.append(f"<caption>{_mathify(table['caption'])}</caption>")
    headers = table.get("headers")
    if headers:
        cells = "".join(f"<th>{_mathify(str(h)) if h is not None else ''}</th>" for h in headers)
        out.append(f"<thead><tr>{cells}</tr></thead>")
    out.append("<tbody>")
    for row in table["rows"]:
        cells = "".join(
            f"<td>{_render_table_cell(c, parts, answer_key=answer_key)}</td>" for c in row
        )
        out.append(f"<tr>{cells}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _render_question_item(obj: dict, *, answer_key: bool, tag: str = "li") -> list[str]:
    """One question's markup (stem, shared figure/table, parts, answer space or solution).

    ``tag`` is ``li`` inside a flat ``<ol class="questions">`` list, or ``section`` when a
    document interleaves questions with rich text (numbering is a CSS counter either way).
    """
    out: list[str] = []
    parts = obj["question"]["parts"]
    multipart = len(parts) > 1
    out.append(f'<{tag} class="question">')
    stem = obj["question"].get("stem")
    if stem:
        out.append(f'<p class="question-stem">{_mathify(stem)}</p>')
    q_diagram = obj["question"].get("diagram")
    if q_diagram is not None:
        out.append(f'<figure class="diagram">{diagram.render_svg(q_diagram)}</figure>')
    q_table = obj["question"].get("table")
    if q_table is not None:
        out.append(_render_table(q_table, parts, answer_key=answer_key))
    for part in parts:
        out.extend(_render_part_head(part, multipart=multipart, answer_key=answer_key))
        if answer_key:
            out.extend(_render_solution(part, q_diagram))
        elif (part.get("answer") or {}).get("type") != "choice":
            # MCQ parts have nothing to hand-write beyond circling a letter
            # (the options themselves were already rendered by
            # _render_part_head) — only constructed-response parts get a
            # blank answer-space filler.
            out.append(
                '<div class="answer-space" aria-hidden="true" '
                f'style="--marks:{part.get("marks", 1)}"></div>'
            )
    out.append(f"</{tag}>")
    return out


def _render_questions(questions: list[dict], *, answer_key: bool) -> str:
    """The ``<ol class="questions">`` body, in the given (tray) order."""
    out: list[str] = ['<ol class="questions">']
    for obj in questions:
        out.extend(_render_question_item(obj, answer_key=answer_key))
    out.append("</ol>")
    return "".join(out)


def _total_marks(questions: list[dict]) -> int:
    """Sheet total = sum of each question's ``total_marks`` (settled default)."""
    return sum(obj["question"]["total_marks"] for obj in questions)


def inline_script_hashes() -> list[str]:
    """CSP ``'sha256-…'`` source expressions for every inline ``<script>`` the print HTML carries.

    The three scripts (KaTeX, auto-render, the bootstrap) are static per engine release, so a host
    page that embeds the print document (the editor's preview iframe inherits its parent's policy)
    can allow exactly these by hash instead of ``'unsafe-inline'``.
    """
    return [
        "'sha256-"
        + base64.b64encode(hashlib.sha256(js.encode("utf-8")).digest()).decode("ascii")
        + "'"
        for js in (_KATEX_JS, _AUTORENDER_JS, _BOOTSTRAP_JS)
    ]


def _document(*, root_class: str, title: str, header_html: str, body_html: str) -> str:
    """Assemble the shared self-contained HTML shell around a rendered body."""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_esc(title)}</title>\n"
        f"<style>{_FONT_CSS}</style>\n"
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


# ---------------------------------------------------------------------------
# Documents (W1b): rich text + templated questions, one continuous numbering.
# ---------------------------------------------------------------------------

_MARK_TAGS = {"bold": "strong", "italic": "em", "underline": "u"}
# Document heading levels 1-3 sit under the sheet title (h1): render as h2-h4.
_HEADING_TAGS = {1: "h2", 2: "h3", 3: "h4"}


# Resolves an asset id to ``(mime, bytes)``, or ``None`` when it is missing. Supplied by the
# API (the engine is storage-agnostic); images are inlined as ``data:`` URIs because headless
# Chromium renders the page from ``set_content`` with no origin to fetch from.
AssetResolver = Callable[[str], "tuple[str, bytes] | None"]


def _render_image(node: dict, assets: AssetResolver | None) -> str:
    attrs = node["attrs"]
    found = assets(attrs["asset_id"]) if assets else None
    if found is None:
        # Visible in every mode: a missing figure must never silently print as nothing.
        return '<p class="missing-image">[image unavailable]</p>'
    mime, data = found
    src = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    width = int(attrs.get("width_pct") or 100)
    alt = html.escape(attrs.get("alt") or "", quote=True)  # attribute context: quotes too
    return (
        f'<figure class="doc-image"><img src="{src}" alt="{alt}" style="width:{width}%"></figure>'
    )


def _render_inline(nodes: list[dict]) -> str:
    out: list[str] = []
    for node in nodes:
        if node["type"] == "hardBreak":
            out.append("<br>")
            continue
        if node["type"] == "math":
            # Escaped, then typeset by the KaTeX bootstrap (trust off: \href etc. are inert).
            out.append(f'<span class="doc-math">\\({_esc(node["attrs"]["latex"])}\\)</span>')
            continue
        html = _mathify(node["text"])
        for mark in node.get("marks", []):
            tag = _MARK_TAGS[mark["type"]]
            html = f"<{tag}>{html}</{tag}>"
        out.append(html)
    return "".join(out)


def _render_rich_block(node: dict, assets: AssetResolver | None = None) -> str:
    """Serialise one whitelisted (schema-validated) rich-text node to escaped HTML."""
    kind = node["type"]
    if kind == "heading":
        tag = _HEADING_TAGS[node["attrs"]["level"]]
        return f'<{tag} class="doc-heading">{_render_inline(node.get("content", []))}</{tag}>'
    if kind == "paragraph":
        return f"<p>{_render_inline(node.get('content', []))}</p>"
    if kind in ("bulletList", "orderedList"):
        tag = "ul" if kind == "bulletList" else "ol"
        start = (node.get("attrs") or {}).get("start")
        attr = f' start="{int(start)}"' if tag == "ol" and start not in (None, 1) else ""
        items = "".join(
            "<li>" + "".join(_render_rich_block(c, assets) for c in li["content"]) + "</li>"
            for li in node["content"]
        )
        return f"<{tag}{attr}>{items}</{tag}>"
    if kind == "image":
        return _render_image(node, assets)
    if kind == "pageBreak":
        return '<div class="page-break"></div>'
    raise ValueError(f"not a rich-text node: {kind!r}")  # pragma: no cover - schema-gated


def _render_freeform_item(
    node: dict,
    *,
    answer_key: bool,
    tag: str = "section",
    assets: AssetResolver | None = None,
) -> list[str]:
    """A teacher-written question (W2a): body + ``[marks]``, then answer space or key answer.

    Free-form blocks carry no verification, so nothing here claims any. In the key an empty
    answer prints a quiet placeholder, so a blank is never mistaken for a written answer.
    """
    attrs = node["attrs"]
    marks = attrs.get("marks")
    body = "".join(_render_rich_block(b, assets) for b in node["content"])
    out = [f'<{tag} class="question freeform">', '<div class="part">']
    out.append(f'<div class="part-text">{body}</div>')
    if marks is not None:
        out.append(f'<span class="marks">[{marks}]</span>')
    out.append("</div>")
    if answer_key:
        answer = attrs.get("answer", {}).get("content", [])
        if answer:
            inner = "".join(_render_rich_block(b, assets) for b in answer)
            out.append(f'<div class="solution teacher-answer">{inner}</div>')
        else:
            out.append('<p class="no-answer">No answer written yet</p>')
    else:
        out.append(
            f'<div class="answer-space" aria-hidden="true" style="--marks:{marks or 2}"></div>'
        )
    out.append(f"</{tag}>")
    return out


def _render_numbered_blocks(
    blocks: list[dict], *, answer_key: bool, assets: AssetResolver | None = None
) -> str:
    """The ``<ol class="questions">`` body for document question blocks (both kinds)."""
    out: list[str] = ['<ol class="questions">']
    for node in blocks:
        if node["type"] == "freeformQuestion":
            out.extend(_render_freeform_item(node, answer_key=answer_key, tag="li", assets=assets))
        else:
            out.extend(_render_question_item(node["attrs"]["question"], answer_key=answer_key))
    out.append("</ol>")
    return "".join(out)


def _doc_total_marks(blocks: list[dict]) -> int:
    return sum(
        n["attrs"].get("marks") or 0
        if n["type"] == "freeformQuestion"
        else n["attrs"]["question"]["question"]["total_marks"]
        for n in blocks
    )


def _render_document_body(
    doc: dict, *, answer_key: bool, assets: AssetResolver | None = None
) -> str:
    """Document blocks in order; questions and rich text share one numbering counter."""
    out: list[str] = ['<div class="doc-body questions">']
    for node in doc["content"]["content"]:
        if node["type"] == "freeformQuestion":
            out.extend(_render_freeform_item(node, answer_key=answer_key, assets=assets))
        elif node["type"] == "templatedQuestion":
            out.extend(
                _render_question_item(
                    node["attrs"]["question"], answer_key=answer_key, tag="section"
                )
            )
        else:
            out.append(_render_rich_block(node, assets))
    out.append("</div>")
    return "".join(out)


def render_document_html(
    title: str, doc: dict, *, mode: str, assets: AssetResolver | None = None
) -> str:
    """Render a document (see :mod:`exam_engine.document`) as self-contained HTML.

    ``mode``: ``student`` — the paper only, no solutions anywhere; ``key`` — the answer
    key only (each question with its worked solution and marking scheme, same numbering);
    ``full`` — the student paper, a page break, then the Answer Key section.
    ``assets`` resolves an image's ``asset_id`` to ``(mime, bytes)`` so figures are inlined as
    ``data:`` URIs; an id it cannot resolve prints a visible "[image unavailable]" line.
    """
    if mode not in ("student", "key", "full"):
        raise ValueError(f"unknown document render mode {mode!r}")

    blocks = [
        n
        for n in doc["content"]["content"]
        if n["type"] in ("templatedQuestion", "freeformQuestion")
    ]
    marks = _doc_total_marks(blocks)

    if mode == "key":
        header = (
            '<header class="sheet-header">'
            f'<h1 class="sheet-title">{_esc(title)} — Answer Key</h1>'
            f'<p class="sheet-meta"><span class="field-marks">Total: {marks} marks</span></p>'
            "</header>"
        )
        body = _render_numbered_blocks(blocks, answer_key=True, assets=assets)
        return _document(
            root_class="sheet answer-key", title=title, header_html=header, body_html=body
        )

    header = (
        '<header class="sheet-header">'
        f'<h1 class="sheet-title">{_esc(title)}</h1>'
        '<p class="sheet-meta">'
        '<span class="field-name">Name: ______________</span>'
        f'<span class="field-marks">Total: {marks} marks</span>'
        "</p>"
        "</header>"
    )
    body = _render_document_body(doc, answer_key=False, assets=assets)
    if mode == "full":
        body += (
            '<section class="key-section">'
            '<h2 class="key-heading">Answer Key</h2>'
            f"{_render_numbered_blocks(blocks, answer_key=True, assets=assets)}"
            "</section>"
        )
    return _document(
        root_class="sheet worksheet" + (" with-key" if mode == "full" else ""),
        title=title,
        header_html=header,
        body_html=body,
    )


# ---------------------------------------------------------------------------
# Question fragments (W1d): one question as embeddable HTML + shared assets.
# ---------------------------------------------------------------------------


def render_question_fragment(obj: dict, *, mode: str = "student", number: int | None = None) -> str:
    """One question as an HTML *fragment* (no ``<html>``), for embedding in the editor.

    The same markup the printed sheets use, so any question the schema can hold — MCQ
    options, tables, grids, constructions, stem figures — draws correctly without a
    TypeScript mirror. ``mode`` is ``student`` (answer space) or ``key`` (worked solution,
    marking scheme, correct option). ``number`` sets the question number shown; omitted,
    the number is hidden (the editor draws its own).
    """
    if mode not in ("student", "key"):
        raise ValueError(f"unknown fragment mode {mode!r}")
    items = _render_question_item(obj, answer_key=mode == "key", tag="section")
    if number is None:
        return '<div class="frag unnumbered">' + "".join(items) + "</div>"
    return f'<div class="frag" style="counter-reset: q {number - 1}">' + "".join(items) + "</div>"


def fragment_css() -> str:
    """KaTeX + print stylesheet for fragments rendered inside a shadow root.

    ``:root`` becomes ``:host`` (the print palette must apply to the shadow host), and the
    host gets the base text settings ``html``/``body`` give a full document.
    """
    base = (
        "\n:host { display: block; font-size: 11pt; color: var(--ink); "
        "font-family: var(--sans); line-height: 1.45; }"
        "\n.frag.unnumbered .question { padding-left: 0; counter-increment: none; }"
        "\n.frag.unnumbered .question::before { content: none; }\n"
    )
    return _KATEX_CSS + "\n" + _PRINT_CSS.replace(":root {", ":host {", 1) + base


def fragment_js() -> str:
    """KaTeX + auto-render, to typeset ``\\(…\\)`` math inside embedded fragments."""
    return _KATEX_JS + "\n" + _AUTORENDER_JS
