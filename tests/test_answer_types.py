"""EXA-155 — a blueprint's declared answer types are honest, and the paper generator routes on
all of them.

The YAML ``answer.type`` (or ``answer.types``, every type a blueprint can give) is what
``paper._fits`` reads to decide whether a blueprint may fill a multiple-choice slot. Before
EXA-155, circles_hard declared ``decimal`` while one template answered in terms of π (an
``expression``): safe only because a 3-mark question never fills an mcq slot. Here every
blueprint is swept through the real ``generate()`` and each answer's type must be declared
(integer, decimal and quantity count as one kind, a number: they print and convert alike).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from exam_engine.blueprints.registry import load_blueprint
from exam_engine.mcq import convertible, to_mcq
from exam_engine.paper import Candidate, _fits, candidates
from exam_engine.pipeline import generate

BLUEPRINTS = sorted(
    p.stem
    for p in (Path(__file__).resolve().parents[1] / "engine/exam_engine/content/blueprints").glob(
        "*.yaml"
    )
)
SEEDS = range(1, 121)
_NUMBER = {"integer", "decimal", "quantity"}


def _kind(answer_type: str) -> str:
    return "number" if answer_type in _NUMBER else answer_type


@pytest.mark.parametrize("code", BLUEPRINTS)
def test_every_answer_type_a_blueprint_gives_is_declared(code):
    declared = {_kind(t) for t in load_blueprint(code).answer_types}
    for seed in SEEDS:
        for part in generate(code, seed)["question"]["parts"]:
            got = part["answer"]["type"]
            assert _kind(got) in declared, (code, seed, got, declared)


def test_the_hard_circles_rung_declares_its_answers_in_terms_of_pi():
    assert "expression" in load_blueprint("circles_hard").answer_types


def _candidate(*types: str) -> Candidate:
    return Candidate("x", "T", "P6", 2, "constructed", answer_types=types)


def test_an_mcq_slot_needs_every_declared_answer_type_convertible():
    assert _fits(_candidate("integer", "decimal", "expression"), "mcq")
    assert not _fits(_candidate("decimal", "text"), "mcq")  # one text answer is enough to bar
    assert not _fits(_candidate(), "mcq")  # nothing declared: not routed by accident
    assert _fits(_candidate("decimal", "text"), "short")


@pytest.mark.parametrize("level", ["P5", "P6"])
def test_every_blueprint_an_mcq_slot_may_take_converts_on_every_seed(level):
    """The routing promise: a blueprint ``_fits`` an mcq slot only if every question it
    generates converts to multiple choice (``to_mcq`` never raises in a paper)."""
    for c in candidates(level):
        if not _fits(c, "mcq"):
            continue
        for seed in range(1, 41):
            obj = generate(c.code, seed)
            assert convertible(obj), (c.code, seed)
            to_mcq(obj, seed)
