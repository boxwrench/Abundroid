"""Tests for the CSV store — strict TDD."""

import tempfile
from pathlib import Path
from datetime import date

from abundroid.models import Event, Organization
from abundroid.stores.csv_store import load_organizations, CsvEventStore


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
