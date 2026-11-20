"""EXA-90 — the paper and its key as an editable Word document (.docx)."""

from __future__ import annotations

import io
import re
import zipfile

import pytest
from app import export
from app.main import app
from documents import (
    freeform_block,
    image_node,
    make_doc,
    math_node,
    multipart_block,
    para,
    part_node,
    question_block,
)
from docx import Document
from exam_engine import generate
from exam_engine.mcq import to_mcq
from fastapi.testclient import TestClient
from images import jpeg, png
from test_export_api import requires_chromium

client = TestClient(app)
ALICE = {"X-Dev-Owner": "alice"}
BOB = {"X-Dev-Owner": "bob"}
SECRET = "Zebra-answer-4217"
FIGURE = generate("geometry_angle_folded", 3)  # a part figure, not a worked model
TABLE = generate("postage_table", 1)
MCQ = to_mcq(generate("ratio_easy", 1), 1)


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXAM_DEV_AUTH", "1")
    monkeypatch.setenv("EXAM_DOCS_PATH", str(tmp_path / "docs.sqlite3"))
    monkeypatch.setenv("EXAM_ASSETS_PATH", str(tmp_path / "assets.sqlite3"))
    monkeypatch.setenv("EXAM_USAGE_PATH", str(tmp_path / "usage.sqlite3"))


@pytest.fixture
def raster(monkeypatch):
    """Stand in for Chromium: every figure becomes a 200 x 100 PNG."""
    calls: list[int] = []

    def fake(svgs: list[str]) -> list[bytes | None]:
        calls.append(len(svgs))
        return [png(200, 100) for _ in svgs]

    monkeypatch.setattr(export, "html_to_png_many", fake)
    return calls


def _section(mode: str, title: str = "Section B") -> dict:
    attrs = {"title": title, "instructions": "Show your working.", "mode": mode}
    return {"type": "section", "attrs": {**attrs, "marks_target": None}}


def _paper(asset_id: str, *, key_style: str = "worked") -> dict:
    image_q = freeform_block("Look at the photo.", marks=1, answer=SECRET)
    image_q["content"].append({"type": "paragraph", "content": [math_node(r"\frac{3}{4}")]})
    image_q["content"].append(image_node(asset_id))
    doc = make_doc(
        {
            "type": "coverPage",
            "attrs": {"school": "Example Primary", "subject": "Mathematics", "paper": "Paper 2"},
        },
        {"type": "blankPage", "attrs": {"kind": "blank"}},
        _section("mcq", "Section A"),
        question_block(MCQ),
        _section("structured"),
        question_block(FIGURE),
        question_block(TABLE),
        image_q,
        multipart_block(
            part_node("Find the volume.", marks=2, answer="1200 cm3", ans_unit="cm^3"),
            part_node("Find the height.", marks=3, answer="Height-answer-77"),
        ),
        title="Docx paper",
    )
    doc["settings"] = {"key_options": {"layout": "full" if key_style == "worked" else "compact"}}
    return doc


def _create(document: dict, headers=ALICE) -> str:
    rec = client.post("/documents", json={"title": "Docx paper"}, headers=headers).json()
    saved = client.put(
        f"/documents/{rec['id']}",
        json={"document": document, "base_version": rec["version"]},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    return rec["id"]


def _asset(headers=ALICE) -> str:
    resp = client.post("/assets", content=png(40, 20), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _export(doc_id: str, mode: str, headers=ALICE, **params):
    return client.post(
        f"/documents/{doc_id}/export/docx", params={"mode": mode, **params}, headers=headers
    )


def _all_text(data: bytes) -> str:
    """Every word in the document body, equations included, in order."""
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
    return " ".join(re.findall(r"<(?:w|m):t(?: [^>]*)?>([^<]*)<", xml))


def _paragraphs(data: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(data)).paragraphs]


def test_student_paper_keeps_the_papers_structure(raster):
    doc_id = _create(_paper(_asset()))
    resp = _export(doc_id, "student")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert resp.headers["content-disposition"].endswith('filename="docx-paper-student.docx"')

    word = Document(io.BytesIO(resp.content))  # opens
    paras = [p.text for p in word.paragraphs]
    numbered = [t.split("\t")[0] for t in paras if re.match(r"^\d+\.\t", t)]
    assert numbered == ["1.", "2.", "3.", "4.", "5."]  # the questions, in order
    text = "\n".join(paras)
    assert "Example Primary" in text and "Paper 2" in text  # the cover
    assert "This page is intentionally left blank." in text
    assert "Show your working." in text  # section instructions
    # MCQ options one to a line, numbered
    assert [t for t in paras if re.match(r"^\(\d\)\t", t)] == [
        f"({o['label']})\t{o['text']}" for o in MCQ["question"]["parts"][0]["answer"]["options"]
    ]
    # marks in brackets, parts lettered, Ans: lines with their units
    assert any(t.endswith("[1]") for t in paras)
    assert any(t.startswith("(a) Find the volume.") for t in paras)
    assert any(t.startswith("Ans: (b)") and t.endswith("[3]") for t in paras)
    assert any(t.startswith("Ans: (a)") and t.endswith("cm3   [2]") for t in paras)  # cm^3
    assert "End of Paper" in text
    # a real table: the cover's fields and the postage data table
    cells = [c.text for t in word.tables for row in t.rows for c in row.cells]
    assert "Name:" in cells and "Up to 20 g" in cells and "$0.48" in cells
    # page breaks: after the cover, around the blank page, each structured question
    breaks = sum(1 for p in word.paragraphs if p.paragraph_format.page_break_before)
    breaks += sum(
        1 for t in word.tables if t.cell(0, 0).paragraphs[0].paragraph_format.page_break_before
    )
    assert breaks >= 5
    # the figure is rasterised once and embedded, the uploaded image too, the fraction is an
    # equation
    assert raster == [1]
    assert len(word.inline_shapes) == 2
    xml = zipfile.ZipFile(io.BytesIO(resp.content)).read("word/document.xml").decode()
    assert "<m:f>" in xml


def test_student_paper_leaks_no_answer(raster):
    doc_id = _create(_paper(_asset()))
    text = _all_text(_export(doc_id, "student").content)
    assert SECRET not in text and "Height-answer-77" not in text and "1200 cm3" not in text
    assert "Answer:" not in text and "No answer written yet" not in text
    for obj in (FIGURE, TABLE, MCQ):
        for part in obj["question"]["parts"]:
            for step in part["solution_steps"]:
                assert step["text"] not in text
            for mark in part["marking_scheme"]:
                assert mark["description"] not in text
    assert "$2.61" not in text  # the postage answer
    # nothing in the package's metadata either
    package = zipfile.ZipFile(io.BytesIO(_export(doc_id, "student").content))
    for name in package.namelist():
        if name.endswith(".xml"):
            assert SECRET not in package.read(name).decode(errors="ignore")


def test_worked_key_has_the_answers_and_steps(raster):
    doc_id = _create(_paper(_asset()))
    resp = _export(doc_id, "key")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].endswith('filename="docx-paper-answer-key.docx"')
    text = _all_text(resp.content)
    assert SECRET in text and "Height-answer-77" in text
    assert "$2.61" in text
    assert TABLE["question"]["parts"][0]["solution_steps"][0]["text"] in text
    assert "Answer Key" in text


def test_school_key_is_a_table_with_an_answer_grid(raster):
    doc_id = _create(_paper(_asset(), key_style="school"))
    resp = _export(doc_id, "key")
    word = Document(io.BytesIO(resp.content))
    cells = [c.text for t in word.tables for row in t.rows for c in row.cells]
    assert "Q1" in cells and MCQ["question"]["parts"][0]["answer"]["correct"] in cells
    assert any(SECRET in c for c in cells) and any("$2.61" in c for c in cells)
    assert "Paper 2" in "\n".join(_paragraphs(resp.content))


def test_no_figures_never_starts_a_browser(raster):
    doc_id = _create(make_doc(freeform_block("Add 2 and 3.", answer="5")))
    assert _export(doc_id, "student").status_code == 200
    assert raster == []


def test_owner_scoping_and_checks(raster):
    doc_id = _create(make_doc(freeform_block("Add.", answer="5")))
    assert _export(doc_id, "student", BOB).status_code == 404
    assert client.post("/documents/missing/export/docx", headers=ALICE).status_code == 404
    assert _export(doc_id, "full").status_code == 422  # Word has a paper and a key, not both
    empty = _create(make_doc(para("Just text.")))
    assert _export(empty, "key").status_code == 422


def test_empty_placeholders_are_refused_unless_allowed(raster):
    block = freeform_block("", marks=2)
    block["content"] = [{"type": "paragraph"}]
    block["attrs"]["slot"] = {"marks": 2, "kind": "short", "placeholder": True}
    doc_id = _create(make_doc(block))
    refused = _export(doc_id, "student")  # the same rule as the PDF (EXA-137)
    assert refused.status_code == 409 and refused.json()["detail"]["questions"] == [1]
    assert _export(doc_id, "student", allow_placeholders="true").status_code == 200


def test_docx_spends_the_export_allowance_like_a_pdf(raster, monkeypatch):
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "2")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_MINUTE", "0")
    monkeypatch.setattr(export, "html_to_pdf", lambda html: b"%PDF-fake")
    doc_id = _create(make_doc(freeform_block("Add.", answer="5")))
    assert _export(doc_id, "student").status_code == 200
    assert client.post(f"/documents/{doc_id}/export/student", headers=ALICE).status_code == 200
    refused = _export(doc_id, "key")
    assert refused.status_code == 429 and int(refused.headers["retry-after"]) > 0


def test_a_failed_figure_render_is_refunded(monkeypatch):
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_DAY", "1")
    monkeypatch.setenv("EXAM_EXPORT_LIMIT_PER_MINUTE", "0")

    def boom(svgs):
        raise RuntimeError("chromium crashed")

    monkeypatch.setattr(export, "html_to_png_many", boom)
    doc_id = _create(make_doc(question_block(FIGURE)))
    failing = TestClient(app, raise_server_exceptions=False)
    assert failing.post(f"/documents/{doc_id}/export/docx", headers=ALICE).status_code == 500
    monkeypatch.setattr(export, "html_to_png_many", lambda svgs: [png() for _ in svgs])
    assert _export(doc_id, "student").status_code == 200


@requires_chromium
def test_figures_are_rasterised_at_print_size():
    doc_id = _create(make_doc(question_block(FIGURE)))
    word = Document(io.BytesIO(_export(doc_id, "student").content))
    (shape,) = word.inline_shapes
    assert 20 < shape.width.mm <= 178  # its print width, never wider than the text


def test_latex_becomes_a_word_equation_or_stays_as_typed():
    from app import docx_math
    from lxml import etree

    latex = r"\left(42\pi + 84\right)\ \text{cm}^{2}"
    xml = etree.tostring(docx_math.omath(latex), encoding="unicode")
    assert "π" in xml and "<m:sSup>" in xml and "<m:nor/>" in xml
    assert "<m:f>" in etree.tostring(docx_math.omath(r"\$\frac{3}{4}"), encoding="unicode")
    for unsupported in (r"\int_0^1 x", r"\frac{1}{2", "a}"):
        with pytest.raises(docx_math.Unsupported):
            docx_math.omath(unsupported)


@pytest.mark.parametrize("template", ["p1_booklet_a", "p1_booklet_b", "p2"])
@pytest.mark.parametrize("style", ["school", "worked"])
def test_every_generated_paper_builds(template, style):
    """Every blueprint a generated paper can hold goes through the builder in both modes."""
    from app.docx_export import build_docx
    from exam_engine import document as docs
    from exam_engine import paper

    for seed in (1, 2, 3):
        doc, _ = paper.generate_paper(template, "P6" if seed % 2 else "P5", seed)
        doc = docs.with_key_style(doc, style)
        for mode in ("student", "key"):
            data = build_docx("P", doc, mode=mode, rasterise=lambda s: [png() for _ in s])
            assert Document(io.BytesIO(data)).paragraphs


def test_text_xml_cannot_hold_is_dropped_not_fatal(raster):
    """A vertical tab pasted from Word (and other C0 controls) passes the schema and the PDF."""
    bad = "Line\x0bone\x0c\x01\x1f\ufffe end"
    block = freeform_block(bad, marks=2, answer=f"Ans\x0b{bad}")
    block["content"].append({"type": "paragraph", "content": [math_node("\\frac{1\x0b}{2}")]})
    doc_id = _create(make_doc(block, title="Paste\x0b test"))
    for mode in ("student", "key"):
        resp = _export(doc_id, mode)
        assert resp.status_code == 200, resp.text
        assert "Lineone end" in _all_text(resp.content)


def test_a_jpeg_without_a_jfif_header_prints_as_unavailable(raster):
    adobe = b"\xff\xee\x00\x0eAdobe\x00\x64\x00\x00\x00\x00\x01"
    data = jpeg().replace(b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00", adobe)
    asset = client.post("/assets", content=data, headers=ALICE)
    assert asset.status_code == 201, asset.text  # the upload gate takes it
    block = freeform_block("See the photo.", marks=1)
    block["content"].append(image_node(asset.json()["id"]))
    resp = _export(_create(make_doc(block)), "student")
    assert resp.status_code == 200
    assert "[image unavailable]" in _all_text(resp.content)


def test_deeply_nested_latex_falls_back_to_text():
    from app import docx_math

    for latex in ("{" * 3000 + "x" + "}" * 3000, r"\frac" * 3000 + "12"):
        with pytest.raises(docx_math.Unsupported):
            docx_math.omath(latex)
    assert docx_math.omath(r"\frac{\frac{1}{2}}{3}") is not None


def test_a_question_keeps_together_and_the_file_says_what_it_is(raster):
    from datetime import UTC, datetime, timedelta

    doc_id = _create(_paper(_asset()))
    word = Document(io.BytesIO(_export(doc_id, "student").content))
    paras = word.paragraphs
    stem = next(p for p in paras if p.text.startswith("1.\t"))
    assert stem.paragraph_format.keep_with_next  # the stem stays with its options
    last_option = [p for p in paras if re.match(r"^\(\d\)\t", p.text)][-1]
    assert not last_option.paragraph_format.keep_with_next  # the next question may break
    assert not any(p.paragraph_format.keep_with_next for p in paras if p.text.startswith("Ans:"))
    props = word.core_properties
    assert props.title == "Docx paper"
    assert abs(datetime.now(UTC) - props.created) < timedelta(days=1)
    xml = zipfile.ZipFile(io.BytesIO(_export(doc_id, "student").content)).read("word/document.xml")
    assert b'descr="A figure"' in xml and b'descr="Figure"' in xml  # the image's alt, a figure's
