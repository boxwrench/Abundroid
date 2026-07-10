"""RSS feed adapter for Abundroid event aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser

from abundroid.item_uid import compute_item_uid, item_content_hash
from abundroid.models import Event, Item, Organization, Source


MAX_SUMMARY_LENGTH = 2000


class _SummaryTextParser(HTMLParser):
    '''Collect visible text from the small HTML fragments used in feeds.'''

    _BLOCK_TAGS = {
        'address', 'article', 'aside', 'blockquote', 'br', 'div', 'footer',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'li', 'main', 'nav',
        'ol', 'p', 'pre', 'section', 'table', 'td', 'th', 'tr', 'ul',
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {'script', 'style'}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append(' ')

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {'script', 'style'} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.parts.append(' ')

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _plain_summary(value: str) -> str:
    parser = _SummaryTextParser()
    parser.feed(value)
    parser.close()
    text = ' '.join(''.join(parser.parts).split())
    return text[:MAX_SUMMARY_LENGTH].rstrip()


def _published_at(entry) -> datetime | None:
    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _canonical_url(entry) -> str:
    for link in entry.get('links', []):
        if link.get('rel', '').lower() == 'canonical' and link.get('href'):
            return str(link['href']).strip()
    return str(entry.get('link', '') or '').strip()


def parse_items(text: str, source: Source) -> list[Item]:
    '''Parse reviewable RSS or Atom entries from a configured source.'''
    feed = feedparser.parse(text)
    items: list[Item] = []

    for entry in feed.entries:
        title = str(entry.get('title', '') or '').strip()
        if not title:
            continue

        summary_html = str(
            entry.get('summary', '') or entry.get('description', '') or ''
        )
        item = Item(
            title=title,
            publisher=source.organization,
            kind=source.default_kind,
            source_item_id=str(entry.get('id', '') or entry.get('guid', '') or '').strip(),
            canonical_url=_canonical_url(entry),
            source_url=source.url,
            published_at=_published_at(entry),
            author=str(entry.get('author', '') or '').strip(),
            summary=_plain_summary(summary_html),
        )
        item.uid = compute_item_uid(item)
        item.source_hash = item_content_hash(item)
        items.append(item)

    return items


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
