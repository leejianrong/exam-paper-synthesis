"""A2 — solver interface + blueprint spec + parameter validation."""

from __future__ import annotations

import functools
import random
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Protocol, runtime_checkable

from ..schema import validate_against


@runtime_checkable
class Solver(Protocol):
    """The maths lives here (ADR-0003). Deterministic given its inputs."""

    def sample(self, schema: dict, rng: random.Random) -> dict:
        """Draw a valid, non-degenerate parameter set (constraints by construction)."""
        ...

    def solve(self, params: dict) -> dict:
        """Return ``{"answer": {...}, "intermediates": {...}}``.

        A multi-part blueprint (P8c, ``BlueprintSpec.parts``) returns ``"answers"`` instead:
        one answer per part, in the order of the YAML ``parts`` list.
        """
        ...

    def validate(self, params: dict, solution: dict) -> dict:
        """Return ``{"ok": bool, "checks": {name: bool|str|None}}``."""
        ...

    # Optional: def diagram(self, params, solution) -> dict  (added in V2)
    # Optional: def table(self, params, solution) -> dict  (EXA-148) the data table printed
    #   before the parts (``question.table``: caption, headers, rows of display strings).
    # Optional: def distractors(self, params, solution) -> list[tuple[number, str]]
    #   (EXA-122) the "common wrong answers" for a multiple-choice copy (mcq.to_mcq): values
    #   in the answer's own quantity and unit, each with the reason a pupil gives it, best
    #   first. mcq filters out the answer itself and anything implausible, then falls back
    #   to its generic candidates; the correct option is still proven by verify_snapshot.
    # Optional: mcq_ascending = False  (EXA-141) the multiple-choice copy keeps a seeded option
    #   order instead of ascending order, for a question whose answer is an extreme of the
    #   options ("which is the greatest?"), where ascending order would give it away.
    # Optional: mcq_whole = True  (EXA-148) every option is a whole number, even in a unit that
    #   allows 1 dp (rental for whole hours: never "3.5 h").


Slip = tuple[int | Fraction, str]


def _numbers(params: object) -> list[int | float]:
    """The numbers in ``params``, in key order (names and items left out, so renaming a
    person keeps the same slips order)."""
    if isinstance(params, dict):
        return [n for k in sorted(params) for n in _numbers(params[k])]
    if isinstance(params, list | tuple):
        return [n for v in params for n in _numbers(v)]
    if isinstance(params, int | float) and not isinstance(params, bool):
        return [params]
    return []


def spread[T](
    slips: list[tuple[T, str]],
    answer: Any,
    params: dict,
    prints: Callable[[Any], bool] | None = None,
    key: Callable[[Any], Any] = Fraction,
) -> list[tuple[T, str]]:
    """``slips`` (best first) reordered so the first two lie both below, either side of, or
    both above ``answer``, chosen by a key from the numbers in ``params`` (EXA-147, EXA-156).

    A multiple-choice copy prints its options in ascending order and takes the first wrong
    options from the hook in order (only the last one is picked to move the answer, see
    ``mcq._last_pick``), so a hook whose best slips all lie on one side would put the answer
    nearly always in one half of the options. Slips a copy cannot use (``prints`` false, by
    default: not positive, the answer itself, or more than 20 times off it) and repeated values
    count for neither side.

    ``key`` maps a slip's value to what is compared with ``answer`` (and passed to
    ``prints``): the number itself, or for an answer in terms of π (EXA-155) its
    ``(π coefficient, constant)``, the order its options print in."""

    def usable(v: Any) -> bool:
        if prints is not None:
            return prints(v)
        return v > 0 and v != answer and answer / 20 <= v <= answer * 20

    seen: set = set()
    below: list[tuple[T, str]] = []
    above: list[tuple[T, str]] = []
    for s in slips:  # a value given twice is one option
        v = key(s[0])
        if usable(v) and v not in seen:
            seen.add(v)
            (below if v < answer else above).append(s)
    pick = zlib.crc32(repr(_numbers(params)).encode())
    first = [below[:2], below[:1] + above[:1], above[:2]][pick % 3]
    if len(first) < 2:
        first = below[:1] + above[:1]
    first.sort(key=slips.index)  # still best first: mcq's give-away guard drops the later one
    return [*first, *(s for s in slips if s not in first)]


def spread_sides(
    hook: Callable[[Any, dict, dict], list[Slip]],
) -> Callable[[Any, dict, dict], list[Slip]]:
    """A ``distractors`` hook whose slips go through :func:`spread`, about the solved answer."""

    @functools.wraps(hook)
    def wrapped(self: Any, params: dict, solution: dict) -> list[Slip]:
        from ..mcq import hook_value_prints  # mcq imports the registry, which imports us

        slips = hook(self, params, solution)
        a = solution.get("answer")
        if not a:  # called before solving (a sampler counting its slips)
            return slips
        answer = (
            Fraction(a["numerator"], a["denominator"])
            if a.get("type") == "fraction"
            else Fraction(str(a["value"]))
        )
        return spread(slips, answer, params, lambda v: hook_value_prints(v, a))

    return wrapped


def carry_slips(a: int, b: int) -> list[Slip]:
    """Carrying slips in the long multiplication ``a × b`` (``b`` one digit), when the ones
    column carries ``c`` tens (``(a % 10) × b // 10``): the carried tens added twice, or left
    out, so the product is ``10c`` too big or too small."""
    c = (a % 10) * b // 10
    if b > 9 or c == 0:
        return []
    tens = "ten" if c == 1 else f"{c} tens"
    return [
        (a * b + 10 * c, f"added the carried {tens} twice when multiplying"),
        (a * b - 10 * c, f"left out the carried {tens} when multiplying"),
    ]


def sum_slip(answer: int, x: int, y: int, what: str) -> list[Slip]:
    """``answer`` is 180° or 360° less ``x + y``: when adding ``x`` and ``y`` carries a ten,
    the carried ten added twice makes the sum 10 too big and the answer 10 too small."""
    if (x % 10) + (y % 10) < 10:
        return []
    return [(answer - 10, f"added the carried ten twice when adding {what}")]


@dataclass
class BlueprintSpec:
    """Parsed ``exam_engine/content/blueprints/<code>.yaml`` (declarative data only)."""

    code: str
    syllabus: dict
    cognitive: dict
    marks: int
    parameter_schema: dict
    story_templates: list[dict]
    solution_template: dict
    marking_scheme: list[dict]
    answer: dict
    diagram: object = None
    param_roles: dict = field(default_factory=dict)
    # P8c multi-part blueprints: one entry per part, in print order, each
    # ``{label, text, marks, marking_scheme, solution_template, answer}``. Empty for a
    # single-part blueprint (the top-level ``marking_scheme``/``solution_template``/
    # ``answer`` describe its only part). ``marks`` is always the question total.
    parts: list[dict] = field(default_factory=list)
    _extra: dict = field(default_factory=dict)

    @property
    def is_multipart(self) -> bool:
        return bool(self.parts)

    @property
    def part_count(self) -> int:
        """How many parts every question of this blueprint has (1 for single-part)."""
        return len(self.parts) or 1

    @property
    def answer_types(self) -> tuple[str, ...]:
        """Every answer type this blueprint's questions can have (EXA-155): the YAML answer's
        ``types`` list when it declares one (a solver that answers some questions in terms of
        π), else its ``type``; over all parts for a multi-part blueprint. The paper generator
        routes on it, so it must be honest: ``tests/test_answer_types.py`` sweeps every solver.
        """
        answers = [p.get("answer") or {} for p in self.parts] or [self.answer or {}]
        out: list[str] = []
        for a in answers:
            for t in a.get("types") or [a.get("type")]:
                if t and t not in out:
                    out.append(str(t))
        return tuple(out)

    @classmethod
    def from_dict(cls, data: dict) -> BlueprintSpec:
        known = {
            "code",
            "syllabus",
            "cognitive",
            "marks",
            "parameter_schema",
            "story_templates",
            "solution_template",
            "marking_scheme",
            "answer",
            "diagram",
            "param_roles",
            "parts",
        }
        parts = data.get("parts") or []
        return cls(
            code=data["code"],
            syllabus=data["syllabus"],
            cognitive=data["cognitive"],
            marks=data["marks"],
            parameter_schema=data["parameter_schema"],
            story_templates=data["story_templates"],
            # A multi-part blueprint describes these per part, so they are optional there.
            solution_template=data["solution_template"] if not parts else {},
            marking_scheme=data["marking_scheme"] if not parts else [],
            answer=data["answer"] if not parts else {},
            diagram=data.get("diagram"),
            param_roles=data.get("param_roles") or {},
            parts=parts,
            _extra={k: v for k, v in data.items() if k not in known},
        )


def check_parts(code: str, spec: BlueprintSpec) -> list[str]:
    """Problems with a multi-part blueprint's ``parts`` (empty when consistent, P8c).

    At least two parts, labels a, b, c… in order, each part's marking scheme sums to
    its marks, and the parts' marks sum to the blueprint's ``marks``.
    """
    if not spec.parts:
        return []
    errors = []
    if len(spec.parts) < 2:
        errors.append(f"{code}: a multi-part blueprint needs at least two parts")
    for i, part in enumerate(spec.parts):
        want = "abcdefgh"[i]
        if part.get("label") != want:
            errors.append(f"{code}: part {i} is labelled {part.get('label')!r}, not {want!r}")
        scheme = sum(m["mark"] for m in part.get("marking_scheme") or [])
        if scheme != part.get("marks"):
            errors.append(
                f"{code}: part ({want}) marking_scheme sums to {scheme}, marks={part.get('marks')}"
            )
    total = sum(p.get("marks") or 0 for p in spec.parts)
    if total != spec.marks:
        errors.append(f"{code}: parts' marks sum to {total} but blueprint marks={spec.marks}")
    return errors


def validate_params(params: dict, parameter_schema: dict) -> list[str]:
    """Validate sampled params against the blueprint's declared schema (ADR-0014)."""
    return validate_against(params, parameter_schema)


PARAM_ROLES = frozenset({"name", "item", "number", "choice"})
# Roles a teacher may change without touching the maths (ADR-0021 tier 1).
COSMETIC_ROLES = frozenset({"name", "item"})


def check_param_roles(code: str, spec: BlueprintSpec) -> list[str]:
    """Problems with a blueprint's ``param_roles`` (empty when complete and valid).

    Every ``parameter_schema`` property needs exactly one declared role, so a new
    blueprint can never ship with an unclassified parameter (W1a).
    """
    props = set((spec.parameter_schema.get("properties") or {}).keys())
    roles = spec.param_roles
    errors = [
        f"{code}: parameter {k!r} has no param_roles entry" for k in sorted(props - set(roles))
    ]
    errors += [
        f"{code}: param_roles names unknown parameter {k!r}" for k in sorted(set(roles) - props)
    ]
    for key, entry in roles.items():
        role = entry.get("role") if isinstance(entry, dict) else None
        if role not in PARAM_ROLES:
            errors.append(f"{code}: parameter {key!r} has invalid role {role!r}")
    return errors
