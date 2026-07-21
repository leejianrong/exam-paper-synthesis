"""Independent correctness authority for the Speed ladder (KAN-234, KAN-237).

Property-based (Hypothesis) tests that re-derive each rung's *defining
relationship* independently of ``solve()`` over params generated directly from
the blueprint's parameter space, shrinking failures to a minimal counterexample.
Every generated object also schema-validates (inside ``build_object``). The
golden fixtures are the regression anchor; these tests are the independent guard
against a solver that is self-consistent but wrong.

Exact arithmetic only (``Fraction`` / integers) — no floats — so the checks are
provable, not approximate.
"""

from __future__ import annotations

from fractions import Fraction

from hypothesis import given
from strategies import (
    build_object,
    speed_easy_params,
    speed_hard_params,
    speed_medium_params,
)


@given(params=speed_easy_params())
def test_easy_invariant_distance_is_speed_times_time(params: dict):
    obj = build_object("speed_easy", params)
    answer = obj["question"]["parts"][0]["answer"]

    # Defining relationship: distance = speed x time, recomputed directly
    # from the params (integers, so exact).
    assert answer["value"] == params["speed"] * params["time"]
    # Unit triple is consistent: km/h x h -> km.
    assert answer["unit"] == "km"
    assert answer["value"] > 0


@given(params=speed_medium_params())
def test_medium_invariant_average_is_total_distance_over_total_time(params: dict):
    obj = build_object("speed_medium", params)
    answer = obj["question"]["parts"][0]["answer"]

    d1, t1, d2, t2 = params["d1"], params["t1"], params["d2"], params["t2"]
    avg = answer["value"]

    # Cross-multiplied (exact, no float division): avg * (t1+t2) == d1+d2.
    assert avg * (t1 + t2) == d1 + d2
    assert answer["unit"] == "km/h"

    # It must NOT be the mean of the two leg speeds. The average equals that
    # mean exactly when (s1 - s2)(t2 - t1) == 0, i.e. only when the legs share
    # a speed OR share a time; this rung is constructed with BOTH the leg
    # speeds and the leg times distinct, so the misconception is always
    # guarded. Leg speeds are exact fractions here.
    s1 = Fraction(d1, t1)
    s2 = Fraction(d2, t2)
    mean_of_speeds = (s1 + s2) / 2
    assert s1 != s2 and t1 != t2  # construction invariant
    assert Fraction(avg) != mean_of_speeds


@given(params=speed_hard_params())
def test_hard_invariant_combined_speed_closes_the_gap(params: dict):
    obj = build_object("speed_hard", params)
    answer = obj["question"]["parts"][0]["answer"]

    s1, s2, gap = params["s1"], params["s2"], params["gap"]
    t_meet = answer["value"]

    # Reconstruct the scenario: the two objects close `gap` together, so the
    # combined speed times the meeting time recovers the gap exactly.
    assert (s1 + s2) * t_meet == gap
    assert answer["unit"] == "h"
    assert t_meet > 0
