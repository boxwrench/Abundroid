# tests/test_ical_live.py
import os
import pytest

from abundroid.adapters import ical
from abundroid.models import Source

LIVE_URL = os.environ.get("ABUNDROID_LIVE_ICS_URL", "")


@pytest.mark.skipif(not LIVE_URL, reason="set ABUNDROID_LIVE_ICS_URL to a real .ics feed to run")
def test_live_ics_parses_events():
    import httpx

    text = httpx.get(LIVE_URL, timeout=30, follow_redirects=True).text
    source = Source(
        organization="Live", name="Live calendar", url=LIVE_URL,
        format="ical", default_kind="event",
    )
    items = ical.parse_items(text, source)
    print(f"\nParsed {len(items)} concrete events from {LIVE_URL}")
    for item in items[:5]:
        print(f"  {item.scheduled_start}  {item.title}")
    assert isinstance(items, list)
