# Unified Items Implementation Plan

This plan converts the calendar-oriented prototype into a publication-monitoring
system without breaking existing Event ingestion during the transition.

## Target Data Model

### Organization

One durable record per organization.

- `name`, `website`, `category`, `priority`, `active`, `stage`, `notes`
- `stage`: `Approved`, `Watchlist`, `Suggested`, or `Archived`
- Removing an organization from monitoring means archiving it, not deleting its
  historical items.

### Source

One record per monitored endpoint, linked to an Organization.

- `organization`, `name`, `url`, `format`, `default_kind`, `active`, `notes`
- `format`: `rss`, `jsonld`, `html`, or `ical`
- `default_kind`: `article`, `post`, `update`, `announcement`, `report`,
  `event`, or `other`
- Health and last-run fields are bookkeeping, not configuration.

### Item

One reviewable occurrence in the monitored ecosystem.

- Identity: `uid`, `source_item_id`, `canonical_url`, `source_url`
- Editorial fields: `title`, `publisher`, `kind`, `published_at`, `author`,
  `summary`, `topics`, `status`, `reviewer_notes`
- Optional event fields: `scheduled_start`, `scheduled_end`, `location`
- Bookkeeping: `source_hash`, `first_seen`, `last_seen`, `changed`,
  `possible_duplicate_of`

The source snapshot/hash and reviewer-edited fields must remain separable so a
source refresh cannot overwrite approved copy.

## Identity and Duplicate Rules

Identity priority:

1. A stable source-native ID namespaced by source, such as an RSS/Atom GUID.
2. A normalized canonical URL with tracking parameters removed.
3. A deterministic hash of publisher, normalized title, publication date, and
   source.

Near-duplicate detection runs against persisted recent items, not only the
current fetch batch. The implemented slice considers normalized title,
canonical URL, and publication proximity. Publisher and summary signals remain
future tuning work. Duplicate matches are flagged for review and never deleted
automatically.

## Ingestion Contract

Adapters return `list[Item]`. Retrieval format and item kind are independent:
an RSS feed may contain articles or announcements, while JSON-LD may contain
articles or scheduled events.

The item pipeline performs:

1. Fetch each active Source with failure isolation.
2. Parse candidates and compute stable identity.
3. Tag topics and compare candidates with persisted recent items.
4. Upsert the complete batch once, avoiding one full table scan per source.
5. Record per-source results for health and operator visibility.

Legacy `run_pipeline`, `Event`, and the Events table remain available until the
Items path reaches parity and a migration tool exists.

## Airtable Administration

Daily operators use an Airtable Interface rather than raw tables where
possible.

- **Organizations:** Add Organization form, Edit, Pause, Archive, Restore.
- **Sources:** related list on each organization; technical `format` may be
  auto-detected or set by an advanced administrator.
- **Review Queue:** all Items with `Status = Needs Review`.
- **Filtered queues:** Articles, Updates, Announcements, Reports, Events.
- **Source Health:** grouped by `Working`, `No recent items`, `Needs attention`,
  and `Paused`.
- **Permanent Delete:** administrator-only, confirmed, and never cascades to
  historical Items by default.

## Delivery Sequence

### Milestone 1 - RSS Items Vertical Slice (implemented)

- Introduce `Source` and `Item` models.
- Parse RSS/Atom GUID, link, author, published timestamp, and bounded summary.
- Add stable Item UID and content hash functions.
- Add CSV Item storage and regression tests.
- Keep existing Event tests passing.

### Milestone 2 - Airtable Items (implementation complete; live validation pending)

- Add Sources and Items schema documentation.
- Load approved Sources linked to Organizations.
- Batch-upsert Items while preserving human edits.
- Add Review Queue and filtered-view setup instructions.

### Milestone 3 - Persistent Deduplication and Health (partially implemented)

- [Done] Query recent stored Items for duplicate candidates.
- [Done] Store duplicate relationships consistently for new and existing records.
- Write Source Run records and update plain-language health.
- Return a failing process status when a scheduled run is systemically broken.

### Milestone 4 - Migration and Admin Interface

- Migrate appropriate legacy Event records into Items with `kind = event`.
  Next implementation batch: [Events-to-Items Migration
  Plan](EVENTS-TO-ITEMS-MIGRATION-PLAN.md).
- Validate and configure the documented Airtable Interface in a live base.
- Add source discovery suggestions from an organization homepage.

### Milestone 5 - Digest and Enrichment

- Generate a reviewable digest from approved Items.
- Add article JSON-LD and grounded HTML extraction.
- Add optional AI only where measured review data justifies it.

## Acceptance Criteria

These are phase-exit criteria, not claims that every item is complete today.
Milestone headings above identify the remaining work.

- A nontechnical operator can add, pause, archive, and restore organizations.
- One organization can own multiple Sources without duplicate organization
  records.
- Re-running an unchanged feed creates zero new Items.
- Feed GUID and canonical URL changes behave predictably and are tested.
- Source changes do not overwrite human-edited fields.
- Duplicate flags can be applied to records created in earlier runs.
- One broken Source does not block other Sources and is visible in Airtable.
- The legacy calendar path remains usable until migration is explicitly run.
