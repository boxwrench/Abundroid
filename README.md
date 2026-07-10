<p align="center">
  <img src="assets/abundroid-logo.png" alt="Abundroid" width="520">
</p>

**Abundroid is a robot assistant that checks the events pages of the
organizations you care about, so nobody on your team has to.**

Every time it runs, it visits each organization on your list, collects any
upcoming events it finds, skips everything it has already seen, and adds only
the genuinely new ones to a shared "Needs Review" list in Airtable. A human
looks at that list, fixes anything wrong, and approves or rejects each event.
Only human-approved events ever go anywhere public.

That's the whole idea: **the bot does the tedious checking; people keep all
the judgment calls.**

> **Ready to set it up?** Follow the step-by-step guide:
> **[docs/SETUP.md](docs/SETUP.md)** — from zero to reviewing real events in
> about 30–45 minutes.

## What it can do today

- Watch any number of organizations that publish a **calendar feed** (iCal),
  a **news feed** (RSS), or an ordinary **events webpage** with embedded event
  data (covers Eventbrite, Luma, and most WordPress event calendars) — you
  just paste the address into a table.
- Collect each event's title, date, location, description, and registration
  link, and put it in your review queue.
- **Suggest topics automatically.** Keywords your team maintains in the Topics
  table ("zoning", "nuclear", "transit"…) are matched against each new event,
  and matching topics are pre-filled for the reviewer to correct.
- **Flag events that need a second look:** an already-reviewed event whose
  details changed at the source, a future event that vanished from its
  organizer's calendar (possibly cancelled), or two organizations announcing
  what looks like the same event on the same day. The bot only ever flags —
  it never edits or removes what a human reviewed.
- **Never show you the same event twice.** Each event gets a fingerprint; on
  every run the bot recognizes events it has already delivered and quietly
  notes "still there" instead of re-adding them. Your review queue only ever
  contains new work.
- Keep going when one source breaks — a dead link on one org's site never
  stops the other orgs from being checked.
- Run entirely without any accounts (using simple spreadsheet files) so anyone
  can try it before connecting the real Airtable base.

## What it deliberately does NOT do

These are design promises, not missing features:

- It **never publishes anything without human approval.**
- It **never makes up details.** If a source doesn't state the date, the date
  arrives blank and a human fills it in.
- It **never deletes or overwrites your edits.** Humans win every conflict.
- It doesn't scrape social media, bypass logins or paywalls, or crawl the
  open internet — it only visits the specific pages you listed.

## How we know it works

- **187 automated tests** check every behavior — parsing, deduplication,
  tagging, flagging, and every "never do" promise above. They all pass before
  any change is published.
- **Verified against the real internet**, not just test files: a live run
  pulled 20 events from a Luma city page, 40 from Eventbrite, 28 from a real
  iCal calendar, and 20 from a real RSS feed. Running the exact same command
  again reported `0 new, 68 seen` — the no-duplicates promise, demonstrated.
- **Failure was tested on purpose**: that same run included a deliberately
  dead URL, which errored cleanly while every other organization was still
  checked.

## How your team controls it

Everything is driven by ordinary Airtable tables — no code, no config files:

| You want to… | You do… |
|---|---|
| Watch a new organization | Add a row to the **Organizations** table |
| Stop watching one (maybe temporarily) | Uncheck its **Active** box — never delete |
| Park a "maybe" organization | Set its **Stage** to `Watchlist` or `Suggested` |
| Change how events get categorized | Edit keywords in the **Topics** table — takes effect next run |
| Approve / reject / fix an event | Work the **Review Queue** view in the **Events** table |
| Re-check events the bot flagged | Work the **Needs Re-review** view (changed / possibly cancelled / possible duplicates) |
| See which sources are broken | Check the **Source Health** view |

Things that currently *do* need a developer: adding a brand-new source type,
changing how often the bot runs, and changing the digest format (once digests
exist). The [roadmap](docs/ROADMAP.md) shows what's coming in what order.

## Where the project stands

**Working now (Phases 1–2):** the complete pipeline described above — iCal,
RSS, and embedded-event webpages (Eventbrite/Luma/WordPress), topic tagging,
change detection, cancellation and duplicate flagging — with 187 automated
tests. One Phase 2 item is deliberately deferred: the AI tiebreaker for
ambiguous topic matches waits until real review data shows it's needed.

**Next (Phase 3):** articles, blog posts, and announcements. "Events" always
meant occurrences broadly — the same watch/dedupe/review pipeline will cover
what organizations *publish*, not just what they schedule, in its own review
queue.

**Then (Phases 4–5):** AI-assisted extraction for pages with no embedded
event data, automatic scheduled runs, source health tracking, and the weekly
digest.

The full plan, including long-term ideas and what was deliberately postponed,
lives in **[docs/ROADMAP.md](docs/ROADMAP.md)**. The original planning
documents are archived in `archive/`.

## Key documents

- **[docs/SETUP.md](docs/SETUP.md)** — install it and connect your own
  Airtable and organizations. **Start here.**
- **[docs/airtable-schema.md](docs/airtable-schema.md)** — the exact Airtable
  base layout to create (tables, fields, views).
- **[docs/ROADMAP.md](docs/ROADMAP.md)** — what's built, what's next, what's
  postponed and why.

## For developers

Python 3.11+, no database — state lives in Airtable (or local CSV in
credential-free mode). Credentials come only from environment variables; see
`.env.example`.

```bash
pip install -e ".[dev]"
python -m pytest          # 187 tests, all offline (golden fixtures)
abundroid run --dry-run   # fetch and print, write nothing
```

Layout: `src/abundroid/adapters/` (one small module per source type, each
exposing `parse(text, org) -> list[Event]`), `stores/` (CSV and Airtable
persistence behind the same upsert interface), `uid.py` (identity and
change-detection fingerprints), `classifier.py` (keyword topic tagging),
`dedupe.py` (cross-organization duplicate flagging), `pipeline.py`
(orchestration), `cli.py` (entry point).
