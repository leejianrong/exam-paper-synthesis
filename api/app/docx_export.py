"""EXA-90 — a paper as an editable Word document (.docx), for teachers who tweak it in Word.

It walks the same document model, in the same order and with the same decisions, as
``exam_engine.render.render_document_html`` (whose helpers it reuses for every derived piece:
section sentences, marks placement, the cover's examiner rows, the school key's groups and
pairs), and writes Word's own structures instead of HTML: headings, paragraphs with a right
tab stop for the ``[n]`` marks, real tables (cover, data tables, the school key), page breaks.
What only a paginated print has (marking strip, tally boxes, page footers) is left out: Word
paginates the document itself.

Figures (server-drawn SVG) are rasterised to PNG by ``export.html_to_png_many`` and placed at
their print size; uploaded images are embedded as they are. Inline LaTeX becomes a Word equation
(``docx_math``) or, outside the subset it reads, the LaTeX as typed. Everything prints black.
"""

from __future__ import annotations

import html
import io
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.image.exceptions import UnrecognizedImageError
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from exam_engine import diagram
from exam_engine.document import (
    GROUP_STEM,
    QUESTION_TYPES,
    cover_page,
    has_content,
    in_key,
    is_unfilled_placeholder,
    number_from,
    paper_outline,
    paper_placement,
    stem_groups,
    stem_sentence,
)
from exam_engine.render import (
    _BLANK_TEXT,
    _BOOKLET_LINE,
    _GENERIC_TITLE,
    _GRID_COLUMNS,
    _KEY_META,
    _NO_LINE,
    AssetResolver,
    KeyOptions,
    Layout,
    _answer_only,
    _cover_time,
    _doc_total_marks,
    _end_text,
    _examiner_rows,
    _fmt_answer,
    _key_groups,
    _key_options,
    _key_paper_name,
    _marks_beside,
    _scheme_text,
    _time_label,
    default_space_mm,
    section_sentence,
    unit_parts,
)

from . import docx_math

Rasterise = Callable[[list[str]], "list[bytes | None]"]

_TEXT_WIDTH = Mm(178)  # A4 less the print margins (print.css @page: 18 mm 16 mm)
_INDENT = Mm(10)
_Q_COL = int(Mm(16))  # the school key's question-number column
_HALF = int(_TEXT_WIDTH) // 2 - _Q_COL
_FIGURE_SCALE = 2  # html_to_png_many's device scale: PNG pixels per CSS pixel
_MATH = re.compile(r"\\\((.+?)\\\)|\\\[(.+?)\\\]", re.DOTALL)
_TAGGED = re.compile(r"(<b>.*?</b>|<sup>.*?</sup>)")
_BLACK = RGBColor(0, 0, 0)
# Characters XML 1.0 cannot hold (a vertical tab pasted from Word, other C0 controls, U+FFFE/F,
# lone surrogates): the schema and the PDF let them through, python-docx refuses them.
_NOT_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def _xml_safe(value: Any) -> Any:
    """``value`` with every string stripped of what XML cannot hold (tab and newline stay)."""
    if isinstance(value, str):
        return _NOT_XML.sub("", value)
    if isinstance(value, dict):
        return {k: _xml_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_xml_safe(v) for v in value]
    return value


class _Writer:
    def __init__(self, title: str, doc: dict, assets: AssetResolver | None) -> None:
        self.doc = doc
        self.title = title
        self.assets = assets
        self.word = Document()
        self.target: Any = self.word  # where paragraphs go: the body or a table cell
        self.reuse: Paragraph | None = None  # a fresh cell's own empty paragraph
        self.number = ""  # the next paragraph starts a numbered question
        self.indent = False  # inside a question: paragraphs sit under its number
        self.break_next = False  # the next paragraph starts a page
        self.keep = False  # inside a shared stem: it stays with its first question
        self.last: Paragraph | None = None
        self.figures: list[tuple[Any, str]] = []  # (run, svg) placed once rasterised
        self._setup()

    # -- page and styles ----------------------------------------------------------------------

    def _setup(self) -> None:
        section = self.word.sections[0]
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.top_margin = section.bottom_margin = Mm(18)
        section.left_margin = section.right_margin = Mm(16)
        styles = self.word.styles
        normal = styles["Normal"]
        normal.font.name = "Arial"  # Inter is rarely installed where Word runs
        normal.font.size = Pt(11)
        normal.font.color.rgb = _BLACK
        normal.paragraph_format.space_after = Pt(4)
        normal.paragraph_format.tab_stops.add_tab_stop(_TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
        for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
            styles[name].font.color.rgb = _BLACK
            styles[name].font.name = "Arial"
        props = self.word.core_properties
        props.title, props.author, props.comments = self.title, "", ""
        props.created = props.modified = datetime.now(UTC).replace(tzinfo=None)
        props.last_modified_by = ""

    # -- paragraphs ---------------------------------------------------------------------------

    def para(self, style: str | None = None) -> Paragraph:
        if self.reuse is not None:
            p, self.reuse = self.reuse, None
        else:
            p = self.target.add_paragraph(style=style)
        fmt = p.paragraph_format
        if self.break_next:
            fmt.page_break_before, self.break_next = True, False
        if self.indent and self.target is self.word:
            fmt.left_indent = _INDENT
            fmt.keep_with_next = True  # a question's lines stay with what follows them
        if self.keep:
            fmt.keep_with_next = True
        if self.number:
            fmt.first_line_indent = -_INDENT
            p.add_run(f"{self.number}\t").bold = True
            self.number = ""
        self.last = p
        return p

    def hang(self, p: Paragraph) -> None:
        """A list line: the label hangs, the text after its tab lines up."""
        left = p.paragraph_format.left_indent or 0
        p.paragraph_format.left_indent = left + _INDENT
        p.paragraph_format.first_line_indent = -_INDENT

    def heading(self, text: str, level: int) -> None:
        p = self.para(style=f"Heading {level}")
        p.add_run(text)

    @contextmanager
    def into(self, cell: Any) -> Iterator[None]:
        saved = (self.target, self.reuse, self.indent)
        self.target, self.reuse, self.indent = cell, cell.paragraphs[0], False
        try:
            yield
        finally:
            self.target, self.reuse, self.indent = saved

    def table(self, rows: int, cols: int, widths: list[int] | None = None) -> Any:
        t = self.target.add_table(rows=rows, cols=cols)
        t.style = self.word.styles["Table Grid"]
        t.autofit = False
        widths = widths or [int(_TEXT_WIDTH) // cols] * cols
        for col, width in zip(t.columns, widths, strict=True):
            col.width = width  # the grid (LibreOffice) and each cell (Word)
            for cell in col.cells:
                cell.width = width
        if self.break_next:
            t.cell(0, 0).paragraphs[0].paragraph_format.page_break_before = True
            self.break_next = False
        return t

    def page_break(self) -> None:
        self.break_next = True

    # -- text ---------------------------------------------------------------------------------

    def text(self, p: Paragraph, s: str, *, escaped: bool = False, bold: bool = False) -> None:
        """Plain text with inline ``\\(…\\)`` maths. ``escaped``: HTML from the renderer's helpers
        (``<b>`` and ``<sup>`` become run formatting)."""
        pos = 0
        for m in _MATH.finditer(s):
            self._plain(p, s[pos : m.start()], escaped, bold)
            self.math(p, m.group(1) or m.group(2))
            pos = m.end()
        self._plain(p, s[pos:], escaped, bold)

    def _plain(self, p: Paragraph, s: str, escaped: bool, bold: bool) -> None:
        if not s:
            return
        if not escaped:
            p.add_run(s).bold = bold or None
            return
        for piece in _TAGGED.split(s):
            if not piece:
                continue
            tag = piece[1 : piece.find(">")] if piece.startswith("<") else ""
            inner = html.unescape(re.sub(r"</?(b|sup)>", "", piece))
            run = p.add_run(inner)
            run.bold = bold or tag == "b" or None
            run.font.superscript = tag == "sup" or None

    def math(self, p: Paragraph, latex: str) -> None:
        try:
            p._p.append(docx_math.omath(html.unescape(latex)))
        except docx_math.Unsupported:
            p.add_run(html.unescape(latex))

    def marks(self, p: Paragraph | None, n: int | None) -> None:
        if p is not None and n is not None:
            p.add_run(f"\t[{n}]")

    def inline(self, p: Paragraph, nodes: list[dict]) -> None:
        for node in nodes:
            if node["type"] == "hardBreak":
                p.add_run().add_break()
            elif node["type"] == "math":
                self.math(p, node["attrs"]["latex"])
            else:
                run = p.add_run(node["text"])
                kinds = {m["type"] for m in node.get("marks", [])}
                run.bold = "bold" in kinds or None
                run.italic = "italic" in kinds or None
                run.underline = "underline" in kinds or None

    def rich(self, node: dict, *, prefix: str = "") -> None:
        kind = node["type"]
        if kind == "heading":
            level = node["attrs"]["level"]
            p = self.para(style=f"Heading {min(level + 1, 3)}")
            self.inline(p, node.get("content", []))
        elif kind == "paragraph":
            p = self.para()
            if prefix:
                p.add_run(prefix)
                if prefix.endswith("\t") and p.paragraph_format.first_line_indent is None:
                    self.hang(p)
            self.inline(p, node.get("content", []))
        elif kind in ("bulletList", "orderedList"):
            start = int((node.get("attrs") or {}).get("start") or 1)
            for i, li in enumerate(node["content"]):
                lead = "•\t" if kind == "bulletList" else f"{start + i}.\t"
                for j, child in enumerate(li["content"]):
                    self.rich(child, prefix=lead if j == 0 else "")
        elif kind == "image":
            self.image(node["attrs"])
        elif kind == "pageBreak":
            self.page_break()

    def image(self, attrs: dict) -> None:
        found = self.assets(attrs["asset_id"]) if self.assets else None
        p = self.para()
        if found is None:  # a missing figure must never silently print as nothing
            p.add_run("[image unavailable]")
            return
        width = int(_TEXT_WIDTH * int(attrs.get("width_pct") or 100) / 100)
        run = p.add_run()
        try:
            _alt(run.add_picture(io.BytesIO(found[1]), width=width), attrs.get("alt") or "")
        except UnrecognizedImageError:  # e.g. a JPEG with neither a JFIF nor an EXIF header
            run.text = "[image unavailable]"

    def figure(self, svg: str) -> None:
        self.figures.append((self.para().add_run(), svg))

    def place_figures(self, rasterise: Rasterise) -> None:
        if not self.figures:
            return
        pngs = rasterise([svg for _, svg in self.figures])
        for (run, _), png in zip(self.figures, pngs, strict=True):
            if png is None:
                run.text = "[figure unavailable]"
                continue
            px = int.from_bytes(png[16:20], "big")  # the PNG header's width
            width = min(int(Inches(px / _FIGURE_SCALE / 96)), int(_TEXT_WIDTH))
            _alt(run.add_picture(io.BytesIO(png), width=width), "Figure")

    # -- the student paper's pieces -----------------------------------------------------------

    def space(self, mm: int) -> None:
        fmt = self.para().paragraph_format
        fmt.line_spacing_rule, fmt.line_spacing = WD_LINE_SPACING.EXACTLY, Mm(mm)
        fmt.keep_with_next = None  # the page may break after the working space

    def answer_line(self, layout: Layout, unit: str | None, label: str, marks: int | None) -> None:
        before, after = unit_parts(layout.ans_unit if layout.ans_unit is not None else unit or "")
        p = self.para()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.add_run("Ans: " + (f"({label}) " if label else "")).bold = True
        self.text(p, f"{before} ________________ {after}".strip(), escaped=True)
        if marks is not None and layout.placement in ("answer", "both"):
            p.add_run(f"   [{marks}]")
        p.paragraph_format.keep_with_next = None

    def work_area(self, layout: Layout, marks: int | None, unit: str | None, label: str) -> None:
        mm = layout.space_mm if layout.space_mm is not None else default_space_mm(marks)
        self.space(mm)
        self.answer_line(layout, unit, label, marks)

    # -- questions ----------------------------------------------------------------------------

    def templated(self, obj: dict, layout: Layout | None, key: KeyOptions | None) -> None:
        answer_key = key is not None
        q = obj["question"]
        parts = q["parts"]
        multipart = len(parts) > 1
        q_diagram = q.get("diagram")
        if key is not None and not key.show_question:
            for spec in (q_diagram, *(p.get("diagram") for p in parts)):
                if diagram.hides_worked_model(obj, spec):
                    self.figure(diagram.render_svg(spec))
            for part in parts:
                p = self.para()
                if multipart:
                    p.add_run(f"({part['label']})")
                self.marks(p, part.get("marks"))
                if part["answer"]["type"] == "tick_table":
                    self.tick_table(part["answer"], reveal=True)
                self.solution(part, q_diagram, key)
            return
        if q.get("stem"):
            self.text(self.para(), q["stem"])
        if q_diagram is not None and (answer_key or not diagram.hides_worked_model(obj, q_diagram)):
            self.figure(diagram.render_svg(q_diagram))
        if q.get("table") is not None:
            self.data_table(q["table"], parts, answer_key)
        hide_worked = obj.get("source_type") == "generated"
        for part in parts:
            answer = part.get("answer") or {}
            p = self.para()
            if multipart and part.get("label"):
                p.add_run(f"({part['label']}) ")
            self.text(p, part["text"])
            has_line = answer.get("type") not in _NO_LINE
            if _marks_beside(layout, answer_key, has_line):
                self.marks(p, part.get("marks"))
            spec = part.get("diagram")
            if spec is not None and (
                answer_key or not (hide_worked and diagram.is_worked_model(spec))
            ):
                self.figure(diagram.render_svg(spec))
            if answer.get("type") == "choice":
                self.options(answer, reveal=answer_key)
            elif answer.get("type") == "tick_table":
                self.tick_table(answer, reveal=answer_key)
            if key is not None:
                self.solution(part, q_diagram, key)
            elif has_line and layout is not None:
                label = part.get("label") if multipart else ""
                self.work_area(layout, part.get("marks", 1), answer.get("unit"), label or "")

    def options(self, answer: dict, *, reveal: bool) -> None:
        """One option a line, as real Booklet A prints them; the key bolds the correct one."""
        for opt in answer.get("options", []):
            p = self.para()
            p.paragraph_format.left_indent = _INDENT * 2
            p.paragraph_format.first_line_indent = -_INDENT
            correct = reveal and opt.get("label") == answer.get("correct")
            p.add_run(f"({opt['label']})\t").bold = correct or None
            if opt.get("text"):
                self.text(p, opt["text"], bold=correct)
            if opt.get("diagram"):
                self.figures.append((p.add_run(), diagram.render_svg(opt["diagram"])))

    def tick_table(self, answer: dict, *, reveal: bool) -> None:
        """EXA-158 statements with a box per column: empty on the paper, ticked in the key."""
        columns = answer["columns"]
        box = int(Mm(24))
        t = self.table(
            len(answer["rows"]) + 1,
            len(columns) + 1,
            [int(_TEXT_WIDTH) - box * len(columns)] + [box] * len(columns),
        )
        for c, head in enumerate(["Statement", *columns]):
            p = t.cell(0, c).paragraphs[0]
            p.add_run(head).bold = True
            if c:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r, row in enumerate(answer["rows"], 1):
            self.text(t.cell(r, 0).paragraphs[0], row["statement"])
            for c, column in enumerate(columns, 1):
                p = t.cell(r, c).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if reveal and row["tick"] == column:
                    p.add_run("\u2713").bold = True
        self.para()

    def data_table(self, table: dict, parts: list[dict], answer_key: bool) -> None:
        if table.get("caption"):
            self.text(self.para(), table["caption"])
        headers = table.get("headers")
        rows = ([headers] if headers else []) + table["rows"]
        t = self.table(len(rows), max(len(r) for r in rows))
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                p = t.cell(r, c).paragraphs[0]
                if isinstance(cell, dict):  # {"answer_for": part}: blank on the paper
                    part = next((x for x in parts if x["label"] == cell["answer_for"]), None)
                    if answer_key and part:
                        self.text(p, _fmt_answer(part["answer"]), escaped=True)
                elif cell is not None:
                    self.text(p, str(cell), bold=headers is not None and r == 0)

    def solution(self, part: dict, q_diagram: dict | None, key: KeyOptions) -> None:
        for i, step in enumerate(part.get("solution_steps", []), 1):
            p = self.para()
            p.add_run(f"{i}. ")
            self.text(p, step["text"])
        answer = part["answer"]
        if answer["type"] == "construction":
            given = part.get("diagram") or q_diagram
            self.figure(diagram.render_svg(answer["diagram"], given=given))
        elif answer["type"] != "tick_table":  # the ticked table, printed with the part, is it
            p = self.para()
            p.add_run("Answer: ").bold = True
            self.text(p, _fmt_answer(answer), escaped=True, bold=True)
        if key.show_scheme:
            for mark in part.get("marking_scheme", []):
                p = self.para()
                p.add_run(f"{mark['type']}{mark['mark']}  ").bold = True
                p.add_run(mark["description"])

    def freeform(
        self, node: dict, layout: Layout, key: KeyOptions | None, *, mcq: bool = False
    ) -> None:
        attrs = node["attrs"]
        answer_key = key is not None
        if mcq and not answer_key and is_unfilled_placeholder(node):
            p = self.para()
            if layout.placement != "none":
                self.marks(p, attrs.get("marks"))
            self.space(
                default_space_mm(attrs.get("marks")) if layout.space_mm is None else layout.space_mm
            )
            return
        parts = [c for c in node["content"] if c.get("type") == "freeformPart"]
        hide = key is not None and not key.show_question
        if not hide:
            for b in node["content"]:
                if b.get("type") != "freeformPart":
                    self.rich(b)
        if not parts:
            if hide or self.number:  # no body paragraph took the number
                self.para()
            if hide or _marks_beside(layout, answer_key):
                self.marks(self.last, attrs.get("marks"))
            self.freeform_answer(attrs, attrs.get("marks"), key, layout, "")
            return
        head_layout = Layout(layout.placement)
        for i, part in enumerate(parts):
            letter = chr(ord("a") + i)
            pattrs = part["attrs"]
            marks = pattrs.get("marks")
            if hide:
                p = self.para()
                p.add_run(f"({letter})")
                self.marks(p, marks)
            else:
                for j, b in enumerate(part["content"]):
                    self.rich(b, prefix=f"({letter}) " if j == 0 else "")
                if _marks_beside(head_layout, answer_key):
                    self.marks(self.last, marks)
            part_layout = Layout(layout.placement, pattrs.get("space_mm"), pattrs.get("ans_unit"))
            self.freeform_answer(pattrs, marks, key, part_layout, letter)

    def freeform_answer(
        self, attrs: dict, marks: int | None, key: KeyOptions | None, layout: Layout, label: str
    ) -> None:
        if key is None:
            self.work_area(layout, marks if marks is not None else 2, None, label)
            return
        written = (attrs.get("answer") or {}).get("content", [])
        if not written:
            self.para().add_run("No answer written yet").italic = True
        for b in written:
            self.rich(b)

    # -- the paper ----------------------------------------------------------------------------

    def group_stem(self, node: dict, numbers: list[int]) -> None:
        """A shared stem (EXA-90): the lead line from its questions' numbers, then its text and
        figures, unnumbered and kept with the question after it."""
        self.keep = True
        if lead := stem_sentence(numbers):
            self.para().add_run(lead).italic = True
        for b in node["content"]:
            self.rich(b)
        self.keep = False

    def start_question(self, number: int) -> None:
        self.number, self.indent = f"{number}.", True

    def end_question(self) -> None:
        """The next question may start a new page."""
        self.indent = False
        if self.last is not None:
            self.last.paragraph_format.keep_with_next = None

    def cover(self, attrs: dict, marks: int) -> None:
        def text(key: str) -> str:
            return str(attrs.get(key) or "").strip()

        paper, booklet = text("paper"), ""
        if m := _BOOKLET_LINE.match(paper):
            paper, booklet = m.group(1), m.group(2)
        lines = [v for v in (text(k) for k in ("school", "exam", "level", "subject")) if v]
        lines += [v for v in (paper, booklet) if v]
        for i, line in enumerate(lines or [self.title]):
            p = self.para()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(line)
            run.bold, run.font.size = True, Pt(16 if i == 0 else 13)
        count = sum(1 for n in self.doc["content"]["content"] if n["type"] in QUESTION_TYPES)
        fields = [
            ("Name:", "______________________________  (     )"),
            ("Class:", f"{text('level')} ________"),
            ("Date:", text("date") or "______________"),
        ]
        if attrs.get("parent_signature"):
            fields.append(("Parent's signature:", "______________________"))
        self.para()
        t = self.table(len(fields), 2, [int(Mm(40)), int(Mm(90))])
        for r, (label, value) in enumerate(fields):
            t.cell(r, 0).paragraphs[0].add_run(label).bold = True
            t.cell(r, 1).paragraphs[0].add_run(value)
        if _cover_time(self.doc):
            self.para().add_run(_cover_time(self.doc)).bold = True
        q = f"{count} question{'' if count == 1 else 's'}"
        self.para().add_run(f"{q}\t{marks} mark{'' if marks == 1 else 's'}").bold = True
        if attrs.get("examiner_table") is not False:
            self.para().add_run("For examiner's use").bold = True
            rows = _examiner_rows(self.doc, marks)
            t = self.table(len(rows), 2, [int(Mm(60)), int(Mm(30))])
            for r, (label, maximum, total) in enumerate(rows):
                t.cell(r, 0).paragraphs[0].add_run(label).bold = total or None
                cell = t.cell(r, 1).paragraphs[0]
                cell.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                cell.add_run(f"/ {maximum}")
        instructions = [x.strip() for x in text("instructions").splitlines() if x.strip()]
        if instructions:
            self.heading("Instructions to candidates", 2)
            for i, line in enumerate(instructions, 1):
                p = self.para()
                p.add_run(f"{i}.\t")
                self.hang(p)
                for piece in re.split(r"(\bNOT\b)", line):
                    run = p.add_run(piece)
                    if piece == "NOT":
                        run.bold = run.underline = True
        self.page_break()

    def header(self, marks: int, key: bool = False) -> None:
        self.heading(f"{self.title} — Answer Key" if key else self.title, 1)
        bits = [] if key else ["Name: ____________________"]
        if not key and _time_label(self.doc):
            bits.append(f"Time: {_time_label(self.doc)}")
        bits.append(f"Total: {marks} marks")
        self.para().add_run("    ".join(bits))

    def section(self, info: dict) -> None:
        title = info["title"].strip()
        if title and not _GENERIC_TITLE.match(title):
            self.heading(title, 2)
        sentence = section_sentence(info)
        instructions = (info["instructions"] or "").strip()
        if not (sentence or instructions or info["count"]):
            return
        p = self.para()
        p.paragraph_format.keep_with_next = True  # the header stays with its first question
        self.text(p, sentence, escaped=True)
        if instructions:
            p.add_run((" " if sentence else "") + instructions)
        if info["count"]:
            p.add_run(f"\t({info['marks']} mark{'' if info['marks'] == 1 else 's'})").bold = True

    def student(self) -> None:
        content = self.doc["content"]["content"]
        blocks = [n for n in content if n["type"] in QUESTION_TYPES]
        marks = _doc_total_marks(blocks)
        if not cover_page(self.doc):
            self.header(marks)
        placement = paper_placement(self.doc)
        outline = iter(paper_outline(self.doc))
        number = number_from(self.doc) - 1
        mcq = own_page = False
        first_in_section = True
        last_q = max((i for i, n in enumerate(content) if n["type"] in QUESTION_TYPES), default=-1)
        groups = stem_groups(self.doc)
        for i, node in enumerate(content):
            kind = node["type"]
            if kind == GROUP_STEM:
                if own_page and not first_in_section:
                    self.page_break()  # a structured question's stem tops its page
                    first_in_section = True  # so its first question does not break again
                self.group_stem(node, groups[i])
            elif kind == "coverPage":
                self.cover(node["attrs"], marks)
            elif kind == "blankPage":
                self.page_break()
                attrs = node["attrs"]
                which = attrs.get("kind") or "blank"
                p = self.para()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run((attrs.get("text") or "").strip() or _BLANK_TEXT[which])
                self.page_break()
            elif kind == "section":
                info = next(outline)
                mcq, own_page = info["mode"] == "mcq", info["mode"] == "structured"
                placement, first_in_section = info["marks_placement"], True
                self.indent = False
                if own_page:
                    self.page_break()
                self.section(info)
            elif kind in QUESTION_TYPES:
                number += 1
                if own_page and not first_in_section:
                    self.page_break()
                first_in_section = False
                self.start_question(number)
                layout = Layout(
                    placement, node["attrs"].get("space_mm"), node["attrs"].get("ans_unit")
                )
                if kind == "freeformQuestion":
                    self.freeform(node, layout, None, mcq=mcq)
                else:
                    self.templated(node["attrs"]["question"], layout, None)
                self.end_question()
                if i == last_q:
                    p = self.para()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.add_run(_end_text(self.doc)).bold = True
            else:
                self.rich(node)

    def key(self) -> None:
        content = self.doc["content"]["content"]
        blocks = [n for n in content if n["type"] in QUESTION_TYPES]
        marks = _doc_total_marks(blocks)
        key = _key_options(self.doc)
        if key.layout == "compact":
            self.compact_key(key, marks)
            return
        self.header(marks, key=True)
        placement = paper_placement(self.doc)
        numbered = [n for n, b in enumerate(blocks, number_from(self.doc)) if in_key(b)]
        stems: dict[int, tuple[dict, list[int]]] = {}  # above the first of its questions here
        if key.show_question:
            for at, numbers in stem_groups(self.doc).items():
                if first := next((n for n in numbered if n in numbers), None):
                    stems[first] = (content[at], numbers)
        for number, node in enumerate(blocks, number_from(self.doc)):
            if not in_key(node):
                continue
            if number in stems:
                self.group_stem(*stems[number])
            self.start_question(number)
            layout = Layout(placement, node["attrs"].get("space_mm"), node["attrs"].get("ans_unit"))
            if node["type"] == "freeformQuestion":
                self.freeform(node, layout, key)
            else:
                self.templated(node["attrs"]["question"], layout, key)
            self.end_question()

    # -- the school key (EXA-142) -------------------------------------------------------------

    def compact_key(self, key: KeyOptions, marks: int) -> None:
        attrs = (cover_page(self.doc) or {}).get("attrs") or {}
        for name, field in _KEY_META:
            if value := str(attrs.get(field) or "").strip():
                p = self.para()
                p.add_run(f"{name} : ").bold = True
                p.add_run(value)
        self.heading(_key_paper_name(self.doc, self.title), 1)
        if key.show_marks:
            self.para().add_run(f"Total: {marks} marks")
        for info, numbered in _key_groups(self.doc):
            name = (info or {}).get("title", "").strip()
            if name and not _GENERIC_TITLE.match(name):
                self.heading(name, 2)
            if info is not None and info["mode"] == "mcq":
                self.key_grid(numbered)
            else:
                self.key_tables(numbered, key)

    def key_grid(self, numbered: list[tuple[int, dict]]) -> None:
        for i in range(0, len(numbered), _GRID_COLUMNS):
            row = numbered[i : i + _GRID_COLUMNS]
            t = self.table(2, _GRID_COLUMNS)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for c, (n, node) in enumerate(row):
                t.cell(0, c).paragraphs[0].add_run(f"Q{n}").bold = True
                with self.into(t.cell(1, c)):
                    self.grid_answer(node)
            self.para()

    def grid_answer(self, node: dict) -> None:
        if node["type"] == "templatedQuestion":
            answers = [p["answer"] for p in node["attrs"]["question"]["question"]["parts"]]
            shown = [a["correct"] if a.get("type") == "choice" else _fmt_answer(a) for a in answers]
            self.text(self.para(), ", ".join(shown), escaped=True)
            return
        written = (node["attrs"].get("answer") or {}).get("content", [])
        if has_content(written):
            for b in written:
                self.rich(b)
        else:
            self.para().add_run("–")

    def key_tables(self, numbered: list[tuple[int, dict]], key: KeyOptions) -> None:
        """1-mark answers two to a row, the other questions one to a row, in question order."""
        runs: list[tuple[bool, list[tuple[int, dict]]]] = []
        for number, node in numbered:
            short = _answer_only(node, key) is not None
            if runs and runs[-1][0] == short:
                runs[-1][1].append((number, node))
            else:
                runs.append((short, [(number, node)]))
        for short, items in runs:
            if short:
                t = self.table((len(items) + 1) // 2, 4, [_Q_COL, _HALF, _Q_COL, _HALF])
                for i, (n, node) in enumerate(items):
                    r, c = divmod(i, 2)
                    t.cell(r, 2 * c).paragraphs[0].add_run(f"Q{n}").bold = True
                    with self.into(t.cell(r, 2 * c + 1)):
                        self.key_work(node, key)
            else:
                t = self.table(len(items), 2, [_Q_COL, int(_TEXT_WIDTH) - _Q_COL])
                for r, (n, node) in enumerate(items):
                    t.cell(r, 0).paragraphs[0].add_run(f"Q{n}").bold = True
                    with self.into(t.cell(r, 1)):
                        self.key_work(node, key)
            self.para()

    def key_ans(self, answer: str, label: str, marks: int | None, key: KeyOptions) -> None:
        p = self.para()
        p.add_run("Ans: " + (f"({label}) " if label else "")).bold = True
        self.text(p, answer, escaped=True)
        if key.show_marks and marks:
            p.add_run(f" [{marks}]")

    def key_work(self, node: dict, key: KeyOptions) -> None:
        if node["type"] == "freeformQuestion":
            parts = [c for c in node["content"] if c.get("type") == "freeformPart"]
            pieces = [(chr(ord("a") + i), p["attrs"]) for i, p in enumerate(parts)]
            for label, attrs in pieces or [("", node["attrs"])]:
                written = (attrs.get("answer") or {}).get("content", [])
                if not has_content(written):
                    lab = f"({label}) " if label else ""
                    self.para().add_run(f"{lab}No answer written yet").italic = True
                    continue
                p = self.para()
                p.add_run("Ans: " + (f"({label}) " if label else "")).bold = True
                if len(written) == 1 and written[0]["type"] == "paragraph":
                    self.inline(p, written[0].get("content", []))
                else:
                    for b in written:
                        self.rich(b)
                if key.show_marks and attrs.get("marks"):
                    self.last.add_run(f" [{attrs['marks']}]")  # type: ignore[union-attr]
            return
        obj = node["attrs"]["question"]
        parts = obj["question"]["parts"]
        q_diagram = obj["question"].get("diagram")
        multipart = len(parts) > 1
        for spec in (q_diagram, *(p.get("diagram") for p in parts)):
            if diagram.hides_worked_model(obj, spec):  # a worked model (bar model) is working
                self.figure(diagram.render_svg(spec))
        one_line = _answer_only(node, key) is not None
        for part in parts:
            label = part["label"] if multipart else ""
            for i, step in enumerate([] if one_line else part.get("solution_steps", [])):
                p = self.para()
                if label and i == 0:
                    p.add_run(f"({label}) ").bold = True
                self.text(p, step["text"])
            answer = part["answer"]
            if answer["type"] == "tick_table":
                # the ticked table is the answer: no "Ans:" line, the marks right under it
                self.tick_table(answer, reveal=True)
                if key.show_marks and part.get("marks"):
                    self.para().add_run(f"[{part['marks']}]")
            elif answer["type"] == "construction":
                if label or (key.show_marks and part.get("marks")):
                    self.key_ans("", label, part.get("marks"), key)
                self.figure(
                    diagram.render_svg(answer["diagram"], given=part.get("diagram") or q_diagram)
                )
            elif one_line:
                p = self.para()
                self.text(p, _fmt_answer(answer), escaped=True)
                if key.show_marks:
                    p.add_run(" [1]")
            else:
                self.key_ans(_fmt_answer(answer), label, part.get("marks"), key)
            if key.show_scheme:
                for mark in part.get("marking_scheme", []):
                    p = self.para()
                    p.add_run(f"{mark['type']}{mark['mark']} ").bold = True
                    self.text(p, _scheme_text(part, mark), escaped=True)


def _alt(shape: Any, text: str) -> None:
    shape._inline.docPr.set("descr", text)  # the picture's alt text, read aloud by Word


def build_docx(
    title: str,
    doc: dict,
    *,
    mode: str,
    rasterise: Rasterise,
    assets: AssetResolver | None = None,
) -> bytes:
    """The paper (``student``) or its answer key (``key``) as .docx bytes. ``rasterise`` turns
    the figures' SVGs into PNGs (one call for the whole document, never when there are none)."""
    if mode not in ("student", "key"):
        raise ValueError(f"unknown docx mode {mode!r}")
    w = _Writer(_xml_safe(title), _xml_safe(doc), assets)
    if mode == "student":
        w.student()
    else:
        w.key()
    w.place_figures(rasterise)
    out = io.BytesIO()
    w.word.save(out)
    return out.getvalue()
