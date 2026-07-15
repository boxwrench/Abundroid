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
