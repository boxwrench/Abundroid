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

## Scale and Handoff

- Scale to 30-50 organizations and multiple Sources per organization.
- Benchmark duplicate detection at expected Item volume before scaling, and add
  candidate indexing only if measured runtime requires it.
- Measure approval rate, edit rate, Source productivity, and reviewer effort.
- Define backup, retention, archival, and credential-rotation policies.
- Document ownership and hand the deployment to its operating team.

The current contracts and milestone checks are in
[`docs/IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
