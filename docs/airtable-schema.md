# Airtable Base Schema

Create a new Airtable base and set up four tables exactly as specified below. Non-technical admins can do this entirely by hand using the Airtable UI.

## Organizations Table

**Primary field**: Name (single line text)

Monitors the sources Abundroid will fetch from.

| Field | Type | Notes |
|---|---|---|
| Name | Single line text (primary) | Organization name; required |
| Website | URL | Homepage URL |
| Events URL | URL | Feed or event page URL (iCal, RSS, or schema.org/JSON-LD page); required |
| Source Type | Single select | Options: `ical`, `rss`, `jsonld`, `html` |
| Category | Multiple select | Multi-select for filtering (e.g., "Housing", "Energy", "Transit") |
| Priority | Single select | Options: `High`, `Medium`, `Low` |
| Active | Checkbox | Default: checked. Unchecked rows are skipped by the bot. |
| Stage | Single select | Options: `Approved`, `Watchlist`, `Suggested`. Default: `Approved`. The bot only monitors rows that are Active **and** Approved; Watchlist/Suggested are a human parking lot for maybe-organizations. |
| Notes | Long text | Internal notes, e.g., "site updated 2024-01", API contact, etc. |
| Last Checked | Date | *Bot writes*. Timestamp of last fetch attempt. |
| Last Successful Pull | Date | *Bot writes*. Timestamp of last successful fetch. |
| Health | Single select | *Bot writes*. Options: `Good`, `No events found`, `Page changed`, `Needs attention`, `Error` |

**Bot permissions**: Writes Last Checked, Last Successful Pull, Health. Reads everything else.

---

## Topics Table

**Primary field**: Topic (single line text)

Categorization taxonomy for events; used for tagging and filtering.

| Field | Type | Notes |
|---|---|---|
| Topic | Single line text (primary) | Topic name, e.g., "Zoning Reform", "Housing Supply"; required |
| Keywords | Long text | Comma-separated keywords used for automated tagging (Phase 2) |
| Aliases | Long text | Comma-separated alternate topic names (e.g., "YIMBY" → "Housing Advocacy") |
| Exclusions | Long text | Comma-separated terms that disqualify an event from this topic |
| Priority | Single select | Options: `High`, `Medium`, `Low`; used to rank topics in the UI |
| Active | Checkbox | Default: checked. Inactive topics are not offered for manual tagging. |
| Notes | Long text | Context or examples |

**Bot permissions**: Read-only (no writes).

---

## Events Table

**Primary field**: Event UID (single line text)

The review queue and event archive. The bot creates rows with deterministic UIDs based on registration URL (or organizer + title + date hash) to prevent duplicates across runs.

| Field | Type | Notes |
|---|---|---|
| Event UID | Single line text (primary) | *Bot writes*. Deterministic identifier; do not edit. Used to detect re-run duplicates. |
| Title | Single line text | Event name; human or bot-provided |
| Organizer | Single line text | Primary organizing entity |
| Co-organizers | Long text | Comma-separated or free-form co-organizers |
| Start | Date + time | Event start datetime; required for approval. Blank for RSS events (human fills in). |
| End | Date + time | Event end datetime |
| Timezone | Single line text | e.g., "America/Los_Angeles", "UTC" |
| Location | Single line text | Physical venue or "Virtual" if online |
| Virtual | Checkbox | Checked if fully online; unchecked if in-person or hybrid |
| Registration URL | URL | Link to RSVP or ticket page |
| Source URL | URL | URL of the page/feed the event was pulled from |
| Short Description | Long text | 1–2 sentence summary |
| Description | Long text | Full event description or abstract |
| Speakers | Long text | Speaker names or list |
| Topics | Multiple select (or linked records) | Link to Topics table for categorization |
| Confidence | Number | *Bot writes for AI extraction (Phase 3)*. Confidence score 0–100 if extracted. |
| Status | Single select | Options: `Needs Review`, `Approved`, `Rejected`, `Duplicate`, `Published`, `Archived`. Humans set this. |
| Changed | Checkbox | *Bot writes*. Checked if a previously seen event (same UID) had details updated at the source. |
| First Seen | Date | *Bot writes*. Date this UID first appeared. |
| Last Seen | Date | *Bot writes*. Most recent date this UID was fetched. |
| Reviewer Notes | Long text | Human notes during review; not sent to output |

**Bot permissions**: Writes Event UID, First Seen, Last Seen, Changed, Confidence (Phase 3). Reads and may update Start, End, Location, Source URL, Description, and other fields from the fetched event. Humans write Status, Topics, Reviewer Notes, and fill blanks (e.g., Start date for RSS events).

---

## Run Log Table

**Primary field**: Run ID (autonumber or date+time)

Execution history; one row per `abundroid run`.

| Field | Type | Notes |
|---|---|---|
| Run ID | Autonumber (or date+time primary) | Auto-created; uniquely identifies this run |
| Timestamp | Date + time | When the run started |
| Organization | Single line text | Name of the organization just processed (if logging per-org) or "Batch" for full runs |
| Events Found | Number | Count of events fetched in this run |
| Events New | Number | Count of new UIDs (not seen before) |
| Errors | Long text | Error messages or issues encountered (empty if successful) |

**Bot permissions**: Writes all fields.

---

## Recommended Views

### Review Queue (Events)
- **Filter**: Status = "Needs Review"
- **Sort**: Start date (ascending)
- Shows human reviewers the next events to process.

### Source Health (Organizations)
- **Group by**: Health
- Shows which organizations have issues at a glance.

### Calendar (Events)
- **View type**: Calendar
- **Date field**: Start
- **Filter**: Status = "Approved" OR Status = "Published"
- Shows approved/published events on a timeline.

### Suggested Sources (Organizations)
- **Filter**: Stage = "Suggested" OR Stage = "Watchlist"
- Parking lot for organizations under consideration; promote to Approved to start monitoring.

---

## Quality Metrics (optional but recommended)

Add these once real data flows — they take minutes and can't be reconstructed later. They also tell you when automated helpers have earned more trust.

- On **Organizations**: rollup/count fields over linked Events — events approved, events rejected, % approved. A source whose events are mostly rejected is a relevance problem, not a technical one.
- On **Events**: a "Edited Before Approval" checkbox reviewers tick when they had to correct bot-extracted details. The rate of this per source measures extraction quality.

(To use rollups, add a linked-record field from Events to Organizations via the Organizer; otherwise approximate with grouped views.)

---

## Setup Checklist

1. Create a new Airtable base (or re-use an existing one).
2. Create the four tables: **Organizations**, **Topics**, **Events**, **Run Log**.
3. Add fields to each table exactly as specified above (order does not matter, but field names and types must match).
4. Create the three recommended views.
5. Create a [personal access token](https://airtable.com/create/tokens) with `data.records:read` and `data.records:write` scopes, restricted to this base.
6. Note your base ID (visible in the URL as `appXXXXX...`).
7. Copy `.env.example` to `.env` and fill in `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID`.
8. Run `abundroid run` to verify the connection.

If table or field names differ, set `AIRTABLE_ORGS_TABLE` and `AIRTABLE_EVENTS_TABLE` in `.env` to override defaults.
