import pytest
from pathlib import Path
from datetime import datetime

from abundroid.adapters.ical import parse
from abundroid.models import Event, Organization


@pytest.fixture
def sample_ics_text():
    """Load sample iCalendar fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample.ics"
    return fixture_path.read_text()


@pytest.fixture
def sample_org():
    """Create a sample Organization for testing."""
    return Organization(
        name="Test Org",
        events_url="https://example.com/calendar.ics",
        source_type="ical",
        website="https://example.com"
    )


def test_parse_skips_events_without_summary(sample_ics_text, sample_org):
    """Returns exactly 2 events; event without SUMMARY is skipped."""
    events = parse(sample_ics_text, sample_org)
    assert len(events) == 2


def test_parse_extracts_title_url_location_description(sample_ics_text, sample_org):
    """Title, url, location, and description extracted correctly on first event."""
    events = parse(sample_ics_text, sample_org)
    first_event = events[0]
    assert first_event.title == "Timed Event with Details"
    assert first_event.url == "https://example.com/events/timed"
    assert first_event.location == "Conference Center, Room A"
    assert first_event.description == "This is a detailed timed event with location and description."


def test_parse_first_event_start_is_timezone_aware_datetime(sample_ics_text, sample_org):
    """First event start is a timezone-aware datetime with the expected instant."""
    events = parse(sample_ics_text, sample_org)
    first_event = events[0]
    assert first_event.start is not None
    assert isinstance(first_event.start, datetime)
    # Should be timezone-aware (tzinfo not None)
    assert first_event.start.tzinfo is not None
    # Should represent 2026-07-09 18:00:00 in America/New_York
    assert first_event.start.year == 2026
    assert first_event.start.month == 7
    assert first_event.start.day == 9
    assert first_event.start.hour == 18


def test_parse_all_day_event_start_is_naive_midnight_datetime(sample_ics_text, sample_org):
    """All-day event start becomes midnight naive datetime of the right date."""
    events = parse(sample_ics_text, sample_org)
    second_event = events[1]
    assert second_event.start is not None
    assert isinstance(second_event.start, datetime)
    # Should be naive (tzinfo is None)
    assert second_event.start.tzinfo is None
    # Should be midnight
    assert second_event.start.hour == 0
    assert second_event.start.minute == 0
    assert second_event.start.second == 0
    # Should be the correct date
    assert second_event.start.year == 2026
    assert second_event.start.month == 7
    assert second_event.start.day == 10


def test_parse_organizer_and_source_url_set_from_org(sample_ics_text, sample_org):
    """organizer and source_url are set from the passed Organization on all events."""
    events = parse(sample_ics_text, sample_org)
    for event in events:
        assert event.organizer == "Test Org"
        assert event.source_url == "https://example.com/calendar.ics"
