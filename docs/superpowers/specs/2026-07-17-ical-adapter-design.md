# Design: iCal (`.ics`) source adapter

**Date:** 2026-07-17
**Status:** Approved for planning
**Author:** Abundroid feedback follow-up

## Problem

Operators want to track events and public meetings (org event calendars, Granicus
Legistar meeting calendars). These are published as **iCalendar (`.ics`)**, not
RSS — the flagship Legistar portals (e.g., the San Francisco Board of Supervisors
calendar) are `.ics`-only, and RSS event aggregators are effectively extinct. The
current collector only parses RSS/Atom, so it cannot ingest any of this.

The `Item` model and identity logic already anticipate events (`Kind = event`,
`Scheduled Start`, `Scheduled End`, `Location`; `compute_item_uid` keys off
`source_item_id`; `item_content_hash` already fingerprints the scheduled fields),
so the missing piece is a parser.

## Goal

Add an `ical` source adapter that turns concrete calendar events into review-queue
Items, reusing the existing pipeline, stores, dedup, change-detection, and review
machinery. One adapter serves both event tracking and Legistar meetings.

## Non-goals (MVP)

- **Recurring events (`RRULE`).** Events carrying an `RRULE` are skipped in v1
  (see Key decisions). No recurrence expansion.
- **Date-window filtering.** Ingest every concrete event the feed contains; the
  review queue handles relevance.
- **Legistar Web API / structured bill data.** A separate Tier 2 path
  (`OpenStates`/`LegiScan`/Legistar Web API), not this adapter.
- **Author/attendee modeling.** No mapping of `ORGANIZER`/`ATTENDEE` in v1.

## Key decisions

| Decision | Choice (v1) | Why this choice |
|---|---|---|
| Recurring events (`RRULE`) | **Skip** events that carry an `RRULE` | Ingesting only the base occurrence would be misleading; government meeting calendars usually list discrete dated meetings, so few or none should drop (Open Item #1). Bounded expansion deferred to a later version. |
| Parsing | Use the **`icalendar`** library (new dependency) | iCal folding, escaping, and timezone rules are error-prone; hand-rolling would be the least safe option. |
| Timezones | Normalize all datetimes to tz-aware **UTC** | Matches how the collector already stores datetimes. Floating (no-`TZID`) times treated as UTC (documented caveat); all-day (`DATE`) events → date at 00:00 UTC. |
| `published_at` | Left **empty** for events | `DTSTAMP` regenerates on every export and would churn the change-detection hash, flagging every event as changed each run. Identity and sorting use `scheduled_start`. |
| Malformed events | **Skip** the event, continue the run | Matches the collector's existing failure isolation — one bad event never drops the rest of the feed. |
| Format value | **`ical`** | Parallel to the existing `rss` value; one Format select gains one option. |
| Item limit | **None** in v1 | Matches the RSS adapter; `.ics` feeds are already bounded in size. |

Every row above is a settled v1 decision. The only one gated on real-world data
is Recurring events — see Open Item #1.

## Architecture

The adapter is a peer of `adapters/rss.py`; the pipeline already dispatches on
`source.format` through a registry, so integration is a registry entry plus a
schema option.

| File | Type | Purpose |
|---|---|---|
| `src/abundroid/adapters/ical.py` | New | `parse_items(content, source) -> list[Item]`: parse an `.ics` document, map each concrete `VEVENT` to an `Item`, skip `RRULE` and malformed events. |
| `src/abundroid/item_pipeline.py` | Edit | Add `'ical': ical.parse_items` to `ITEM_ADAPTERS`. |
| `src/abundroid/airtable_schema.py` | Edit | Add `ical` to the Sources `Format` single-select choices. |
| `pyproject.toml` | Edit | Add `icalendar` to dependencies. |
| `docs/airtable-schema.md`, `docs/SETUP.md` | Edit | Document `ical` as a Format option; note events use `Default Kind = event`. |
| `docs/example-feeds.md` | Edit | Move Legistar meetings / event calendars from "needs an adapter" to usable, keeping the RRULE caveat. |
| `tests/test_ical_adapter.py` | New | Fixture-driven parser tests. |

### Field mapping (`VEVENT` → `Item`)

| Item field | Source |
|---|---|
| `title` | `SUMMARY` |
| `scheduled_start` | `DTSTART` → tz-aware UTC |
| `scheduled_end` | `DTEND`; else `DTSTART + DURATION` if `DURATION` present; else empty |
| `location` | `LOCATION` |
| `canonical_url` | `URL` (empty if absent) |
| `source_item_id` | `UID` (gives stable identity via `compute_item_uid`) |
| `summary` | `DESCRIPTION` |
| `kind` | `source.default_kind` (operators set `event` on the Source) |
| `publisher` | `source.organization` |
| `source_url` | `source.url` |
| `published_at` | empty |

`fetch.py` is unchanged — an `.ics` URL is a normal HTTP GET.

## Data flow

`collect` → `run_item_pipeline` → for each active `ical` Source: `default_fetch(url)`
→ `.ics` text → `ical.parse_items(content, source)` → concrete-event Items →
existing `compute_item_uid` / `item_content_hash` / dedup / store / Source Run.
No pipeline changes beyond the registry entry.

## Error handling

- A single malformed `VEVENT` (missing `DTSTART`, unparseable datetime) is skipped;
  the rest of the feed still ingests.
- A wholly unparseable document raises so the pipeline records a failed Source Run
  with the error, exactly like a broken RSS feed — one broken Source never blocks
  the others.

## Testing strategy

Fixture-driven, no network:

- **Timed event with `TZID`** → asserts `scheduled_start`/`scheduled_end` are the
  correct UTC instants, `title`, `location`, `canonical_url`, `source_item_id`.
- **All-day (`DATE`) event** → asserts date-at-midnight-UTC start, empty end.
- **Event with `DURATION` and no `DTEND`** → asserts computed end.
- **Malformed event (no `DTSTART`)** → asserts it is skipped and siblings survive.
- **`RRULE` event** → asserts it is skipped (documents the v1 limitation).
- **Identity/change** → a re-parsed unchanged event yields the same `uid`; a
  rescheduled event (changed `DTSTART`) yields a different content hash.

## Open items to confirm during implementation

1. Fetch a real Legistar `.ics` (e.g., SF Board of Supervisors) and confirm its
   meetings are discrete `VEVENT`s rather than `RRULE`-based. If they are
   `RRULE`-based, bounded expansion moves from "later" to "required," and this
   spec must be revised before shipping.
2. Confirm `icalendar`'s returned datetime types (`datetime` vs `date`) and how it
   surfaces `TZID` so the UTC normalization is exact.
3. Confirm the exact select-option addition does not disturb the existing `rss`
   option or the collector's `Format` reads.
