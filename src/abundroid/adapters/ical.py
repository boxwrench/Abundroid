"""iCalendar (.ics) adapter for event Items.

Parses concrete VEVENTs into review-queue Items. Recurring (RRULE) events are
skipped in v1; datetimes are normalized to timezone-aware UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar

from abundroid.models import Item, Source


MAX_SUMMARY_LENGTH = 2000


def _to_utc(value) -> datetime | None:
    """Normalize an iCal date/datetime to a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return None


def _text(component, key) -> str:
    value = component.get(key)
    return str(value).strip() if value is not None else ""


def _end(component, start: datetime | None) -> datetime | None:
    dtend = component.get("DTEND")
    if dtend is not None:
        end_value = dtend.dt
        # RFC 5545: an all-day DTEND is exclusive (the day after the event's
        # last day), so the inclusive last day is one day earlier.
        if isinstance(end_value, date) and not isinstance(end_value, datetime):
            end_value = end_value - timedelta(days=1)
        return _to_utc(end_value)
    duration = component.get("DURATION")
    if duration is not None and start is not None:
        return start + duration.dt
    return None


def parse_items(text: str, source: Source) -> list[Item]:
    """Parse concrete calendar events from an .ics document."""
    calendar = Calendar.from_ical(text)
    items: list[Item] = []

    for component in calendar.walk("VEVENT"):
        try:
            if component.get("RRULE"):
                continue
            dtstart = component.get("DTSTART")
            title = _text(component, "SUMMARY")
            if dtstart is None or not title:
                continue
            start = _to_utc(dtstart.dt)
            item = Item(
                title=title,
                publisher=source.organization,
                kind=source.default_kind,
                source_item_id=_text(component, "UID"),
                canonical_url=_text(component, "URL"),
                source_url=source.url,
                published_at=None,
                summary=_text(component, "DESCRIPTION")[:MAX_SUMMARY_LENGTH].rstrip(),
                scheduled_start=start,
                scheduled_end=_end(component, start),
                location=_text(component, "LOCATION"),
            )
        except (ValueError, TypeError, AttributeError):
            continue
        items.append(item)

    return items
