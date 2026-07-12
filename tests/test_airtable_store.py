"""Tests for the Airtable store — strict TDD."""

from datetime import datetime, date, timedelta

from abundroid.models import Event, Organization
from abundroid.stores.airtable_store import load_organizations, AirtableEventStore
from abundroid.uid import content_hash


class FakeTable:
    """Fake Airtable table for testing (in-memory)."""

    def __init__(self):
        """Initialize with empty records."""
        self.records = []
        self.next_id = 1
        self.last_create_typecast = None  # Track typecast parameter

    def all(self):
        """Return all records."""
        return self.records

    def create(self, fields, typecast=None):
        """Create a record with the given fields."""
        record_id = f"rec{self.next_id}"
        self.next_id += 1
        record = {"id": record_id, "fields": fields}
        self.records.append(record)
        self.last_create_typecast = typecast
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

    def test_watchlist_and_suggested_stage_are_not_active(self):
        """Orgs staged Watchlist or Suggested are parked, not monitored, even if Active."""
        table = FakeTable()
        table.records = [
            {"id": "rec1", "fields": {"Name": "Parked A", "Events URL": "https://a.com/e",
                                      "Source Type": "rss", "Active": True, "Stage": "Watchlist"}},
            {"id": "rec2", "fields": {"Name": "Parked B", "Events URL": "https://b.com/e",
                                      "Source Type": "rss", "Active": True, "Stage": "Suggested"}},
        ]
        orgs = load_organizations(table)
        assert orgs[0].active is False
        assert orgs[1].active is False

    def test_approved_or_absent_stage_stays_active(self):
        """Stage 'Approved' or no Stage field at all leaves Active as-is."""
        table = FakeTable()
        table.records = [
            {"id": "rec1", "fields": {"Name": "Approved Org", "Events URL": "https://a.com/e",
                                      "Source Type": "rss", "Active": True, "Stage": "Approved"}},
            {"id": "rec2", "fields": {"Name": "No Stage Org", "Events URL": "https://b.com/e",
                                      "Source Type": "rss", "Active": True}},
        ]
        orgs = load_organizations(table)
        assert orgs[0].active is True
        assert orgs[1].active is True

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

    def test_new_event_writes_phase2_fields(self):
        """New event includes Source Hash, Topics, Possible Duplicate Of fields."""
        table = FakeTable()
        store = AirtableEventStore(table)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            topics=["Housing", "Community"],
            possible_duplicate_of="hash:abc123",
        )
        store.upsert([event])

        assert len(table.records) == 1
        fields = table.records[0]["fields"]

        # Verify new Phase 2 fields are present
        expected_hash = content_hash(event)
        assert fields["Source Hash"] == expected_hash
        assert fields["Topics"] == ["Housing", "Community"]
        assert fields["Possible Duplicate Of"] == "hash:abc123"
        assert fields.get("Changed") != True  # Should not be set on create
        assert fields.get("Possibly Cancelled") != True

    def test_new_event_with_empty_topics_omits_field(self):
        """Topics field is omitted when empty."""
        table = FakeTable()
        store = AirtableEventStore(table)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            topics=[],
        )
        store.upsert([event])

        fields = table.records[0]["fields"]
        assert "Topics" not in fields

    def test_new_event_with_empty_duplicate_omits_field(self):
        """Possible Duplicate Of field is omitted when empty."""
        table = FakeTable()
        store = AirtableEventStore(table)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            possible_duplicate_of="",
        )
        store.upsert([event])

        fields = table.records[0]["fields"]
        assert "Possible Duplicate Of" not in fields

    def test_create_passes_typecast_true(self):
        """create() is called with typecast=True."""
        table = FakeTable()
        store = AirtableEventStore(table)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
        )
        store.upsert([event])

        assert table.last_create_typecast is True

    def test_seen_event_update_dict_contains_only_allowed_keys(self):
        """Seen event update contains only allowed keys (not title, organizer, etc.)."""
        table = FakeTable()
        store = AirtableEventStore(table)

        # Create an event first
        event1 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event1])

        # Manually track what update() was called with
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(fields)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Upsert the same event (should be seen)
        store.upsert([event1])

        # Verify update was called with only Last Seen
        assert len(update_calls) == 1
        update_dict = update_calls[0]
        assert "Last Seen" in update_dict
        assert "Title" not in update_dict
        assert "Organizer" not in update_dict
        assert "Description" not in update_dict

    def test_seen_event_with_changed_details_includes_changed_and_source_hash(self):
        """Seen event with different content includes Changed: True and updated Source Hash."""
        table = FakeTable()
        store = AirtableEventStore(table)

        event1 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event1])

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(fields)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Upsert with different content
        event2 = Event(
            title="Event 1 Updated",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event2])

        update_dict = update_calls[0]
        assert "Changed" in update_dict
        assert update_dict["Changed"] is True
        assert "Source Hash" in update_dict
        assert update_dict["Source Hash"] == content_hash(event2)

    def test_seen_event_with_identical_details_no_changed_flag(self):
        """Seen event with identical content does NOT include Changed."""
        table = FakeTable()
        store = AirtableEventStore(table)

        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event])

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(fields)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Upsert with identical content
        store.upsert([event])

        update_dict = update_calls[0]
        # Update should only have Last Seen, no Changed
        assert set(update_dict.keys()) == {"Last Seen"}

    def test_seen_event_clears_possibly_cancelled_when_truthy(self):
        """Seen event clears Possibly Cancelled from True to False."""
        table = FakeTable()
        store = AirtableEventStore(table)

        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event])

        # Manually set Possibly Cancelled to True
        table.records[0]["fields"]["Possibly Cancelled"] = True

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(fields)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Upsert again
        store.upsert([event])

        update_dict = update_calls[0]
        assert "Possibly Cancelled" in update_dict
        assert update_dict["Possibly Cancelled"] is False

    def test_seen_event_omits_possibly_cancelled_when_falsy(self):
        """Seen event omits Possibly Cancelled when it's already falsy."""
        table = FakeTable()
        store = AirtableEventStore(table)

        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event])

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(fields)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Upsert again (Possibly Cancelled not set, so falsy)
        store.upsert([event])

        update_dict = update_calls[0]
        # Only Last Seen should be in update, not Possibly Cancelled
        assert set(update_dict.keys()) == {"Last Seen"}

    def test_flag_missing_flags_future_dated_absent_event(self):
        """flag_missing flags events absent from present_uids if they're future-dated and Approved/Needs Review."""
        table = FakeTable()
        store = AirtableEventStore(table)

        future_date = (date.today() + timedelta(days=1)).isoformat()
        past_date = (date.today() - timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        # Create events
        table.records = [
            {"id": "rec1", "fields": {
                "Event UID": "uid1", "Title": "Event Future", "Organizer": "Org A",
                "Source URL": "https://a.com/events",
                "Start": f"{future_date}T10:00:00", "Status": "Needs Review",
                "Possibly Cancelled": False
            }},
            {"id": "rec2", "fields": {
                "Event UID": "uid2", "Title": "Event Past", "Organizer": "Org A",
                "Source URL": "https://a.com/events",
                "Start": f"{past_date}T10:00:00", "Status": "Approved",
                "Possibly Cancelled": False
            }},
            {"id": "rec3", "fields": {
                "Event UID": "uid3", "Title": "Event No Start", "Organizer": "Org A",
                "Source URL": "https://a.com/events",
                "Status": "Needs Review",
                "Possibly Cancelled": False
            }},
        ]

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append((record_id, fields))
            return original_update(record_id, fields)
        table.update = tracked_update

        # Flag missing for Org A, only uid3 is present
        result = store.flag_missing("Org A", "https://a.com/events", {"uid3"})

        # Should flag only uid1
        assert result == 1
        assert len(update_calls) == 1
        record_id, fields = update_calls[0]
        assert record_id == "rec1"
        assert fields["Possibly Cancelled"] is True

    def test_flag_missing_does_not_flag_other_organizers(self):
        """flag_missing only flags events matching the given organizer."""
        table = FakeTable()
        store = AirtableEventStore(table)

        future_date = (date.today() + timedelta(days=1)).isoformat()

        table.records = [
            {"id": "rec1", "fields": {
                "Event UID": "uid1", "Title": "Event 1", "Organizer": "Org A",
                "Source URL": "https://a.com/events",
                "Start": f"{future_date}T10:00:00", "Status": "Needs Review"
            }},
            {"id": "rec2", "fields": {
                "Event UID": "uid2", "Title": "Event 2", "Organizer": "Org B",
                "Source URL": "https://a.com/events",
                "Start": f"{future_date}T10:00:00", "Status": "Needs Review"
            }},
        ]

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(record_id)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Flag missing for Org A only
        result = store.flag_missing("Org A", "https://a.com/events", set())

        # Should flag only uid1
        assert result == 1
        assert update_calls == ["rec1"]

    def test_flag_missing_does_not_flag_other_sources(self):
        """flag_missing only flags records matching the given source_url, even for the same organizer."""
        table = FakeTable()
        store = AirtableEventStore(table)

        future_date = (date.today() + timedelta(days=1)).isoformat()

        table.records = [
            {"id": "rec1", "fields": {
                "Event UID": "uid1", "Title": "Event Source A", "Organizer": "Org A",
                "Source URL": "https://a.com/events",
                "Start": f"{future_date}T10:00:00", "Status": "Needs Review"
            }},
            {"id": "rec2", "fields": {
                "Event UID": "uid2", "Title": "Event Source B", "Organizer": "Org A",
                "Source URL": "https://b.com/events",
                "Start": f"{future_date}T10:00:00", "Status": "Needs Review"
            }},
        ]

        # Track update calls
        original_update = table.update
        update_calls = []
        def tracked_update(record_id, fields):
            update_calls.append(record_id)
            return original_update(record_id, fields)
        table.update = tracked_update

        # Flag missing for Org A's source A only; neither uid present in this fetch
        result = store.flag_missing("Org A", "https://a.com/events", set())

        # Should flag only rec1 (source A), not rec2 (same organizer, different source)
        assert result == 1
        assert update_calls == ["rec1"]
