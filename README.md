# Abundroid

Abundroid is an event-discovery and review pipeline for the abundance ecosystem. It monitors a curated list of organizations (housing/YIMBY, energy, permitting reform, state capacity, transit, water, science policy, government modernization), pulls upcoming events from their feeds, deduplicates them, and puts them in a human review queue (Airtable) before publishing to a weekly digest or calendar.

## How It Works

- **Table-driven configuration**: Non-technical admins control everything via Airtable tables—Organizations (what to monitor), Topics (how to categorize), Events (review queue + archive), and Run Log (execution history).
- **Event fetching**: The bot reads active organizations, fetches events from their sources (iCal or RSS), and normalizes each event to a standard format.
- **Deterministic deduplication**: Computes a deterministic `event_uid` from the registration URL (if present) or a hash of organizer + title + date, preventing duplicates on re-runs.
- **Review queue**: New events (new uid) land with status "Needs Review"; already-seen uids just update Last Seen, keeping the queue free of re-run duplicates.
- **No credentials shipped**: The codebase ships with no secrets. Each deployment supplies API keys via environment variables, or runs in local CSV mode (zero accounts needed).
- **Scheduled runs**: Designed to run as a cron job (e.g., on GitHub Actions) to continuously monitor sources.

## Quickstart (No Credentials)

Try Abundroid with zero accounts:

```bash
git clone https://github.com/boxwrench/Abundroid.git
cd Abundroid
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

Edit `data/organizations.csv` to add a few seed organizations (or use the example row). Then run:

```bash
abundroid run
```

Events will be written to `output/events.csv` with status "Needs Review". You can review them, update status, and re-run without losing your edits (uids prevent duplicates).

## Connecting Your Own Airtable

To use Airtable instead of local CSV:

1. Create a new Airtable base and set up the schema (see `docs/airtable-schema.md` for the exact field structure).
2. Create a [personal access token](https://airtable.com/create/tokens) with `data.records:read` and `data.records:write` scopes, restricted to your new base.
3. Copy `.env.example` to `.env` and fill in:
   ```
   AIRTABLE_API_KEY=your_token_here
   AIRTABLE_BASE_ID=your_base_id_here
   ```
4. Run `abundroid run`. Events will be upserted into the Events table, and the Run Log will capture execution details.

Optional: set `AIRTABLE_ORGS_TABLE` and `AIRTABLE_EVENTS_TABLE` if you renamed the tables.

## Configuration Reference

| Environment Variable | Purpose | Example |
|---|---|---|
| `AIRTABLE_API_KEY` | Personal access token for Airtable (optional) | `pat...` |
| `AIRTABLE_BASE_ID` | Base ID (optional) | `appXXX` |
| `AIRTABLE_ORGS_TABLE` | Organizations table name (default: `Organizations`) | `Sources` |
| `AIRTABLE_EVENTS_TABLE` | Events table name (default: `Events`) | `Calendar` |
| `ANTHROPIC_API_KEY` | Claude API key for AI extraction (Phase 3, not yet used) | `sk-ant-...` |

## Project Status & Roadmap

**Phase 1 (In Progress)**: iCal and RSS source types, deduplication, local CSV and Airtable storage.

**Phase 2 (Planned)**: schema.org/JSON-LD page scraping (covers Eventbrite, Luma, WordPress), keyword-based topic tagging, change detection for previously seen events.

**Phase 3 (Planned)**: AI-assisted event extraction for plain HTML pages (Claude API), source health tracking, GitHub Actions scheduling with cron.

**Phase 4 (Planned)**: Weekly digest generation, scaling to 30–50 organizations, integration with published calendar.

## Design Notes

- **RSS special case**: RSS post dates are publication dates, not event dates. Events sourced from RSS arrive with no start date; the human reviewer fills it in. The system never fabricates event details.
- **Browser automation**: Out of scope. Use iCal/RSS/schema.org feeds; extraction is AI-assisted (Phase 3), not browser-driven.
- **Project briefs**: The original requirement PDFs are archived in `archive/`; the living, reconciled plan is `docs/ROADMAP.md`.
