from datetime import datetime, timezone

from abundroid.adapters import ical
from abundroid.models import Source


SOURCE = Source(
    organization="City of Example",
    name="Council calendar",
    url="https://example.org/calendar.ics",
    format="ical",
    default_kind="event",
)


def _ics(*vevents: str) -> str:
    body = "\n".join(vevents)
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n"
        f"{body}\r\nEND:VCALENDAR\r\n"
    )


TIMED = (
    "BEGIN:VEVENT\r\nUID:evt-1@example.org\r\nSUMMARY:City Council Meeting\r\n"
    "DTSTART:20260720T190000Z\r\nDTEND:20260720T210000Z\r\n"
    "LOCATION:City Hall\r\nURL:https://example.org/meetings/1\r\n"
    "DESCRIPTION:Regular session\r\nEND:VEVENT"
)


def test_timed_event_maps_all_fields_in_utc():
    items = ical.parse_items(_ics(TIMED), SOURCE)
    assert len(items) == 1
    item = items[0]
    assert item.title == "City Council Meeting"
    assert item.scheduled_start == datetime(2026, 7, 20, 19, 0, tzinfo=timezone.utc)
    assert item.scheduled_end == datetime(2026, 7, 20, 21, 0, tzinfo=timezone.utc)
    assert item.location == "City Hall"
    assert item.canonical_url == "https://example.org/meetings/1"
    assert item.source_item_id == "evt-1@example.org"
    assert item.summary == "Regular session"
    assert item.kind == "event"
    assert item.publisher == "City of Example"
    assert item.source_url == "https://example.org/calendar.ics"
    assert item.published_at is None


def test_all_day_event_is_midnight_utc_with_no_end():
    vevent = (
        "BEGIN:VEVENT\r\nUID:allday@example.org\r\nSUMMARY:Public Comment Day\r\n"
        "DTSTART;VALUE=DATE:20260721\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(vevent), SOURCE)
    assert items[0].scheduled_start == datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
    assert items[0].scheduled_end is None


def test_duration_without_dtend_computes_end():
    vevent = (
        "BEGIN:VEVENT\r\nUID:dur@example.org\r\nSUMMARY:Hearing\r\n"
        "DTSTART:20260722T140000Z\r\nDURATION:PT1H30M\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(vevent), SOURCE)
    assert items[0].scheduled_end == datetime(2026, 7, 22, 15, 30, tzinfo=timezone.utc)


def test_floating_datetime_treated_as_utc():
    vevent = (
        "BEGIN:VEVENT\r\nUID:float@example.org\r\nSUMMARY:Floating\r\n"
        "DTSTART:20260723T090000\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(vevent), SOURCE)
    assert items[0].scheduled_start == datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


def test_tzid_event_converts_to_utc():
    # icalendar resolves an IANA TZID via zoneinfo; no VTIMEZONE block needed.
    vevent = (
        "BEGIN:VEVENT\r\nUID:tz@example.org\r\nSUMMARY:Eastern Meeting\r\n"
        "DTSTART;TZID=America/New_York:20260720T190000\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(vevent), SOURCE)
    # 19:00 EDT (UTC-4 in July) == 23:00 UTC
    assert items[0].scheduled_start == datetime(2026, 7, 20, 23, 0, tzinfo=timezone.utc)


def test_recurring_event_is_skipped():
    vevent = (
        "BEGIN:VEVENT\r\nUID:weekly@example.org\r\nSUMMARY:Weekly Standup\r\n"
        "DTSTART:20260720T090000Z\r\nRRULE:FREQ=WEEKLY;COUNT=10\r\nEND:VEVENT"
    )
    assert ical.parse_items(_ics(vevent), SOURCE) == []


def test_event_without_dtstart_is_skipped_siblings_survive():
    bad = "BEGIN:VEVENT\r\nUID:bad@example.org\r\nSUMMARY:No start\r\nEND:VEVENT"
    items = ical.parse_items(_ics(bad, TIMED), SOURCE)
    assert [i.title for i in items] == ["City Council Meeting"]


def test_event_without_title_is_skipped():
    vevent = (
        "BEGIN:VEVENT\r\nUID:notitle@example.org\r\n"
        "DTSTART:20260720T190000Z\r\nEND:VEVENT"
    )
    assert ical.parse_items(_ics(vevent), SOURCE) == []


def test_all_day_dtend_is_exclusive_last_day():
    # RFC 5545: an all-day DTEND is exclusive (the day after the last day).
    vevent = (
        "BEGIN:VEVENT\r\nUID:multiday@example.org\r\nSUMMARY:Budget Week\r\n"
        "DTSTART;VALUE=DATE:20260721\r\nDTEND;VALUE=DATE:20260724\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(vevent), SOURCE)
    assert items[0].scheduled_start == datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc)
    # DTEND 07-24 is exclusive -> inclusive last day is 07-23
    assert items[0].scheduled_end == datetime(2026, 7, 23, 0, 0, tzinfo=timezone.utc)


def test_event_raising_during_parse_is_skipped_siblings_survive(monkeypatch):
    # Exercises the per-event try/except: if parsing one event raises, it is
    # skipped and the rest of the feed still ingests.
    original = ical._to_utc
    state = {"first": True}

    def flaky(value):
        if state["first"]:
            state["first"] = False
            raise ValueError("boom")
        return original(value)

    monkeypatch.setattr(ical, "_to_utc", flaky)
    bad = (
        "BEGIN:VEVENT\r\nUID:raise@example.org\r\nSUMMARY:Explodes\r\n"
        "DTSTART:20260720T080000Z\r\nEND:VEVENT"
    )
    items = ical.parse_items(_ics(bad, TIMED), SOURCE)
    assert [i.title for i in items] == ["City Council Meeting"]
