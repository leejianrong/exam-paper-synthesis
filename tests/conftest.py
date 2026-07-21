"""Pytest + Hypothesis configuration for the test suite (KAN-237).

Registers Hypothesis profiles so the property-based invariant tests
(``test_invariants_*.py``) stay **deterministic** and **fast** by default while a
larger budget is available on demand:

* ``ci`` / ``dev`` (the default) — a bounded ``max_examples`` with
  ``derandomize=True`` so example selection is a deterministic function of the
  test (a green run stays green on re-run with no code change, and a failure
  reproduces exactly). ``deadline=None`` deliberately removes Hypothesis's
  per-example wall-clock deadline: on shared CI runners a timing deadline is the
  one source of flakiness we must not introduce (dev-playbook: tests must be
  deterministic). Determinism of *example choice* comes from ``derandomize``, not
  from a clock.
* ``nightly`` — the same determinism with a much larger ``max_examples`` for a
  deeper nightly sweep.

Select a profile with ``HYPOTHESIS_PROFILE=<name>`` (e.g. ``HYPOTHESIS_PROFILE=nightly
uv run pytest``); the default is ``ci``.
"""

from __future__ import annotations

import os

from hypothesis import settings

settings.register_profile("ci", max_examples=50, deadline=None, derandomize=True)
settings.register_profile("dev", max_examples=50, deadline=None, derandomize=True)
settings.register_profile("nightly", max_examples=1000, deadline=None, derandomize=True)

settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))
