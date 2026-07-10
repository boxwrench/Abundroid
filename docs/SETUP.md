# Setting Up and Operating Abundroid

This guide has two audiences:

- **Technical deployer:** completes installation, Airtable schema, credentials,
  and manual collection until Phase 4 scheduling is implemented.
- **Daily operator:** adds, pauses, archives, and restores organizations;
  and reviews Items entirely in Airtable. Live source health arrives in
  Phase 4.

Routine operation must not require a terminal or knowledge of RSS, JSON-LD,
or adapters.

## The short version for Abundance staff

The tracker watches approved organizations and collects the things they publish.
You work in the **Abundroid Admin** Airtable Interface:

1. Add or update an organization.
2. Make sure it has at least one active source, such as a newsroom or blog. If
   you do not know the source URL or format, leave that step for the technical
   deployer.
3. Open **Review Queue** when new items arrive.
4. Check the link, adjust the title, summary, or topics, then choose a status.

Use **Pause** when monitoring should stop temporarily. Use **Archive** when the
organization should leave the active list but its history should remain. Use
**Restore** to bring it back. Prefer archiving to deleting; permanent deletion
is reserved for base administrators.

The Airtable words translate simply:

| Airtable word | In plain language |
|---|---|
| Organization | The publisher being tracked |
| Source | A specific blog, newsroom, or updates page to check |
| Item | One article, post, update, announcement, or report |
| Active | Include this organization or source in the next check |
| Stage | Whether the organization is approved, a candidate, or archived |
| Review Queue | New publications waiting for a person to check them |

Only edit fields intended for people. Leave IDs, hashes, and first/last-seen
dates alone; those are how the tracker recognizes the same publication later.
## One-Time Technical Deployment

### 1. Install Abundroid

Install Python 3.11 or newer, then run:

```powershell
git clone https://github.com/boxwrench/Abundroid.git
cd Abundroid
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e '.[dev]'
python -m pytest
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

### 2. Test the unified Items path locally

Without Airtable credentials, the new collection path reads
`data/sources.csv` and writes `output/items.csv`:

First replace the disabled example URL with a real RSS or Atom feed and set
`active` to `true`. The checked-in example is inactive so a fresh checkout
does not make an unexpected network request.

```powershell
abundroid collect
```

Run it a second time to verify that an unchanged feed creates no new Items.
The legacy calendar path remains available as `abundroid run`; it reads
`data/organizations.csv` and writes `output/events.csv`.

### 3. Create the Airtable base

Create the tables and fields in [airtable-schema.md](airtable-schema.md):

1. **Organizations**
2. **Sources**
3. **Items**
4. **Topics**

Create **Source Runs** now if you want the base ready for Phase 4 health
history. The collector does not write that table yet.

Keep **Events** in an existing deployment because it supports the legacy
`abundroid run` path. Retain **Run Log** if the base already uses it for
history, but the current commands do not write it.

Create the saved views and Airtable Interface described in the schema guide.
This is deployment work, not a task for daily operators.

### 4. Create an Airtable token

1. Open [airtable.com/create/tokens](https://airtable.com/create/tokens).
2. Create a token named `Abundroid`.
3. Add `data.records:read` and `data.records:write` scopes.
4. Restrict access to the Abundroid base.
5. Store the token in the deployment secret store. Do not paste it into
   Airtable or commit it to Git.

### 5. Configure environment variables

Copy `.env.example` to `.env` for a local deployment and set:

```dotenv
AIRTABLE_API_KEY=pat_your_token
AIRTABLE_BASE_ID=app_your_base_id
```

The base ID is the value beginning with `app` in the Airtable base URL. The
default table names can be overridden with the variables listed in
`.env.example`.

For GitHub Actions or another scheduler, store the token and base ID as secret
environment variables rather than committing a `.env` file.

### 6. Verify both paths

Run the new collection path:

```powershell
abundroid collect
```

Confirm that a new record appears in **Items**, then run the command again and
confirm it does not create a duplicate. Existing calendar deployments should
also run `abundroid run` and confirm their **Events** queue still works.

Automatic scheduling and source discovery are Phase 4 work. Until scheduling
is configured, a technical operator must start collection with the command
above; daily Airtable work still requires no terminal.

## Daily Operation: No Terminal

Use the Abundroid Airtable Interface rather than raw tables for routine work.
The interface should expose friendly actions and hide IDs, hashes, source
formats, and other bookkeeping fields.

### Add an organization

1. Select **Add Organization**.
2. Enter its **Name** and **Website**. Add category, priority, and notes if
   useful.
3. Leave **Active** on and choose `Approved` when monitoring should begin.
   Choose `Watchlist` or `Suggested` when the organization is only a
   candidate.
4. Add and activate at least one related **Source**. A Source is the specific
   blog, newsroom, feed, or calendar to check.

During the RSS-first milestone, an advanced administrator may need to paste a
feed URL and select `rss`. The planned source discovery assistant will
suggest Sources from the organization website so normal operators only approve
them. An approved organization with no active Sources is safely stored but
produces no Items.

### Edit or pause an organization

- Use **Edit** to change its display name, website, category, priority, or
  notes. Editing an organization does not change old Items.
- Use **Pause** for a temporary stop. This clears **Active** and prevents all
  related Sources from being collected without changing their individual
  settings.
- To pause only one endpoint, clear **Active** on that Source instead.

### Archive and restore

- Use **Archive** when the team no longer wants to monitor an organization.
  The action sets **Stage** to `Archived` and clears **Active**.
- Archived organizations and their Sources disappear from normal active views,
  but their Items and future Source Runs remain available.
- Use **Restore** to return an organization to `Approved`, then turn
  **Active** on when collection should resume. Sources that were individually
  paused remain paused.

### Permanently delete

Permanent deletion is not a normal operator action. A base administrator must
confirm it in an admin-only view or interface.

Before deleting an Organization, deactivate its Sources. Do not cascade the
deletion to historical Items. Retain the publisher text and source facts on
those Items, and unlink the deleted configuration record if Airtable requires
it. Prefer archiving unless privacy, legal, or data-quality policy requires
erasure.

### Review new Items

1. Open **Review Queue**.
2. Open the **Canonical URL** or **Source URL** and compare it with the record.
3. Correct the title, kind, author, summary, or Topics if needed.
4. Set **Status** to `Approved`, `Rejected`, or `Duplicate`.
5. Add **Reviewer Notes** when another reviewer will need context.

Do not edit **Item UID**, **Source Item ID**, **Source Hash**, **First Seen**,
or **Last Seen**. These fields let the bot recognize a publication across
runs. Once a person edits editorial copy, later source updates do not silently
replace it; a change is flagged for review.

### Check source health (Phase 4)

Once Phase 4 is implemented, open **Source Health** and use the plain-language
status:

| Status | Meaning | Operator action |
|---|---|---|
| `Working` | The last fetch succeeded | None |
| `No recent items` | Fetch succeeded but found nothing new recently | Usually none; inspect if unexpected |
| `Needs attention` | The source failed or its format changed | Open the latest Source Run and ask an advanced admin to fix the URL or format |
| `Paused` | The Source or its Organization is inactive | None unless it should resume |

The current collector does not write these statuses. Until Phase 4, the
technical operator checks command output. One broken Source does not stop other
Sources.

## Legacy Events Compatibility

`abundroid run` is the existing calendar-oriented command. It continues to
read the legacy **Events URL** and **Source Type** fields on **Organizations**
and write the **Events** table. Do not rename those fields, remove the table,
or point `AIRTABLE_EVENTS_TABLE` at **Items**.

The unified `abundroid collect` command reads **Sources** and writes **Items**.
Running both during migration is supported. A future migration tool will copy
appropriate Events into Items with `Kind = event`; do not copy records by
hand unless you also preserve their identity fields.

## Troubleshooting

| Symptom | Action |
|---|---|
| `abundroid: command not found` | Activate the virtual environment and reinstall with `pip install -e .` |
| Airtable returns `401` or `403` | Check the token, scopes, and base access |
| Airtable reports an unknown field | Match field names and types to `airtable-schema.md` |
| A Source is not collected | Confirm its Organization is `Approved` and Active, and the Source is Active |
| A feed succeeds but produces no Items | An empty feed may be valid; inspect command output until Source Runs is wired |
| The same publication appears twice | Mark one `Duplicate`; retain both until identity rules are checked |
| An archived organization still runs | Confirm **Active** is off on the Organization and restart the next collection |

## Safety Rules

- The bot never approves or publishes an Item.
- Missing source facts remain blank; the bot does not invent them.
- Human editorial changes are not silently overwritten.
- Archiving configuration preserves history.
- Credentials belong in environment secrets, never Airtable fields or Git.
