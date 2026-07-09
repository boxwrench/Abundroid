# Abundroid

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

- Watch any number of organizations that publish a **calendar feed** (iCal) or
  a **news feed** (RSS) — you just paste the address into a table.
- Collect each event's title, date, location, description, and registration
  link, and put it in your review queue.
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

## How your team controls it

Everything is driven by ordinary Airtable tables — no code, no config files:

| You want to… | You do… |
|---|---|
| Watch a new organization | Add a row to the **Organizations** table |
| Stop watching one (maybe temporarily) | Uncheck its **Active** box — never delete |
| Park a "maybe" organization | Set its **Stage** to `Watchlist` or `Suggested` |
| Change how events get categorized | Edit keywords in the **Topics** table *(tagging arrives in Phase 2)* |
| Approve / reject / fix an event | Work the **Review Queue** view in the **Events** table |
| See which sources are broken | Check the **Source Health** view |

Things that currently *do* need a developer: adding a brand-new source type,
changing how often the bot runs, and changing the digest format (once digests
exist). The [roadmap](docs/ROADMAP.md) shows what's coming in what order.

## Where the project stands

**Working now (Phase 1):** the complete pipeline described above, for iCal and
RSS sources, with 72 automated tests.

**Next (Phase 2):** reading normal event webpages (covers Eventbrite, Luma,
and most WordPress sites), automatic topic tagging from your Topics table, and
flagging events whose details changed after approval.

**Then (Phases 3–4):** AI-assisted extraction for stubborn pages, automatic
scheduled runs, source health tracking, and the weekly digest.

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
python -m pytest          # 72 tests, all offline (golden fixtures)
abundroid run --dry-run   # fetch and print, write nothing
```

Layout: `src/abundroid/adapters/` (one small module per source type, each
exposing `parse(text, org) -> list[Event]`), `stores/` (CSV and Airtable
persistence behind the same upsert interface), `uid.py` (the deduplication
fingerprint), `pipeline.py` (orchestration), `cli.py` (entry point).
