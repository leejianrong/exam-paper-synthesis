"""Shared structural check for the per-blueprint invariant tests.

KAN-237 graduated the KAN-236 seed sweeps to Hypothesis property tests: the input
generation (formerly ``sweep_generate`` over ``range(1, 400)``) and the sweep
runner (``check_invariant``) now live in :mod:`strategies` as ``@composite`` param
strategies + :func:`strategies.build_object`. What remains here is the one purely
structural helper the property tests still share.

The golden fixtures remain the regression anchor; the property tests are the
independent correctness authority.
"""

from __future__ import annotations


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
