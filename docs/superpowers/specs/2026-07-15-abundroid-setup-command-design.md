# Design: `abundroid setup` command

**Date:** 2026-07-15
**Status:** Approved for planning
**Author:** Abundroid deployer walkthrough

## Problem

Deploying Abundroid to Airtable currently requires building the base entirely by
hand: 5 tables, ~50 fields with exact names/types/select options, and seed rows,
following `docs/airtable-schema.md` click by click. This is tedious and
error-prone — a single mis-typed field name or missing select option silently
breaks live collection later. The collector addresses tables and fields by exact
name, so the manual build is a fragile contract.

Airtable's Web API (via `pyairtable>=2.3`, already a dependency) can create bases,
tables, fields, select options, and records programmatically. We can eliminate the
most tedious and failure-prone part of setup with a single command.

## Goal

Add `abundroid setup` that creates the entire Abundroid base — base, all 5 tables,
every field with correct type and select options, and the seed rows — in one
command, then writes the resulting base ID into `.env`.

## Non-goals (remain manual)

These cannot be created through Airtable's public API and stay manual, documented
in the command's closing summary and in the guide:

- **Interface pages** (the 3-page "Abundroid Admin" app). No Interface API exists.
- **Saved views** (the 9 views). View creation is not in the Web API. *(Verify
  during implementation; plan for manual.)*
- **Runtime personal access token.** Airtable has no API to mint a PAT; the user
  creates the minimal `data.records:read` + `data.records:write` token by hand.

## Key decisions

| Decision | Choice |
|---|---|
| Base creation | Create everything from scratch: given a workspace ID + schema token, create a new base and return its ID. |
| Re-run behavior | Fresh base each run. No reconciliation. Partial failures are deleted manually by the user, then re-run. |
| Setup token supply | Read `AIRTABLE_SETUP_TOKEN` + `AIRTABLE_WORKSPACE_ID` from the environment (exported for one shell session), never written to `.env`. Token is revoked after use. |
| Base ID handoff | Auto-write `AIRTABLE_BASE_ID=app…` into `.env` (creating it from `.env.example` if absent). Never writes any token to `.env`. |
| Seed data | On by default: the real **Hypertext** Organization + Source. `--no-seed` flag to skip. Hypertext's real feed URL doubles as a worked example of a valid feed URL (not a placeholder). |
| Architecture | Declarative schema-as-data module + thin builder. |
| New dependencies | None. `pyairtable>=2.3` already provides the metadata API. |

## Token scopes

- **Setup token (`AIRTABLE_SETUP_TOKEN`):** `schema.bases:write` (and read as
  required) at the workspace level. One-time; revoked after a successful build.
- **Runtime token (`AIRTABLE_API_KEY` in `.env`):** unchanged — only
  `data.records:read` + `data.records:write`, scoped to the one base. The setup
  command never touches or creates this token. Two tokens, two lifetimes; a leaked
  runtime token still cannot alter schema.

## Architecture

Declarative schema-as-data separated from the builder, so the schema can be
verified with zero network calls and the builder logic can be tested against a
fake Airtable client.

| File | Type | Purpose |
|---|---|---|
| `src/abundroid/airtable_schema.py` | New | The declarative schema: list of table specs (name, primary field, fields with type + options) and the seed rows. Pure data + light helpers, no I/O. Single source of truth. |
| `src/abundroid/setup_base.py` | New | The builder: given a pyairtable `Api`, workspace ID, and the schema, creates the base + tables + fields, adds the dependent lookup field, seeds rows, and writes `.env`. Returns the new base ID. |
| `src/abundroid/cli.py` | Edit | Add a `setup` subparser wired to `run_setup(args)`. |
| `tests/test_airtable_schema.py` | New | Assert the schema data matches the collector's contract. |
| `tests/test_setup_base.py` | New | Exercise the builder against a mocked `Api`. |

### Schema data shape (illustrative)

The schema module defines each table declaratively, e.g. a table has a name, a
primary field spec, and an ordered list of field specs; each field spec carries
its Airtable type and, where relevant, select options or link/lookup targets. The
Hypertext seed is defined alongside as data. Exact Python structure is an
implementation detail for the plan.

## Data flow (one run)

1. `abundroid setup` → `run_setup(args)`.
2. Read `AIRTABLE_SETUP_TOKEN` and `AIRTABLE_WORKSPACE_ID` from env. If either is
   missing, print actionable guidance (how to create a one-time `schema.bases:write`
   token; where to find the workspace ID in the Airtable URL) and exit 1.
3. Create base `Abundroid` in the workspace, with all 5 tables and all non-lookup
   fields (including link fields) in the batched `create_base` call.
4. Second pass: add the `Organization Name` **lookup** field to Sources (requires
   the Organization link to already exist).
5. Seed rows (unless `--no-seed`): create the Hypertext Organization, then the
   Hypertext Source linked to it. Verify the `Organization Name` lookup populates.
6. Write `AIRTABLE_BASE_ID=app…` into `.env` (create from `.env.example` if
   absent). No token is ever written.
7. Print a summary and the manual next steps: build the 9 views, build the 3
   Interface pages, create the minimal runtime token, then revoke the setup token
   — pointing at the exact `airtable-schema.md` sections.

## Error handling

- **Fresh base each run:** no reconciliation logic. If a step after base creation
  fails, print the partial base's name and ID and instruct the user to delete it
  in Airtable before re-running, so a half-built base is never silently reused.
- **Env/credential problems** fail before any API call, with actionable text.
- **Airtable API errors** (401/403 wrong scope, workspace not found, rate limits)
  are caught and translated to a plain-English cause and fix, not a raw traceback.

## Testing strategy

- **Schema tests (no network):** assert exact table names, primary fields, and
  every field's name/type; assert select options match the collector's contract
  (Source Runs `Result` = Working / No recent items / Needs attention; Items
  `Status` and `Kind` option sets; Sources `Format` = rss; Default Kind set). This
  ties the schema to code like `SourceRun.derive_health()` and guards against
  drift.
- **Builder tests (mocked Api):** a fake pyairtable `Api` records calls; assert
  `create_base` received the correct table/field payload, the lookup pass runs
  after the link field, seed rows link correctly, `.env` is written with the
  returned base ID, and `--no-seed` skips seeding. Assert no token is written to
  `.env`.
- **One guarded live smoke test** (opt-in via an env flag, skipped by default) to
  perform a real end-to-end build during the deployer walkthrough.

## Documentation changes

- `docs/SETUP.md`: present `abundroid setup` as the primary Airtable path. Keep
  the manual build as a clearly labeled fallback/appendix (not deleted).
- `docs/airtable-schema.md`: cross-reference the command; retain the click-through
  as the manual/fallback path and as the human-readable schema reference.

## Open items to confirm during implementation

1. Whether `create_base` accepts link fields referencing sibling tables created in
   the same call, or whether link fields also need a second pass alongside lookups.
2. Final confirmation that saved-view creation is unsupported by the Web API.
3. Exact pyairtable 2.3 method signatures for `create_base` / `create_table` /
   field creation and the field-spec payload format.
