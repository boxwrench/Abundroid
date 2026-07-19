# Handoff: iCal source adapter

**Status: PAUSED — design + plan complete, implementation not started.**
Last updated 2026-07-17.

## Where this stands

- **Branch:** `feature/ical-adapter` (pushed).
- **Spec:** [`docs/superpowers/specs/2026-07-17-ical-adapter-design.md`](specs/2026-07-17-ical-adapter-design.md) — approved.
- **Plan:** [`docs/superpowers/plans/2026-07-17-ical-adapter.md`](plans/2026-07-17-ical-adapter.md) — 4 TDD tasks, complete code.
- **Implementation:** none of the 4 tasks executed yet.

## To resume

Run subagent-driven-development on the plan, starting at Task 1. Tasks:

1. `adapters/ical.py` — parse concrete VEVENTs to Items, UTC-normalize, skip RRULE/malformed (+ `icalendar` dependency, 8 tests).
2. Register `ical` in `ITEM_ADAPTERS` and add `ical` to the Sources `Format` select.
3. Docs — `airtable-schema.md`, `SETUP.md`, `example-feeds.md`.
4. Opt-in live `.ics` verification (the recurring-events decision gate).

## Key decisions (v1)

- **Skip `RRULE` (recurring) events** — ingest only concrete dated events. Assumes government meeting calendars list discrete meetings; **verify against a real Legistar `.ics` (Open Item #1) before shipping** — if meetings are RRULE-based, recurrence expansion becomes required and the spec must be revised.
- Normalize datetimes to tz-aware **UTC**; `published_at` left empty for events.
- One new dependency: `icalendar`.

## Open item at pause

- `pyproject.toml` has an **uncommitted** addition of `icalendar>=5.0` (matches Task 1 Step 1). Task 1 never ran, so this was not committed deliberately. Decide on resume: let Task 1 own it (revert now) or commit it standalone.

## Related context (already shipped to `main`)

- `abundroid setup` command — merged, live-verified.
- `docs/example-feeds.md` — curated feed list (verified + to-verify + needs-adapter).
- `docs/ROADMAP.md` — Tier 1 (track curators via RSS) / Tier 2 (iCal + APIs) framing. This adapter is the Tier 2 iCal build.
