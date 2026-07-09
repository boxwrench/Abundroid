"""RSS feed adapter for Abundroid event aggregation."""

import feedparser

from abundroid.models import Event, Organization


def parse(text: str, org: Organization) -> list[Event]:
    """
    Parse an RSS feed and extract events.

    Args:
        text: RSS feed content as a string.
        org: Organization metadata to associate with extracted events.

    Returns:
        List of Event objects extracted from the RSS feed.
    """
    feed = feedparser.parse(text)
    events = []

    for entry in feed.entries:
        # Skip entries without title or link
        if not hasattr(entry, 'title') or not entry.title:
            continue
        if not hasattr(entry, 'link') or not entry.link:
            continue

        # Extract event fields from entry
        title = entry.title
        url = entry.link
        description = getattr(entry, 'summary', '') or ''

        # NOTE: start is intentionally always None. An RSS entry's published date
        # (pubDate/published) is the publication date of the post, NOT the event date.
        # Abundroid principle: never fabricate event details. A human reviewer or a
        # later extraction phase must supply the actual event start date.
        event = Event(
            title=title,
            organizer=org.name,
            url=url,
            start=None,
            end=None,
            location='',
            description=description,
            source_url=org.events_url,
            uid=''
        )
        events.append(event)

    return events
