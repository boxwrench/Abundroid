# Setting Up Abundroid — Step by Step

This guide walks you through making Abundroid work with **your** accounts and
**your** list of organizations. No programming knowledge needed, but you will
copy and paste a few commands into a terminal.

Total time: about 30–45 minutes, most of it setting up the Airtable base.

---

## What you'll need

| Thing | Why | Cost |
|---|---|---|
| A computer (Windows or Mac) | To install and run the bot | — |
| Python 3.11 or newer | The language the bot is written in | Free — [python.org/downloads](https://www.python.org/downloads/) |
| An Airtable account | Where your team reviews events | Free tier works to start (note: free bases cap total records, so plan to archive old events or upgrade later) |

> **Just want a quick look first?** Do Steps 1–2 only. Abundroid runs without
> any accounts at all, using simple files on your computer.

---

## Step 1 — Install Abundroid

Open a terminal (Windows: press Start, type "PowerShell", press Enter.
Mac: open the Terminal app), then paste these lines one at a time:

```bash
git clone https://github.com/boxwrench/Abundroid.git
cd Abundroid
python -m venv .venv
```

Then activate the environment:

- **Windows:** `.venv\Scripts\activate`
- **Mac:** `source .venv/bin/activate`

And install:

```bash
pip install -e .
```

If you see no red error text, it worked.

## Step 2 — Test drive with zero accounts

The repo ships with a file called `data/organizations.csv` — a starter list
with one example row. Run the bot against it:

```bash
abundroid run
```

You'll see one line per organization saying how many events were found. Found
events land in `output/events.csv`, which you can open in Excel. Every event
arrives marked **Needs Review** — nothing is ever auto-approved.

Run the same command again: notice it reports `0 new`. The bot remembers what
it has already seen, so re-running never creates duplicates. This is the core
promise of the whole system.

There's also a starter `data/topics.csv` with a few example topics (Housing,
Energy, Transit). Events whose title or description mention those keywords
get the topic filled in automatically — edit the file to try your own. In
Airtable mode the **Topics** table plays this role instead.

---

## Step 3 — Create your Airtable base

This is where your team will actually work day to day.

1. Log in to Airtable and create a new base (name it "Abundroid" or anything
   you like).
2. Create four tables with the exact fields listed in
   **[docs/airtable-schema.md](airtable-schema.md)**: `Organizations`,
   `Topics`, `Events`, and `Run Log`. Field **names and types must match
   exactly** — the bot finds fields by name.
3. Create the recommended views from the same document (Review Queue, Source
   Health, Calendar, Suggested Sources). Views are just saved filters — they
   take a minute each and they're how reviewers will live in this base.

## Step 4 — Create an access token

The bot needs permission to read and write your base. Airtable does this with
a "personal access token" — think of it as a password that only works for this
one base.

1. Go to [airtable.com/create/tokens](https://airtable.com/create/tokens).
2. Click **Create new token**. Name it "Abundroid".
3. Under **Scopes**, add `data.records:read` and `data.records:write`.
4. Under **Access**, add **only** your new Abundroid base.
5. Click **Create token** and copy it somewhere safe — Airtable shows it once.

## Step 5 — Connect Abundroid to your base

1. In the Abundroid folder, copy the file `.env.example` and name the copy
   `.env` (yes, just a dot and "env").
2. Open `.env` in any text editor and fill in two lines:

   ```
   AIRTABLE_API_KEY=paste_your_token_here
   AIRTABLE_BASE_ID=paste_your_base_id_here
   ```

   Your **base ID** is in the web address when your base is open: the part
   that starts with `app`, e.g. `airtable.com/appABC123xyz/...` → `appABC123xyz`.

The `.env` file stays on your computer. It is deliberately ignored by git, so
your token can never end up on GitHub by accident.

## Step 6 — Add your organizations

In the **Organizations** table, add a row per organization you want to watch:

- **Name** — the org's name.
- **Events URL** — the address the bot should check (see below).
- **Source Type** — what kind of address it is (see below).
- **Active** — check it.
- **Stage** — set to `Approved` (that's what tells the bot "yes, monitor this
  one"; use `Watchlist` or `Suggested` to park maybes).

### Finding the Events URL and Source Type

This is the only genuinely fiddly part. The bot reads three kinds of sources
today, in order of preference:

- **`ical`** — a calendar feed. Look for "Subscribe to calendar", "Add to
  calendar", or a link ending in `.ics` on the org's events page. These are
  the best sources: complete dates, times, and locations.
- **`jsonld`** — an ordinary events webpage with event data embedded in it.
  You can't see the data, but Eventbrite pages, Luma (lu.ma) pages, and most
  WordPress event calendars have it. Just paste the address of the org's
  events page and try it — if the run reports `0 found` on a page that
  clearly lists events, the site doesn't embed data and you should park the
  row as `html` instead.
- **`rss`** — a news feed. Try adding `/feed` to the end of the org's site
  address, or look for an RSS icon. Note: RSS tells us an event was
  *announced* but usually not *when it happens*, so RSS events arrive without
  a date and a reviewer fills it in.

If none of those work, set Source Type to `html` and leave the row Active.
The bot will report it as `unknown source type` for now; AI-assisted reading
of plain webpages is Phase 4 on the [roadmap](ROADMAP.md) and those rows will
start working without any changes on your side.

## Step 7 — Run it and review

```bash
abundroid run
```

With your `.env` in place, the bot automatically uses Airtable instead of the
local files. Then open your base:

1. Open the **Review Queue** view — every new event is there, marked
   **Needs Review**, often with suggested **Topics** already filled in from
   your Topics table keywords.
2. For each event: check the details against the **Source URL** link, fix
   anything wrong (especially missing dates on RSS events), correct the
   Topics if the bot guessed badly, then set **Status** to `Approved`,
   `Rejected`, or `Duplicate`.
3. Check the **Needs Re-review** view occasionally. Events land there when
   the bot notices something *after* your first review:
   - **Changed** — the details changed at the source. The bot deliberately
     does not update the row (your edits always win); open the Source URL,
     see what changed, fix the row if needed, and uncheck the box.
   - **Possibly Cancelled** — a future event disappeared from its
     organization's calendar. Confirm at the source; the box clears itself if
     the event reappears.
   - **Possible Duplicate Of** — another organization posted what looks like
     the same event on the same day. Review both rows and mark one
     `Duplicate`.
4. That's the whole job. Approved events are what future digests and calendars
   will publish.

**Never edit the Event UID or Source Hash columns** — those are how the bot
recognizes events and detects changes.

## Step 8 — Running it regularly

For now, run `abundroid run` whenever you want fresh events (daily or weekly
is plenty). Automatic scheduled runs (the bot running itself every morning via
GitHub Actions, no computer needed) are Phase 4 on the roadmap.

---

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `error (getaddrinfo failed)` or `error (404 ...)` next to an org | That org's URL is wrong or unreachable | Check the Events URL in a browser; fix or mark org Inactive |
| `unknown source type` | Source Type isn't `ical`, `rss`, or `jsonld` | That's expected for `html` rows until Phase 4 — leave them or pause them |
| `ok, 0 found` | The feed is real but currently empty | Usually fine on feeds; on a `jsonld` row whose page clearly lists events, the site doesn't embed event data — change the row to `html` |
| `abundroid: command not found` | The environment isn't active | Re-run the activate command from Step 1 |
| Events show up twice | Two different URLs for the same event (e.g., org page + Eventbrite) | If both are same-day with similar titles, the bot cross-flags them (**Possible Duplicate Of**); either way, mark one `Duplicate` |

## Rules the bot always follows

- It never approves or publishes anything — humans do that.
- It never invents dates, titles, or links; missing details stay blank for a
  human to fill in.
- It never deletes rows, and it never overwrites edits a human made to an
  event.
- One broken source never stops the rest of the run.

Questions or something not covered here? Open an issue on the
[GitHub repository](https://github.com/boxwrench/Abundroid/issues).
