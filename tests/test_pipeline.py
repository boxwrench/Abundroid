"""Tests for the pipeline — strict TDD."""

from datetime import datetime
from pathlib import Path

from abundroid.models import Event, Organization
from abundroid.pipeline import run_pipeline, default_fetch, ADAPTERS


class FakeEventStore:
    """Fake event store for testing."""

    def __init__(self):
        """Initialize."""
        self.upserts = []

    def upsert(self, events):
        """Record upsert call and return fake result."""
        self.upserts.append(events)
        return {"new": len(events), "seen": 0}


def test_adapters_dict_exists():
    """ADAPTERS dict should exist with ical and rss entries."""
    assert "ical" in ADAPTERS
    assert "rss" in ADAPTERS
    assert callable(ADAPTERS["ical"])
    assert callable(ADAPTERS["rss"])


def test_default_fetch_returns_string():
    """default_fetch should return a string."""
    # This is a live test against httpx; we'll test the signature
    # Real implementation will be tested via monkeypatch in cli tests
    assert callable(default_fetch)


def test_run_pipeline_skips_inactive_orgs():
    """Inactive orgs should be skipped with no summary entry."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Active Org",
            events_url="https://example.com/feed",
            source_type="rss",
            active=True
        ),
        Organization(
            name="Inactive Org",
            events_url="https://example.com/feed2",
            source_type="rss",
            active=False
        ),
    ]

    def fake_fetch(url):
        return ""

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    # Only active org should have a summary
    assert len(summaries) == 1
    assert summaries[0]["org"] == "Active Org"


def test_run_pipeline_unknown_source_type():
    """Unknown source_type should produce error summary."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Unknown Org",
            events_url="https://example.com/feed",
            source_type="unknown_type",
            active=True
        ),
    ]

    def fake_fetch(url):
        return ""

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["org"] == "Unknown Org"
    assert summary["ok"] is False
    assert "unknown source type" in summary["error"]
    assert summary["events_found"] == 0
    assert summary["new"] == 0
    assert summary["seen"] == 0


def test_run_pipeline_fetch_error_isolation():
    """If one org's fetch fails, others should still process."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Org A",
            events_url="https://example.com/feed1",
            source_type="rss",
            active=True
        ),
        Organization(
            name="Org B",
            events_url="https://example.com/feed2",
            source_type="rss",
            active=True
        ),
    ]

    def fake_fetch(url):
        if "feed1" in url:
            raise ValueError("Network error")
        return '<?xml version="1.0"?><rss><channel><item><title>Event</title><link>url</link></item></channel></rss>'

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    assert len(summaries) == 2
    assert summaries[0]["org"] == "Org A"
    assert summaries[0]["ok"] is False
    assert "Network error" in summaries[0]["error"]
    assert summaries[1]["org"] == "Org B"
    assert summaries[1]["ok"] is True


def test_run_pipeline_sets_uid_on_events():
    """Events should have uid set before upsert."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Test Org",
            events_url="https://example.com/feed",
            source_type="rss",
            active=True
        ),
    ]

    def fake_fetch(url):
        return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    assert len(store.upserts) == 1
    events = store.upserts[0]
    assert len(events) > 0
    for event in events:
        assert event.uid != ""
        assert event.uid.startswith("url:") or event.uid.startswith("hash:")


def test_run_pipeline_success_summary():
    """Successful pipeline run should produce proper summary."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Test Org",
            events_url="https://example.com/feed",
            source_type="rss",
            active=True
        ),
    ]

    def fake_fetch(url):
        return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item><item><title>Event 2</title><link>https://example.com/event2</link></item></channel></rss>'

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["org"] == "Test Org"
    assert summary["ok"] is True
    assert summary["error"] == ""
    assert summary["events_found"] == 2
    assert summary["new"] == 2
    assert summary["seen"] == 0


def test_run_pipeline_with_ical():
    """Pipeline should work with ical adapter."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Test Org",
            events_url="https://example.com/cal.ics",
            source_type="ical",
            active=True
        ),
    ]

    # Read the sample ical fixture
    fixture_path = Path(__file__).parent / "fixtures" / "sample.ics"
    ical_content = fixture_path.read_text()

    def fake_fetch(url):
        return ical_content

    summaries = run_pipeline(orgs, store, fetch=fake_fetch)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["ok"] is True
    assert summary["events_found"] == 2  # sample.ics has 2 valid events
    assert len(store.upserts[0]) == 2


def test_run_pipeline_uses_provided_adapters():
    """Pipeline should use provided adapters dict."""
    store = FakeEventStore()
    orgs = [
        Organization(
            name="Test Org",
            events_url="https://example.com/feed",
            source_type="custom_type",
            active=True
        ),
    ]

    def fake_parse(text, org):
        return [Event(title="Custom Event", organizer=org.name, url="https://example.com/custom")]

    custom_adapters = {
        "custom_type": fake_parse
    }

    def fake_fetch(url):
        return "fake content"

    summaries = run_pipeline(orgs, store, fetch=fake_fetch, adapters=custom_adapters)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["ok"] is True
    assert summary["events_found"] == 1


class FlagRecordingStore(FakeEventStore):
    """Fake store that also records flag_missing calls."""

    def __init__(self):
        super().__init__()
        self.flag_calls = []

    def flag_missing(self, organizer, present_uids):
        self.flag_calls.append((organizer, set(present_uids)))
        return 2


def test_jsonld_in_adapters():
    """ADAPTERS should include the Phase 2 jsonld adapter."""
    assert "jsonld" in ADAPTERS
    assert callable(ADAPTERS["jsonld"])


def test_run_pipeline_tags_events_with_topics():
    """When topics are provided, events are tagged before upsert."""
    from abundroid.models import Topic

    store = FakeEventStore()
    orgs = [
        Organization(name="Test Org", events_url="https://example.com/feed",
                     source_type="custom", active=True),
    ]

    def fake_parse(text, org):
        return [Event(title="Zoning Reform 101", organizer=org.name,
                      url="https://example.com/e1")]

    topics = [Topic(name="Housing", keywords=["zoning"])]
    run_pipeline(orgs, store, fetch=lambda url: "x",
                 adapters={"custom": fake_parse}, topics=topics)

    assert store.upserts[0][0].topics == ["Housing"]


def test_run_pipeline_flags_cross_org_duplicates():
    """Same-day near-identical titles from two different orgs get cross-flagged."""
    store = FakeEventStore()
    orgs = [
        Organization(name="Org A", events_url="https://a.com/feed",
                     source_type="custom", active=True),
        Organization(name="Org B", events_url="https://b.com/feed",
                     source_type="custom", active=True),
    ]

    def fake_parse(text, org):
        n = "1" if org.name == "Org A" else "2"
        return [Event(title="Housing Summit 2026", organizer=org.name,
                      url=f"https://site{n}.com/event",
                      start=datetime(2026, 9, 1, 18, 0))]

    run_pipeline(orgs, store, fetch=lambda url: "x",
                 adapters={"custom": fake_parse})

    event_a = store.upserts[0][0]
    event_b = store.upserts[1][0]
    assert event_a.possible_duplicate_of == event_b.uid
    assert event_b.possible_duplicate_of == event_a.uid


def test_run_pipeline_flag_missing_for_full_calendar_sources():
    """ical/jsonld orgs trigger flag_missing with the uids found this run."""
    store = FlagRecordingStore()
    orgs = [
        Organization(name="Cal Org", events_url="https://example.com/cal.ics",
                     source_type="ical", active=True),
    ]
    fixture_path = Path(__file__).parent / "fixtures" / "sample.ics"
    ical_content = fixture_path.read_text()

    summaries = run_pipeline(orgs, store, fetch=lambda url: ical_content)

    assert len(store.flag_calls) == 1
    organizer, present_uids = store.flag_calls[0]
    assert organizer == "Cal Org"
    assert present_uids == {e.uid for e in store.upserts[0]}
    assert summaries[0]["possibly_cancelled"] == 2


def test_run_pipeline_no_flag_missing_for_rss():
    """RSS feeds naturally drop old posts — never treat absence as cancellation."""
    store = FlagRecordingStore()
    orgs = [
        Organization(name="Feed Org", events_url="https://example.com/feed",
                     source_type="rss", active=True),
    ]
    rss = '<?xml version="1.0"?><rss><channel><item><title>E</title><link>https://x.com/e</link></item></channel></rss>'

    summaries = run_pipeline(orgs, store, fetch=lambda url: rss)

    assert store.flag_calls == []
    assert summaries[0]["possibly_cancelled"] == 0


def test_run_pipeline_store_without_flag_missing_is_fine():
    """Stores lacking flag_missing (e.g. dry-run) must not crash ical runs."""
    store = FakeEventStore()
    orgs = [
        Organization(name="Cal Org", events_url="https://example.com/cal.ics",
                     source_type="ical", active=True),
    ]
    fixture_path = Path(__file__).parent / "fixtures" / "sample.ics"
    ical_content = fixture_path.read_text()

    summaries = run_pipeline(orgs, store, fetch=lambda url: ical_content)

    assert summaries[0]["ok"] is True
    assert summaries[0]["possibly_cancelled"] == 0
