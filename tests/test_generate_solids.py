"""Generation suite for the solids blueprints (EXA-147): cube stacks and nets.

Schema-valid, load-gated, tagged, deterministic, on no ladder, goldens (a person checks them,
see the PR); the two counting blueprints convert to multiple choice through their distractors
hook; the two that ask multiple choice themselves go into a paper's MCQ slots as they are,
only there, and stay engine-proven (a tampered option is caught).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from exam_engine import canonical, edits, generate, mcq
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.document import verify_snapshot
from exam_engine.ladder import ladder_for
from exam_engine.paper import _fits, as_slot_question, candidates, generate_paper
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

GOLDEN = Path(__file__).parent / "golden"
SEEDS = [1, 2, 7, 42, 100, 999, 123456]
CASES = {
    # code: (level, topic, marks, rung, answer type, diagram)
    "cubes_count": ("P5", "Solids", 1, "easy", "integer", "cube_stack"),
    "cubes_complete": ("P5", "Solids", 2, "medium", "integer", "cube_stack"),
    "cubes_view": ("P6", "Solids", 1, "easy", "choice", "cube_stack"),
    "net_opposite": ("P6", "Nets", 1, "easy", "choice", "net"),
}
NUMERIC = ["cubes_count", "cubes_complete"]
CHOICE = ["cubes_view", "net_opposite"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("code", CASES)
def test_generate_is_valid_tagged_and_load_gated(code, seed):
    level, topic, marks, rung, atype, dtype = CASES[code]
    obj = generate(code, seed)
    assert validate_object(obj) == []
    canonical.load(obj)
    assert obj["syllabus"]["level"] == level and obj["syllabus"]["topic"] == topic
    assert obj["syllabus"]["strand"] == "Geometry"
    assert obj["cognitive"]["difficulty"] == rung
    parts = obj["question"]["parts"]
    assert len(parts) == 1 and obj["question"]["total_marks"] == marks
    assert parts[0]["answer"]["type"] == atype and parts[0]["diagram"]["type"] == dtype
    assert obj["validation"]["status"] == "pass"
    assert verify_snapshot(obj) == []


@pytest.mark.parametrize("code", CASES)
def test_deterministic_and_varied(code):
    assert generate(code, 5) == generate(code, 5)
    figures = {json.dumps(generate(code, s)["question"]["parts"][0]["diagram"]) for s in SEEDS}
    assert len(figures) >= len(SEEDS) - 1


@pytest.mark.parametrize("code", CASES)
def test_on_no_ladder(code):
    assert ladder_for(code) is None
    ops = edits.available_ops(generate(code, 3))
    assert ops == (set() if code in CHOICE else {"regenerate"})


@pytest.mark.parametrize("code", CASES)
def test_worksheet_shows_the_figure_and_hides_the_answer(code):
    obj = generate(code, 3)
    paper = render_worksheet_html("P", [obj])
    assert "<svg" in paper and "Answer:" not in paper
    assert "Answer:" in render_answer_key_html("P", [obj])
    if code in CHOICE:
        assert 'class="option option-correct"' not in paper
        assert 'class="option option-correct"' in render_answer_key_html("P", [obj])


def test_view_options_are_pictures_and_net_options_are_letters():
    for seed in range(1, 41):
        view = generate("cubes_view", seed)["question"]["parts"][0]["answer"]
        assert [o["label"] for o in view["options"]] == ["1", "2", "3", "4"]
        assert all(o["text"] is None for o in view["options"])
        assert all(o["diagram"]["type"] == "cube_stack" for o in view["options"])
        assert all("title" not in o["diagram"] for o in view["options"])  # no give-away captions
        net = generate("net_opposite", seed)["question"]["parts"][0]["answer"]
        texts = [o["text"] for o in net["options"]]
        assert texts == sorted(texts) and len(set(texts)) == 4
        assert all(len(t) == 1 and "A" <= t <= "F" for t in texts)


@pytest.mark.parametrize("code", NUMERIC)
def test_mcq_copies_use_the_hook_and_stay_proven(code):
    """The counting blueprints go into Booklet A as MCQs: most wrong options are named
    counting slips (the hook), never the answer, and the copy verifies."""
    from_hook = 0
    for seed in range(1, 61):
        obj = generate(code, seed)
        m = mcq.to_mcq(obj, seed)
        assert verify_snapshot(m) == []
        answer = m["question"]["parts"][0]["answer"]
        hooked = {str(int(v)) for v, _ in mcq.common_wrong_answers(obj)}
        wrong = [o["text"] for o in answer["options"] if o["label"] != answer["correct"]]
        from_hook += sum(t in hooked for t in wrong)
    assert from_hook >= 0.6 * 60 * 3


@pytest.mark.parametrize("code", NUMERIC)
def test_the_answers_place_among_the_options_gives_nothing_away(code):
    """Options print in ascending order, so the hook offers slips on both sides of the answer:
    over many seeds the answer is in every place and neither mostly the largest nor mostly
    the smallest."""
    places = [
        int(mcq.to_mcq(generate(code, s), s)["question"]["parts"][0]["answer"]["correct"])
        for s in range(1, 201)
    ]
    share = {p: places.count(p) / len(places) for p in (1, 2, 3, 4)}
    assert all(v >= 0.05 for v in share.values()), share
    assert share[1] <= 0.4 and share[4] <= 0.4, share
    assert max(share.values()) <= 0.5, share


def test_count_hook_names_the_hidden_cubes_slip():
    obj = generate("cubes_count", 4)
    solver = get_solver("cubes_count")
    slips = dict((why, v) for v, why in solver.distractors(obj["parameters"], {}))
    answer = obj["question"]["parts"][0]["answer"]["value"]
    assert slips["counted only the cubes that can be seen"] < answer
    assert slips["counted the hidden cubes twice"] > answer


@pytest.mark.parametrize("code", CHOICE)
def test_a_tampered_choice_is_caught(code):
    obj = generate(code, 9)
    bad = copy.deepcopy(obj)
    answer = bad["question"]["parts"][0]["answer"]
    answer["correct"] = next(
        o["label"] for o in answer["options"] if o["label"] != answer["correct"]
    )
    assert verify_snapshot(bad) != []
    swapped = copy.deepcopy(obj)
    opts = swapped["question"]["parts"][0]["answer"]["options"]
    opts[0]["diagram" if code == "cubes_view" else "text"] = opts[1][
        "diagram" if code == "cubes_view" else "text"
    ]
    assert verify_snapshot(swapped) != []


@pytest.mark.parametrize("code", CASES)
def test_a_tampered_figure_is_caught(code):
    """The drawn solid or net is the question: changing it must not keep the proof."""
    obj = generate(code, 9)
    bad = copy.deepcopy(obj)
    figure = bad["question"]["parts"][0]["diagram"]
    if figure["type"] == "cube_stack":
        figure["heights"][0][0] += 1
    else:
        figure["faces"][0]["label"], figure["faces"][1]["label"] = (
            figure["faces"][1]["label"],
            figure["faces"][0]["label"],
        )
    assert verify_snapshot(obj) == []
    assert verify_snapshot(bad) == [
        "the figure does not match the engine's figure for these parameters"
    ]


@pytest.mark.parametrize("code", CHOICE)
def test_choice_blueprints_fill_mcq_slots_only_and_unchanged(code):
    c = next(c for c in candidates("P6") if c.code == code)
    assert _fits(c, "mcq") and not _fits(c, "short") and not _fits(c, "structured")
    obj = generate(code, 4)
    assert as_slot_question(obj, "mcq", 1) is obj


def test_a_p6_booklet_a_takes_them_as_they_are():
    seen = set()
    for seed in range(1, 31):
        doc, _ = generate_paper("p1_booklet_a", "P6", seed)
        for node in doc["content"]["content"]:
            q = (node.get("attrs") or {}).get("question")
            if q and q["blueprint_code"] in CASES:
                seen.add(q["blueprint_code"])
                assert q["question"]["parts"][0]["answer"]["type"] == "choice"
                assert verify_snapshot(q) == []
    assert {"cubes_view", "net_opposite"} <= seen


@pytest.mark.parametrize("code", CASES)
def test_golden_fixtures(code):
    """Seed-picked params -> expected answer, checked by a person (ADR-0003)."""
    solver = get_solver(code)
    lines = [ln for ln in (GOLDEN / f"{code}.jsonl").read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        solution = solver.solve(rec["params"])
        assert solution["answer"] == rec["expected"]["answer"]
        assert solver.validate(rec["params"], solution)["ok"] is True
        assert load_blueprint(code).marks == rec["expected"]["total_marks"]
