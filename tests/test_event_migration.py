"""Unit tests for the pure event migration converter."""

from __future__ import annotations

from datetime import datetime, timezone
from abundroid.event_migration import (
    migrate_events,
    normalize_row,
    CSV_TO_LEGACY_MAP,
    AIRTABLE_TO_LEGACY_MAP,
    MigrationWarning,
)


def test_normalize_row_csv():
    raw_row = {
        "uid": "legacy-123",
        "title": "My Event",
        "organizer": "My Org",
        "url": "https://example.com/reg",
        "source_url": "https://example.com/source",
        "start": "2026-07-15T10:00:00Z",
        "end": "2026-07-15T12:00:00Z",
        "location": "Room A",
        "description": "Event Description",
        "topics": "Housing; Community",
        "status": "Approved",
        "reviewer_notes": "Great event",
        "first_seen": "2026-07-01T09:00:00Z",
        "last_seen": "2026-07-02T10:00:00Z",
        "changed": "yes",
        "possible_duplicate_of": "legacy-999",
        "extra_field": "ignore me",
    }
    normalized = normalize_row(raw_row, CSV_TO_LEGACY_MAP)

    # Check that extra fields are not present
    assert "extra_field" not in normalized
    # Check all fields survive
    assert normalized["uid"] == "legacy-123"
    assert normalized["title"] == "My Event"
    assert normalized["organizer"] == "My Org"
    assert normalized["url"] == "https://example.com/reg"
    assert normalized["source_url"] == "https://example.com/source"
    assert normalized["start"] == "2026-07-15T10:00:00Z"
    assert normalized["end"] == "2026-07-15T12:00:00Z"
    assert normalized["location"] == "Room A"
    assert normalized["description"] == "Event Description"
    assert normalized["topics"] == "Housing; Community"
    assert normalized["status"] == "Approved"
    assert normalized["reviewer_notes"] == "Great event"
    assert normalized["first_seen"] == "2026-07-01T09:00:00Z"
    assert normalized["last_seen"] == "2026-07-02T10:00:00Z"
    assert normalized["changed"] == "yes"
    assert normalized["possible_duplicate_of"] == "legacy-999"


def test_normalize_row_airtable():
    raw_row = {
        "UID": "legacy-123",
        "Title": "My Event",
        "Organizer": "My Org",
        "Registration URL": "https://example.com/reg",
        "Source URL": "https://example.com/source",
        "Start": "2026-07-15T10:00:00Z",
        "End": "2026-07-15T12:00:00Z",
        "Location": "Room A",
        "Description": "Event Description",
        "Topics": ["Housing", "Community"],
        "Status": "Approved",
        "Reviewer Notes": "Great event",
        "First Seen": "2026-07-01T09:00:00Z",
        "Last Seen": "2026-07-02T10:00:00Z",
        "Changed": True,
        "Possible Duplicate Of": "legacy-999",
        "extra_field": "ignore me",
    }
    normalized = normalize_row(raw_row, AIRTABLE_TO_LEGACY_MAP)

    # Check that extra fields are not present
    assert "extra_field" not in normalized
    # Check mapping
    assert normalized["uid"] == "legacy-123"
    assert normalized["title"] == "My Event"
    assert normalized["organizer"] == "My Org"
    assert normalized["url"] == "https://example.com/reg"
    assert normalized["source_url"] == "https://example.com/source"
    assert normalized["start"] == "2026-07-15T10:00:00Z"
    assert normalized["end"] == "2026-07-15T12:00:00Z"
    assert normalized["location"] == "Room A"
    assert normalized["description"] == "Event Description"
    assert normalized["topics"] == ["Housing", "Community"]
    assert normalized["status"] == "Approved"
    assert normalized["reviewer_notes"] == "Great event"
    assert normalized["first_seen"] == "2026-07-01T09:00:00Z"
    assert normalized["last_seen"] == "2026-07-02T10:00:00Z"
    assert normalized["changed"] is True
    assert normalized["possible_duplicate_of"] == "legacy-999"


def test_migrate_events_basic():
    # Test that a valid normalized legacy event converts perfectly.
    rows = [
        {
            "uid": "legacy-1",
            "title": "Community Meeting",
            "organizer": "City Council",
            "url": "https://example.com/meeting",
            "source_url": "https://example.com/feed",
            "start": "2026-07-15T10:00:00Z",
            "end": "2026-07-15T12:00:00Z",
            "location": "City Hall",
            "description": "Discussing neighborhood plans.",
            "topics": "Housing; Community",
            "status": "Needs Review",
            "reviewer_notes": "First meeting",
            "first_seen": "2026-07-01T09:00:00Z",
            "last_seen": "2026-07-01T09:00:00Z",
            "changed": "no",
        }
    ]

    # Keep a copy of input rows to check they are not mutated
    rows_copy = [dict(r) for r in rows]

    items, warnings = migrate_events(rows)

    # Input dictionaries must not be mutated
    assert rows == rows_copy

    assert len(items) == 1
    item = items[0]
    assert item.title == "Community Meeting"
    assert item.publisher == "City Council"
    assert item.kind == "event"
    assert item.canonical_url == "https://example.com/meeting"
    assert item.source_url == "https://example.com/feed"
    assert item.scheduled_start == datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)
    assert item.scheduled_end == datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    assert item.location == "City Hall"
    assert item.summary == "Discussing neighborhood plans."
    assert item.topics == ["Housing", "Community"]
    assert item.status == "Needs Review"
    assert item.reviewer_notes == "First meeting"
    assert item.first_seen == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    assert item.last_seen == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    assert item.changed is False
    assert item.uid.startswith("url:")  # computed from canonical_url

    # Check there are no warnings
    assert len(warnings) == 0


def test_migrate_events_missing_required():
    rows = [
        # Missing title
        {
            "uid": "legacy-1",
            "title": "",
            "organizer": "City Council",
        },
        # Missing organizer
        {
            "uid": "legacy-2",
            "title": "Community Meeting",
            "organizer": "",
        },
    ]

    items, warnings = migrate_events(rows)
    assert len(items) == 0
    # Filter only missing field warnings
    missing_warnings = [w for w in warnings if w.warning_type == "missing_field"]
    assert len(missing_warnings) == 2
    assert "missing required fields: title" in missing_warnings[0].message
    assert "missing required fields: organizer" in missing_warnings[1].message


def test_migrate_events_invalid_and_blank_dates():
    rows = [
        {
            "uid": "legacy-1",
            "title": "Meeting",
            "organizer": "City Council",
            "start": "not-a-date",
            "end": "",
            "first_seen": None,
            "last_seen": "2026-07-01T09:00:00Z",
        }
    ]

    items, warnings = migrate_events(rows)
    assert len(items) == 1
    item = items[0]
    assert item.scheduled_start is None
    assert item.scheduled_end is None
    assert item.first_seen is None
    assert item.last_seen == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)

    # We expect warnings for invalid start, blank end, and blank first_seen
    warning_types = [w.warning_type for w in warnings]
    assert "invalid_date" in warning_types
    assert "blank_date" in warning_types

    invalid_warn = [w for w in warnings if w.warning_type == "invalid_date"][0]
    assert invalid_warn.message == "Invalid timestamp format: 'not-a-date' for field 'start'."


def test_migrate_events_topics_parsing():
    rows = [
        {
            "uid": "legacy-1",
            "title": "Meeting A",
            "organizer": "Org A",
            "topics": "Housing; Community",
        },
        {
            "uid": "legacy-2",
            "title": "Meeting B",
            "organizer": "Org B",
            "topics": ["Community", "Education", ""],
        },
        {
            "uid": "legacy-3",
            "title": "Meeting C",
            "organizer": "Org C",
            "topics": None,
        },
    ]

    items, warnings = migrate_events(rows)
    assert len(items) == 3
    assert items[0].topics == ["Housing", "Community"]
    assert items[1].topics == ["Community", "Education"]
    assert items[2].topics == []


def test_migrate_events_duplicate_resolution():
    rows = [
        {
            "uid": "legacy-1",
            "title": "First Meeting",
            "organizer": "City Council",
            "url": "https://example.com/meeting1",
            "possible_duplicate_of": "legacy-2",
            "start": "2026-07-15T10:00:00Z",
            "end": "2026-07-15T12:00:00Z",
            "first_seen": "2026-07-01T09:00:00Z",
            "last_seen": "2026-07-01T09:00:00Z",
        },
        {
            "uid": "legacy-2",
            "title": "Second Meeting",
            "organizer": "City Council",
            "url": "https://example.com/meeting2",
            "possible_duplicate_of": "legacy-999",  # Unresolved
            "start": "2026-07-15T10:00:00Z",
            "end": "2026-07-15T12:00:00Z",
            "first_seen": "2026-07-01T09:00:00Z",
            "last_seen": "2026-07-01T09:00:00Z",
        },
    ]

    items, warnings = migrate_events(rows)
    assert len(items) == 2

    item1, item2 = items[0], items[1]
    # item1 possible_duplicate_of should resolve to item2's new UID
    assert item1.possible_duplicate_of == item2.uid
    # item2 possible_duplicate_of should be empty (unresolved)
    assert item2.possible_duplicate_of == ""

    # Filter only unresolved duplicate warnings
    unresolved_warnings = [w for w in warnings if w.warning_type == "unresolved_duplicate"]
    assert len(unresolved_warnings) == 1
    assert "Unresolved duplicate reference: 'legacy-999' not found" in unresolved_warnings[0].message


def test_url_less_recurring_events_get_distinct_item_uids():
    rows = [
        {
            "uid": "legacy-1",
            "title": "Weekly Meeting",
            "organizer": "Community Org",
            "source_url": "https://example.com/calendar",
            "start": "2026-08-01T10:00:00",
        },
        {
            "uid": "legacy-2",
            "title": "Weekly Meeting",
            "organizer": "Community Org",
            "source_url": "https://example.com/calendar",
            "start": "2026-08-08T10:00:00",
        },
    ]

    items, _ = migrate_events(rows)

    assert len(items) == 2
    assert items[0].uid != items[1].uid
