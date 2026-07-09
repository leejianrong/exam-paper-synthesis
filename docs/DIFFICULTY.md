# DIFFICULTY — the principled difficulty model

Difficulty is not a single dial; it is a small set of **named levers**. A "harder"
blueprint is one that deliberately pulls more of them. This makes difficulty
principled, deterministic (no LLM), authorable, and consistent with how SEAB/MOE
escalate items (AO1 → AO2 → AO3).

Related: ADR-0009 (edit semantics), ADR-0015 (this model), ADR-0003 (blueprints).

## Two levels of difficulty

1. **Composition (whole question).** Harder questions have **more sub-parts** that
   **build on each other** (part (c) uses the answer to (a)/(b)) and carry **more
   marks**. Easier = fewer, independent, lower-mark parts. Represented directly by
   how many entries a blueprint puts in `question.parts[]` and each part's `marks`.
2. **Intrinsic (single part).** The same sub-question is made harder via the levers
   below. This is what the **3-blueprint-per-topic ladder** encodes.

## Generic difficulty levers (topic-agnostic)

| Lever | Easier → Harder |
|---|---|
| Reasoning depth | 1 step → multi-step chain |
| Sub-parts | few, independent → many, each depending on the previous |
| Number type / magnitude | small integers → large / decimals / fractions / mixed |
| Direction | direct ("given X find Y") → inverse / work-backwards |
| Extraneous info | none → distractor data to filter out |
| Representation translation | one form → must convert words↔table↔diagram↔equation |
| Hidden structure | relationship stated → must be inferred (e.g. an unsignposted invariant) |
| Cross-topic integration | single skill → two skills combined |
| Heuristic demand | routine algorithm → must *choose* a strategy |
| Answer form | clean integer → needs rounding / units / interpretation |

Each blueprint tags which levers it uses in `cognitive.difficulty_levers[]`.

## Per-topic ladders (5 MVP topics)

| Topic | Easy | Medium | Hard |
|---|---|---|---|
| Ratio | Share a total in a 2-term ratio (direct) | 3-term ratio, or ratio given the difference | Before-after with an invariant quantity (hidden structure) |
| Fractions | Fraction of a quantity (1 step) | Fraction of a remainder (2 step) | Successive fractions of a remainder; unknown whole (inverse) |
| Percentage | Find X% of a number | Percentage increase/decrease | Reverse % (original before change); successive % changes |
| Area/Geometry | Area of a rectangle | Composite figure (add/subtract rectangles) | Overlapping figures; missing dimension given the area (inverse) |
| Speed (P6) | d = s × t (direct) | Average speed over two legs | Meeting/overtaking; before-after speed change |

Each "hard" cell deliberately pulls multiple levers (inverse + hidden structure +
more steps) — that is the mechanism.

## Encoding

- Ladder = **3 blueprints per topic × 5 topics = 15 blueprints for v1**.
- Each blueprint declares `difficulty ∈ {easy, medium, hard}` and
  `difficulty_levers[]`.
- **make harder / make easier** = swap to the sibling one rung up/down the same
  topic ladder. **regenerate** = resample within the same rung.

## Caveat (calibration)

Difficulty is partly **empirical**: a "hard" blueprint may test as "medium" with
real students. The levers give a principled, consistent starting point; calibrate
against gold samples and teacher feedback later. This is tuning, not a design flaw.

## Build order

Prove **one full topic ladder end-to-end** (all 3 Ratio rungs:
generate → solve → validate → render → swap) before building the other four
topics. Lowest-risk way to validate the whole model.
