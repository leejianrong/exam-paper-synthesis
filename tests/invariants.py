"""Shared substrate for the per-blueprint independent invariant sweeps (KAN-236).

This is **not** a test module (no ``test_`` functions) — it is an importable
helper that factors out the seed-sweep boilerplate every
``test_invariants_*.py`` repeats:

* :func:`sweep_generate` — yield ``(seed, obj)`` for a wide seed range, asserting
  each generated object is schema-valid.
* :func:`single_part_answer` — the per-object structural invariants that hold for
  every single-part blueprint (exactly one part, the marking-scheme marks sum to
  ``total_marks``), returning the part's answer dict.
* :func:`check_invariant` — run a per-object invariant callable across the sweep
  with a failure message that names the seed (and the relationship) that broke,
  optionally asserting the full set of templates was exercised.

The golden fixtures remain the regression anchor; these sweeps are the
independent correctness authority. KAN-237 will graduate this substrate to full
Hypothesis property testing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from exam_engine import generate
from exam_engine.schema import validate_object

# The standard wide seed range every invariant sweep walks.
SWEEP = range(1, 400)


def sweep_generate(blueprint_code: str, seeds: Iterable[int] = SWEEP) -> Iterator[tuple[int, dict]]:
    """Yield ``(seed, canonical_object)`` for each seed, asserting schema validity.

    A self-consistent-but-wrong solver still produces schema-valid objects, so
    this only guards the structural contract; the caller supplies the
    independent *mathematical* invariant.
    """
    for seed in seeds:
        obj = generate(blueprint_code, seed)
        errors = validate_object(obj)
        assert errors == [], (blueprint_code, seed, errors)
        yield seed, obj


def single_part_answer(obj: dict) -> dict:
    """Return the sole part's answer, asserting the single-part marks contract.

    Holds for every single-part blueprint: exactly one part, and the
    marking-scheme marks sum to the question's ``total_marks``.
    """
    parts = obj["question"]["parts"]
    assert len(parts) == 1, f"expected a single part, got {len(parts)}"
    part = parts[0]
    marks = sum(m["mark"] for m in part["marking_scheme"])
    assert marks == obj["question"]["total_marks"], (marks, obj["question"]["total_marks"])
    return part["answer"]


def check_invariant(
    blueprint_code: str,
    invariant: Callable[[dict], str | None],
    seeds: Iterable[int] = SWEEP,
    *,
    expect_templates: Iterable[str] | None = None,
) -> None:
    """Run ``invariant(obj)`` across the sweep with a seed-tagged failure message.

    ``invariant`` may return a template/family name; when ``expect_templates`` is
    given, the sweep must have exercised exactly that set (so a template silently
    dropping out of the sampler is caught too).
    """
    seen: set[str] = set()
    for seed, obj in sweep_generate(blueprint_code, seeds):
        try:
            tag = invariant(obj)
        except AssertionError as exc:  # re-raise with the offending seed attached
            raise AssertionError(f"{blueprint_code} seed={seed}: {exc}") from exc
        if tag is not None:
            seen.add(tag)
    if expect_templates is not None:
        assert seen == set(expect_templates), (blueprint_code, seen, set(expect_templates))
