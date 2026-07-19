# iCal Source Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `ical` source adapter that turns concrete `.ics` calendar events into review-queue Items, reusing the existing pipeline. Skip recurring (`RRULE`) events in v1.

**Architecture:** A new `adapters/ical.py` mirrors `adapters/rss.py` (`parse_items(text, source) -> list[Item]`). It parses each concrete `VEVENT` with the `icalendar` library, mapping fields to `Item` and normalizing datetimes to UTC. The pipeline already dispatches on `source.format` via a registry, so integration is one registry entry plus one Format select option.

**Tech Stack:** Python 3.11+, `icalendar` (installed, 7.2.0), `feedparser` (existing), pytest.

## Global Constraints

- Python floor `>=3.11`. Add `icalendar>=5.0` to dependencies (7.2.0 is installed).
- Run commands from repo root with the venv interpreter: `.venv/Scripts/python.exe` (Windows) or `./.venv/bin/python` (Ubuntu/macOS). Commands below use the Windows form.
- Mirror the RSS adapter's conventions (`src/abundroid/adapters/rss.py`): `publisher = source.organization`, `kind = source.default_kind`, `source_url = source.url`, require a non-empty title, truncate summary to 2000 chars.
- Datetimes stored tz-aware **UTC**. Floating (naive) datetimes → UTC. All-day (`date`) → that date at 00:00 UTC.
- `published_at` is left `None` for events (avoids `DTSTAMP` hash churn).
- Skip events that (a) carry an `RRULE`, (b) lack `DTSTART`, or (c) lack a title. A single bad event is skipped, never fatal; a wholly unparseable document raises (pipeline records a failed Source Run).
- Exact Airtable names remain a contract. The Sources `Format` select gains exactly one option: `ical` (keep `rss`).
- Commit after each task.

---

### Task 1: iCal adapter

**Files:**
- Create: `src/abundroid/adapters/ical.py`
- Modify: `pyproject.toml` (add `icalendar` dependency)
- Test: `tests/test_ical_adapter.py`

**Interfaces:**
- Consumes: `abundroid.models.Item`, `abundroid.models.Source`; the `icalendar` library.
- Produces: `parse_items(text: str, source: Source) -> list[Item]`.

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add `icalendar>=5.0` to the `dependencies` list (after `feedparser>=6.0`). Then reinstall:

Run: `.venv/Scripts/python.exe -m pip install -e ".[dev]"`
Expected: completes; `icalendar` already satisfied.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_ical_adapter.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ical_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'abundroid.adapters.ical'`

- [ ] **Step 4: Write the adapter**

```python
# src/abundroid/adapters/ical.py
"""iCalendar (.ics) adapter for event Items.

Parses concrete VEVENTs into review-queue Items. Recurring (RRULE) events are
skipped in v1; datetimes are normalized to timezone-aware UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

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
        return _to_utc(dtend.dt)
    duration = component.get("DURATION")
    if duration is not None and start is not None:
        return start + duration.dt
    return None


def parse_items(text: str, source: Source) -> list[Item]:
    """Parse concrete calendar events from an .ics document."""
    calendar = Calendar.from_ical(text)
    items: list[Item] = []

    for component in calendar.walk("VEVENT"):
        if component.get("RRULE"):
            continue
        try:
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ical_adapter.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/abundroid/adapters/ical.py tests/test_ical_adapter.py
git commit -m "feat: add iCal source adapter for concrete calendar events"
```

---

### Task 2: Register the adapter and add the Format option

**Files:**
- Modify: `src/abundroid/item_pipeline.py` (register `ical`)
- Modify: `src/abundroid/airtable_schema.py` (add `ical` Format choice)
- Test: `tests/test_item_pipeline.py` (dispatch), `tests/test_airtable_schema.py` (option)

**Interfaces:**
- Consumes: `abundroid.adapters.ical.parse_items` from Task 1.
- Produces: `ITEM_ADAPTERS` gains key `'ical'`; Sources `Format` select gains option `ical`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_item_pipeline.py  (add; create the file if absent)
from abundroid.item_pipeline import ITEM_ADAPTERS
from abundroid.adapters import ical


def test_ical_format_is_registered():
    assert ITEM_ADAPTERS["ical"] is ical.parse_items
```

```python
# tests/test_airtable_schema.py  (append)
def test_format_options_include_rss_and_ical():
    choices = {c["name"] for c in _field("Sources", "Format")["options"]["choices"]}
    assert choices == {"rss", "ical"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_item_pipeline.py::test_ical_format_is_registered tests/test_airtable_schema.py::test_format_options_include_rss_and_ical -v`
Expected: FAIL — `KeyError: 'ical'` and the schema assertion fails (`{"rss"} != {"rss", "ical"}`).

- [ ] **Step 3: Register the adapter**

In `src/abundroid/item_pipeline.py`, update the adapter import and registry:

```python
from abundroid.adapters import rss, ical
```

```python
ITEM_ADAPTERS = {'rss': rss.parse_items, 'ical': ical.parse_items}
```

- [ ] **Step 4: Add the Format option**

In `src/abundroid/airtable_schema.py`, in the `Sources` table's `Format` field, add the `ical` choice:

```python
            {"name": "Format", "type": "singleSelect", "options": _select([{"name": "rss"}, {"name": "ical"}])},
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add src/abundroid/item_pipeline.py src/abundroid/airtable_schema.py tests/test_item_pipeline.py tests/test_airtable_schema.py
git commit -m "feat: register ical adapter and add ical Format option"
```

---

### Task 3: Documentation

**Files:**
- Modify: `docs/airtable-schema.md` (Sources `Format` field)
- Modify: `docs/SETUP.md` (Format wording; add an event Source example)
- Modify: `docs/example-feeds.md` (move Legistar/events from "needs an adapter")

**Interfaces:** none (docs only).

- [ ] **Step 1: Update airtable-schema.md**

In the Sources table field list, change the `Format` row so it lists both options and states usage:

Old (single option): `| Format | Single select | Add only \`rss\` |`
New: `| Format | Single select | Add \`rss\` and \`ical\`. Use \`rss\` for RSS and Atom; use \`ical\` for iCalendar (.ics) event calendars |`

- [ ] **Step 2: Update SETUP.md**

Where the guide describes adding a Source `Format`, note that `ical` is available for `.ics` calendar feeds, and that event Sources set `Default Kind = event`. Keep existing `rss` guidance intact.

- [ ] **Step 3: Update example-feeds.md**

In the "Needs an adapter" section, change the framing: the iCal adapter now exists (v1), so Legistar meeting calendars and event `.ics` feeds are usable as `ical` Sources, with the caveat that **recurring (`RRULE`) events are skipped in v1**. Keep the note that Legistar RSS is jurisdiction-dependent and that the Web API remains Tier 2.

- [ ] **Step 4: Verify nothing broke and commit**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: PASS (docs don't affect tests).

```bash
git add docs/airtable-schema.md docs/SETUP.md docs/example-feeds.md
git commit -m "docs: document the ical Format option and event Sources"
```

---

### Task 4: Real-feed verification (Open Item #1)

**Files:**
- Create: `tests/test_ical_live.py` (opt-in, skipped by default)

**Interfaces:** none (opt-in integration test).

- [ ] **Step 1: Write the guarded live test**

```python
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
```

- [ ] **Step 2: Verify it skips by default**

Run: `.venv/Scripts/python.exe -m pytest tests/test_ical_live.py -v`
Expected: SKIPPED (1 skipped).

- [ ] **Step 3: Commit**

```bash
git add tests/test_ical_live.py
git commit -m "test: add opt-in live .ics parsing check"
```

- [ ] **Step 4: Manual verification against a real Legistar feed**

Obtain a real Legistar/event `.ics` URL (e.g., from a city's Legistar calendar "iCalendar" export, or a public org events `.ics`). Run:

`ABUNDROID_LIVE_ICS_URL="<url>" .venv/Scripts/python.exe -m pytest tests/test_ical_live.py -s`

Confirm concrete events parse with sensible titles and UTC start times. **Decision gate:** if the feed's meetings are `RRULE`-based and the parsed count is near zero, recurrence expansion becomes required — stop and revise the spec before shipping. If discrete events parse as expected, the v1 assumption holds.

---

## Self-review checklist (author)

- Spec coverage: adapter (T1), registration + Format option (T2), docs (T3), Open Item #1 verification (T4). Timezone/all-day/duration/RRULE-skip/malformed-skip all covered by T1 tests.
- No placeholders: all code is complete and runnable.
- Type consistency: `parse_items(text, source) -> list[Item]` used identically in T1, T2, T4; `_to_utc`/`_end`/`_text` are internal to the adapter.
