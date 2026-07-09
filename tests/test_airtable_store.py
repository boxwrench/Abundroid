"""Tests for the Airtable store — strict TDD."""

from datetime import datetime, date

from abundroid.models import Event, Organization
from abundroid.stores.airtable_store import load_organizations, AirtableEventStore


class FakeTable:
    """Fake Airtable table for testing (in-memory)."""

    def __init__(self):
        """Initialize with empty records."""
        self.records = []
        self.next_id = 1

    def all(self):
        """Return all records."""
        return self.records

    def create(self, fields):
        """Create a record with the given fields."""
        record_id = f"rec{self.next_id}"
        self.next_id += 1
        record = {"id": record_id, "fields": fields}
        self.records.append(record)
        return record_id

    def update(self, record_id, fields):
        """Update a record."""
        for record in self.records:
            if record["id"] == record_id:
                record["fields"].update(fields)
                break


class TestLoadOrganizations:
    """Tests for loading organizations from Airtable."""

    def test_load_organizations_basic(self):
        """Load organizations from Airtable."""
        table = FakeTable()
        table.records = [
            {
                "id": "rec1",
                "fields": {
                    "Name": "Org A",
                    "Website": "https://orga.com",
                    "Events URL": "https://orga.com/events",
                    "Source Type": "ical",
                    "Active": True,
                    "Notes": "",
                }
            },
            {
                "id": "rec2",
                "fields": {
                    "Name": "Org B",
                    "Website": "https://orgb.com",
                    "Events URL": "https://orgb.com/events",
                    "Source Type": "rss",
                    "Active": False,
                    "Notes": "On hold",
                }
            },
        ]
        orgs = load_organizations(table)
        assert len(orgs) == 2
        assert orgs[0].name == "Org A"
        assert orgs[0].website == "https://orga.com"
        assert orgs[0].events_url == "https://orga.com/events"
        assert orgs[0].source_type == "ical"
        assert orgs[0].active is True
        assert orgs[1].name == "Org B"
        assert orgs[1].active is False
        assert orgs[1].notes == "On hold"

    def test_load_organizations_missing_fields(self):
        """Missing fields should default sensibly."""
        table = FakeTable()
        table.records = [
            {
                "id": "rec1",
                "fields": {
                    "Name": "Org A",
                    "Events URL": "https://orga.com/events",
                    # Website, Source Type, Active, Notes missing
                }
            },
        ]
        orgs = load_organizations(table)
        assert len(orgs) == 1
        assert orgs[0].name == "Org A"
        assert orgs[0].website == ""
        assert orgs[0].source_type == ""
        assert orgs[0].active is False  # checkbox absent = False
        assert orgs[0].notes == ""

    def test_load_organizations_active_is_checkbox(self):
        """Active is a checkbox field (absent = False)."""
        table = FakeTable()
        table.records = [
            {"id": "rec1", "fields": {"Name": "Org A", "Events URL": "url1"}},
            {"id": "rec2", "fields": {"Name": "Org B", "Events URL": "url2", "Active": True}},
            {"id": "rec3", "fields": {"Name": "Org C", "Events URL": "url3", "Active": False}},
        ]
        orgs = load_organizations(table)
        assert orgs[0].active is False
        assert orgs[1].active is True
        assert orgs[2].active is False


class TestAirtableEventStore:
    """Tests for the AirtableEventStore."""

    def test_upsert_new_events(self):
        """Upsert new events — should create with Status 'Needs Review'."""
        table = FakeTable()
        store = AirtableEventStore(table)
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                uid="url:https://example.com/event1"
            ),
            Event(
                title="Event 2",
                organizer="Org B",
                url="https://example.com/event2",
                start=datetime(2026, 7, 15, 10, 0, 0),
                uid="url:https://example.com/event2"
            ),
        ]
        result = store.upsert(events)
        assert result["new"] == 2
        assert result["seen"] == 0
        assert len(table.records) == 2

        # Verify records have correct fields
        record1 = table.records[0]
        assert record1["fields"]["Event UID"] == "url:https://example.com/event1"
        assert record1["fields"]["Title"] == "Event 1"
        assert record1["fields"]["Organizer"] == "Org A"
        assert record1["fields"]["Registration URL"] == "https://example.com/event1"
        assert record1["fields"]["Status"] == "Needs Review"
        assert record1["fields"]["First Seen"] == date.today().isoformat()
        assert record1["fields"]["Last Seen"] == date.today().isoformat()

    def test_upsert_existing_events_update_last_seen(self):
        """Upsert existing events — should update only Last Seen."""
        table = FakeTable()
        store = AirtableEventStore(table)

        # Create an event
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                uid="url:https://example.com/event1"
            ),
        ]
        result1 = store.upsert(events)
        assert result1["new"] == 1
        assert result1["seen"] == 0

        # Manually edit the record to simulate human input
        old_last_seen = table.records[0]["fields"]["Last Seen"]
        table.records[0]["fields"]["Status"] = "Approved"
        table.records[0]["fields"]["Title"] = "Event 1 (Edited)"

        # Upsert same event
        result2 = store.upsert(events)
        assert result2["new"] == 0
        assert result2["seen"] == 1

        # Verify Status and Title unchanged, Last Seen updated
        updated_record = table.records[0]
        assert updated_record["fields"]["Status"] == "Approved"
        assert updated_record["fields"]["Title"] == "Event 1 (Edited)"
        assert updated_record["fields"]["Last Seen"] == date.today().isoformat()

    def test_upsert_with_dates(self):
        """Upsert events with start and end dates formatted as ISO."""
        table = FakeTable()
        store = AirtableEventStore(table)
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                start=datetime(2026, 7, 15, 10, 30, 0),
                end=datetime(2026, 7, 15, 12, 0, 0),
                uid="url:https://example.com/event1"
            ),
        ]
        store.upsert(events)
        record = table.records[0]
        assert record["fields"]["Start"] == "2026-07-15T10:30:00"
        assert record["fields"]["End"] == "2026-07-15T12:00:00"

    def test_upsert_start_none_omits_key(self):
        """When start is None, the key should be omitted (not set to empty string)."""
        table = FakeTable()
        store = AirtableEventStore(table)
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                start=None,
                uid="url:https://example.com/event1"
            ),
        ]
        store.upsert(events)
        record = table.records[0]
        assert "Start" not in record["fields"]

    def test_upsert_end_none_omits_key(self):
        """When end is None, the key should be omitted."""
        table = FakeTable()
        store = AirtableEventStore(table)
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                start=datetime(2026, 7, 15, 10, 0, 0),
                end=None,
                uid="url:https://example.com/event1"
            ),
        ]
        store.upsert(events)
        record = table.records[0]
        assert "End" not in record["fields"]

    def test_upsert_duplicate_uid_in_batch(self):
        """Duplicate UIDs in batch count as new once, then seen."""
        table = FakeTable()
        store = AirtableEventStore(table)
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                uid="url:https://example.com/event1"
            ),
            Event(
                title="Event 1 Duplicate",
                organizer="Org A",
                url="https://example.com/event1",
                uid="url:https://example.com/event1"
            ),
        ]
        result = store.upsert(events)
        assert result["new"] == 1
        assert result["seen"] == 1
        assert len(table.records) == 1
