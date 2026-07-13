# Unified Items Implementation Plan

## Current Objective

Deploy and validate the smallest real Airtable RSS workflow. No new adapter,
enrichment subsystem, scheduler, or public output is current work. The milestone
closes only after real reruns, reviewer-edit preservation, failure visibility,
and the nontechnical operator workflow have been exercised in one base.

## Data Model

### Organization

One durable publisher record with `name`, `website`, `category`, `priority`,
`active`, `stage`, and `notes`. Stopping monitoring means archiving the record,
not deleting collected history.

### Source

One monitored endpoint linked to an Organization, with `name`, `url`, `format`,
`default_kind`, `active`, and `notes`. The deployed format selector contains
only `rss`.

### Item

One reviewable publication with:

- Identity: `uid`, `source_item_id`, `canonical_url`, `source_url`
- Editorial fields: `title`, `publisher`, `kind`, `published_at`, `author`,
  `summary`, `topics`, `status`, `reviewer_notes`
- Optional scheduled fields: `scheduled_start`, `scheduled_end`, `location`
- Bookkeeping: `source_hash`, `first_seen`, `last_seen`, `changed`,
  `possible_duplicate_of`

### Source Run

One active Source attempt with timestamps, result, Item counts, optional HTTP
status, and an actionable error.

## Implemented Collection Contract

1. Load active RSS Sources belonging to approved active Organizations.
2. Fetch each Source independently.
3. Parse candidates and compute stable identity and source-content hashes.
4. Suggest Topics and compare candidates with recently persisted Items.
5. Batch-upsert Items without replacing reviewer-owned fields.
6. Write one Source Run per attempted Source.
7. Return a failing command status if any Source fails, after preserving work
   from successful Sources.

Identity priority is source-native ID, canonical URL, then a deterministic
metadata fallback. Possible duplicates are flagged for review and never deleted
automatically.

## Live Deployment Tasks

- [ ] Create the five documented Airtable tables and fields.
- [ ] Create one approved active Organization with one working RSS Source.
- [ ] Run a read-only preview.
- [ ] Run collection twice and verify Item idempotency.
- [ ] Edit reviewer-owned fields and verify they survive a rerun.
- [ ] Exercise a broken, inactive, and unlinked Source.
- [ ] Build and publish the minimum operator Interface.
- [ ] Have a non-developer complete the operator workflow.
- [ ] Record workarounds and revise the product only where validation requires.

## Acceptance Criteria

- A nontechnical operator can add, edit, pause, archive, and restore an
  Organization.
- One Organization can own multiple Sources.
- Re-running an unchanged feed creates zero new Items.
- Source changes do not overwrite human-edited fields.
- Duplicate flags can be applied to Items created in earlier runs.
- One broken Source does not block working Sources and is visible in Airtable.
- Routine review requires no terminal or raw-table access.

## Deferred Until Evidence Exists

- Automatic Source discovery
- Scheduled execution
- Additional source formats
- Network caching and retries
- AI classification or summarization
- Digest or public publishing output
