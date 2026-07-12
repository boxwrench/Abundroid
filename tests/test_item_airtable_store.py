"""Focused tests for unified Item Airtable persistence."""

from datetime import date, datetime

from abundroid.models import Item
from abundroid.stores.item_airtable_store import AirtableItemStore, load_sources


class FakeTable:
    def __init__(self, records=None):
        self.records = records or []
        self.all_calls = 0
        self.update_calls = []

    def all(self):
        self.all_calls += 1
        return self.records

    def create(self, fields, typecast=False):
        record = {"id": f"rec{len(self.records) + 1}", "fields": dict(fields)}
        self.records.append(record)
        return record

    def update(self, record_id, fields):
        self.update_calls.append((record_id, fields))
        record = next(record for record in self.records if record["id"] == record_id)
        record["fields"].update(fields)


def item(uid: str = "guid:feed:one", **changes) -> Item:
    values = {
        "title": "Original title",
        "publisher": "Publisher",
        "kind": "article",
        "uid": uid,
        "source_item_id": "one",
        "canonical_url": "https://example.com/one",
        "source_url": "https://example.com/feed.xml",
        "published_at": datetime(2026, 7, 1, 9, 30),
        "author": "Author",
        "summary": "Source summary",
        "topics": ["Housing"],
        "source_hash": "hash-one",
    }
    values.update(changes)
    return Item(**values)


def test_upsert_loads_existing_once_and_preserves_editorial_fields():
    table = FakeTable(
        [{
            "id": "rec1",
            "fields": {
                "Item UID": "guid:feed:one",
                "Title": "Reviewed title",
                "Summary": "Reviewed summary",
                "Status": "Approved",
                "Reviewer Notes": "Keep this",
                "Source Hash": "hash-one",
            },
        }]
    )
    store = AirtableItemStore(table)

    result = store.upsert([item(source_hash="hash-two"), item(uid="guid:feed:two")])

    assert result == {"new": 1, "seen": 1}
    assert table.all_calls == 1
    assert table.records[0]["fields"]["Title"] == "Reviewed title"
    assert table.records[0]["fields"]["Summary"] == "Reviewed summary"
    assert table.records[0]["fields"]["Status"] == "Approved"
    assert table.records[0]["fields"]["Reviewer Notes"] == "Keep this"
    assert table.update_calls == [
        ("rec1", {"Last Seen": date.today().isoformat(), "Source Hash": "hash-two", "Changed": True})
    ]


def test_new_item_writes_all_available_fields():
    table = FakeTable()
    AirtableItemStore(table).upsert([item()])

    stored = table.records[0]["fields"]
    assert stored["Item UID"] == "guid:feed:one"
    assert stored["Source Item ID"] == "one"
    assert stored["Published At"] == "2026-07-01T09:30:00"
    assert stored["Topics"] == ["Housing"]
    assert stored["Status"] == "Needs Review"
    assert stored["First Seen"] == date.today().isoformat()


def test_load_sources_resolves_link_and_honors_organization_stage():
    organizations = FakeTable(
        [
            {"id": "org1", "fields": {"Name": "Approved Org", "Active": True, "Stage": "Approved"}},
            {"id": "org2", "fields": {"Name": "Archived Org", "Active": True, "Stage": "Archived"}},
        ]
    )
    source_table = FakeTable(
        [
            {
                "id": "src1",
                "fields": {
                    "Organization": ["org1"],
                    "Organization Name": ["Approved Org"],
                    "Name": "Newsroom",
                    "URL": "https://example.com/feed.xml",
                    "Format": "rss",
                    "Default Kind": "article",
                    "Active": True,
                },
            },
            {
                "id": "src2",
                "fields": {
                    "Organization": ["org2"],
                    "Name": "Old newsroom",
                    "URL": "https://old.example.com/feed.xml",
                    "Format": "rss",
                    "Active": True,
                },
            },
        ]
    )

    sources = load_sources(source_table, organizations)

    assert sources[0].organization == "Approved Org"
    assert sources[0].active is True
    assert sources[1].organization == "Archived Org"
    assert sources[1].active is False


def test_set_possible_duplicates_updates_only_existing_records():
    table = FakeTable(
        [{
            "id": "rec1",
            "fields": {
                "Item UID": "guid:feed:one",
                "Title": "Reviewed title",
                "Last Seen": "2026-06-01",
            },
        }]
    )

    updated = AirtableItemStore(table).set_possible_duplicates(
        {"guid:feed:one": "guid:other:one", "missing": "guid:other:two"}
    )

    assert updated == 1
    assert table.update_calls == [("rec1", {"Possible Duplicate Of": "guid:other:one"})]
    assert table.records[0]["fields"]["Last Seen"] == "2026-06-01"
    assert table.records[0]["fields"]["Title"] == "Reviewed title"


def test_upsert_does_not_replace_reviewed_duplicate_link():
    table = FakeTable(
        [{
            "id": "rec1",
            "fields": {
                "Item UID": "guid:feed:one",
                "Source Hash": "hash-one",
                "Possible Duplicate Of": "reviewed-match",
            },
        }]
    )

    AirtableItemStore(table).upsert([item(possible_duplicate_of="new-suggestion")])

    assert table.records[0]["fields"]["Possible Duplicate Of"] == "reviewed-match"
    assert "Possible Duplicate Of" not in table.update_calls[0][1]
