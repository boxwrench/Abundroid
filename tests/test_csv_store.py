"""Tests for the CSV store — strict TDD."""

import tempfile
from pathlib import Path
from datetime import date, datetime

from abundroid.models import Event, Organization
from abundroid.stores.csv_store import load_organizations, CsvEventStore
from abundroid.uid import content_hash


class TestLoadOrganizations:
    """Tests for loading organizations from CSV."""

    def test_load_organizations_basic(self, tmp_path):
        """Load a basic CSV with organizations."""
        csv_file = tmp_path / "orgs.csv"
        csv_file.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org A,https://orga.com,https://orga.com/events,ical,yes,\n"
            "Org B,https://orgb.com,https://orgb.com/events,rss,true,Good org\n"
        )
        orgs = load_organizations(str(csv_file))
        assert len(orgs) == 2
        assert orgs[0].name == "Org A"
        assert orgs[0].website == "https://orga.com"
        assert orgs[0].events_url == "https://orga.com/events"
        assert orgs[0].source_type == "ical"
        assert orgs[0].active is True
        assert orgs[1].name == "Org B"
        assert orgs[1].active is True
        assert orgs[1].notes == "Good org"

    def test_active_flag_parsing(self, tmp_path):
        """Test that active flag parses yes/true/1 as True."""
        csv_file = tmp_path / "orgs.csv"
        csv_file.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org 1,https://org1.com,https://org1.com/events,ical,yes,\n"
            "Org 2,https://org2.com,https://org2.com/events,ical,true,\n"
            "Org 3,https://org3.com,https://org3.com/events,ical,1,\n"
            "Org 4,https://org4.com,https://org4.com/events,ical,no,\n"
            "Org 5,https://org5.com,https://org5.com/events,ical,false,\n"
            "Org 6,https://org6.com,https://org6.com/events,ical,0,\n"
        )
        orgs = load_organizations(str(csv_file))
        assert len(orgs) == 6
        assert orgs[0].active is True
        assert orgs[1].active is True
        assert orgs[2].active is True
        assert orgs[3].active is False
        assert orgs[4].active is False
        assert orgs[5].active is False

    def test_active_flag_case_insensitive(self, tmp_path):
        """Test that active flag parsing is case-insensitive."""
        csv_file = tmp_path / "orgs.csv"
        csv_file.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org 1,https://org1.com,https://org1.com/events,ical,YES,\n"
            "Org 2,https://org2.com,https://org2.com/events,ical,True,\n"
        )
        orgs = load_organizations(str(csv_file))
        assert len(orgs) == 2
        assert orgs[0].active is True
        assert orgs[1].active is True

    def test_skip_empty_name(self, tmp_path):
        """Skip rows where name is empty."""
        csv_file = tmp_path / "orgs.csv"
        csv_file.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org A,https://orga.com,https://orga.com/events,ical,yes,\n"
            ",https://orgb.com,https://orgb.com/events,rss,yes,\n"
            "Org C,https://orgc.com,https://orgc.com/events,ical,yes,\n"
        )
        orgs = load_organizations(str(csv_file))
        assert len(orgs) == 2
        assert orgs[0].name == "Org A"
        assert orgs[1].name == "Org C"

    def test_skip_empty_events_url(self, tmp_path):
        """Skip rows where events_url is empty."""
        csv_file = tmp_path / "orgs.csv"
        csv_file.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org A,https://orga.com,https://orga.com/events,ical,yes,\n"
            "Org B,https://orgb.com,,rss,yes,\n"
            "Org C,https://orgc.com,https://orgc.com/events,ical,yes,\n"
        )
        orgs = load_organizations(str(csv_file))
        assert len(orgs) == 2
        assert orgs[0].name == "Org A"
        assert orgs[1].name == "Org C"


class TestCsvEventStore:
    """Tests for the CsvEventStore."""

    def test_upsert_new_events(self, tmp_path):
        """Upsert new events — should have Needs Review status and today's date."""
        store = CsvEventStore(tmp_path / "events.csv")
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
                uid="url:https://example.com/event2"
            ),
        ]
        result = store.upsert(events)
        assert result["new"] == 2
        assert result["seen"] == 0

        # Check CSV was written
        csv_file = tmp_path / "events.csv"
        assert csv_file.exists()
        lines = csv_file.read_text().strip().split("\n")
        assert len(lines) == 3  # header + 2 events
        # Verify header
        header = lines[0]
        assert "uid" in header
        assert "title" in header
        assert "status" in header
        assert "first_seen" in header
        assert "last_seen" in header

    def test_upsert_second_time_preserves_status(self, tmp_path):
        """Second upsert of same events updates only last_seen, preserves status."""
        store = CsvEventStore(tmp_path / "events.csv")
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

        # Manually edit the CSV to change status
        csv_file = tmp_path / "events.csv"
        lines = csv_file.read_text().split("\n")
        # Change the status field from "Needs Review" to "Approved"
        lines[1] = lines[1].replace("Needs Review", "Approved")
        csv_file.write_text("\n".join(lines))

        # Upsert again with same event
        result2 = store.upsert(events)
        assert result2["new"] == 0
        assert result2["seen"] == 1

        # Verify status is still "Approved" (human edit preserved)
        csv_content = csv_file.read_text()
        assert "Approved" in csv_content

    def test_upsert_creates_directory(self, tmp_path):
        """Upsert should create parent directory if missing."""
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                uid="url:https://example.com/event1"
            ),
        ]
        deep_path = tmp_path / "deep" / "nested" / "events.csv"
        store = CsvEventStore(deep_path)
        result = store.upsert(events)
        assert result["new"] == 1
        assert deep_path.exists()

    def test_upsert_duplicate_uid_in_batch(self, tmp_path):
        """Duplicate UIDs within one batch count as new once, then seen."""
        store = CsvEventStore(tmp_path / "events.csv")
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

    def test_csv_columns_and_iso_format(self, tmp_path):
        """Verify CSV has correct columns and datetime fields are ISO formatted."""
        from datetime import datetime
        store = CsvEventStore(tmp_path / "events.csv")
        events = [
            Event(
                title="Event 1",
                organizer="Org A",
                url="https://example.com/event1",
                start=datetime(2026, 7, 15, 10, 30, 0),
                end=datetime(2026, 7, 15, 12, 0, 0),
                location="Room A",
                description="Test event",
                source_url="https://example.com/feed",
                uid="url:https://example.com/event1"
            ),
        ]
        store.upsert(events)
        csv_file = tmp_path / "events.csv"
        content = csv_file.read_text()
        lines = content.strip().split("\n")

        # Check header
        header = lines[0]
        expected_cols = ["uid", "title", "organizer", "url", "start", "end",
                         "location", "description", "source_url", "status",
                         "first_seen", "last_seen"]
        for col in expected_cols:
            assert col in header

        # Check data row has ISO formatted dates
        assert "2026-07-15T10:30:00" in content
        assert "2026-07-15T12:00:00" in content

    def test_new_event_writes_phase2_columns(self, tmp_path):
        """New event row includes source_hash, topics, possible_duplicate_of, changed, possibly_cancelled."""
        store = CsvEventStore(tmp_path / "events.csv")
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            topics=["Housing", "Community"],
            possible_duplicate_of="hash:abc123",
        )
        store.upsert([event])

        csv_file = tmp_path / "events.csv"
        content = csv_file.read_text()
        lines = content.strip().split("\n")

        # Check header includes new columns
        header = lines[0]
        assert "topics" in header
        assert "possible_duplicate_of" in header
        assert "source_hash" in header
        assert "changed" in header
        assert "possibly_cancelled" in header

        # Check data row has correct values
        data_row = lines[1]
        expected_hash = content_hash(event)
        assert expected_hash in data_row
        assert "Housing; Community" in data_row
        assert "hash:abc123" in data_row
        # changed and possibly_cancelled should be empty on new
        import csv
        reader = csv.DictReader(lines)
        rows = list(reader)
        assert rows[0]["changed"] == ""
        assert rows[0]["possibly_cancelled"] == ""

    def test_seen_event_with_changed_details_sets_changed_flag(self, tmp_path):
        """Seen event with different source_hash sets changed='yes' and updates source_hash."""
        store = CsvEventStore(tmp_path / "events.csv")
        event1 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        # First upsert
        store.upsert([event1])

        # Second upsert with same uid but different content (title changed)
        event2 = Event(
            title="Event 1 Updated",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event2])

        csv_file = tmp_path / "events.csv"
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["changed"] == "yes"
        # source_hash should be updated to the new hash
        new_hash = content_hash(event2)
        assert rows[0]["source_hash"] == new_hash

    def test_seen_event_with_identical_details_no_changed_flag(self, tmp_path):
        """Seen event with identical source_hash does NOT set changed flag."""
        store = CsvEventStore(tmp_path / "events.csv")
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        # First upsert
        store.upsert([event])

        # Second upsert with same event (identical content)
        store.upsert([event])

        csv_file = tmp_path / "events.csv"
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        # changed should remain empty (not "yes")
        assert rows[0]["changed"] == ""

    def test_legacy_row_with_empty_source_hash_gets_backfilled(self, tmp_path):
        """Legacy row with empty source_hash gets backfilled without setting changed."""
        csv_file = tmp_path / "events.csv"
        # Create a legacy CSV file with old format (no source_hash, topics, etc.)
        csv_file.write_text(
            "uid,title,organizer,url,start,end,location,description,source_url,status,first_seen,last_seen\n"
            "url:https://example.com/event1,Event 1,Org A,https://example.com/event1,2026-07-15T10:00:00,,,,,Needs Review,2026-07-01,2026-07-01\n"
        )

        store = CsvEventStore(csv_file)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        # Upsert the same event
        store.upsert([event])

        # Read back the CSV
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        # source_hash should be backfilled with the new hash
        expected_hash = content_hash(event)
        assert rows[0]["source_hash"] == expected_hash
        # But changed should NOT be set
        assert rows[0]["changed"] == ""

    def test_seen_event_clears_possibly_cancelled(self, tmp_path):
        """Seen event clears possibly_cancelled back to empty."""
        csv_file = tmp_path / "events.csv"
        # Create a CSV file with an event marked as possibly_cancelled
        csv_file.write_text(
            "uid,title,organizer,url,start,end,location,description,source_url,topics,possible_duplicate_of,status,changed,possibly_cancelled,source_hash,first_seen,last_seen\n"
            "url:https://example.com/event1,Event 1,Org A,https://example.com/event1,2026-07-15T10:00:00,,,,,,Needs Review,,yes,abcdef123456,2026-07-01,2026-07-01\n"
        )

        store = CsvEventStore(csv_file)
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        # Upsert the event (should be seen)
        store.upsert([event])

        # Read back and verify possibly_cancelled is cleared
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["possibly_cancelled"] == ""

    def test_seen_event_gains_duplicate_link_when_stored_value_empty(self, tmp_path):
        """Seen event with a newly-discovered possible_duplicate_of persists it when stored value is empty."""
        store = CsvEventStore(tmp_path / "events.csv")
        event1 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
        )
        # First upsert: no duplicate known yet
        store.upsert([event1])

        # Second upsert (later run): dedupe found a cross-org twin
        event2 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            possible_duplicate_of="url:https://other.com/eventX",
        )
        store.upsert([event2])

        csv_file = tmp_path / "events.csv"
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["possible_duplicate_of"] == "url:https://other.com/eventX"

    def test_seen_event_preserves_existing_nonempty_duplicate_link(self, tmp_path):
        """A pre-existing, possibly human-reviewed possible_duplicate_of is not overwritten."""
        store = CsvEventStore(tmp_path / "events.csv")
        event1 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            possible_duplicate_of="url:https://other.com/original-match",
        )
        store.upsert([event1])

        # Later run finds a *different* suspected duplicate
        event2 = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            possible_duplicate_of="url:https://other.com/new-match",
        )
        store.upsert([event2])

        csv_file = tmp_path / "events.csv"
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        # Original stored value wins; not replaced by the new run's match.
        assert rows[0]["possible_duplicate_of"] == "url:https://other.com/original-match"

    def test_flag_missing_flags_future_dated_absent_event(self, tmp_path):
        """flag_missing flags events absent from present_uids if they're future-dated and Approved/Needs Review."""
        from datetime import timedelta
        import csv
        csv_file = tmp_path / "events.csv"
        future_date = (date.today() + timedelta(days=1)).isoformat()
        past_date = (date.today() - timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        # Create CSV properly using DictWriter
        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        rows_data = [
            {"uid": "uid1", "title": "Event Future", "organizer": "Org A", "url": "url1",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash1",
             "first_seen": today_str, "last_seen": today_str},
            {"uid": "uid2", "title": "Event Past", "organizer": "Org A", "url": "url2",
             "start": f"{past_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Approved",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash2",
             "first_seen": today_str, "last_seen": today_str},
            {"uid": "uid3", "title": "Event Blank Start", "organizer": "Org A", "url": "url3",
             "start": "", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash3",
             "first_seen": today_str, "last_seen": today_str},
        ]
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_data)

        store = CsvEventStore(csv_file)
        # Only uid3 is present
        result = store.flag_missing("Org A", "https://a.com/events", {"uid3"})

        # Should flag uid1 (future and Needs Review), not uid2 (past), not uid3 (present)
        assert result == 1

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Find uid1 and verify it's flagged
        for row in rows:
            if row["uid"] == "uid1":
                assert row["possibly_cancelled"] == "yes"
            elif row["uid"] == "uid2":
                assert row["possibly_cancelled"] == ""
            elif row["uid"] == "uid3":
                assert row["possibly_cancelled"] == ""

    def test_flag_missing_does_not_flag_rejected_duplicate_status(self, tmp_path):
        """flag_missing does NOT flag events with Rejected or Duplicate status."""
        from datetime import timedelta
        import csv
        csv_file = tmp_path / "events.csv"
        future_date = (date.today() + timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        rows_data = [
            {"uid": "uid1", "title": "Event Rejected", "organizer": "Org A", "url": "url1",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Rejected",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash1",
             "first_seen": today_str, "last_seen": today_str},
            {"uid": "uid2", "title": "Event Duplicate", "organizer": "Org A", "url": "url2",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Duplicate",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash2",
             "first_seen": today_str, "last_seen": today_str},
        ]
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_data)

        store = CsvEventStore(csv_file)
        # Empty present_uids means both would be flagged if not rejected
        result = store.flag_missing("Org A", "https://a.com/events", set())

        # Should flag nothing due to status
        assert result == 0

    def test_flag_missing_does_not_flag_other_organizers(self, tmp_path):
        """flag_missing only flags events matching the given organizer."""
        from datetime import timedelta
        import csv
        csv_file = tmp_path / "events.csv"
        future_date = (date.today() + timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        rows_data = [
            {"uid": "uid1", "title": "Event 1", "organizer": "Org A", "url": "url1",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash1",
             "first_seen": today_str, "last_seen": today_str},
            {"uid": "uid2", "title": "Event 2", "organizer": "Org B", "url": "url2",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash2",
             "first_seen": today_str, "last_seen": today_str},
        ]
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_data)

        store = CsvEventStore(csv_file)
        # Flag missing only for Org A
        result = store.flag_missing("Org A", "https://a.com/events", set())

        # Should flag only uid1
        assert result == 1

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for row in rows:
            if row["uid"] == "uid1":
                assert row["possibly_cancelled"] == "yes"
            elif row["uid"] == "uid2":
                assert row["possibly_cancelled"] == ""

    def test_flag_missing_does_not_flag_other_sources(self, tmp_path):
        """flag_missing only flags events matching the given source_url, even for the same organizer."""
        from datetime import timedelta
        import csv
        csv_file = tmp_path / "events.csv"
        future_date = (date.today() + timedelta(days=1)).isoformat()
        today_str = date.today().isoformat()

        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        rows_data = [
            {"uid": "uid1", "title": "Event Source A", "organizer": "Org A", "url": "url1",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://a.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash1",
             "first_seen": today_str, "last_seen": today_str},
            {"uid": "uid2", "title": "Event Source B", "organizer": "Org A", "url": "url2",
             "start": f"{future_date}T10:00:00", "end": "", "location": "", "description": "",
             "source_url": "https://b.com/events", "topics": "", "possible_duplicate_of": "", "status": "Needs Review",
             "changed": "", "possibly_cancelled": "", "source_hash": "hash2",
             "first_seen": today_str, "last_seen": today_str},
        ]
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_data)

        store = CsvEventStore(csv_file)
        # Flag missing for Org A's source A only; neither uid is present in this fetch
        result = store.flag_missing("Org A", "https://a.com/events", set())

        # Should flag only uid1 (source A), not uid2 (same organizer, different source)
        assert result == 1

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        for row in rows:
            if row["uid"] == "uid1":
                assert row["possibly_cancelled"] == "yes"
            elif row["uid"] == "uid2":
                assert row["possibly_cancelled"] == ""

    def test_human_edited_columns_survive_updates(self, tmp_path):
        """Human-edited columns (title, status, etc.) survive upserts and flag_missing."""
        import csv
        store = CsvEventStore(tmp_path / "events.csv")

        # Create an event
        event = Event(
            title="Event 1",
            organizer="Org A",
            url="https://example.com/event1",
            uid="url:https://example.com/event1",
            start=datetime(2026, 7, 15, 10, 0, 0),
        )
        store.upsert([event])

        csv_file = tmp_path / "events.csv"

        # Manually edit the CSV: change title and status
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        rows[0]["title"] = "Event 1 (Edited by Human)"
        rows[0]["status"] = "Approved"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "uid", "title", "organizer", "url", "start", "end",
                "location", "description", "source_url", "topics",
                "possible_duplicate_of", "status", "changed",
                "possibly_cancelled", "source_hash", "first_seen", "last_seen"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # Upsert the same event again
        store.upsert([event])

        # Verify edits are preserved
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["title"] == "Event 1 (Edited by Human)"
        assert rows[0]["status"] == "Approved"
