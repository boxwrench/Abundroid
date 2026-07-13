# Abundroid Roadmap

Abundroid monitors what organizations publish: articles, posts, updates,
announcements, reports, and other notable output. Scheduled gatherings may be
collected as one optional item type, but Abundroid is not primarily an event
calendar.

The product is operated through Airtable by nontechnical staff. A normal admin
must be able to add, edit, pause, archive, or restore an organization without
using a terminal or knowing what RSS, JSON-LD, or an adapter is.

> Reliable first. Useful second. Agentic third. Public later.

## Product Principles

- **One item stream.** Articles, updates, announcements, reports, posts, and
  scheduled events share identity, topics, review, and publishing machinery.
- **Organizations are not sources.** One organization can have a blog,
  newsroom, newsletter, podcast feed, and calendar without duplicating its
  organization record.
- **Nontechnical daily operation.** Airtable forms and interfaces are the
  control panel. Initial deployment may require technical setup; ongoing use
  must not.
- **Human editorial control.** The bot suggests and records. Humans approve,
  reject, edit, archive, and publish.
- **Source facts and human edits stay separate.** A source update never
  silently overwrites reviewed copy. Reviewers can see what changed.
- **Archive by default.** Stopping monitoring must preserve historical items.
  Permanent deletion is an explicit administrator action.

## Historical Phases 1-2 - Calendar-Oriented Prototype (complete)

The existing Python pipeline fetches RSS, iCal, and schema.org Event JSON-LD;
tags topics; detects a narrow class of duplicates; and writes review records to
CSV or Airtable. Its 204 tests protect this behavior while the data model is
migrated.

This prototype is useful infrastructure, but `Event`, `Events URL`, required
start dates, same-day deduplication, and cancellation handling reflect the old
calendar interpretation. They are compatibility features, not the target
product model.

A stabilization batch closed four correctness gaps in this pipeline's
already-promised behavior: source-scoped cancellation checks, persisted
duplicate flags on previously-seen events, relative JSON-LD URL resolution,
and a failing CLI exit status on partial run failure, with a regression test
behind each fix. See the [Phase 2 Stabilization
Plan](PHASE2-STABILIZATION-PLAN.md). Worth doing because the legacy Events
path stays live until existing deployments migrate (see Phase 3 exit criteria
below).

Retire the legacy Event path only after every known deployment has exported a
backup, completed migration, verified Item counts and reviewer fields, run at
least three successful unified collection cycles, and confirmed that no job or
operator still invokes `abundroid run`. Delete the compatibility code at that
point rather than preserving it behind new abstractions.

## Phase 3 - Unified Published Items (in progress)

**Implemented:** the RSS/Atom Item model, Source model, stable identity,
topic tagging, cross-run duplicate flags, CSV/Airtable batch stores, Source Run
history and health, the `abundroid collect` command, and legacy Event migration
tooling. **The sole current milestone is live Airtable validation and minimum
operator-interface setup.**

- [Done] Add an `Item` model with `kind`, publisher, canonical URL, source item ID,
  publication date, author, summary, topics, and optional scheduled-event
  fields.
- [Done] Add a `Source` model separate from `Organization`. Sources record retrieval
  format (`rss`, `jsonld`, `html`, `ical`) independently from item kind.
- [Done] Make RSS the first complete content path. Preserve RSS/Atom GUIDs, canonical
  URLs, authors, and publication timestamps rather than forcing posts into an
  event shape.
- [Done] Add an **Items** table and review queue. Use filtered Airtable views for
  articles, updates, announcements, and events rather than separate tables and
  pipelines.
- [Done] Replace URL-only identity with source ID -> canonical URL -> deterministic
  fallback priority.
- [Done] Compare new candidates with persisted recent items. Calendar date must not be
  required for content duplicate detection.
- [Done] Keep the legacy Events path working until existing deployments can migrate.

**Exit criteria:** monitor one to three real organizations through RSS; collect
at least twice without duplicate Items; preserve reviewer edits across a
rerun; exercise a broken and an unlinked Source; and have a non-developer add,
pause, archive, restore, and review through the Airtable Interface. Record all
manual workarounds.

No new ingestion or enrichment feature enters current scope unless it is
required to complete this validation.

## Phase 4 - Administration, Health, and Automation

- Airtable Organizations interface with Add, Edit, Pause, Archive, Restore,
  and administrator-only Permanent Delete actions.
- Source discovery assistant: a user enters an organization website; the bot
  suggests likely feeds and pages for human approval.
- [Done] Plain-language source health backed by per-source run history, pending
  live Airtable validation.
- Scheduled GitHub Actions runs with secrets stored as repository secrets.
- Conditional HTTP requests, caching, connection reuse, and bounded retries.

**Exit criteria:** after one-time deployment, routine operation requires no
terminal use and a failed source is visible from the Airtable interface.

## Phase 5 - Enrichment and Useful Output

- JSON-LD support for `Article`, `BlogPosting`, `NewsArticle`, and related
  types.
- Grounded extraction for plain HTML pages, with cached source snapshots and
  no invented fields.
- Optional AI assistance for ambiguous topic classification, summaries, and
  change explanations. All AI output remains reviewable.
- A minimal digest generated from approved items, with a human reviewing and
  sending it.
- Query views and, only if needed, natural-language questions over approved
  items.

**Exit criteria:** approved items produce a useful recurring digest and source
changes can be reviewed without losing editorial edits.

## Phase 6 - Scale and Handoff

- Scale to 30-50 organizations and multiple sources per organization.
- Measure approval rate, edit rate, source productivity, and reviewer effort.
- Define retention, archival, backup, and credential-rotation policies.
- Document admin ownership and hand the deployment to its operating team.

## Later

- Human-approved source and organization discovery suggestions.
- Public feeds or pages when a concrete audience needs them.
- Organization, author, topic, and co-publication relationship analysis.
- Trend reports, opt-in alerts, and recommendations.
- Multi-ecosystem deployments using separate bases and schedules.

## Feature Gates

- Add another Item source format only when a named high-priority organization
  cannot be covered by RSS.
- Add discovery only when manual Source setup repeatedly blocks operators.
- Add caching or retries only after measured latency, rate limits, bandwidth,
  or transient failures justify them.
- Add AI assistance only when review data shows recurring errors or material
  editing effort that deterministic rules cannot address.
- Add a digest only when it has a named owner, audience, cadence, and enough
  approved Items.
- Add public or multi-ecosystem output only for an approved real deployment or
  concrete audience.

The detailed contracts and migration sequence are in
[`docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
