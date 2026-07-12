# Events-to-Items Migration Implementation Plan

## Objective

Provide a safe, repeatable way to copy legacy Event records into unified Items
with `kind = event`. This is the next Phase 3 exit requirement that can be
implemented and tested offline. Deliver conversion, CSV migration, Airtable
migration, CLI integration, and operator documentation as one bounded batch.

## Safety Contract

- Preview is the default. No records are written unless `--apply` is supplied.
- Migration copies records; it never deletes or modifies legacy Events.
- Reviewer-owned values are preserved when creating Items.
- Existing Items are not overwritten. The current Item-store upsert contract
  controls idempotency and preserves reviewer edits.
- Invalid rows are reported and skipped without stopping valid rows.
- Do not add a migration framework, schema-version system, or generalized ETL
  abstraction. This tool has one source model and one target model.

## Field Mapping

Map legacy fields as follows:

| Legacy Event | Unified Item |
|---|---|
| `Title` / `title` | `title` |
| `Organizer` / `organizer` | `publisher` |
| constant | `kind = event` |
| `Registration URL` / `url` | `canonical_url` |
| `Source URL` / `source_url` | `source_url` |
| `Start` / `start` | `scheduled_start` |
| `End` / `end` | `scheduled_end` |
| `Location` / `location` | `location` |
| `Description` / `description` | `summary` |
| `Topics` / `topics` | `topics` |
| `Status` / `status` | `status` |
| `Reviewer Notes` / `reviewer_notes` | `reviewer_notes` |
| `First Seen` / `first_seen` | `first_seen` |
| `Last Seen` / `last_seen` | `last_seen` |
| `Changed` / `changed` | `changed` |

Compute `uid` with `compute_item_uid` and `source_hash` with
`item_content_hash`. Do not reuse the legacy Event UID because it follows a
different identity contract. Parse ISO timestamps including a trailing `Z`;
blank or invalid optional timestamps become `None` and produce a warning.

Duplicate links require a two-pass conversion: first build the legacy Event UID
to new Item UID map, then translate `Possible Duplicate Of` where the referenced
Event is in the migration set. Leave unresolved references blank and warn.

## Task 1: Pure conversion and reporting

Add a migration module that accepts normalized legacy row dictionaries and
returns converted Items plus structured warnings. Keep CSV/Airtable field-name
translation at the input boundary so conversion rules are shared.

Suggested file: `src/abundroid/event_migration.py`.

Acceptance criteria:

- All mapped editorial and bookkeeping fields survive conversion.
- Missing title or publisher causes the row to be skipped with a warning.
- Invalid optional dates warn but do not discard an otherwise valid row.
- Topics accept Airtable lists and legacy CSV semicolon-separated strings.
- Legacy duplicate references translate to new Item UIDs in a second pass.
- Input dictionaries are not mutated.

## Task 2: CSV preview and apply

Add a migration CLI subcommand for local files:

```text
abundroid migrate-events --events input/events.csv --items output/items.csv
abundroid migrate-events --events input/events.csv --items output/items.csv --apply
```

Without `--apply`, print counts and warnings without creating or changing the
Items file. With `--apply`, pass converted Items to `CsvItemStore.upsert` once.

Acceptance criteria:

- Preview performs no filesystem write.
- Apply reports converted, skipped, new, and seen counts.
- Running apply twice creates no duplicate Items.
- Existing Item editorial fields remain unchanged on rerun.
- A missing or unreadable input returns a nonzero exit status with a concise
  error rather than a traceback.

## Task 3: Airtable preview and apply

When `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` are set, use the legacy Events
table as input and Items table as output. Respect `AIRTABLE_EVENTS_TABLE` and
`AIRTABLE_ITEMS_TABLE`. Fetch Events once and batch-upsert converted Items once.
Preview may read Airtable but must not create or update records.

Acceptance criteria:

- Airtable field names map according to the table above.
- Preview makes zero create/update calls.
- Apply uses the existing `AirtableItemStore` and is idempotent.
- Partial invalid data is reported while valid records migrate.
- Airtable API/setup failures return nonzero and do not fall back silently to
  CSV mode when credentials were supplied.

## Task 4: Documentation and regression coverage

Document the migration command in `docs/SETUP.md` and update
`docs/IMPLEMENTATION_PLAN.md` only after the implemented behavior is verified.
Add focused tests rather than duplicating every store test.

Expected files:

- `src/abundroid/event_migration.py`
- `src/abundroid/cli.py`
- `tests/test_event_migration.py`
- `tests/test_migration_cli.py`
- `docs/SETUP.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/ROADMAP.md`

## Execution Order

1. Implement the pure converter with table-driven unit tests.
2. Implement CSV preview/apply and idempotency tests.
3. Implement Airtable preview/apply using fake tables.
4. Add operator documentation and update milestone status.
5. Run the full suite and review the branch against this scope.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .review-tmp\pytest -p no:cacheprovider
git diff --check
git status --short
```

The batch is complete when each acceptance criterion has regression coverage,
the complete offline suite passes, preview paths demonstrably perform no writes,
and the legacy `run` plus unified `collect` commands remain unchanged.
