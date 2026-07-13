# Offline Operations Stability Implementation Plan

> **Status: completed July 12, 2026.** Retained as a decision record; it is not
> the current implementation batch. Configuration safety, Source Run history,
> health rules, and offline/Airtable store boundaries are implemented.

## Objective

Make unified Item collection safe to run unattended and observable per Source,
without requiring access to a live Airtable base. Implement and test the
Airtable boundary with fakes; live base validation proceeds separately.

## Scope

1. Reject ambiguous collector configuration and define run exit semantics.
2. Model per-Source attempts and derive plain-language health.
3. Persist Source Runs in CSV and through an Airtable store boundary.
4. Wire run recording into collection and cover unattended-run scenarios.

Out of scope: creating or configuring a live Airtable base, Airtable Interface
work, scheduling, retries, caching, source discovery, new adapters, digest
generation, and changes to duplicate heuristics.

## Task 1: Collector configuration and exit semantics

Make `collect` reject configurations where exactly one of
`AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` is set. After processing all active
Sources, return `0` when every attempted Source succeeds and `1` when any
attempt fails. Preserve failure isolation: successful Sources must still be
stored when another Source fails, and summaries must print before returning.

Files:

- `src/abundroid/cli.py`
- `tests/test_item_cli.py`

Acceptance criteria:

- Partial Airtable credentials produce a concise error and exit `1` without
  reading or writing CSV.
- Full success exits `0`; mixed and total failure exit `1`.
- A mixed run persists successful Items and prints every Source result.
- `--dry-run` follows the same exit policy without writing Items.

## Task 2: Source Run model and health rules

Add a `SourceRun` value object containing run ID, Source identity, start and
finish timestamps, result, Item counts, optional HTTP status, and error. Keep
health derivation pure and explicit:

- inactive Source: `Paused`;
- failed attempt: `Needs attention`;
- successful attempt with zero Items: `No recent items`;
- successful attempt with one or more Items: `Working`.

Use a deterministic injectable clock/ID seam in tests. Do not add retry or
staleness policy in this batch.

Files:

- `src/abundroid/models.py`
- a focused Source Run module if needed
- `tests/test_source_runs.py`

Acceptance criteria:

- Every health state has a unit test.
- Timestamps are timezone-aware and finish is not earlier than start.
- Errors are blank on success and retained on failure.
- Item counts cannot silently describe Items from a different Source.

## Task 3: Source Run stores

Add a small store contract that accepts a completed batch once per collection
run. Implement CSV persistence for offline operation and an Airtable
implementation against the documented `Source Runs` fields. Airtable tests
must use fake tables and assert payloads; no credentials or network calls are
allowed. Batch writes where the client supports them.

Files:

- `src/abundroid/stores/source_run_csv_store.py`
- `src/abundroid/stores/source_run_airtable_store.py`
- `tests/test_source_run_csv_store.py`
- `tests/test_source_run_airtable_store.py`
- `docs/airtable-schema.md` only if the implemented contract exposes a real
  mismatch

Acceptance criteria:

- CSV writes one durable row per attempted Source and preserves prior runs.
- Airtable field names and result values match `docs/airtable-schema.md`.
- Source links use the Source record identity supplied by the loader, not a
  name lookup that can collide.
- Store failure is surfaced as a run-level error; it is never reported as a
  successful, observable collection.

## Task 4: Pipeline and CLI integration

Have the Item pipeline produce one completed `SourceRun` for every active
Source attempt, including unknown formats and adapter exceptions. Allocate
batch-level `new` and `seen` counts back to a Source only if the Item store can
report those counts reliably; otherwise leave those per-Source values at zero
rather than inventing them. The CLI selects the matching Source Run store:
CSV beside offline output, Airtable `Source Runs` when fully configured, and a
no-write store for `--dry-run`.

Files:

- `src/abundroid/item_pipeline.py`
- `src/abundroid/cli.py`
- Source loading/model files needed to retain Airtable Source record IDs
- `tests/test_item_pipeline.py`
- `tests/test_item_cli.py`

Acceptance criteria:

- Success, empty success, unknown format, and fetch/parse failure each produce
  exactly one correct Source Run.
- Inactive Sources are not fetched; if `Paused` records are emitted, that
  policy is consistent and tested. Prefer not emitting them unless operator
  visibility requires it.
- Mixed success persists successful Items and records both Source outcomes.
- A Source Run write failure makes the command fail after Item outcomes are
  printed.
- Existing Item idempotency, duplicate preservation, and editorial-field
  preservation tests continue to pass.

## Parallel Live Airtable Track

This is not part of the local agent's implementation batch. While the batch is
being built, prepare a test base using `docs/airtable-schema.md`:

1. Create Organizations, Sources, Items, Topics, and Source Runs tables.
2. Retain the exact documented field names and select values.
3. Create one approved active Organization with a working RSS Source, one
   broken Source, and one paused Source.
4. Create the Review Queue and basic Abundroid Admin Interface.
5. Do not migrate production data yet.

When both tracks finish, run a live acceptance pass: collect twice, confirm
idempotency, inspect all Source Run links and health values, edit an Item as a
reviewer, collect again, and confirm the edit is preserved.

## Execution Order

1. Implement Task 1 with failing CLI tests.
2. Implement the pure model and health rules in Task 2.
3. Implement both stores in Task 3 using only local fakes.
4. Integrate them in Task 4 and add mixed-run tests.
5. Run the complete offline suite and review the diff for scope creep.

Tasks 2 and 3 may be delegated in parallel after the `SourceRun` fields and
store method signature are agreed. Task 4 must wait for both.

## Verification

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .review-tmp\pytest -p no:cacheprovider
git diff --check
git status --short
```

The batch is complete when every acceptance criterion has regression coverage,
the entire offline suite passes, no test needs Airtable credentials or network
access, and the local collector exposes failures reliably. Remove
`.review-tmp` after testing and do not modify the pre-existing `.claude/`
directory.
