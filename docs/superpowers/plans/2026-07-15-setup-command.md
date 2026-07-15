# abundroid setup Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `abundroid setup`, a one-command bootstrap that creates the entire Abundroid Airtable base (base, 5 tables, all fields, select options, seed rows) via the metadata API and writes the base ID into `.env`.

**Architecture:** A declarative schema module (`airtable_schema.py`, pure data) is the single source of truth; a thin builder (`setup_base.py`) walks that data and calls pyairtable's metadata API in three passes — create_base with simple fields, add link fields, add the lookup field — then seeds rows and writes `.env`. The CLI gains a `setup` subcommand.

**Tech Stack:** Python 3.11+, pyairtable 3.4 (metadata API: `Api.create_base`, `Table.create_field`, `Table.create`), pytest.

## Global Constraints

- Python floor: `>=3.11`. No new dependencies — `pyairtable` is already required.
- Run all commands from the repository root. Use the venv interpreter: `.venv/Scripts/python.exe` (Windows) or `./.venv/bin/python` (Ubuntu/macOS). Plan commands below use the Windows form; substitute as needed.
- Exact Airtable names are a contract the collector relies on. Table names: `Organizations`, `Sources`, `Items`, `Topics`, `Source Runs` (note the space). Field names, capitalization, and select-option spellings must match `docs/airtable-schema.md` exactly.
- The setup token is read from env var `AIRTABLE_SETUP_TOKEN` (scope `schema.bases:write`) and workspace from `AIRTABLE_WORKSPACE_ID`. Neither is ever written to `.env`. Only the non-secret `AIRTABLE_BASE_ID` is written to `.env`.
- Fresh base each run: no reconciliation. On partial failure, tell the user to delete the half-built base before re-running.
- Airtable field-creation API requires: `checkbox` fields must include `options={"icon": "check", "color": "greenBright"}`; `singleSelect`/`multipleSelects` use `options={"choices": [{"name": "..."}]}`; `number` uses `options={"precision": 0}`; date-only uses `options={"dateFormat": {"name": "iso"}}`; date-time uses `options={"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "utc"}`.
- Commit after each task.

---

### Task 1: Schema module — tables and simple fields

**Files:**
- Create: `src/abundroid/airtable_schema.py`
- Test: `tests/test_airtable_schema.py`

**Interfaces:**
- Produces: `BASE_NAME: str`; `SIMPLE_TABLES: list[dict]` — the exact `tables` payload for `Api.create_base`, where each dict is `{"name": str, "fields": list[dict]}` and each field dict is a valid Airtable field-creation payload. Link and lookup fields are NOT included here (added in Task 2's specs). Later tasks consume `SIMPLE_TABLES`, `BASE_NAME`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_airtable_schema.py
from abundroid import airtable_schema as schema


def _table(name):
    return next(t for t in schema.SIMPLE_TABLES if t["name"] == name)


def _field(table_name, field_name):
    return next(f for f in _table(table_name)["fields"] if f["name"] == field_name)


def test_base_name_is_exact():
    assert schema.BASE_NAME == "Abundroid"


def test_exactly_five_tables_in_order():
    names = [t["name"] for t in schema.SIMPLE_TABLES]
    assert names == ["Organizations", "Sources", "Items", "Topics", "Source Runs"]


def test_primary_fields_are_first_and_correct():
    expected = {
        "Organizations": "Name",
        "Sources": "Name",
        "Items": "Item UID",
        "Topics": "Topic",
        "Source Runs": "Run ID",
    }
    for table_name, primary in expected.items():
        assert _table(table_name)["fields"][0]["name"] == primary


def test_source_runs_result_options_match_collector_contract():
    # Must equal SourceRun.derive_health() outputs exactly.
    choices = {c["name"] for c in _field("Source Runs", "Result")["options"]["choices"]}
    assert choices == {"Working", "No recent items", "Needs attention"}


def test_items_status_options():
    choices = {c["name"] for c in _field("Items", "Status")["options"]["choices"]}
    assert choices == {
        "Needs Review", "Approved", "Rejected", "Duplicate", "Published", "Archived",
    }


def test_format_option_is_only_rss():
    choices = {c["name"] for c in _field("Sources", "Format")["options"]["choices"]}
    assert choices == {"rss"}


def test_checkboxes_have_required_icon_and_color():
    for table_name, field_name in [
        ("Organizations", "Active"), ("Items", "Changed"),
        ("Topics", "Active"), ("Sources", "Active"),
    ]:
        opts = _field(table_name, field_name).get("options", {})
        assert opts.get("icon") and opts.get("color"), (table_name, field_name)


def test_published_at_is_datetime_first_seen_is_date_only():
    assert _field("Items", "Published At")["type"] == "dateTime"
    assert _field("Items", "First Seen")["type"] == "date"
    assert "timeFormat" not in _field("Items", "First Seen").get("options", {})


def test_no_link_or_lookup_fields_in_simple_tables():
    for table in schema.SIMPLE_TABLES:
        for field in table["fields"]:
            assert field["type"] not in ("multipleRecordLinks", "multipleLookupValues")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_airtable_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'abundroid.airtable_schema'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/abundroid/airtable_schema.py
"""Declarative Airtable schema for the Abundroid base (single source of truth)."""

from __future__ import annotations

BASE_NAME = "Abundroid"

_CHECKBOX = {"icon": "check", "color": "greenBright"}
_DATE_ONLY = {"dateFormat": {"name": "iso"}}
_DATE_TIME = {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "utc"}
_KIND_CHOICES = [
    {"name": "article"}, {"name": "post"}, {"name": "update"},
    {"name": "announcement"}, {"name": "report"}, {"name": "event"}, {"name": "other"},
]
_PRIORITY_CHOICES = [{"name": "High"}, {"name": "Medium"}, {"name": "Low"}]


def _select(choices):
    return {"choices": choices}


SIMPLE_TABLES = [
    {
        "name": "Organizations",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "Website", "type": "url"},
            {"name": "Category", "type": "multipleSelects", "options": _select([])},
            {"name": "Priority", "type": "singleSelect", "options": _select(_PRIORITY_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Stage", "type": "singleSelect", "options": _select([
                {"name": "Approved"}, {"name": "Watchlist"},
                {"name": "Suggested"}, {"name": "Archived"},
            ])},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Sources",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "URL", "type": "url"},
            {"name": "Format", "type": "singleSelect", "options": _select([{"name": "rss"}])},
            {"name": "Default Kind", "type": "singleSelect", "options": _select(_KIND_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Items",
        "fields": [
            {"name": "Item UID", "type": "singleLineText"},
            {"name": "Source Item ID", "type": "singleLineText"},
            {"name": "Canonical URL", "type": "url"},
            {"name": "Source URL", "type": "url"},
            {"name": "Title", "type": "singleLineText"},
            {"name": "Publisher", "type": "singleLineText"},
            {"name": "Kind", "type": "singleSelect", "options": _select(_KIND_CHOICES)},
            {"name": "Published At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Author", "type": "singleLineText"},
            {"name": "Summary", "type": "multilineText"},
            {"name": "Topics", "type": "multipleSelects", "options": _select([])},
            {"name": "Status", "type": "singleSelect", "options": _select([
                {"name": "Needs Review"}, {"name": "Approved"}, {"name": "Rejected"},
                {"name": "Duplicate"}, {"name": "Published"}, {"name": "Archived"},
            ])},
            {"name": "Reviewer Notes", "type": "multilineText"},
            {"name": "Scheduled Start", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Scheduled End", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Location", "type": "singleLineText"},
            {"name": "Source Hash", "type": "singleLineText"},
            {"name": "First Seen", "type": "date", "options": _DATE_ONLY},
            {"name": "Last Seen", "type": "date", "options": _DATE_ONLY},
            {"name": "Changed", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Possible Duplicate Of", "type": "singleLineText"},
        ],
    },
    {
        "name": "Topics",
        "fields": [
            {"name": "Topic", "type": "singleLineText"},
            {"name": "Keywords", "type": "multilineText"},
            {"name": "Aliases", "type": "multilineText"},
            {"name": "Exclusions", "type": "multilineText"},
            {"name": "Priority", "type": "singleSelect", "options": _select(_PRIORITY_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Source Runs",
        "fields": [
            {"name": "Run ID", "type": "singleLineText"},
            {"name": "Started At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Finished At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Result", "type": "singleSelect", "options": _select([
                {"name": "Working"}, {"name": "No recent items"}, {"name": "Needs attention"},
            ])},
            {"name": "Items Found", "type": "number", "options": {"precision": 0}},
            {"name": "HTTP Status", "type": "number", "options": {"precision": 0}},
            {"name": "Error", "type": "multilineText"},
        ],
    },
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_airtable_schema.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/abundroid/airtable_schema.py tests/test_airtable_schema.py
git commit -m "feat: add declarative Airtable schema (tables + simple fields)"
```

---

### Task 2: Schema module — link, lookup, and seed specs

**Files:**
- Modify: `src/abundroid/airtable_schema.py`
- Test: `tests/test_airtable_schema.py`

**Interfaces:**
- Produces:
  - `LINK_FIELDS: list[dict]` — each `{"table", "name", "linked_table", "single": bool}`.
  - `LOOKUP_FIELDS: list[dict]` — each `{"table", "name", "via_link_field", "linked_table", "linked_field"}`.
  - `SEED_ORGANIZATION: dict` — Organizations field values.
  - `SEED_SOURCE: dict` — Sources field values (without the Organization link, added by the builder).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_airtable_schema.py
def test_link_fields_cover_organization_and_source():
    by_name = {(l["table"], l["name"]): l for l in schema.LINK_FIELDS}
    org = by_name[("Sources", "Organization")]
    assert org["linked_table"] == "Organizations" and org["single"] is True
    src = by_name[("Source Runs", "Source")]
    assert src["linked_table"] == "Sources" and src["single"] is True


def test_lookup_field_is_organization_name():
    lookup = schema.LOOKUP_FIELDS[0]
    assert lookup == {
        "table": "Sources",
        "name": "Organization Name",
        "via_link_field": "Organization",
        "linked_table": "Organizations",
        "linked_field": "Name",
    }


def test_seed_uses_hypertext_real_feed_url():
    assert schema.SEED_ORGANIZATION["Name"] == "Hypertext"
    assert schema.SEED_ORGANIZATION["Stage"] == "Approved"
    assert schema.SEED_ORGANIZATION["Active"] is True
    assert schema.SEED_SOURCE["URL"] == "https://hypertext.niskanencenter.org/feed/"
    assert schema.SEED_SOURCE["Format"] == "rss"
    assert "Organization" not in schema.SEED_SOURCE  # link added by builder
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_airtable_schema.py -k "link or lookup or seed" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'LINK_FIELDS'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/abundroid/airtable_schema.py
LINK_FIELDS = [
    {"table": "Sources", "name": "Organization", "linked_table": "Organizations", "single": True},
    {"table": "Source Runs", "name": "Source", "linked_table": "Sources", "single": True},
]

LOOKUP_FIELDS = [
    {
        "table": "Sources",
        "name": "Organization Name",
        "via_link_field": "Organization",
        "linked_table": "Organizations",
        "linked_field": "Name",
    },
]

SEED_ORGANIZATION = {
    "Name": "Hypertext",
    "Website": "https://hypertext.niskanencenter.org",
    "Active": True,
    "Stage": "Approved",
}

SEED_SOURCE = {
    "Name": "Hypertext journal feed",
    "URL": "https://hypertext.niskanencenter.org/feed/",
    "Format": "rss",
    "Default Kind": "article",
    "Active": True,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_airtable_schema.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/abundroid/airtable_schema.py tests/test_airtable_schema.py
git commit -m "feat: add link, lookup, and Hypertext seed specs to schema"
```

---

### Task 3: `.env` writer

**Files:**
- Create: `src/abundroid/setup_base.py`
- Test: `tests/test_setup_base.py`

**Interfaces:**
- Produces:
  - `env_text_with_base_id(existing_text: str, base_id: str) -> str` — pure; upserts an `AIRTABLE_BASE_ID=` line.
  - `write_base_id_to_env(base_id: str, env_path: str = ".env", example_path: str = ".env.example") -> None` — creates `.env` from example if absent, then upserts the base ID line.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_setup_base.py
from abundroid import setup_base


def test_env_text_appends_when_absent():
    out = setup_base.env_text_with_base_id("AIRTABLE_API_KEY=pat_x\n", "appABC123")
    assert "AIRTABLE_API_KEY=pat_x" in out
    assert "AIRTABLE_BASE_ID=appABC123" in out


def test_env_text_replaces_placeholder():
    existing = "AIRTABLE_API_KEY=pat_x\nAIRTABLE_BASE_ID=app_your_base_id\n"
    out = setup_base.env_text_with_base_id(existing, "appREAL999")
    assert "AIRTABLE_BASE_ID=appREAL999" in out
    assert "app_your_base_id" not in out
    assert out.count("AIRTABLE_BASE_ID=") == 1


def test_env_text_never_duplicates_on_repeat():
    once = setup_base.env_text_with_base_id("", "appONE")
    twice = setup_base.env_text_with_base_id(once, "appTWO")
    assert twice.count("AIRTABLE_BASE_ID=") == 1
    assert "AIRTABLE_BASE_ID=appTWO" in twice


def test_write_creates_env_from_example(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text("AIRTABLE_API_KEY=pat_your_token\nAIRTABLE_BASE_ID=app_your_base_id\n", encoding="utf-8")
    env = tmp_path / ".env"
    setup_base.write_base_id_to_env("appXYZ", env_path=str(env), example_path=str(example))
    text = env.read_text(encoding="utf-8")
    assert "AIRTABLE_BASE_ID=appXYZ" in text
    assert "AIRTABLE_API_KEY=pat_your_token" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_setup_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'abundroid.setup_base'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/abundroid/setup_base.py
"""Builder that creates the Abundroid Airtable base from the declarative schema."""

from __future__ import annotations

import os


def env_text_with_base_id(existing_text: str, base_id: str) -> str:
    """Return env-file text with AIRTABLE_BASE_ID set to base_id (upsert)."""
    line = f"AIRTABLE_BASE_ID={base_id}"
    lines = existing_text.splitlines()
    replaced = False
    for i, raw in enumerate(lines):
        if raw.strip().startswith("AIRTABLE_BASE_ID="):
            lines[i] = line
            replaced = True
            break
    if not replaced:
        lines.append(line)
    return "\n".join(lines) + "\n"


def write_base_id_to_env(base_id: str, env_path: str = ".env", example_path: str = ".env.example") -> None:
    """Create .env from the example if missing, then upsert the base ID line."""
    if not os.path.exists(env_path) and os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as example:
            existing = example.read()
    elif os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as env_file:
            existing = env_file.read()
    else:
        existing = ""
    with open(env_path, "w", encoding="utf-8") as env_file:
        env_file.write(env_text_with_base_id(existing, base_id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_setup_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/abundroid/setup_base.py tests/test_setup_base.py
git commit -m "feat: add .env base-id writer for setup command"
```

---

### Task 4: Builder — `build_base`

**Files:**
- Modify: `src/abundroid/setup_base.py`
- Test: `tests/test_setup_base.py`

**Interfaces:**
- Consumes: `airtable_schema.SIMPLE_TABLES`, `LINK_FIELDS`, `LOOKUP_FIELDS`, `SEED_ORGANIZATION`, `SEED_SOURCE`; a pyairtable-like `api` object exposing `create_base(workspace_id, name, tables) -> base`, where `base` has `.id`, `.tables() -> list[table]`; each `table` has `.name`, `.id`, `.schema().fields` (each field has `.name`, `.id`), `.create_field(name, field_type, options=None) -> field`, and `.create(fields) -> {"id": ...}`.
- Produces: `build_base(api, workspace_id, *, seed: bool = True) -> str` returning the new base ID.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_setup_base.py
from abundroid import airtable_schema as schema


class FakeField:
    def __init__(self, name, fid):
        self.name = name
        self.id = fid


class FakeSchema:
    def __init__(self, fields):
        self.fields = fields


class FakeTable:
    def __init__(self, name, tid):
        self.name = name
        self.id = tid
        self._fields = []
        self.created_records = []

    def add_initial_field(self, name):
        self._fields.append(FakeField(name, f"fld_{self.name}_{name}".replace(" ", "")))

    def schema(self):
        return FakeSchema(list(self._fields))

    def create_field(self, name, field_type, options=None):
        field = FakeField(name, f"fld_{self.name}_{name}".replace(" ", ""))
        self._fields.append(field)
        self.calls_append(("create_field", self.name, name, field_type, options))
        return field

    def create(self, fields):
        self.created_records.append(fields)
        rec_id = f"rec_{self.name}_{len(self.created_records)}"
        self.calls_append(("create", self.name, fields))
        return {"id": rec_id}

    calls = None

    def calls_append(self, item):
        FakeTable.calls.append(item)


class FakeBase:
    def __init__(self, tables):
        self.id = "appFAKE123"
        self._tables = tables

    def tables(self):
        return self._tables


class FakeApi:
    def __init__(self):
        self.create_base_args = None

    def create_base(self, workspace_id, name, tables):
        self.create_base_args = (workspace_id, name, tables)
        built = []
        for spec in tables:
            t = FakeTable(spec["name"], f"tbl_{spec['name']}".replace(" ", ""))
            for field in spec["fields"]:
                t.add_initial_field(field["name"])
            built.append(t)
        return FakeBase(built)


def test_build_base_creates_base_with_all_tables_and_returns_id():
    FakeTable.calls = []
    api = FakeApi()
    base_id = setup_base.build_base(api, "wspTEST", seed=False)
    assert base_id == "appFAKE123"
    ws, name, tables = api.create_base_args
    assert ws == "wspTEST"
    assert name == "Abundroid"
    assert [t["name"] for t in tables] == [
        "Organizations", "Sources", "Items", "Topics", "Source Runs",
    ]


def test_build_base_adds_link_then_lookup_fields():
    FakeTable.calls = []
    api = FakeApi()
    setup_base.build_base(api, "wspTEST", seed=False)
    field_calls = [c for c in FakeTable.calls if c[0] == "create_field"]
    types = [c[3] for c in field_calls]
    # Link fields created before lookup fields
    assert types == ["multipleRecordLinks", "multipleRecordLinks", "multipleLookupValues"]
    org_link = field_calls[0]
    assert org_link[1:3] == ("Sources", "Organization")
    assert org_link[4]["linkedTableId"] == "tbl_Organizations"
    assert org_link[4]["prefersSingleRecordLink"] is True
    lookup = field_calls[2]
    assert lookup[4]["recordLinkFieldId"] == "fld_Sources_Organization"
    assert lookup[4]["fieldIdInLinkedTable"] == "fld_Organizations_Name"


def test_build_base_seeds_hypertext_with_link():
    FakeTable.calls = []
    api = FakeApi()
    setup_base.build_base(api, "wspTEST", seed=True)
    creates = [c for c in FakeTable.calls if c[0] == "create"]
    org_create = next(c for c in creates if c[1] == "Organizations")
    assert org_create[2]["Name"] == "Hypertext"
    src_create = next(c for c in creates if c[1] == "Sources")
    assert src_create[2]["URL"] == "https://hypertext.niskanencenter.org/feed/"
    assert src_create[2]["Organization"] == ["rec_Organizations_1"]


def test_build_base_seed_false_creates_no_records():
    FakeTable.calls = []
    api = FakeApi()
    setup_base.build_base(api, "wspTEST", seed=False)
    assert [c for c in FakeTable.calls if c[0] == "create"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_setup_base.py -k build_base -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'build_base'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/abundroid/setup_base.py
from abundroid import airtable_schema as schema


def _field_id(table, field_name):
    for field in table.schema().fields:
        if field.name == field_name:
            return field.id
    raise KeyError(f"field {field_name!r} not found on table {table.name!r}")


def build_base(api, workspace_id, *, seed: bool = True) -> str:
    """Create the Abundroid base, its link/lookup fields, and (optionally) seed rows."""
    base = api.create_base(workspace_id, schema.BASE_NAME, schema.SIMPLE_TABLES)
    tables = {t.name: t for t in base.tables()}

    for link in schema.LINK_FIELDS:
        linked_id = tables[link["linked_table"]].id
        tables[link["table"]].create_field(
            link["name"],
            "multipleRecordLinks",
            options={"linkedTableId": linked_id, "prefersSingleRecordLink": link["single"]},
        )

    for lookup in schema.LOOKUP_FIELDS:
        table = tables[lookup["table"]]
        link_field_id = _field_id(table, lookup["via_link_field"])
        linked_field_id = _field_id(tables[lookup["linked_table"]], lookup["linked_field"])
        table.create_field(
            lookup["name"],
            "multipleLookupValues",
            options={"recordLinkFieldId": link_field_id, "fieldIdInLinkedTable": linked_field_id},
        )

    if seed:
        org = tables["Organizations"].create(dict(schema.SEED_ORGANIZATION))
        source_fields = dict(schema.SEED_SOURCE)
        source_fields["Organization"] = [org["id"]]
        tables["Sources"].create(source_fields)

    return base.id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_setup_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/abundroid/setup_base.py tests/test_setup_base.py
git commit -m "feat: add build_base three-pass Airtable builder"
```

---

### Task 5: CLI `setup` subcommand

**Files:**
- Modify: `src/abundroid/cli.py`
- Test: `tests/test_cli_setup.py`

**Interfaces:**
- Consumes: `setup_base.build_base`, `setup_base.write_base_id_to_env`.
- Produces: `run_setup(args) -> int`; a `setup` subparser with `--no-seed` (store_true). `main()` routes `setup` to `run_setup`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_setup.py
import abundroid.cli as cli


def test_setup_missing_env_returns_1(monkeypatch, capsys):
    monkeypatch.delenv("AIRTABLE_SETUP_TOKEN", raising=False)
    monkeypatch.delenv("AIRTABLE_WORKSPACE_ID", raising=False)
    rc = cli.main(["setup"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "AIRTABLE_SETUP_TOKEN" in err


def test_setup_happy_path(monkeypatch, capsys):
    monkeypatch.setenv("AIRTABLE_SETUP_TOKEN", "pat_setup")
    monkeypatch.setenv("AIRTABLE_WORKSPACE_ID", "wsp123")
    calls = {}

    class FakeApi:
        def __init__(self, token):
            calls["token"] = token

    monkeypatch.setattr(cli, "_make_setup_api", lambda token: FakeApi(token))

    def fake_build(api, ws, seed=True):
        calls["build"] = (ws, seed)
        return "appNEW1"

    def fake_write(base_id, **kw):
        calls["wrote"] = base_id

    monkeypatch.setattr(cli.setup_base, "build_base", fake_build)
    monkeypatch.setattr(cli.setup_base, "write_base_id_to_env", fake_write)
    rc = cli.main(["setup"])
    assert rc == 0
    assert calls["build"] == ("wsp123", True)
    assert calls["wrote"] == "appNEW1"
    out = capsys.readouterr().out
    assert "appNEW1" in out
    assert "revoke" in out.lower()  # reminds user to revoke the setup token


def test_setup_no_seed_flag(monkeypatch):
    monkeypatch.setenv("AIRTABLE_SETUP_TOKEN", "pat_setup")
    monkeypatch.setenv("AIRTABLE_WORKSPACE_ID", "wsp123")
    seen = {}
    monkeypatch.setattr(cli, "_make_setup_api", lambda token: object())

    def fake_build(api, ws, seed=True):
        seen["seed"] = seed
        return "appNEW2"

    monkeypatch.setattr(cli.setup_base, "build_base", fake_build)
    monkeypatch.setattr(cli.setup_base, "write_base_id_to_env", lambda base_id, **kw: None)
    cli.main(["setup", "--no-seed"])
    assert seen["seed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli_setup.py -v`
Expected: FAIL — `AttributeError: module 'abundroid.cli' has no attribute 'setup_base'` (or `run_setup`)

- [ ] **Step 3: Write minimal implementation**

```python
# in src/abundroid/cli.py — add import near the top
from abundroid import setup_base
```

```python
# in src/abundroid/cli.py — add these functions above main()
def _make_setup_api(token):
    import pyairtable

    return pyairtable.Api(token)


def run_setup(args):
    """Create the Abundroid Airtable base from the declarative schema."""
    token = os.environ.get("AIRTABLE_SETUP_TOKEN", "").strip()
    workspace = os.environ.get("AIRTABLE_WORKSPACE_ID", "").strip()
    if not token or not workspace:
        print(
            "Error: set AIRTABLE_SETUP_TOKEN (a one-time token with "
            "schema.bases:write) and AIRTABLE_WORKSPACE_ID (from the Airtable "
            "URL, the wsp... segment). Do not put these in .env.",
            file=sys.stderr,
        )
        return 1

    api = _make_setup_api(token)
    try:
        base_id = setup_base.build_base(api, workspace, seed=not args.no_seed)
    except Exception as exc:
        print(
            f"Error creating base: {exc}\n"
            "If a partial 'Abundroid' base was created, delete it in Airtable "
            "before running setup again.",
            file=sys.stderr,
        )
        return 1

    setup_base.write_base_id_to_env(base_id)
    print(f"Created base {base_id} and wrote AIRTABLE_BASE_ID to .env.")
    print("Next steps (not automatable via the Airtable API):")
    print("  1. Build the 9 saved views (airtable-schema.md section 9).")
    print("  2. Build the 3 Interface pages (airtable-schema.md sections 10-11).")
    print("  3. Create the minimal runtime token: data.records:read + "
          "data.records:write, scoped to this base (section 12).")
    print("  4. Revoke the AIRTABLE_SETUP_TOKEN now that setup is complete.")
    return 0
```

```python
# in src/abundroid/cli.py main() — register the subparser after the collect block
    setup_parser = subparsers.add_parser(
        "setup", help="Create the Abundroid Airtable base, fields, and seed rows"
    )
    setup_parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip creating the Hypertext example Organization and Source",
    )
```

```python
# in src/abundroid/cli.py main() — add routing next to the collect branch
    if args.command == "setup":
        return run_setup(args)
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (all tests, including existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/abundroid/cli.py tests/test_cli_setup.py
git commit -m "feat: wire up abundroid setup subcommand"
```

---

### Task 6: Documentation — promote `setup` to the primary path

**Files:**
- Modify: `docs/SETUP.md`
- Modify: `docs/airtable-schema.md`
- Modify: `.env.example` (only if it lacks an `AIRTABLE_BASE_ID` line to upsert)

**Interfaces:** none (docs only).

- [ ] **Step 1: Confirm `.env.example` has an upsert target**

Run: `.venv/Scripts/python.exe -c "print(open('.env.example').read())"`
Expected: shows an `AIRTABLE_BASE_ID=` line. If absent, add `AIRTABLE_BASE_ID=app_your_base_id` under the API key line.

- [ ] **Step 2: Rewrite SETUP.md section 3 as the automated path**

Replace the "Build the Airtable Base and Interface" step so it reads: create a one-time token with `schema.bases:write`; find the workspace ID (`wsp...`) in the Airtable URL; then run — export the two env vars and `abundroid setup`. Document that it creates the base + tables + fields + Hypertext seed and writes the base ID to `.env`, then that views, the Interface, and the runtime token remain manual (cross-reference `airtable-schema.md` sections 9–12). Keep the old manual build available.

Example block to include:

```powershell
# Windows
$env:AIRTABLE_SETUP_TOKEN = "pat_one_time_schema_token"
$env:AIRTABLE_WORKSPACE_ID = "wsp_your_workspace"
.\.venv\Scripts\abundroid.exe setup
```

```bash
# Ubuntu or macOS
export AIRTABLE_SETUP_TOKEN=pat_one_time_schema_token
export AIRTABLE_WORKSPACE_ID=wsp_your_workspace
./.venv/bin/abundroid setup
```

- [ ] **Step 3: Add a fallback banner to airtable-schema.md**

At the top of `docs/airtable-schema.md`, add a note: "You can create everything in sections 1–8 automatically with `abundroid setup` (see SETUP.md). Follow the manual steps below only if you prefer to build by hand or need to understand the schema. Sections 9–12 (views, Interface, token) are manual either way."

- [ ] **Step 4: Commit**

```bash
git add docs/SETUP.md docs/airtable-schema.md .env.example
git commit -m "docs: promote abundroid setup as the primary Airtable path"
```

---

### Task 7: Guarded live smoke test (opt-in)

**Files:**
- Create: `tests/test_setup_live.py`

**Interfaces:** none (opt-in integration test).

- [ ] **Step 1: Write the guarded live test**

```python
# tests/test_setup_live.py
import os
import pytest

from abundroid import setup_base


LIVE = os.environ.get("ABUNDROID_LIVE_SETUP") == "1"


@pytest.mark.skipif(not LIVE, reason="set ABUNDROID_LIVE_SETUP=1 to run a real Airtable build")
def test_live_build_creates_base():
    import pyairtable

    token = os.environ["AIRTABLE_SETUP_TOKEN"]
    workspace = os.environ["AIRTABLE_WORKSPACE_ID"]
    api = pyairtable.Api(token)
    base_id = setup_base.build_base(api, workspace, seed=True)
    assert base_id.startswith("app")
    print(f"\nLive base created: {base_id} — delete it in Airtable when done.")
```

- [ ] **Step 2: Verify it is skipped by default**

Run: `.venv/Scripts/python.exe -m pytest tests/test_setup_live.py -v`
Expected: SKIPPED (1 skipped)

- [ ] **Step 3: Commit**

```bash
git add tests/test_setup_live.py
git commit -m "test: add opt-in live Airtable setup smoke test"
```

- [ ] **Step 4: Manual live verification (during the deployer walkthrough)**

Create a one-time `schema.bases:write` token and export it with the workspace ID, then run `abundroid setup`. In Airtable confirm: base `Abundroid` exists; 5 tables with exact names; the Sources `Organization Name` lookup populates `Hypertext`; the Source Runs `Result` field has the three expected options. Then run `abundroid collect --dry-run` and confirm the Airtable Source (not the CSV source) reports `ok`.

---

## Notes / risks to watch during implementation

- **Empty select choices:** `Category`, `Topics` (Items), and Organizations `Category` are created with `"choices": []`. If Airtable rejects empty-choice select creation, add a temporary placeholder choice or omit `options` and confirm the field still creates as a select. Verify in the Task 7 live run.
- **Link fields in initial payload:** the builder deliberately adds link fields *after* `create_base` (never in the initial table payload), because linked-table IDs do not exist until the base is created. Do not move them into `SIMPLE_TABLES`.
- **Field ordering:** link/lookup fields land at the end of their tables rather than in the doc's listed position. This is cosmetic and does not affect the collector.
