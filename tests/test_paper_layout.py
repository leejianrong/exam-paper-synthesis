"""P2 — working space, the Ans: line (with its unit) and marks placement on a paper."""

from __future__ import annotations

import copy
import re

import pytest
from documents import freeform_block, gen_block, make_doc
from exam_engine import generate
from exam_engine.document import validate_document
from exam_engine.render import (
    default_space_mm,
    render_document_html,
    render_question_fragment,
    unit_parts,
)


def _html(doc: dict, mode: str = "student") -> str:
    return render_document_html("Paper", doc, mode=mode)


def _heights(html: str) -> list[int]:
    return [int(m) for m in re.findall(r'class="answer-space"[^>]*style="height:(\d+)mm"', html)]


def test_default_space_grows_with_marks_and_beats_the_old_box():
    assert [default_space_mm(m) for m in (1, 2, 3, 4)] == [35, 50, 65, 80]
    assert default_space_mm(None) == default_space_mm(2)
    assert default_space_mm(0) == default_space_mm(1)
    # the old box was 18px + 16px per mark (~13 mm for a 2-mark question)
    assert default_space_mm(2) > 3 * 13


def test_space_override_and_default_on_both_block_kinds():
    doc = make_doc(
        freeform_block("a", marks=3),
        freeform_block("b", marks=3),
        gen_block("fractions_easy", 1),
    )
    doc["content"]["content"][1]["attrs"]["space_mm"] = 120
    got = _heights(_html(doc))
    assert got[0] == default_space_mm(3) and got[1] == 120
    assert len(got) == 3


def test_answer_line_prints_the_unit_so_students_need_not_pick_one():
    q = generate("volume_easy", 1)
    unit = q["question"]["parts"][0]["answer"]["unit"]
    assert unit in ("cm^3", "l")
    html = _html(
        make_doc({"type": "templatedQuestion", "attrs": {"block_id": "t_0001", "question": q}})
    )
    line = re.search(r'<div class="answer-line">.*?</div>', html).group(0)
    assert "Ans:" in line and 'class="ans-blank"' in line
    assert ("<sup>3</sup>" in line) or ("l</span>" in line)


@pytest.mark.parametrize(
    "unit,before,after",
    [
        ("$", "$", ""),
        ("degrees", "", "°"),
        ("%", "", "%"),
        ("cm^2", "", "cm<sup>2</sup>"),
        ("m^3", "", "m<sup>3</sup>"),
        ("km/h", "", "km/h"),
        ("", "", ""),
        (None, "", ""),
        ("<b>", "", "&lt;b&gt;"),
    ],
)
def test_unit_parts(unit, before, after):
    assert unit_parts(unit) == (before, after)


def test_freeform_unit_comes_from_the_block_and_a_blank_line_has_no_unit():
    doc = make_doc(freeform_block("q", marks=1), freeform_block("r", marks=1))
    doc["content"]["content"][0]["attrs"]["ans_unit"] = "degrees"
    html = _html(doc)
    lines = re.findall(r'<div class="answer-line">.*?</div>', html)
    assert "°" in lines[0] and "ans-unit" not in lines[1]


def test_a_templated_blocks_unit_can_be_overridden():
    q = generate("volume_easy", 1)
    block = {"type": "templatedQuestion", "attrs": {"block_id": "t_0001", "question": q}}
    block["attrs"]["ans_unit"] = "m"
    line = re.search(r'<div class="answer-line">.*?</div>', _html(make_doc(block))).group(0)
    assert ">m</span>" in line and "<sup>" not in line


def test_marks_placement_question_answer_both_default_answer():
    base = make_doc(freeform_block("Find x.", marks=2))

    def where(placement):
        doc = copy.deepcopy(base)
        if placement:
            doc["settings"] = {"marks_placement": placement}
        html = _html(doc)
        head = '<span class="marks">[2]</span></div><div class="answer-space"'
        line = re.search(r'<div class="answer-line">.*?</div>', html).group(0)
        return (head in html, "[2]" in line)

    assert where(None) == (False, True)  # default: beside the answer line
    assert where("answer") == (False, True)
    assert where("question") == (True, False)
    assert where("both") == (True, True)


def test_the_key_always_shows_marks_and_has_no_answer_line():
    doc = make_doc(freeform_block("q", marks=2, answer="4"))
    key = _html(doc, "key")
    assert "[2]" in key
    assert '<div class="answer-line"' not in key and '<div class="answer-space"' not in key


def test_multipart_parts_each_get_a_labelled_line_and_space():
    q = generate("ratio_medium", 1)
    q["question"]["parts"] = [
        {**copy.deepcopy(q["question"]["parts"][0]), "label": "a", "marks": 1},
        {**copy.deepcopy(q["question"]["parts"][0]), "label": "b", "marks": 2},
    ]
    q["question"]["total_marks"] = 3
    html = _html(
        make_doc({"type": "templatedQuestion", "attrs": {"block_id": "t_0001", "question": q}})
    )
    assert re.findall(r'<span class="ans-part">\((\w)\)</span>', html) == ["a", "b"]
    assert _heights(html) == [default_space_mm(1), default_space_mm(2)]


def test_mcq_and_constructions_get_no_space_or_line():
    import json
    from pathlib import Path

    src = Path(__file__).parent / "fixtures" / "sourced" / "standin_cubestack_view.json"
    q = json.loads(src.read_text("utf-8"))
    html = _html(
        make_doc({"type": "templatedQuestion", "attrs": {"block_id": "t_0001", "question": q}})
    )
    assert '<div class="answer-space"' not in html and '<div class="answer-line"' not in html


def test_classic_worksheet_look_is_unchanged_without_a_layout():
    q = generate("ratio_medium", 1)
    frag = render_question_fragment(q)
    assert "--marks:" in frag and "answer-line" not in frag


def test_fragment_can_leave_the_answer_area_to_the_editor():
    q = generate("ratio_medium", 1)
    frag = render_question_fragment(q, placement="answer", answer_area=False)
    assert "answer-space" not in frag and "answer-line" not in frag
    assert '<span class="marks">' not in frag  # marks belong to the Ans: line
    on_q = render_question_fragment(q, placement="question", answer_area=False)
    assert '<span class="marks">' in on_q


def test_schema_accepts_the_new_fields_and_old_documents_still_validate():
    doc = make_doc(freeform_block("q"), gen_block())
    doc["settings"] = {"marks_placement": "both"}
    for b in doc["content"]["content"]:
        b["attrs"].update(space_mm=80, ans_unit="cm")
    assert validate_document(doc) == []
    legacy = make_doc(freeform_block("q"), gen_block())
    legacy["schema_version"] = "1.3.0"
    assert validate_document(legacy) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["content"]["content"][0]["attrs"].update(space_mm=-1),
        lambda d: d["content"]["content"][0]["attrs"].update(space_mm=251),
        lambda d: d["content"]["content"][0]["attrs"].update(space_mm=1.5),
        lambda d: d["content"]["content"][0]["attrs"].update(ans_unit="x" * 13),
        lambda d: d.update(settings={"marks_placement": "nowhere"}),
        lambda d: d.update(settings={"other": 1}),
    ],
)
def test_schema_rejects_bad_layout_values(mutate):
    doc = make_doc(freeform_block("q"))
    mutate(doc)
    assert validate_document(doc)
