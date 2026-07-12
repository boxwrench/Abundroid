# Phase 2 Stabilization Implementation Plan

## Objective

Close four correctness gaps in behavior already promised by Phase 2 before
starting Phase 3. Deliver this as one small stabilization batch with regression
tests. Do not introduce new storage layers, protocols, migrations, or product
features.

## Scope

1. Scope cancellation checks by source.
2. Persist duplicate flags for previously seen events.
3. Resolve relative JSON-LD event URLs.
4. Return a failing CLI status when part of a run fails.

Out of scope: changing duplicate matching heuristics, detecting incomplete but
successfully parsed calendars, redesigning UIDs, adding source-health history,
or refactoring the CSV and Airtable stores behind a new abstraction.

## Task 1: Source-scoped cancellation checks

Change `flag_missing` in both event stores to accept `source_url` in addition to
`organizer` and `present_uids`. Only inspect stored events whose organizer and
source URL both match. Update `run_pipeline` to pass `org.events_url`.

Files:

- `src/abundroid/pipeline.py`
- `src/abundroid/stores/csv_store.py`
- `src/abundroid/stores/airtable_store.py`
- `tests/test_pipeline.py`
- `tests/test_csv_store.py`
- `tests/test_airtable_store.py`

Acceptance criteria:

- A missing future event from the same organizer and source is flagged.
- A future event from the same organizer but another source is not flagged.
- Existing status and future-date restrictions remain unchanged.
- RSS sources still never run missing-event detection.

## Task 2: Persist late duplicate flags

When an incoming event already exists and has `possible_duplicate_of`, persist
that value if the stored duplicate field is empty. Do not replace a non-empty
stored value, because it may have been reviewed or edited by a human. Apply the
same rule to CSV and Airtable.

Files:

- `src/abundroid/stores/csv_store.py`
- `src/abundroid/stores/airtable_store.py`
- `tests/test_csv_store.py`
- `tests/test_airtable_store.py`
- `tests/test_pipeline.py`

Acceptance criteria:

- A previously stored event gains a duplicate link when a matching event is
  discovered on a later run.
- A pre-existing non-empty duplicate link is preserved.
- Both new-event behavior and human-edited event fields remain unchanged.

## Task 3: Resolve relative JSON-LD URLs

Use `urllib.parse.urljoin` to resolve a string event URL against
`org.events_url` in the JSON-LD adapter. Empty and non-string URLs should retain
their current empty-string behavior. UID computation itself should not change.

Files:

- `src/abundroid/adapters/jsonld.py`
- `tests/test_jsonld_adapter.py`
- `tests/test_pipeline.py` only if an end-to-end identity assertion adds value

Acceptance criteria:

- `/events/123` from `https://example.com/calendar` becomes
  `https://example.com/events/123`.
- An absolute event URL remains unchanged.
- Relative paths from different source hosts produce different UIDs.

## Task 4: Signal partial run failure to automation

Keep processing and printing every organization exactly as today. After all
summaries are printed, return `1` if any summary has `ok == False`; otherwise
return `0`. Argument-help behavior should remain unchanged.

Files:

- `src/abundroid/cli.py`
- `tests/test_cli.py`

Acceptance criteria:

- A fully successful run returns `0`.
- A mixed success/failure run processes all sources and returns `1`.
- An all-failure run returns `1`.
- Summary and totals output are still emitted before returning.

## Execution Order

1. Add failing regression tests for Task 1 and implement it.
2. Add failing regression tests for Task 2 and implement it.
3. Add failing regression tests for Task 3 and implement it.
4. Update CLI tests and implement Task 4.
5. Run the entire offline suite and inspect the final diff for scope creep.

## Verification

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .review-tmp\pytest -p no:cacheprovider
git diff --check
git status --short
```

The batch is complete when all tests pass, every acceptance criterion has a
regression test, and no files outside the listed implementation/test files and
roadmap documentation changed. Remove the local `.review-tmp` directory after
testing; do not modify the pre-existing untracked `.claude/` directory.

