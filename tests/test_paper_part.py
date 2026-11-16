"""O3 — ``document.paper_part``: which exam-set paper a document is, from its cover page's
``paper`` field (survives a rename), falling back to the title."""

from __future__ import annotations

import pytest
from exam_engine import paper
from exam_engine.document import empty_document, paper_part, validate_document


@pytest.mark.parametrize(
    ("code", "part"),
    [("p1_booklet_a", "booklet_a"), ("p1_booklet_b", "booklet_b"), ("p2", "paper_2")],
)
def test_every_template_and_generated_paper_names_its_part(code, part):
    starter = paper.template_document(code)
    generated, _ = paper.generate_paper(code, "P6", 3)
    assert paper_part(starter) == part
    assert paper_part(generated) == part


def test_the_cover_wins_over_a_renamed_title():
    doc = paper.template_document("p1_booklet_b")
    doc["title"] = "Term 3 practice (was Paper 2)"
    validate_document(doc)
    assert paper_part(doc) == "booklet_b"


@pytest.mark.parametrize(
    ("title", "part"),
    [
        ("P6 Paper 1 Booklet A", "booklet_a"),
        ("booklet b revision", "booklet_b"),
        ("Prelim Paper 2", "paper_2"),
        ("Paper II", "paper_2"),
        ("Paper 1", None),
        ("Paper 20 drafts", None),
        ("Untitled paper", None),
    ],
)
def test_without_a_cover_the_title_decides(title, part):
    assert paper_part(empty_document(title)) == part


def test_a_cover_naming_no_part_falls_back_to_the_title():
    doc = paper.template_document("p2")
    doc["content"]["content"][0]["attrs"]["paper"] = "Mock"
    assert paper_part(doc) == "paper_2"  # title "Paper 2"
    doc["title"] = "Mock exam"
    assert paper_part(doc) is None
    doc["content"]["content"][0]["attrs"]["paper"] = None
    assert paper_part(doc) is None


def test_malformed_input_is_none_not_an_error():
    assert paper_part({}) is None
    assert paper_part({"title": "Booklet A", "content": {}}) == "booklet_a"
