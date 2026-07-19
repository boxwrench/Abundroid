# Abundroid Roadmap

Abundroid monitors what organizations publish and puts new articles, posts,
updates, announcements, reports, and scheduled items into one human review
queue.

> Reliable first. Useful second. Agentic third. Public later.

## Product Principles

- **One item stream.** Publication kinds share identity, topics, review, and
  publishing machinery.
- **Organizations are not sources.** One organization can have several feeds
  without duplicating its organization record.
- **Nontechnical daily operation.** Airtable is the control panel after the
  one-time technical deployment.
- **Human editorial control.** The collector suggests and records; people
  approve, reject, edit, and archive.
- **Reviewer edits are durable.** A source refresh never silently overwrites
  reviewed copy.
- **Archive by default.** Stopping monitoring preserves collected history.

## Current Milestone: Live Airtable Validation

The RSS/Atom Item path is implemented with stable identity, topic suggestions,
cross-run duplicate flags, review-safe CSV/Airtable stores, Source Run history,
failure isolation, and meaningful command exit codes.

The only current milestone is deploying that path in one real Airtable base and
testing it with people who did not build the system.

### Exit Criteria

- Monitor one to three real organizations through RSS or Atom.
- Run collection at least twice without duplicate Items.
- Confirm reviewer edits survive another collection run.
- Confirm one broken Source does not block a working Source.
- Confirm inactive and unlinked Sources are skipped.
- Have a non-developer add, edit, pause, archive, restore, and review through
  the Airtable Interface.
- Record every workaround, unclear label, raw-table visit, and terminal step.

No new ingestion or enrichment feature enters scope unless this validation
cannot finish without it.

## Next: Operations and Automation

Only after live validation:

- Correct problems found in the base schema or operator Interface.
- Schedule collection with secrets stored outside the repository.
- Add bounded retries, connection reuse, or conditional HTTP requests only if
  measured failures or rate limits justify them.
- Add source discovery only if manual feed setup repeatedly blocks operators.

**Exit criterion:** routine operation requires no terminal use and a failed
Source is visible from the Interface.

## Later: Useful Output

- Add another source format only for a named high-priority publisher that RSS
  cannot cover.
- Generate a digest only when it has an owner, audience, cadence, and enough
  approved Items.
- Add optional AI assistance only when review data identifies recurring work
  that deterministic rules cannot handle.
- Add public output only for an approved audience and publishing workflow.

## Feedback: Candidate Directions

Recorded from stakeholder feedback during live validation. These are desired
directions, not committed scope. Each needs its own design pass before work
begins, and none preempts the current validation milestone.

**Prefer tracking curators before building adapters.** For both directions
below, the first move reuses the existing RSS/Atom pipeline to track people who
already curate the material (Tier 1, no new code); a structured-source adapter
(Tier 2) is warranted only for coverage the curators miss. This keeps "reliable
first, useful second" and avoids new ingestion code until a real gap justifies
it. Tier 1 sources also count toward the current validation milestone rather
than expanding it. Confirmed and candidate feeds are collected in
[docs/example-feeds.md](example-feeds.md).

### Event tracking

Operators want to track events, not only publications. The Item model already
carries the fields for it (`Kind = event`, Scheduled Start, Scheduled End,
Location), so events join the single Item stream rather than a separate
pipeline. The earlier calendar pipeline was removed as undeployed; reinstating
it should reuse those scheduled-item fields and the same identity, review, and
archive machinery.

- **Tier 1 — track event publishers (now, no new code).** Organizations that
  already announce or aggregate events through RSS or newsletters enter the
  existing pipeline as Items, populating the scheduled-item fields with whatever
  the feed provides.
- **Tier 2 — structured calendars (shipped).** Modern calendars — organization
  events, Legistar meetings, event platforms — export iCalendar (`.ics`), not
  RSS. The iCal adapter now ships: set a Source's **Format** to `ical` to pull
  reliable start, end, and location data for concrete, dated events, covering
  both organization events and Legistar meeting calendars. **Recurring
  (`RRULE`) events are skipped in v1** — a Source built from a recurring
  series only surfaces occurrences the feed also lists as individual,
  non-recurring entries.

### Local legislation

There is demand to track abundance-relevant legislation and the public meetings
attached to it.

- **Tier 1 — track the curators (now, no new code).** Organizations already
  publish curated legislative updates as posts, newsletters, and roundups;
  adding their feeds as Sources brings this in through the existing pipeline.
  Candidate curators to check for feeds: Sightline Institute, Institute for
  Progress, Employ America, Mercatus, Center for Growth and Opportunity, EIG,
  YIMBY organizations, and the Substack roundups many of them run.
- **Tier 2 — structured legislative data.** Two shapes, one shipped and one
  still future work: (a) **meeting calendars** — shipped. The same iCal
  adapter that serves events covers Legistar meetings now (for example, the
  San Francisco Board of Supervisors calendar is `.ics`-only, no RSS), subject
  to the same v1 caveat that recurring (`RRULE`) meeting series are skipped;
  (b) **bill text and status via API (later, needs an adapter)** — the
  Granicus **Legistar Web API** (municipal) and **OpenStates/Plural** or
  **LegiScan** (all fifty states) remain unbuilt. Evaluate in a design pass
  before committing.

## Scale and Handoff

- Scale to 30-50 organizations and multiple Sources per organization.
- Benchmark duplicate detection at expected Item volume before scaling, and add
  candidate indexing only if measured runtime requires it.
- Measure approval rate, edit rate, Source productivity, and reviewer effort.
- Define backup, retention, archival, and credential-rotation policies.
- Document ownership and hand the deployment to its operating team.

The current contracts and milestone checks are in
[`docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
