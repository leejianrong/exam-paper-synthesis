---
shaping: true
---

# E1 Slice Plan — Bank + review gate (CLI, schema unchanged)

> **Slice E1 of `docs/planning/editor/SLICES.md`.** The persistence spine: a
> durable local bank that can hold any object the engine already accepts
> (generated or sourced, schema v1.4.0 — no schema change in this slice) plus a
> real review gate. Ground truth: `docs/planning/editor/SHAPING.md` (R1, R5,
> Shape A1/A2/A10/A11). Decisions: ADR-0017 (persistence), ADR-0019 (review
> gate). Schema contract: `schemas/canonical-question.schema.json` — unchanged.
>
> **Demo goal:** `mathgen bank import q.json` persists a hand-authored sourced
> question; it survives closing and reopening the CLI; `mathgen bank
> list`/`search` finds it as unreviewed; `mathgen bank review <id>
> --mark-reviewed` (optionally editing a field first) makes it reviewed;
> `search --reviewed true` now returns it.

---

## Scope

**In (Shape-A parts A1, A2, A10, A11's CLI stage):**
- **A1** — SQLite bank: one row per canonical object, schema-validated on
  write *and* read; no second blob-storage mechanism (figures stay
  self-contained `data:` URIs inside the stored object, as V7 established).
- **A2** — a minimal search/query layer (topic, difficulty, level,
  `source_type`, reviewed) shared by `list` and `search`.
- **A10** — the import/review gate: `validation.status:"unverified"` on
  arrival; a review action that can hand-correct any field and then flips
  `checks.human_reviewed:true`; re-validated on every write.
- **A11 (CLI stage only)** — `mathgen bank {import,list,search,review}`.

**Explicitly deferred (later slices):**
- Any schema change (`choice`, stem-diagram, optional marks, `table`,
  `grid`/`polygons`, `construction`) → **E2/E3**. E1 proves the bank against
  the *existing* v1.4.0 schema only.
- The paper/section/question-group container and `paper_id`-scoped
  search/export → **E4**. E1's bank has no notion of a paper; adding one is a
  straightforward `ALTER TABLE` later, not designed here.
- Bank-retrieval-on-swap (KAN-163) → parked (`SHAPING.md` R8.3).
- A web UI over any of this → **E5**. Everything below is CLI/file-based.
- "Flag (don't block) unreviewed content in a paper" (R5.4's second half) has
  no paper to flag against yet — E1 only builds the *distinguish reviewed vs
  not* half (search/list), which is all R5.4 needs before E4 exists.

---

## Repo layout (new/changed files)

No new workspace member, no new dependency — `sqlite3` is stdlib, so
`engine/pyproject.toml` is unchanged (keeps ADR-0017's "no second storage
mechanism" and the engine's minimal-dependency discipline both intact).

```
engine/
  exam_engine/
    bank.py                # NEW — A1/A2/A10: Bank class, open_bank(), default_path()
    errors.py               # + BankObjectNotFound, BankDuplicateId
cli/
  mathgen/
    __main__.py             # + `bank` subparser (import/list/search/review)
    commands.py              # + cmd_bank_import/list/search/review
tests/
  test_bank.py               # NEW — engine-level Bank roundtrip/search/review tests
cli/tests/
  test_cli_bank.py            # NEW — mathgen bank behavioural tests
```

---

## A1/A2/A10 — `engine/exam_engine/bank.py`

### Storage

- **One SQLite file.** Default path `~/.exam_engine/bank.sqlite3`, override
  with **`EXAM_BANK_PATH`** — the same env-var-override convention as
  `EXAM_SCHEMA_PATH`/`EXAM_CONTENT_DIR` (`schema.py`), so this is consistent
  with how the engine already resolves out-of-tree paths. No `platformdirs`
  dependency — `Path.home()` is enough for a single-user local tool.
- **One row per canonical object**, stored as the exact JSON the engine's own
  load gate already validates. A handful of columns are **denormalized out of
  that JSON purely for indexed search** — they are never a second source of
  truth; every read that returns an object reads the `json` column and hands
  back exactly what was stored.

```sql
CREATE TABLE IF NOT EXISTS objects (
    id             TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    source_type    TEXT NOT NULL,   -- 'generated' | 'sourced'
    topic          TEXT,            -- syllabus.topic
    level          TEXT,            -- syllabus.level
    difficulty     TEXT,            -- cognitive.difficulty
    created_by     TEXT NOT NULL,   -- provenance.created_by
    reviewed       INTEGER NOT NULL DEFAULT 0,  -- derived from checks.human_reviewed
    imported_at    TEXT NOT NULL,   -- ISO-8601; stamped once, on first insert; never changes
    json           TEXT NOT NULL    -- the full canonical object
);
CREATE INDEX IF NOT EXISTS idx_objects_topic       ON objects(topic);
CREATE INDEX IF NOT EXISTS idx_objects_difficulty  ON objects(difficulty);
CREATE INDEX IF NOT EXISTS idx_objects_level       ON objects(level);
CREATE INDEX IF NOT EXISTS idx_objects_source_type ON objects(source_type);
CREATE INDEX IF NOT EXISTS idx_objects_reviewed    ON objects(reviewed);
```

### `Bank` class

```python
class Bank:
    def __init__(self, path: Path):
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(_DDL)
        self._conn.commit()

    def add(self, obj: dict, *, overwrite: bool = False) -> dict:
        """Insert a new object. Raises BankDuplicateId unless overwrite=True."""
        obj = canonical.load(dict(obj))  # defensive copy; re-validate, never trust the caller
        existing = self._row(obj["id"])
        if existing and not overwrite:
            raise BankDuplicateId(obj["id"])
        if not obj["provenance"].get("created_at"):
            obj["provenance"]["created_at"] = _now_iso()
            obj = canonical.load(obj)  # re-validate after the stamp
        imported_at = existing["imported_at"] if existing else _now_iso()
        self._upsert(obj, imported_at)
        return obj

    def get(self, id: str) -> dict:
        row = self._row(id)
        if row is None:
            raise BankObjectNotFound(id)
        return json.loads(row["json"])

    def update(self, obj: dict) -> dict:
        """Overwrite an existing row with a hand-corrected object.

        Bumps provenance.version; preserves id and imported_at. Re-validates.
        """
        existing = self._row(obj["id"])
        if existing is None:
            raise BankObjectNotFound(obj["id"])
        old_version = json.loads(existing["json"])["provenance"].get("version", 1)
        obj = dict(obj)
        obj["provenance"]["version"] = old_version + 1
        obj = canonical.load(obj)
        self._upsert(obj, existing["imported_at"])
        return obj

    def mark_reviewed(self, id: str) -> dict:
        """Flip checks.human_reviewed and persist (ADR-0019's review action)."""
        obj = self.get(id)
        obj.setdefault("validation", {}).setdefault("checks", {})["human_reviewed"] = True
        return self.update(obj)

    def search(
        self, *, topic=None, difficulty=None, level=None, source_type=None, reviewed=None
    ) -> list[dict]:
        """topic/difficulty/level/source_type/reviewed all default to "no filter".
        search() with no arguments IS `list` — one query layer for both (R1.4/R1.5).
        """
        ...  # builds a parameterized WHERE clause over the indexed columns above

    def close(self) -> None: ...
    def __enter__(self) -> "Bank": return self
    def __exit__(self, *exc) -> None: self.close()
```

- **`add()` stamps `provenance.created_at` if it's still `null`.** For a
  hand-authored `sourced` object this is the *first* durable boundary it
  crosses (there is no API in front of it yet), matching how V1 stamps
  `created_at` for `generated` objects at the API boundary — same rule
  ("stamp once, at the first durable boundary"), applied to whichever boundary
  actually exists. A `generated` object produced by `mathgen generate` and then
  imported gets the same treatment if its `created_at` is still `null`.
- **`update()`/`mark_reviewed()` never change `id` or `imported_at`.** This is
  a correction of the same bank record, not a lineage fork (unlike the MVP's
  edit ops, which mint a new id + `parent_id`) — ADR-0019 calls this out
  explicitly ("re-validated... same as any other write"), and a stable id
  matters here because E4's question groups will reference ids directly.
- **`reviewed` (the indexed column) is always derived from
  `checks.human_reviewed` at write time** — never set independently, so it can
  never drift from the object it summarizes.

### Errors — `engine/exam_engine/errors.py`

```python
class BankObjectNotFound(EngineError):
    def __init__(self, id: str):
        self.id = id
        super().__init__(f"no bank object with id {id!r}")

class BankDuplicateId(EngineError):
    def __init__(self, id: str):
        self.id = id
        super().__init__(f"bank already has an object with id {id!r} (use --overwrite)")
```

Both subclass `EngineError`, so `mathgen`'s existing catch-all
(`except EngineError as e: _err(str(e)); return 2`) handles them with no new
`dispatch()` branch.

---

## A11 (CLI stage) — `mathgen bank {import,list,search,review}`

```
mathgen bank import <FILE.json> [--overwrite]
mathgen bank list
mathgen bank search [--topic T] [--difficulty D] [--level L]
                     [--source-type {generated,sourced}] [--reviewed {true,false}]
mathgen bank review <ID> [--mark-reviewed] [--no-edit] [--editor CMD]
```

- **`import`** — reuses `_load_questions`'s existing pattern (a file holding
  one object or a JSON array, each passed through `canonical.load`), then
  `bank.add()`s each. Prints one inserted id per line. A duplicate id without
  `--overwrite` is a handled `BankDuplicateId` → exit 2.
- **`list`** / **`search`** — one shared tabular renderer (id · source_type ·
  topic · level · difficulty · reviewed) over `bank.search(**filters)`;
  `list` is `search` with no filters. Matches the breadboard's two CLI
  affordances while sharing one query implementation (R1.5).
- **`review <ID>`** — the CLI-idiomatic shape for "edit a field by hand,
  same as `git commit` opening `$EDITOR`":
  1. `obj = bank.get(id)`.
  2. Unless `--no-edit`: write `obj` to a `NamedTemporaryFile(suffix=".json")`,
     run `$EDITOR` (or `--editor`) on it via `subprocess.run`, re-read and
     `json.loads` the result. A parse failure is a handled error (exit 2,
     nothing is written) — the reviewer gets another try.
  3. If `--mark-reviewed`: flip `checks.human_reviewed` on the (possibly
     edited) object.
  4. If anything changed (an edit happened or `--mark-reviewed` was passed):
     `bank.update(obj)` (which re-validates and bumps `version`). Otherwise
     no-op — running `review <ID>` with neither flag is a no-op preview, not
     an error.
  5. Print the resulting object.
  - No `$EDITOR` set and neither `--no-edit` nor `--editor` given → a clear
    error ("set $EDITOR, or pass --no-edit / --editor") rather than a hang.

### `__main__.py` additions (argparse)

```python
bank = sub.add_parser("bank", help="query/manage the local question bank")
bank_sub = bank.add_subparsers(dest="bank_cmd", required=True)

bimp = bank_sub.add_parser("import")
bimp.add_argument("file")
bimp.add_argument("--overwrite", action="store_true")

bank_sub.add_parser("list")

bsearch = bank_sub.add_parser("search")
bsearch.add_argument("--topic", default=None)
bsearch.add_argument("--difficulty", default=None)
bsearch.add_argument("--level", default=None)
bsearch.add_argument("--source-type", choices=["generated", "sourced"], default=None)
bsearch.add_argument("--reviewed", choices=["true", "false"], default=None)

brev = bank_sub.add_parser("review")
brev.add_argument("id")
brev.add_argument("--mark-reviewed", action="store_true")
brev.add_argument("--no-edit", action="store_true")
brev.add_argument("--editor", default=None)
```

`dispatch()` gains one more top-level route, `"bank": cmd_bank`, which itself
dispatches on `args.bank_cmd` (mirrors `export`'s existing `export_cmd`
nested-subcommand pattern).

---

## Tests

| Test | Asserts | Seam |
|---|---|---|
| `test_bank.py::test_add_get_roundtrip` | `add()` then `get()` returns the same object; `created_at` stamped if it was `null` | A1 |
| `test_bank.py::test_add_rejects_invalid_object` | A schema-invalid object raises `CanonicalValidationError` and is never inserted | A1 |
| `test_bank.py::test_add_duplicate_id` | Second `add()` of the same id raises `BankDuplicateId`; `overwrite=True` succeeds | A1 |
| `test_bank.py::test_search_filters` | Seed several objects; `search(topic=…)`, `search(difficulty=…)`, `search(reviewed=False)` each return exactly the matching subset; `search()` with no args returns everything | A2 |
| `test_bank.py::test_mark_reviewed` | `mark_reviewed()` sets `checks.human_reviewed=True`, bumps `provenance.version`, **keeps `id` and `imported_at` unchanged**; `reviewed` column flips | A10 |
| `test_bank.py::test_update_unknown_id_raises` | `update()`/`mark_reviewed()` on a missing id raises `BankObjectNotFound` | A10 |
| `test_bank.py::test_reviewed_column_never_drifts` | Directly mutating a fetched dict's `checks.human_reviewed` without calling `update()` does not change the indexed column (round-trip through `get()` again shows the stored value) | A1/A10 |
| `cli/tests/test_cli_bank.py::test_import_then_list` | Import the existing `tests/fixtures/sourced/psle_2023_ratio.json`; `bank list` shows it as unreviewed | A11 |
| `cli/tests/test_cli_bank.py::test_persists_across_invocations` | Two separate `main()` calls against the same `EXAM_BANK_PATH` — import in one process-call, `get`/`list` in the next — see the same row (the E1 demo goal, proven directly) | A1, A11 |
| `cli/tests/test_cli_bank.py::test_search_by_reviewed` | `search --reviewed false` finds it; `--reviewed true` doesn't; after `review --mark-reviewed --no-edit`, the reverse | A10, A11 |
| `cli/tests/test_cli_bank.py::test_review_with_editor` | `--editor` set to a tiny stub script that rewrites one field in the tempfile; the bank row reflects the edit and `version` incremented | A11 |
| `cli/tests/test_cli_bank.py::test_import_duplicate_without_overwrite_fails` | Exit code 2, clear stderr message; `--overwrite` succeeds | A11 |
| `cli/tests/test_cli_bank.py::test_bank_path_resolution` | `EXAM_BANK_PATH` unset → falls back to `~/.exam_engine/bank.sqlite3` (assert via `bank.default_path()`, not by touching the real home dir in the test) | A1 |

All CLI tests set `EXAM_BANK_PATH` to a `tmp_path` file via `monkeypatch.setenv`,
mirroring how existing tests already override `EXAM_SCHEMA_PATH`/
`EXAM_CONTENT_DIR`.

---

## Demo / acceptance (E1 done when)

1. `uv run pytest` green (all tables above).
2. `EXAM_BANK_PATH=/tmp/demo.sqlite3 mathgen bank import
   tests/fixtures/sourced/psle_2023_ratio.json` → prints the inserted id.
3. In a **fresh process**, `EXAM_BANK_PATH=/tmp/demo.sqlite3 mathgen bank
   list` → shows the row, `reviewed=no`.
4. `EXAM_BANK_PATH=/tmp/demo.sqlite3 mathgen bank search --reviewed true` →
   empty. `mathgen bank review <id> --mark-reviewed --no-edit` → then
   `search --reviewed true` returns it.
5. Re-running `import` on the same file without `--overwrite` fails with a
   clear message; with `--overwrite` it succeeds and `version` is unchanged
   (overwrite from `add()` re-imports the same content, not a correction —
   only `update()`/`mark_reviewed()` bump `version`).

---

## Decisions resolved

1. ✅ **Bank lives in `engine/exam_engine/bank.py`**, using stdlib `sqlite3` —
   no new dependency, no new workspace member (ADR-0017).
2. ✅ **Default path `~/.exam_engine/bank.sqlite3`, override via
   `EXAM_BANK_PATH`** — mirrors the existing `EXAM_SCHEMA_PATH`/
   `EXAM_CONTENT_DIR` convention rather than inventing a new one.
3. ✅ **`list` and `search` are one query implementation** (`bank.search()`
   with all-optional filters); `list` is the zero-filter case. Two CLI verbs,
   one engine seam.
4. ✅ **Reviewing/correcting a bank object bumps `provenance.version` in
   place; it never gets a new `id` or a `parent_id`.** This is deliberately
   different from the MVP's edit ops (`regenerate`/`make-harder`/…), which
   fork a new versioned object — a bank correction is fixing the *same*
   record, and E4's question groups need that id to stay stable to reference
   it.
5. ✅ **The review action is CLI-editor-based (`$EDITOR`), not a structured
   field-by-field CLI form.** A general "edit any field" affordance is
   exactly what a text editor already is; building a field-by-field CLI UI
   for every canonical-object shape would be thrown away once E5's web forms
   land. `--no-edit`/`--editor` make it scriptable/testable without a real
   terminal editor.
6. ✅ **No `paper_id` column yet.** E4 owns the container; adding it later is
   an additive `ALTER TABLE`, so there's nothing to design ahead of that
   slice.
