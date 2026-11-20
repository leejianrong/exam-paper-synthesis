"""EXA-90 — the paper's LaTeX as Word equations (OMML), for the .docx export.

No maintained library turns LaTeX into OMML without Word's own MathML stylesheet (proprietary)
or a long-abandoned converter, so this reads the small subset the papers use: what the engine
emits (``\\frac``, ``\\text``, ``\\pi``, ``\\times``, ``\\div``, ``\\ell``, ``\\left( \\right)``,
``\\$``, ``^{…}``) and the usual extras a teacher types in an equation (``\\sqrt``, ``_``,
``\\cdot``, ``\\le``, ``\\ge``, ``\\neq``, ``\\circ``). The result is a real, editable Word
equation. Anything outside the subset raises :class:`Unsupported`, and the caller prints the
LaTeX as typed: a wrong-looking equation is worse than a visible source.
"""

from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement

_TOKEN = re.compile(r"\\[a-zA-Z]+|\\.|[{}^_]|[^\\{}^_]")

_SYMBOLS = {
    r"\pi": "π",
    r"\times": "×",
    r"\div": "÷",
    r"\ell": "ℓ",
    r"\cdot": "·",
    r"\le": "≤",
    r"\leq": "≤",
    r"\ge": "≥",
    r"\geq": "≥",
    r"\neq": "≠",
    r"\circ": "°",
    r"\degree": "°",
    r"\angle": "∠",
    r"\pm": "±",
    r"\approx": "≈",
    r"\$": "$",
    r"\%": "%",
    r"\{": "{",
    r"\}": "}",
    r"\ ": " ",
    r"\,": " ",
    r"\;": " ",
    r"\:": " ",
    r"\quad": "  ",
}
_IGNORED = {r"\left", r"\right", r"\displaystyle"}  # sizing only: the bracket that follows prints


class Unsupported(ValueError):
    """The LaTeX uses something outside the subset this module reads."""


def _el(tag: str, *children: BaseOxmlElement) -> BaseOxmlElement:
    el = OxmlElement(tag)
    for c in children:
        el.append(c)
    return el


def _run(text: str, *, plain: bool = False) -> BaseOxmlElement:
    r = OxmlElement("m:r")
    if plain:  # \text{…}: ordinary upright text, as KaTeX prints it
        r.append(_el("m:rPr", OxmlElement("m:nor")))
    t = OxmlElement("m:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    r.append(t)
    return r


class _Parser:
    def __init__(self, latex: str) -> None:
        self.toks = _TOKEN.findall(latex)
        self.i = 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> str:
        tok = self.peek()
        if tok is None:
            raise Unsupported("unexpected end")
        self.i += 1
        return tok

    def seq(self, closing: bool = False) -> list[BaseOxmlElement]:
        out: list[BaseOxmlElement] = []
        while (tok := self.peek()) is not None:
            if tok == "}":
                if not closing:
                    raise Unsupported("unbalanced }")
                self.i += 1
                return out
            if tok in "^_":
                self.i += 1
                base = out.pop() if out else _run("")
                script = self.arg()
                kind, part = ("m:sSup", "m:sup") if tok == "^" else ("m:sSub", "m:sub")
                out.append(_el(kind, _el("m:e", base), _el(part, *script)))
                continue
            out.extend(self.atom())
        if closing:
            raise Unsupported("unbalanced {")
        return out

    def arg(self) -> list[BaseOxmlElement]:
        """A command's argument: a {group} or a single token."""
        if self.peek() == "{":
            self.i += 1
            return self.seq(closing=True)
        return self.atom()

    def atom(self) -> list[BaseOxmlElement]:
        tok = self.take()
        if tok == "{":
            return self.seq(closing=True)
        if tok == r"\frac":
            return [_el("m:f", _el("m:num", *self.arg()), _el("m:den", *self.arg()))]
        if tok == r"\sqrt":
            hide = OxmlElement("m:degHide")
            hide.set(qn("m:val"), "1")
            return [
                _el("m:rad", _el("m:radPr", hide), OxmlElement("m:deg"), _el("m:e", *self.arg()))
            ]
        if tok in (r"\text", r"\mathrm"):
            return [_run(self.raw_group(), plain=True)]
        if tok in _IGNORED:
            return []
        if tok in _SYMBOLS:
            return [_run(_SYMBOLS[tok])]
        if tok.startswith("\\"):
            raise Unsupported(tok)
        return [_run(tok)]

    def raw_group(self) -> str:
        """The literal text of a {group} (``\\text`` takes its contents as written)."""
        if self.take() != "{":
            raise Unsupported(r"\text without a group")
        depth, text = 1, list[str]()
        while True:
            tok = self.take()
            depth += {"{": 1, "}": -1}.get(tok, 0)
            if depth == 0:
                return "".join(text)
            text.append(_SYMBOLS.get(tok, tok))


def omath(latex: str) -> BaseOxmlElement:
    """An ``<m:oMath>`` for ``latex``, or :class:`Unsupported`."""
    return _el("m:oMath", *_Parser(latex).seq())
