"""Tests for the uid module — strict TDD."""

from datetime import datetime
from abundroid.models import Event
from abundroid.uid import normalize_url, compute_uid


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_url_with_utm_params_ignored(self):
        """Two URLs differing only by utm_* params should normalize to the same value."""
        url1 = "https://example.com/event?utm_source=email&utm_medium=newsletter"
        url2 = "https://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_fbclid_and_gclid_removed(self):
        """fbclid and gclid params should be removed."""
        url1 = "https://example.com/event?fbclid=abc123&gclid=def456"
        url2 = "https://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_fragment_removed(self):
        """URL fragments should not affect the normalized URL."""
        url1 = "https://example.com/event#section"
        url2 = "https://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_scheme_and_host_lowercased(self):
        """Scheme and host should be lowercased."""
        url1 = "HTTPS://EXAMPLE.COM/Event"
        url2 = "https://example.com/Event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_path_case_preserved(self):
        """Path case should be preserved."""
        url1 = "https://example.com/MyEvent/Details"
        url2 = "https://example.com/myevent/details"
        assert normalize_url(url1) != normalize_url(url2)

    def test_query_param_order_sorted(self):
        """Query parameters should be sorted by name."""
        url1 = "https://example.com/event?z=1&a=2&m=3"
        url2 = "https://example.com/event?a=2&m=3&z=1"
        assert normalize_url(url1) == normalize_url(url2)

    def test_trailing_slash_removed(self):
        """Trailing slash should be removed from paths longer than '/'."""
        url1 = "https://example.com/event/"
        url2 = "https://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_root_path_no_trailing_slash(self):
        """Root path should not have a trailing slash."""
        url1 = "https://example.com/"
        url2 = "https://example.com"
        assert normalize_url(url1) == normalize_url(url2)

    def test_default_http_port_removed(self):
        """Default HTTP port (:80) should be removed."""
        url1 = "http://example.com:80/event"
        url2 = "http://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_default_https_port_removed(self):
        """Default HTTPS port (:443) should be removed."""
        url1 = "https://example.com:443/event"
        url2 = "https://example.com/event"
        assert normalize_url(url1) == normalize_url(url2)

    def test_non_default_port_preserved(self):
        """Non-default ports should be preserved."""
        url1 = "https://example.com:8443/event"
        url2 = "https://example.com/event"
        assert normalize_url(url1) != normalize_url(url2)

    def test_mixed_utm_and_normal_params(self):
        """Normal params should be kept, utm_* removed."""
        url1 = "https://example.com/event?id=123&utm_source=email&name=test"
        url2 = "https://example.com/event?id=123&name=test"
        assert normalize_url(url1) == normalize_url(url2)


class TestComputeUid:
    """Tests for UID computation."""

    def test_uid_with_url_has_url_prefix(self):
        """UID should be prefixed 'url:' when event has a URL."""
        event = Event(
            title="Test Event",
            organizer="Test Org",
            url="https://example.com/event"
        )
        uid = compute_uid(event)
        assert uid.startswith("url:")

    def test_uid_without_url_has_hash_prefix(self):
        """UID should be prefixed 'hash:' when event has no URL."""
        event = Event(
            title="Test Event",
            organizer="Test Org",
            url=""
        )
        uid = compute_uid(event)
        assert uid.startswith("hash:")

    def test_same_url_same_uid(self):
        """Events with the same URL should have the same UID."""
        event1 = Event(
            title="Event A",
            organizer="Org A",
            url="https://example.com/event"
        )
        event2 = Event(
            title="Event B",
            organizer="Org B",
            url="https://example.com/event"
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_different_url_different_uid(self):
        """Events with different URLs should have different UIDs."""
        event1 = Event(
            title="Event A",
            organizer="Org A",
            url="https://example.com/event1"
        )
        event2 = Event(
            title="Event A",
            organizer="Org A",
            url="https://example.com/event2"
        )
        assert compute_uid(event1) != compute_uid(event2)

    def test_url_with_utm_params_same_uid(self):
        """Events whose URLs differ only by utm_* params should have the same UID."""
        event1 = Event(
            title="Event",
            organizer="Org",
            url="https://example.com/event?utm_source=email"
        )
        event2 = Event(
            title="Event",
            organizer="Org",
            url="https://example.com/event"
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_same_org_title_date_same_uid(self):
        """Events without URL with same org, title, and date should have same UID."""
        date = datetime(2024, 6, 15, 10, 0, 0)
        event1 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        event2 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_title_case_insensitive(self):
        """Events without URL with titles differing only in case should have same UID."""
        date = datetime(2024, 6, 15, 10, 0, 0)
        event1 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        event2 = Event(
            title="test event",
            organizer="Test Org",
            url="",
            start=date
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_title_whitespace_normalized(self):
        """Events without URL with titles differing only in internal whitespace should have same UID."""
        date = datetime(2024, 6, 15, 10, 0, 0)
        event1 = Event(
            title="Test  Event",
            organizer="Test Org",
            url="",
            start=date
        )
        event2 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_organizer_case_insensitive(self):
        """Events without URL with organizers differing only in case should have same UID."""
        date = datetime(2024, 6, 15, 10, 0, 0)
        event1 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        event2 = Event(
            title="Test Event",
            organizer="test org",
            url="",
            start=date
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_organizer_whitespace_normalized(self):
        """Events without URL with organizers differing only in internal whitespace should have same UID."""
        date = datetime(2024, 6, 15, 10, 0, 0)
        event1 = Event(
            title="Test Event",
            organizer="Test  Org",
            url="",
            start=date
        )
        event2 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date
        )
        assert compute_uid(event1) == compute_uid(event2)

    def test_no_url_different_dates_different_uids(self):
        """Events without URL with different start dates should have different UIDs."""
        date1 = datetime(2024, 6, 15, 10, 0, 0)
        date2 = datetime(2024, 6, 16, 10, 0, 0)
        event1 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date1
        )
        event2 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=date2
        )
        assert compute_uid(event1) != compute_uid(event2)

    def test_no_url_no_start_date_stable_hash(self):
        """Event without URL and start=None should still produce a stable 'hash:' UID."""
        event1 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=None
        )
        event2 = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=None
        )
        uid1 = compute_uid(event1)
        uid2 = compute_uid(event2)
        assert uid1.startswith("hash:")
        assert uid2.startswith("hash:")
        assert uid1 == uid2

    def test_hash_uid_format(self):
        """Hash UID should contain first 16 hex chars of sha256."""
        event = Event(
            title="Test Event",
            organizer="Test Org",
            url="",
            start=datetime(2024, 6, 15)
        )
        uid = compute_uid(event)
        assert uid.startswith("hash:")
        hash_part = uid[5:]  # Remove "hash:" prefix
        assert len(hash_part) == 16
        # Verify it's valid hex
        try:
            int(hash_part, 16)
        except ValueError:
            assert False, "Hash part is not valid hex"


class TestContentHash:
    """content_hash fingerprints the source-provided details of an event."""

    def test_same_details_same_hash(self):
        from abundroid.uid import content_hash
        a = Event(title="Meetup", organizer="Org", url="https://x.com/e",
                  start=datetime(2026, 8, 1, 18, 0), location="Hall A",
                  description="Talk")
        b = Event(title="Meetup", organizer="Org", url="https://x.com/e",
                  start=datetime(2026, 8, 1, 18, 0), location="Hall A",
                  description="Talk")
        assert content_hash(a) == content_hash(b)

    def test_changed_start_changes_hash(self):
        from abundroid.uid import content_hash
        a = Event(title="Meetup", organizer="Org", url="https://x.com/e",
                  start=datetime(2026, 8, 1, 18, 0))
        b = Event(title="Meetup", organizer="Org", url="https://x.com/e",
                  start=datetime(2026, 8, 1, 19, 0))
        assert content_hash(a) != content_hash(b)

    def test_changed_location_changes_hash(self):
        from abundroid.uid import content_hash
        a = Event(title="Meetup", organizer="Org", location="Hall A")
        b = Event(title="Meetup", organizer="Org", location="Hall B")
        assert content_hash(a) != content_hash(b)

    def test_none_dates_are_stable(self):
        from abundroid.uid import content_hash
        a = Event(title="Meetup", organizer="Org")
        assert content_hash(a) == content_hash(Event(title="Meetup", organizer="Org"))

    def test_hash_is_short_hex(self):
        from abundroid.uid import content_hash
        h = content_hash(Event(title="Meetup", organizer="Org"))
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)
