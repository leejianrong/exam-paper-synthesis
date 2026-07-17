"""V3 — edit operations: object -> object transforms (ADR-0004/0009).

Every edit is a pure, deterministic, re-validated transform: it deep-copies the
source (never mutates it), produces a NEW canonical object, and re-validates it
through :func:`canonical.load` (the schema gate). Lineage is stamped so the child
records its parent + a bumped version. ``created_at`` stays ``None`` — it is
stamped only at the API boundary (ADR-0016).

Two flavours of transform:
  * resample ops (regenerate / make-harder / make-easier) re-run the pipeline on
    a target blueprint + fresh seed;
  * representation ops (change-to-decimals / toggle-diagram) rebuild the object
    in place from the same integer parameters.
"""

from __future__ import annotations

import copy

from . import canonical
from .blueprints.registry import get_solver, load_blueprint
from .canonical import _fill
from .errors import EditNotApplicable
from .ladder import sibling
from .pipeline import generate

# The five known ops (the API rejects anything else with a 404).
KNOWN_OPS = frozenset(
    {"regenerate", "make-harder", "make-easier", "change-to-decimals", "toggle-diagram"}
)

# toggle-diagram only applies to *aid* figures — bar models that scaffold the
# reasoning and can be shown or hidden. Mandatory figures (shaded_fraction and
# future geometry) carry information the question depends on, so they must never
# be toggled off (ADR-0007/0009).
AID_DIAGRAM_TYPES = frozenset({"bar_model", "bar_model_before_after"})


def _part(obj: dict) -> dict:
    return obj["question"]["parts"][0]


def available_ops(obj: dict) -> set[str]:
    """Which edit ops apply to ``obj`` (drives button availability, ADR-0009)."""
    code = obj["blueprint_code"]
    ops: set[str] = {"regenerate"}

    if sibling(code, +1):
        ops.add("make-harder")
    if sibling(code, -1):
        ops.add("make-easier")

    answer = _part(obj).get("answer", {})
    solver = get_solver(code)
    if answer.get("unit") == "$" and getattr(solver, "MONEY_KEYS", None):
        ops.add("change-to-decimals")

    # Offer toggle-diagram only for aid figures — the blueprint's declared
    # diagram family must be an aid type. Keying on the blueprint (not the
    # object's current diagram, which is None while toggled off) keeps the toggle
    # available in both directions.
    if load_blueprint(code).diagram in AID_DIAGRAM_TYPES:
        ops.add("toggle-diagram")

    return ops


def _stamp_lineage(child: dict, source: dict) -> dict:
    """Record parent + bump version; keep engine authorship, clear the clock."""
    prov = child["provenance"]
    prov["parent_id"] = source["id"]
    prov["version"] = source["provenance"]["version"] + 1
    prov["created_by"] = "engine"
    prov["llm_used"] = False
    prov["created_at"] = None  # stamped only at the API boundary (ADR-0016)
    return child


# --- resample ops -----------------------------------------------------------


def _resample(source: dict, target_code: str, seed: int | None) -> dict:
    source_seed = source.get("seed")
    new_seed = seed if seed is not None else (source_seed or 0) + 1
    child = generate(target_code, new_seed)  # fresh, schema-valid, version 1
    return _stamp_lineage(child, source)


def _regenerate(source: dict, seed: int | None) -> dict:
    return _resample(source, source["blueprint_code"], seed)


def _make_harder(source: dict, seed: int | None) -> dict:
    target = sibling(source["blueprint_code"], +1)
    assert target is not None  # guarded by available_ops (make-harder)
    return _resample(source, target, seed)


def _make_easier(source: dict, seed: int | None) -> dict:
    target = sibling(source["blueprint_code"], -1)
    assert target is not None  # guarded by available_ops (make-easier)
    return _resample(source, target, seed)


# --- representation ops -----------------------------------------------------


def _change_to_decimals(source: dict, seed: int | None) -> dict:
    """Money ÷10 -> 1 dp: a derived decimals *view* of the same integer params.

    ``parameters`` stays the original integer sample (the param schema requires
    integers; the decimals form is a derived rendering, plan D2). Only ``$`` values
    scale — ratio terms and unit counts stay integer, so the bars are unchanged.
    """
    code = source["blueprint_code"]
    spec = load_blueprint(code)
    solver = get_solver(code)
    money_keys: set[str] = getattr(solver, "MONEY_KEYS", set())  # guarded by available_ops

    params = source["parameters"]
    solution = solver.solve(params)
    inter = solution["intermediates"]

    def scale(key: str, value: object) -> object:
        if key in money_keys:
            assert isinstance(value, int | float)  # money keys hold numbers
            return value / 10
        return value

    scaled_params = {k: scale(k, v) for k, v in params.items()}
    scaled_inter = {k: scale(k, v) for k, v in inter.items()}
    scaled_ctx = {**scaled_params, **scaled_inter}

    seed_val = source["seed"]
    template = spec.story_templates[seed_val % len(spec.story_templates)]
    part_text = _fill(template["text"], scaled_ctx)

    steps = []
    for step in spec.solution_template.get("steps", []):
        steps.append(
            {
                "text": _fill(step["text"], scaled_ctx),
                "expr": _fill(step["expr"], scaled_ctx) if step.get("expr") else None,
            }
        )

    orig_value = solution["answer"]["value"]
    answer = {"type": "decimal", "value": orig_value / 10, "dp": 1, "unit": "$"}

    diagram = None
    diagram_fn = getattr(solver, "diagram", None)
    if _part(source).get("diagram") is not None and diagram_fn is not None:
        # Keep the diagram if the source had one; rebuild it with scaled $ labels.
        # Bars come from the integer ratio/unit counts (unchanged); only labels scale.
        scaled_solution = {"answer": answer, "intermediates": scaled_inter}
        diagram = diagram_fn(scaled_params, scaled_solution)

    version = source["provenance"]["version"] + 1
    validation = copy.deepcopy(source["validation"])
    validation.setdefault("checks", {})
    validation["checks"]["representation"] = "decimals"

    part = {
        "label": _part(source)["label"],
        "text": part_text,
        "marks": spec.marks,
        "answer": answer,
        "marking_scheme": spec.marking_scheme,
        "solution_steps": steps,
        "diagram": diagram,
    }

    child = {
        "schema_version": canonical.SCHEMA_VERSION,
        "id": f"{code}:{seed_val}:v{version}",
        "source_type": "generated",
        "blueprint_code": code,
        "seed": seed_val,
        "syllabus": copy.deepcopy(spec.syllabus),
        "cognitive": copy.deepcopy(spec.cognitive),
        "parameters": copy.deepcopy(params),  # original INTEGER sample (plan D2)
        "question": {
            "stem": template.get("stem"),
            "parts": [part],
            "total_marks": spec.marks,
        },
        "validation": validation,
        "provenance": {
            "created_by": "engine",
            "llm_used": False,
            "created_at": None,
            "parent_id": source["id"],
            "version": version,
        },
    }
    return canonical.load(child)


def _toggle_diagram(source: dict, seed: int | None) -> dict:
    """Flip the part's diagram: present -> null, or null -> rebuilt from params."""
    child = copy.deepcopy(source)
    code = source["blueprint_code"]
    part = child["question"]["parts"][0]

    if part["diagram"] is not None:
        part["diagram"] = None
    else:
        solver = get_solver(code)
        params = child["parameters"]
        diagram_fn = getattr(solver, "diagram", None)
        assert diagram_fn is not None  # guarded by available_ops (toggle-diagram)
        part["diagram"] = diagram_fn(params, solver.solve(params))

    version = source["provenance"]["version"] + 1
    child["id"] = f"{code}:{source['seed']}:v{version}"
    _stamp_lineage(child, source)
    return canonical.load(child)


_DISPATCH = {
    "regenerate": _regenerate,
    "make-harder": _make_harder,
    "make-easier": _make_easier,
    "change-to-decimals": _change_to_decimals,
    "toggle-diagram": _toggle_diagram,
}


def apply(op: str, obj: dict, *, seed: int | None = None) -> dict:
    """Apply edit ``op`` to ``obj``, returning a new lineage-stamped child.

    Raises :class:`EditNotApplicable` if ``op`` is unavailable for this object.
    The source object is never mutated.
    """
    if op not in available_ops(obj):
        raise EditNotApplicable(op, f"not available for blueprint {obj['blueprint_code']!r}")
    return _DISPATCH[op](obj, seed)
