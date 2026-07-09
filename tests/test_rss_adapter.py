import pytest
from pathlib import Path

from abundroid.adapters.rss import parse
from abundroid.models import Event, Organization


@pytest.fixture
def sample_rss_text():
    """Load sample RSS fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_rss.xml"
    return fixture_path.read_text()


@pytest.fixture
def sample_org():
    """Create a sample Organization for testing."""
    return Organization(
        name="Test Org",
        events_url="https://example.com/feed.xml",
        source_type="rss",
        website="https://example.com"
    )


def test_parse_skips_entries_without_link(sample_rss_text, sample_org):
    """Returns exactly 2 events; entry without link is skipped."""
    events = parse(sample_rss_text, sample_org)
    assert len(events) == 2


def test_parse_extracts_title_url_description(sample_rss_text, sample_org):
    """Title, url, and description extracted correctly on first event."""
    events = parse(sample_rss_text, sample_org)
    first_event = events[0]
    assert first_event.title == "Community Meetup"
    assert first_event.url == "https://example.com/events/1"
    assert first_event.description == "Join us for a community meetup with food and networking."


def test_parse_missing_description_is_empty_string(sample_rss_text, sample_org):
    """Missing description yields empty string, not None."""
    events = parse(sample_rss_text, sample_org)
    second_event = events[1]
    assert second_event.description == ""
    assert second_event.description is not None


def test_parse_start_is_always_none(sample_rss_text, sample_org):
    """start is None even though the item has a pubDate."""
    events = parse(sample_rss_text, sample_org)
    first_event = events[0]
    assert first_event.start is None


def test_parse_organizer_and_source_url_from_org(sample_rss_text, sample_org):
    """organizer and source_url come from the passed Organization."""
    events = parse(sample_rss_text, sample_org)
    for event in events:
        assert event.organizer == "Test Org"
        assert event.source_url == "https://example.com/feed.xml"
