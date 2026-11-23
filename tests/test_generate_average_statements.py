"""Generation suite for ``average_statements`` and the ``tick_table`` answer (EXA-158, schema
1.16.0): the load gate, the printed table (empty boxes on the paper, ticks in both keys), no
multiple-choice copy, the snapshot check, conversion to a free-form question, and the goldens.
The correctness authority is ``test_invariants_average_statements.py``."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from documents import make_doc, question_block
from exam_engine import canonical, convert, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.canonical import CanonicalValidationError
from exam_engine.document import verify_snapshot, wording_differences
from exam_engine.errors import EditNotApplicable
from exam_engine.render import (
    render_answer_key_html,
    render_document_html,
    render_question_fragment,
    render_worksheet_html,
)

GOLDEN = Path(__file__).parent / "golden"
CODE = "average_statements"


def _obj(seed: int = 3) -> dict:
    return generate(CODE, seed)


def _answer(obj: dict) -> dict:
    return obj["question"]["parts"][0]["answer"]


def test_objects_are_schema_valid_deterministic_and_varied():
    obj = _obj()
    assert obj["schema_version"] == "1.17.0"
    assert canonical.load(copy.deepcopy(obj)) == obj
    assert generate(CODE, 3) == obj
    assert len({json.dumps(_answer(generate(CODE, s))) for s in range(1, 21)}) == 20


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (lambda a: a["rows"][0].update(tick="Maybe"), "schema"),
        (lambda a: a["columns"].remove("Not possible to tell") or None, "ticks_in_columns"),
        (lambda a: a["rows"][1].update(statement=a["rows"][0]["statement"]), "distinct"),
        (lambda a: a["columns"].append("Yes"), "schema"),
        (lambda a: a["columns"].append("True"), "schema"),
    ],
)
def test_the_load_gate_rejects_an_inconsistent_table(change, error):
    obj = _obj()
    answer = _answer(obj)
    for row in answer["rows"]:
        row["tick"] = "Not possible to tell"
    change(answer)
    with pytest.raises(CanonicalValidationError) as exc:
        canonical.load(obj)
    if error != "schema":
        assert "tick_table inconsistent: " in str(exc.value) and error in str(exc.value)


def _boxes(html: str) -> tuple[int, int]:
    """(boxes, ticked boxes) in the printed tick tables."""
    return html.count('<td class="tick-box">'), html.count('<svg class="tick"')


def test_the_paper_prints_empty_boxes_and_the_keys_print_the_ticks():
    obj = _obj()
    rows = _answer(obj)["rows"]
    sheet = render_worksheet_html("T", [obj])
    assert _boxes(sheet) == (9, 0)
    assert all(r["statement"] in sheet for r in rows)
    assert "answer-space" not in sheet.split("<main")[1]  # the table is the answer surface
    key = render_answer_key_html("T", [obj])
    assert _boxes(key) == (9, 3)
    assert "Answer:" not in key  # the ticked table is the answer

    doc = make_doc(question_block(obj))
    paper = render_document_html("T", doc, mode="student")
    assert _boxes(paper) == (9, 0) and "answer-line" not in paper.split("<main")[1]
    assert _boxes(render_document_html("T", doc, mode="full")) == (18, 3)
    for options in (
        {"layout": "compact", "show_question": False},
        {"layout": "full", "show_question": False},
        {"layout": "full", "show_question": True},
    ):
        doc["settings"] = {"key_options": options}
        assert _boxes(render_document_html("T", doc, mode="key")) == (9, 3), options

    fragment = render_question_fragment(obj, placement="answer", answer_area=False)
    assert _boxes(fragment) == (9, 0) and "[2]" in fragment
    assert _boxes(render_question_fragment(obj, mode="key")) == (9, 3)


def test_the_ticks_sit_in_the_right_columns():
    obj = _obj()
    key = render_answer_key_html("T", [obj])
    table = key[key.index('<table class="tick-table">') :]
    body_rows = table.split("<tbody>")[1].split("</tbody>")[0].split("</tr>")[:-1]
    for row, html in zip(_answer(obj)["rows"], body_rows, strict=True):
        boxes = html.split('<td class="tick-box">')[1:]
        ticked = [i for i, b in enumerate(boxes) if b.startswith("<svg")]
        assert ticked == [_answer(obj)["columns"].index(row["tick"])]


def test_no_multiple_choice_copy():
    obj = _obj()
    assert not mcq.convertible(obj)
    with pytest.raises(EditNotApplicable):
        mcq.to_mcq(obj, 1)
    from exam_engine.paper import Candidate, _fits

    spec = load_blueprint(CODE)
    c = Candidate(CODE, "Average", "P5", 2, "constructed", spec.answer_types, "medium")
    assert spec.answer_types == ("tick_table",)
    assert not _fits(c, "mcq") and _fits(c, "short") and _fits(c, "structured")


@pytest.mark.parametrize(
    "tamper",
    [
        lambda a: a["rows"][0].update(
            tick=next(c for c in a["columns"] if c != a["rows"][0]["tick"])
        ),
        lambda a: a["rows"].reverse(),
        lambda a: a["rows"].pop(),
        lambda a: a["columns"].pop(),
    ],
)
def test_a_tampered_tick_does_not_verify(tamper):
    obj = _obj(2)
    assert len({r["tick"] for r in _answer(obj)["rows"]}) == 3  # reversing moves every tick
    assert verify_snapshot(obj) == []
    tamper(_answer(obj))
    assert verify_snapshot(obj) != []


def test_changed_words_lose_the_verified_claim():
    """EXA-157: a statement or the question text that is not the engine's is flagged (the
    question becomes unverified); the untouched question is not."""
    obj = _obj()
    assert wording_differences(obj) == []
    row = _answer(obj)["rows"][1]
    row["statement"] = row["statement"].replace(" P,", " P, S,")
    assert verify_snapshot(obj) == [] and wording_differences(obj) == ["statements"]
    obj = _obj()
    obj["question"]["parts"][0]["text"] = obj["question"]["parts"][0]["text"].replace("3", "4")
    assert wording_differences(obj) == ["question text"]


def test_a_count_for_s_with_three_containers_does_not_verify():
    """The stem prints S only with four containers: a ``known`` on three would change every tick
    without the printed facts saying so (e.g. "fewer than 26" ticked Not possible to tell)."""
    solver = get_solver(CODE)
    for seed in range(1, 40):
        obj = _obj(seed)
        params = obj["parameters"]
        forged = copy.deepcopy(obj)
        if params["count"] == 3:
            forged["parameters"]["known"] = params["average"]
        else:
            forged["parameters"]["known"] = None
        p = forged["parameters"]
        if p["known"] is not None:
            assert solver.validate(p, solver.solve(p))["ok"] is False
            forged["question"]["parts"][0]["answer"] = solver.solve(p)["answer"]
        assert verify_snapshot(forged) != [], seed


def test_the_school_key_shows_the_marks_without_an_empty_ans_line():
    doc = make_doc(question_block(_obj()))
    doc["settings"] = {"key_options": {"layout": "compact", "show_marks": True}}
    key = render_document_html("T", doc, mode="key")
    work = key[key.index('<td class="key-work">') :]
    assert "Ans:" not in work.split("</td>")[0].split('<table class="tick-table">')[0]
    after = work.split("</table>", 1)[1]
    assert after.startswith('<p class="key-ans"> <span class="key-marks">[2]</span></p>')


def test_conversion_keeps_the_statements_in_the_body_and_the_ticks_in_the_answer():
    obj = _obj()
    pieces = convert.to_freeform(obj)
    body, answer = json.dumps(pieces["body"]), json.dumps(pieces["answer"])
    for row in _answer(obj)["rows"]:
        assert row["statement"] in body
    assert "Not possible to tell" in answer
    assert pieces["marks"] == 2


def test_golden_fixtures():
    """Engine output pinned for params the owner checks by hand (ADR-0003)."""
    solver = get_solver(CODE)
    lines = [ln for ln in (GOLDEN / f"{CODE}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(CODE).marks == rec["expected"]["total_marks"]
