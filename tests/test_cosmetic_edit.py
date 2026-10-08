"""W1a — param roles + the ``set-cosmetic`` edit (ADR-0021 tier 1).

The invariant: renaming people / swapping an item never changes the maths. After a
cosmetic edit the object is identical to the original once the old values are mapped
to the new ones — answer, marks, marking scheme, steps, diagram — and it is a valid
canonical object produced by re-solving (not string substitution).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from exam_engine import cosmetic, edits, generate
from exam_engine.blueprints.base import COSMETIC_ROLES, PARAM_ROLES, check_param_roles
from exam_engine.blueprints.registry import get_solver, load_blueprint
from exam_engine.errors import EditNotApplicable
from exam_engine.render import render_answer_key_html, render_worksheet_html
from exam_engine.schema import validate_object

BLUEPRINT_DIR = Path(__file__).parent.parent / "engine" / "exam_engine" / "content" / "blueprints"
CODES = sorted(p.stem for p in BLUEPRINT_DIR.glob("*.yaml"))
COSMETIC_CODES = [c for c in CODES if cosmetic.editable_slots(c)]
SEEDS = range(1, 21)
FRESH_NAMES = ["Zara", "Yusof", "Xin Yi", "Wafi", "Vikram"]  # none in any NAME_POOL


# --- param_roles are complete and sensible ----------------------------------


@pytest.mark.parametrize("code", CODES)
def test_param_roles_complete(code):
    spec = load_blueprint(code)  # also raises if roles are incomplete
    assert check_param_roles(code, spec) == []
    assert set(spec.param_roles) == set(spec.parameter_schema["properties"])
    assert all(e["role"] in PARAM_ROLES for e in spec.param_roles.values())


def test_missing_role_is_reported():
    spec = copy.deepcopy(load_blueprint("ratio_medium"))
    del spec.param_roles["ratio"]
    spec.param_roles["bogus"] = {"role": "name"}
    spec.param_roles["total"] = {"role": "nonsense"}
    errors = " ".join(check_param_roles("ratio_medium", spec))
    assert "'ratio' has no param_roles entry" in errors
    assert "unknown parameter 'bogus'" in errors
    assert "invalid role 'nonsense'" in errors


def test_every_blueprint_with_a_person_has_a_name_slot():
    # Guards against a template with a person being left classified as `number`.
    for code in CODES:
        spec = load_blueprint(code)
        if any(re.search(r"\{names?\d?(\[|\})", t["text"]) for t in spec.story_templates):
            assert any(e["role"] == "name" for e in spec.param_roles.values()), code


@pytest.mark.parametrize("code", CODES)
def test_templates_have_no_pronouns(code):
    """Names are unpaired slots only while no template says he/she/his/her."""
    spec = load_blueprint(code)
    texts = [t["text"] for t in spec.story_templates]
    texts += [s["text"] for s in spec.solution_template.get("steps", [])]
    for text in texts:
        assert not re.search(r"\b(he|she|his|her|hers|him|himself|herself)\b", text, re.I), text


@pytest.mark.parametrize("code", [c for c in CODES if getattr(get_solver(c), "ITEM_POOL", None)])
def test_item_pool_words_take_the_article_a(code):
    for item in get_solver(code).ITEM_POOL:
        assert item[0].lower() not in "aeiou", f"{item!r} would read 'a {item}'"


def test_item_roles_have_a_pool():
    for code in CODES:
        for slot in cosmetic.editable_slots(code):
            if slot["role"] == "item":
                assert slot["pool"], code


# --- the invariant, swept ---------------------------------------------------


def _tokenise(obj: dict, old: list[str]) -> str:
    """The question part as JSON with each edited value replaced by a stable token."""
    text = json.dumps(obj["question"], sort_keys=True, ensure_ascii=False)
    for i, value in sorted(enumerate(old), key=lambda p: -len(p[1])):
        text = text.replace(value, f"@@{i}@@")
    return text


def _changes_for(code: str, params: dict) -> tuple[dict, list[str], list[str]]:
    """Cosmetic changes touching every slot, plus the (old, new) values in order."""
    changes: dict = {}
    old: list[str] = []
    new: list[str] = []
    fresh = iter(FRESH_NAMES)
    for slot in cosmetic.editable_slots(code):
        key = slot["key"]
        current = params[key]
        if slot["role"] == "name":
            if isinstance(current, list):
                values = [next(fresh) for _ in current]
                old += current
            else:
                values = next(fresh)
                old.append(current)
            changes[key] = values
            new += values if isinstance(values, list) else [values]
        else:
            alternative = next(i for i in slot["pool"] if i != current)
            changes[key] = alternative
            old.append(current)
            new.append(alternative)
    return changes, old, new


@pytest.mark.parametrize("code", COSMETIC_CODES)
def test_set_cosmetic_changes_only_the_cosmetics(code):
    for seed in SEEDS:
        source = generate(code, seed)
        changes, old, new = _changes_for(code, source["parameters"])
        child = edits.apply("set-cosmetic", source, changes=changes)

        assert validate_object(child) == []
        part, src_part = child["question"]["parts"][0], source["question"]["parts"][0]
        # The maths is untouched.
        assert part["answer"] == src_part["answer"]
        assert part["marks"] == src_part["marks"]
        assert part["marking_scheme"] == src_part["marking_scheme"]
        assert child["question"]["total_marks"] == source["question"]["total_marks"]
        # Non-cosmetic params are untouched.
        for key, value in source["parameters"].items():
            if key not in changes:
                assert child["parameters"][key] == value
        # Text, steps and diagram match the original modulo the renamed values …
        assert _tokenise(child, new) == _tokenise(source, old), (code, seed)
        # … the new values are really present and the old ones really gone.
        dump = json.dumps(child["question"], ensure_ascii=False)
        assert all(n in dump for n in new)
        assert not any(re.search(rf"\b{re.escape(o)}\b", dump) for o in old if o not in new)
        # Lineage + seed.
        assert child["seed"] == source["seed"]
        assert child["provenance"]["parent_id"] == source["id"]
        assert child["provenance"]["version"] == source["provenance"]["version"] + 1
        assert child["id"] == f"{code}:{seed}:v{child['provenance']['version']}"
        assert child["provenance"]["created_by"] == "engine"


def test_set_cosmetic_does_not_mutate_source():
    source = generate("ratio_medium", 3)
    frozen = copy.deepcopy(source)
    edits.apply("set-cosmetic", source, changes={"names": ["Ann", "Ben", "Cal"]})
    assert source == frozen


def test_bar_model_labels_follow_the_names():
    source = generate("ratio_medium", 5)
    child = edits.apply("set-cosmetic", source, changes={"names": ["Ann", "Ben", "Cal"]})
    labels = [b["label"] for b in child["question"]["parts"][0]["diagram"]["bars"]]
    assert labels == ["Ann", "Ben", "Cal"]


# --- refusals ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "changes"),
    [
        ("ratio_medium", {"ratio": [1, 2, 3]}),
        ("ratio_medium", {"total": 99}),
        ("percentage_hard", {"direction": "increase"}),
        ("fractions_easy", {"shape": "circle"}),
        ("ratio_medium", {"nonexistent": "x"}),
    ],
)
def test_set_cosmetic_rejects_numeric_choice_and_unknown(code, changes):
    source = generate(code, 1)
    with pytest.raises(EditNotApplicable):
        edits.apply("set-cosmetic", source, changes=changes)


def test_numeric_refusal_points_at_the_right_ops():
    with pytest.raises(EditNotApplicable, match="changes the maths"):
        edits.apply("set-cosmetic", generate("ratio_medium", 1), changes={"total": 99})


def test_set_cosmetic_needs_changes():
    with pytest.raises(EditNotApplicable, match="no changes"):
        edits.apply("set-cosmetic", generate("ratio_medium", 1), changes={})


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "A" * 25,
        "<script>alert(1)</script>",
        "Ann & Ben",
        "Ann2",
        'Ann\nBen"',
        "-Ann",
        "Ann--Ben ",
        123,
    ],
)
def test_set_cosmetic_rejects_bad_names(bad):
    source = generate("speed_easy", 1)
    with pytest.raises(EditNotApplicable):
        edits.apply("set-cosmetic", source, changes={"name": bad})


def test_set_cosmetic_rejects_duplicate_names():
    source = generate("ratio_medium", 1)
    with pytest.raises(EditNotApplicable, match="different from each other"):
        edits.apply("set-cosmetic", source, changes={"names": ["Ann", "ann", "Cal"]})
    # A duplicate against an *unchanged* name slot is caught too.
    two = generate("speed_hard", 1)
    with pytest.raises(EditNotApplicable, match="different from each other"):
        edits.apply("set-cosmetic", two, changes={"name1": two["parameters"]["name2"]})


def test_set_cosmetic_rejects_wrong_array_shape():
    source = generate("ratio_medium", 1)
    with pytest.raises(EditNotApplicable, match="list of 3"):
        edits.apply("set-cosmetic", source, changes={"names": ["Ann", "Ben"]})
    with pytest.raises(EditNotApplicable, match="list of 3"):
        edits.apply("set-cosmetic", source, changes={"names": "Ann"})
    scalar = generate("speed_easy", 1)
    with pytest.raises(EditNotApplicable, match="single value"):
        edits.apply("set-cosmetic", scalar, changes={"name": ["Ann"]})


def test_set_cosmetic_rejects_item_outside_pool():
    source = generate("percentage_hard", 1)
    with pytest.raises(EditNotApplicable, match="allowed list"):
        edits.apply("set-cosmetic", source, changes={"context": "umbrella"})


def test_set_cosmetic_refused_on_sourced_objects():
    fixture = Path(__file__).parent / "fixtures" / "sourced" / "psle_2023_ratio.json"
    sourced = json.loads(fixture.read_text(encoding="utf-8"))
    assert not edits.applicable("set-cosmetic", {**sourced, "blueprint_code": "ratio_medium"})
    with pytest.raises(EditNotApplicable):
        edits.apply("set-cosmetic", sourced, changes={"names": ["A", "B", "C"]})


def test_names_are_normalised():
    source = generate("speed_easy", 2)
    child = edits.apply("set-cosmetic", source, changes={"name": "  Mary   Anne  "})
    assert child["parameters"]["name"] == "Mary Anne"
    assert "Mary Anne" in child["question"]["parts"][0]["text"]


def test_unicode_and_punctuated_names_are_accepted():
    source = generate("speed_easy", 2)
    for name in ("Nurul Aini", "Mary-Anne", "O'Brien", "Zoë", "李明"):
        child = edits.apply("set-cosmetic", source, changes={"name": name})
        assert child["parameters"]["name"] == name


# --- view state is replayed after the rebuild -------------------------------


def test_decimals_view_survives_a_rename():
    source = edits.apply("change-to-decimals", generate("ratio_medium", 7))
    child = edits.apply("set-cosmetic", source, changes={"names": ["Ann", "Ben", "Cal"]})
    assert child["validation"]["checks"]["representation"] == "decimals"
    assert child["question"]["parts"][0]["answer"] == source["question"]["parts"][0]["answer"]
    assert (
        "$10.80" in child["question"]["parts"][0]["text"]
        or "." in (child["question"]["parts"][0]["text"])
    )
    assert child["question"]["parts"][0]["answer"]["dp"] == 2


def test_diagram_toggled_off_stays_off():
    source = edits.apply("toggle-diagram", generate("ratio_medium", 7))
    assert source["question"]["parts"][0]["diagram"] is None
    child = edits.apply("set-cosmetic", source, changes={"names": ["Ann", "Ben", "Cal"]})
    assert child["question"]["parts"][0]["diagram"] is None


def test_bar_view_mode_survives_a_rename():
    base = generate("ratio_hard", 3)
    flipped = edits.apply("toggle-bar-view", base)
    mode = flipped["question"]["parts"][0]["diagram"]["view_mode"]
    child = edits.apply("set-cosmetic", flipped, changes={"names": ["Ann", "Ben"]})
    assert child["question"]["parts"][0]["diagram"]["view_mode"] == mode
    assert "Ann" in json.dumps(child["question"]["parts"][0]["diagram"])


# --- rendering escapes ------------------------------------------------------


def test_punctuated_name_renders_in_both_sheets():
    source = generate("ratio_medium", 7)
    child = edits.apply("set-cosmetic", source, changes={"names": ["O'Brien", "Ben", "Cal"]})
    for html in (render_worksheet_html("W", [child]), render_answer_key_html("A", [child])):
        body = html.split('<ol class="questions">', 1)[1]
        # Apostrophe is the only markup-adjacent character names may contain; the
        # renderers escape &, < and > in text nodes and names can't contain quotes.
        assert "O'Brien, Ben and Cal" in body
        assert "<O" not in body


# --- slots ------------------------------------------------------------------


def test_editable_slots_describe_the_form():
    slots = {s["key"]: s for s in cosmetic.editable_slots("ratio_medium")}
    assert slots["names"] == {"key": "names", "role": "name", "count": 3, "max_length": 24}
    ph = {s["key"]: s for s in cosmetic.editable_slots("percentage_hard")}
    assert ph["context"]["role"] == "item" and "bicycle" in ph["context"]["pool"]
    assert cosmetic.editable_slots("geometry_angle_easy") == []
    assert {"name", "item"} == COSMETIC_ROLES
