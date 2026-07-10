"""Tests for JSON-LD adapter."""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from abundroid.adapters.jsonld import parse
from abundroid.models import Event, Organization


@pytest.fixture
def sample_jsonld_text():
    """Load sample JSON-LD fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_jsonld.html"
    return fixture_path.read_text()


@pytest.fixture
def sample_org():
    """Create a sample Organization for testing."""
    return Organization(
        name="Test Event Org",
        events_url="https://example.com/events",
        source_type="jsonld",
        website="https://example.com"
    )


def test_parse_total_event_count(sample_jsonld_text, sample_org):
    """Fixture contains exactly 4 valid events (skips malformed, org, and nameless blocks)."""
    events = parse(sample_jsonld_text, sample_org)
    assert len(events) == 4


def test_parse_extracts_graph_events(sample_jsonld_text, sample_org):
    """First two events come from the @graph block."""
    events = parse(sample_jsonld_text, sample_org)
    # Tech Conference 2026 should be first
    assert events[0].title == "Tech Conference 2026"
    # Virtual Networking Mixer should be second
    assert events[1].title == "Virtual Networking Mixer"


def test_parse_extracts_single_event_dict(sample_jsonld_text, sample_org):
    """Third event is a single plain Event dict from block 2."""
    events = parse(sample_jsonld_text, sample_org)
    assert events[2].title == "Local Workshop"


def test_parse_timezone_aware_iso_dates_preserved(sample_jsonld_text, sample_org):
    """Timezone offset is preserved exactly as given (-07:00)."""
    events = parse(sample_jsonld_text, sample_org)
    tech_conf = events[0]
    assert tech_conf.start is not None
    # Check that the offset is -07:00 (Pacific Daylight Time)
    offset = tech_conf.start.utcoffset()
    assert offset == timedelta(hours=-7)
    # Check that isoformat contains the offset
    assert "-07:00" in tech_conf.start.isoformat()


def test_parse_place_address_location_joining(sample_jsonld_text, sample_org):
    """Place location with missing name uses address components joined with ', '."""
    events = parse(sample_jsonld_text, sample_org)
    tech_conf = events[0]
    assert tech_conf.location == "123 Main St, San Francisco, CA"


def test_parse_virtual_location_string(sample_jsonld_text, sample_org):
    """VirtualLocation dict is resolved to 'Virtual' string."""
    events = parse(sample_jsonld_text, sample_org)
    virtual_event = events[1]
    assert virtual_event.location == "Virtual"


def test_parse_string_location_passthrough(sample_jsonld_text, sample_org):
    """String location values pass through unchanged (after strip)."""
    events = parse(sample_jsonld_text, sample_org)
    workshop = events[2]
    assert workshop.location == "Downtown Community Center, Room 101"


def test_parse_list_type_recognized(sample_jsonld_text, sample_org):
    """@type as list with 'Event' element is recognized as event."""
    events = parse(sample_jsonld_text, sample_org)
    # Virtual Networking Mixer has @type: ["Event", "SocialEvent"]
    virtual_event = events[1]
    assert virtual_event.title == "Virtual Networking Mixer"
    assert virtual_event.url == "https://zoom.example.com/meeting"


def test_parse_organization_block_ignored(sample_jsonld_text, sample_org):
    """Organization blocks (@type: Organization) are ignored, not counted as events."""
    events = parse(sample_jsonld_text, sample_org)
    # Should have 4 events, not 5 (excluding the Organization block)
    assert len(events) == 4
    # No event should have name from the Organization
    org_names = [e.title for e in events]
    assert "Example Tech Company" not in org_names


def test_parse_malformed_json_skipped(sample_jsonld_text, sample_org):
    """Malformed JSON blocks are silently skipped without raising an error."""
    events = parse(sample_jsonld_text, sample_org)
    # Should not raise an error and should continue processing
    # The malformed block should not appear in results
    malformed_names = [e.title for e in events]
    assert "Broken Event" not in malformed_names


def test_parse_nameless_event_skipped(sample_jsonld_text, sample_org):
    """Event nodes without 'name' or with empty 'name' are skipped entirely."""
    events = parse(sample_jsonld_text, sample_org)
    # The event without a name should be skipped
    names = [e.title for e in events]
    # Should not have any events with empty title
    assert all(name.strip() for name in names)
    # Verify we don't have a generic "no name" event
    assert len(events) == 4


def test_parse_missing_startdate_yields_none(sample_jsonld_text, sample_org):
    """Event with 'name' but missing 'startDate' yields start=None."""
    events = parse(sample_jsonld_text, sample_org)
    date_tbd = events[3]
    assert date_tbd.title == "Date TBD Event"
    assert date_tbd.start is None


def test_parse_organizer_from_org(sample_jsonld_text, sample_org):
    """All events have organizer set to the passed Organization's name."""
    events = parse(sample_jsonld_text, sample_org)
    for event in events:
        assert event.organizer == "Test Event Org"


def test_parse_source_url_from_org(sample_jsonld_text, sample_org):
    """All events have source_url set to the passed Organization's events_url."""
    events = parse(sample_jsonld_text, sample_org)
    for event in events:
        assert event.source_url == "https://example.com/events"


def test_parse_url_extraction(sample_jsonld_text, sample_org):
    """URL fields are extracted when present as strings."""
    events = parse(sample_jsonld_text, sample_org)
    tech_conf = events[0]
    assert tech_conf.url == "https://example.com/techconf"
    virtual_event = events[1]
    assert virtual_event.url == "https://zoom.example.com/meeting"


def test_parse_description_extraction(sample_jsonld_text, sample_org):
    """Description fields are extracted and stripped."""
    events = parse(sample_jsonld_text, sample_org)
    tech_conf = events[0]
    assert tech_conf.description == "Annual technology conference with multiple tracks"
    workshop = events[2]
    assert workshop.description == "Learn web development basics"


def test_parse_end_date_extraction(sample_jsonld_text, sample_org):
    """End date is extracted and timezone info preserved."""
    events = parse(sample_jsonld_text, sample_org)
    tech_conf = events[0]
    assert tech_conf.end is not None
    assert "-07:00" in tech_conf.end.isoformat()


def test_parse_empty_html_returns_empty_list():
    """HTML with no JSON-LD blocks returns empty list."""
    empty_html = "<html><body><h1>No events</h1></body></html>"
    org = Organization(
        name="Empty Org",
        events_url="https://example.com/empty",
        source_type="jsonld"
    )
    events = parse(empty_html, org)
    assert events == []


def test_parse_no_event_nodes_returns_empty_list():
    """JSON-LD blocks with no event nodes return empty list."""
    no_events_html = """
    <html>
    <head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Organization", "name": "Test Org"}
        </script>
    </head>
    </html>
    """
    org = Organization(
        name="Org Without Events",
        events_url="https://example.com/noevent",
        source_type="jsonld"
    )
    events = parse(no_events_html, org)
    assert events == []


def test_parse_case_insensitive_script_type():
    """Script type attribute match is case-insensitive."""
    mixed_case_html = """
    <html>
    <head>
        <script type="Application/LD+JSON">
        {"@context": "https://schema.org", "@type": "Event", "name": "Case Test", "startDate": "2026-07-25T10:00:00"}
        </script>
    </head>
    </html>
    """
    org = Organization(
        name="Test",
        events_url="https://example.com",
        source_type="jsonld"
    )
    events = parse(mixed_case_html, org)
    assert len(events) == 1
    assert events[0].title == "Case Test"


def test_parse_defaults_for_optional_fields(sample_jsonld_text, sample_org):
    """Optional fields are left at defaults when not present."""
    events = parse(sample_jsonld_text, sample_org)
    for event in events:
        # Check that optional fields have correct defaults
        assert event.uid == ""
        assert event.topics == []
        assert event.possible_duplicate_of == ""


class TestItemListTraversal:
    """Listing pages (Eventbrite, Luma) wrap events in schema.org ItemList."""

    HTML = """<html><head><script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "ItemList",
     "numberOfItems": 2,
     "itemListElement": [
       {"@type": "ListItem", "position": 1,
        "item": {"@type": "Event", "name": "Wrapped Event One",
                 "startDate": "2026-10-01T18:00:00-07:00",
                 "url": "https://example.com/e1"}},
       {"@type": "Event", "name": "Direct Event Two",
        "startDate": "2026-10-02T18:00:00-07:00",
        "url": "https://example.com/e2"}
     ]}
    </script></head><body></body></html>"""

    def _org(self):
        from abundroid.models import Organization
        return Organization(name="List Org", events_url="https://example.com/events",
                            source_type="jsonld")

    def test_events_inside_itemlist_are_found(self):
        from abundroid.adapters.jsonld import parse
        events = parse(self.HTML, self._org())
        titles = {e.title for e in events}
        assert titles == {"Wrapped Event One", "Direct Event Two"}

    def test_itemlist_inside_graph_is_found(self):
        from abundroid.adapters.jsonld import parse
        html = self.HTML.replace(
            '{"@context": "https://schema.org", "@type": "ItemList"',
            '{"@context": "https://schema.org", "@graph": [{"@type": "ItemList"'
        ).replace(']}\n    </script>', ']}]}\n    </script>')
        events = parse(html, self._org())
        assert {e.title for e in events} == {"Wrapped Event One", "Direct Event Two"}
