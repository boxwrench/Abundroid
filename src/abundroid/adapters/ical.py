"""iCalendar adapter for parsing VEVENT components."""

from datetime import datetime, time

from icalendar import Calendar

from abundroid.models import Event, Organization


def parse(text: str, org: Organization) -> list[Event]:
    """
    Parse an iCalendar document and extract events.

    Parses the iCalendar (RFC 5545) text using icalendar library.
    For each VEVENT:
    - Extracts title (SUMMARY), location (LOCATION), description (DESCRIPTION),
      and registration URL (URL property).
    - All-day events (DTSTART as date) are converted to naive datetime at midnight.
    - Timezone-aware datetimes pass through as-is.
    - Events without SUMMARY are skipped.
    - Phase 1 limitation: if RRULE is present, only the base occurrence is included;
      recurrence expansion is not yet implemented.

    Args:
        text: iCalendar data as string.
        org: Organization object providing organizer name and source URL.

    Returns:
        List of Event objects extracted from the calendar, in file order.
    """
    calendar = Calendar.from_ical(text)
    events = []

    for component in calendar.walk():
        if component.name != "VEVENT":
            continue

        # Skip events without SUMMARY
        summary = component.get("SUMMARY")
        if not summary:
            continue

        # Extract fields
        title = str(summary)
        location = str(component.get("LOCATION", "")) or ""
        description = str(component.get("DESCRIPTION", "")) or ""
        url = str(component.get("URL", "")) or ""

        # Extract start datetime
        dtstart = component.get("DTSTART")
        if dtstart:
            # Handle both date and datetime objects
            if isinstance(dtstart.dt, datetime):
                start = dtstart.dt
            else:  # It's a date object; convert to naive datetime at midnight
                start = datetime.combine(dtstart.dt, time.min)
        else:
            start = None

        # Extract end datetime (similar handling)
        dtend = component.get("DTEND")
        if dtend:
            if isinstance(dtend.dt, datetime):
                end = dtend.dt
            else:  # It's a date object
                end = datetime.combine(dtend.dt, time.min)
        else:
            end = None

        # Phase 1 limitation: if RRULE is present, only the base occurrence
        # is included; recurrence expansion is not yet implemented.
        if component.get("RRULE"):
            pass  # Just include the base event without expansion

        event = Event(
            title=title,
            organizer=org.name,
            url=url,
            start=start,
            end=end,
            location=location,
            description=description,
            source_url=org.events_url,
            uid="",
        )
        events.append(event)

    return events
