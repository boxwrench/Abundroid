# tests/test_setup_base.py
from abundroid import setup_base
from abundroid import airtable_schema as schema


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


def test_write_preserves_existing_env_token(tmp_path):
    """Test that real tokens in existing .env are preserved unchanged when updating base ID."""
    # Create .env.example to prove it's NOT used when .env exists
    example = tmp_path / ".env.example"
    example.write_text("AIRTABLE_API_KEY=pat_example_token\nAIRTABLE_BASE_ID=app_your_base_id\n", encoding="utf-8")

    # Create pre-existing .env with real secret and stale base id
    env = tmp_path / ".env"
    env.write_text("AIRTABLE_API_KEY=pat_real_secret_value\nAIRTABLE_BASE_ID=appOLD000\n", encoding="utf-8")

    # Update the base id
    setup_base.write_base_id_to_env("appNEW777", env_path=str(env), example_path=str(example))

    # Verify the result
    result_text = env.read_text(encoding="utf-8")

    # Real token must be preserved unchanged (byte-for-byte)
    assert "AIRTABLE_API_KEY=pat_real_secret_value" in result_text
    # New base id must be present
    assert "AIRTABLE_BASE_ID=appNEW777" in result_text
    # Old base id must be gone
    assert "appOLD000" not in result_text
    # Example API key must NOT appear (proves .env.example wasn't used)
    assert "pat_example_token" not in result_text
    # Exactly one AIRTABLE_BASE_ID line
    assert result_text.count("AIRTABLE_BASE_ID=") == 1


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
