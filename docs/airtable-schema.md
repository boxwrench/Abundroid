# Airtable Base Schema

This is the target Airtable layout for Abundroid's unified publication
monitoring workflow. A technical deployer creates the fields, views,
permissions, and Interface once. Daily operators then use the Interface
without a terminal or knowledge of source formats.

The new **Sources** and **Items** tables do not replace the legacy **Events**
table in place. Existing deployments keep **Events** and **Run Log** while the
two ingestion paths coexist.

## Organizations

**Primary field:** `Name` (single line text)

Create one durable record per organization, regardless of how many blogs,
newsrooms, feeds, or calendars it owns.

| Field | Type | Owner and purpose |
|---|---|---|
| Name | Single line text (primary) | Human; required organization name |
| Website | URL | Human; public homepage, not a feed URL |
| Category | Multiple select | Human; ecosystem categories for filtering |
| Priority | Single select | Human; `High`, `Medium`, or `Low` |
| Active | Checkbox | Human; unchecked pauses organization-wide collection |
| Stage | Single select | Human; `Approved`, `Watchlist`, `Suggested`, or `Archived` |
| Notes | Long text | Human; internal context |
| Sources | Link to Sources | Airtable reciprocal link; one organization can have many |
| Events URL | URL | Legacy only; retained for `abundroid run` |
| Source Type | Single select | Legacy only; `ical`, `rss`, `jsonld`, or `html` |
| Last Checked | Date + time | Legacy bot bookkeeping |
| Last Successful Pull | Date + time | Legacy bot bookkeeping |
| Health | Single select | Reserved legacy field; current commands do not update it |

The unified collector processes Sources whose linked Organization is approved
and active. An organization without an active Source produces no Items.
Pausing the Organization skips all its Sources without changing their
individual Active values.

Archiving is the normal removal operation. Set `Stage = Archived`, clear
`Active`, and retain the record and all history.

## Sources

**Primary field:** `Name` (single line text)

A Source is a specific endpoint Abundroid fetches. Retrieval format and
publication kind are separate: an RSS feed may contain articles, updates, or
announcements.

| Field | Type | Owner and purpose |
|---|---|---|
| Name | Single line text (primary) | Human; friendly label such as `Newsroom feed` |
| Organization | Link to Organizations | Human; required, exactly one organization |
| Organization Name | Lookup from Organization -> Name | Airtable; collector uses the linked organization's name |
| URL | URL | Human/advanced admin; required endpoint |
| Format | Single select | Advanced admin; deploy with only the `rss` option |
| Default Kind | Single select | Human; `article`, `post`, `update`, `announcement`, `report`, `event`, or `other` |
| Active | Checkbox | Human; unchecked skips only this Source |
| Notes | Long text | Human; internal context or troubleshooting notes |

The unified Items collector currently supports only `rss`. Keep `jsonld`,
`html`, and `ical` out of the normal Source selector until a concrete source
requires another format and its Item adapter is implemented. The generic
string field in the code preserves that future option without exposing
non-working choices to operators.

For local CSV mode, the equivalent columns are:

```text
organization,name,url,format,default_kind,active,notes
```

## Items

**Primary field:** `Item UID` (single line text)

Items is the unified editorial queue. Scheduled events are Items with
`Kind = event` and optional scheduled fields; they are not the root product
model.

| Field | Type | Owner and purpose |
|---|---|---|
| Item UID | Single line text (primary) | Bot; stable identifier, never edit |
| Source Item ID | Single line text | Bot; source-native ID such as RSS/Atom GUID |
| Canonical URL | URL | Bot at creation; preferred public link |
| Source URL | URL | Bot at creation; endpoint or entry link used for verification |
| Title | Single line text | Bot suggests at creation; human may edit |
| Publisher | Single line text | Bot snapshots organization name so history survives unlinking |
| Kind | Single select | Bot defaults; human may correct: `article`, `post`, `update`, `announcement`, `report`, `event`, or `other` |
| Published At | Date + time | Bot at creation; human may correct |
| Author | Single line text | Bot at creation; human may correct |
| Summary | Long text | Bot at creation; human may edit |
| Topics | Multiple select | Bot suggests at creation; human owns review |
| Status | Single select | Human; `Needs Review`, `Approved`, `Rejected`, `Duplicate`, `Published`, or `Archived` |
| Reviewer Notes | Long text | Human-only internal notes |
| Scheduled Start | Date + time | Optional for `event` Items |
| Scheduled End | Date + time | Optional for `event` Items |
| Location | Single line text | Optional for `event` Items |
| Source Hash | Single line text | Bot; fingerprint of source-provided facts, never edit |
| First Seen | Date | Bot; first ingestion date |
| Last Seen | Date | Bot; most recent ingestion date |
| Changed | Checkbox | Bot; source facts changed after initial ingestion |
| Possible Duplicate Of | Single line text | Bot; suspected Item UID for human review |

At creation, the bot fills the source-derived fields and sets
`Status = Needs Review`. On later runs it updates bookkeeping fields but does
not silently replace human-edited title, kind, author, summary, topics, status,
or notes. `Publisher` and source facts remain on the Item even if an
administrator later unlinks or permanently deletes configuration.

Identity priority is source-native ID, then normalized canonical URL, then a
deterministic fallback. Possible duplicates are flagged, never auto-deleted.

## Topics

**Primary field:** `Topic` (single line text)

| Field | Type | Owner and purpose |
|---|---|---|
| Topic | Single line text (primary) | Human; required topic name |
| Keywords | Long text | Human; comma-separated case-insensitive whole-word matches |
| Aliases | Long text | Human; comma-separated alternate terms |
| Exclusions | Long text | Human; comma-separated disqualifying terms |
| Priority | Single select | Human; `High`, `Medium`, or `Low` |
| Active | Checkbox | Human; inactive topics are not suggested |
| Notes | Long text | Human; examples and guidance |

The bot reads Topics and suggests matches. Reviewers remain responsible for
the final Topics on an Item.

## Source Runs

**Primary field:** `Run ID` (single line text)

Create this table for the current deployment. The Items collector writes one
record per active Source attempt.

| Field | Type | Owner and purpose |
|---|---|---|
| Run ID | Single line text (primary) | Bot; unique attempt identifier |
| Source | Link to Sources | Bot; Source attempted |
| Started At | Date + time | Bot |
| Finished At | Date + time | Bot |
| Result | Single select | Bot; `Working`, `No recent items`, `Needs attention`, or `Paused` |
| Items Found | Number | Bot; valid candidates parsed |
| Items New | Number | Bot; records newly created |
| Items Seen | Number | Bot; existing records encountered |
| HTTP Status | Number | Bot; response status when applicable |
| Error | Long text | Bot; actionable failure detail, blank on success |

Health is per Source, not per Organization, because one broken endpoint must
not make a working newsroom appear broken.

## Recommended Views

### Organizations

- **Active Organizations:** `Stage = Approved` and `Active` checked.
- **Candidates:** `Stage = Watchlist` or `Stage = Suggested`.
- **Archived Organizations:** `Stage = Archived`; hidden from normal users.
- **Permanent Delete:** admin-only view; never expose it in the normal
  operator Interface.

### Sources

- **Active Sources:** `Active` checked, grouped by Organization.
- **Sources Needing Setup:** URL empty or Format empty.
- **Paused Sources:** `Active` unchecked.
- **Source Health:** view of Sources and their related Source Runs, showing the
  latest Result.

### Items

- **Review Queue:** `Status = Needs Review`, newest `Published At` first.
- **Needs Re-review:** `Changed` checked or `Possible Duplicate Of` not
  empty.
- **Articles:** `Kind = article`.
- **Updates:** `Kind = update` or `Kind = post`.
- **Announcements:** `Kind = announcement`.
- **Reports:** `Kind = report`.
- **Events:** `Kind = event`, optionally displayed as a calendar using
  `Scheduled Start`.
- **Approved Items:** `Status = Approved` or `Status = Published`.

## Airtable Interface for Daily Operators

Create an Interface named **Abundroid Admin** with these pages:

1. **Organizations:** searchable active list, Add Organization form, record
   detail, related Sources, and Edit, Pause, Archive, and Restore actions.
2. **Review:** Review Queue with the source links, editable editorial fields,
   and status controls; hide IDs and hashes.
3. **Source Health:** related Source list with latest Result and Source Runs.
4. **Candidates:** Watchlist and Suggested organizations awaiting a decision.

Configure Pause to clear Organization Active. Configure Archive to clear
Organization Active and set Stage to `Archived`. Restore sets Stage to
`Approved` and turns Organization Active on; Sources that were individually
paused remain paused.

Restrict raw-table deletion and the **Permanent Delete** view to base
administrators. Deleting an Organization must not cascade to Items. Archive by
default.

## Legacy Events Compatibility

Existing deployments must keep the **Events** table, its current fields, and
the optional **Run Log** table. `abundroid run` uses these fields:

- Identity/bookkeeping: **Event UID**, **Source Hash**, **First Seen**,
  **Last Seen**, **Changed**, **Possibly Cancelled**, **Possible Duplicate Of**.
- Editorial data: **Title**, **Organizer**, **Co-organizers**, **Start**,
  **End**, **Timezone**, **Location**, **Virtual**, **Registration URL**,
  **Source URL**, **Short Description**, **Description**, **Speakers**,
  **Topics**, **Status**, and **Reviewer Notes**.
- Optional extraction field: **Confidence**.

Do not rename **Events** to **Items**, point `AIRTABLE_EVENTS_TABLE` at
**Items**, or manually merge the records. `abundroid run` and
`abundroid collect` are separate compatibility paths until each known legacy
deployment completes migration and the retirement gate in the roadmap.

## Setup Checklist

1. Create **Organizations**, **Sources**, **Items**, **Topics**, and **Source
   Runs** with the exact field names and types above.
2. Retain **Events**, **Run Log**, **Events URL**, and **Source Type** in
   existing calendar deployments.
3. Create the saved views and the **Abundroid Admin** Interface.
4. Configure Pause/Archive/Restore actions and restrict permanent deletion to
   base administrators.
5. Create a personal access token with `data.records:read` and
   `data.records:write`, restricted to this base.
6. Set `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID`; use table-name overrides
   only when the Airtable names differ.
7. Run `abundroid collect` twice and verify that the second run creates no
   duplicate Items.
8. In an existing deployment, run `abundroid run` and verify the Events
   compatibility path separately.
