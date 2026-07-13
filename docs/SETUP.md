# Setting Up and Operating Abundroid

This guide has two audiences:

- **Technical deployer:** completes installation, Airtable schema, credentials,
  and manual collection until Phase 4 scheduling is implemented.
- **Daily operator:** adds, pauses, archives, and restores organizations;
  reviews Items; and checks Source health entirely in Airtable.

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

Complete the following steps on the computer that will run collection. Airtable
table and Interface setup is browser-based and may be done on another computer,
but the repository, `.env`, and collection command must be on the collection
computer.

The Windows examples use PowerShell. Unless a step explicitly says to use the
Airtable website, run every command from the repository root: the `Abundroid`
folder containing `pyproject.toml`, `src`, and `docs`.

### 1. Install Abundroid

#### Windows

These commands have been smoke-tested on Windows 11. Install
[Git](https://git-scm.com/downloads) and Python 3.11 or newer. Open **Windows
PowerShell** from the Start menu and verify both programs:

```powershell
git --version
python --version
```

Choose a parent folder for the repository. The example below uses `C:\GitHub`;
use a different absolute path if that is where you keep projects. `git clone`
creates the `Abundroid` folder, and `Set-Location` enters it:

```powershell
New-Item -ItemType Directory -Force C:\GitHub
Set-Location C:\GitHub
git clone https://github.com/boxwrench/Abundroid.git
Set-Location .\Abundroid
```

If the repository is already cloned, do not clone it again. Open PowerShell and
enter the existing folder directly, for example:

```powershell
Set-Location C:\GitHub\Abundroid
```

Confirm that PowerShell is in the repository root. This command must print
`True`:

```powershell
Test-Path .\pyproject.toml
```

Create the virtual environment, install Abundroid and its test dependencies,
then run the test suite:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

All tests should pass. The rest of this guide uses
`.\.venv\Scripts\abundroid.exe` explicitly, so activating the virtual
environment is optional. If you activate it, `abundroid` is equivalent to that
full path.

#### Ubuntu 24.04

These commands have been smoke-tested on Ubuntu 24.04. Open **Terminal** and
install Git, Python, virtual-environment support, pip, certificates, and a text
editor:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ca-certificates nano
git --version
python3 --version
```

`python3 --version` must report Python 3.11 or newer. If it reports an older
version, stop and install a supported Python version before continuing.

Choose a parent folder, clone the repository, and enter its root. This example
uses `~/projects`:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/boxwrench/Abundroid.git
cd Abundroid
test -f pyproject.toml && echo "Repository root confirmed"
```

If the repository is already cloned, skip `git clone` and use `cd` with its
existing absolute path. Then install and test Abundroid:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pytest
```

All tests should pass. For every later command in this guide, replace the
Windows path `.\.venv\Scripts\abundroid.exe` with
`./.venv/bin/abundroid`. The data file and output paths work unchanged.

On macOS, use the same `.venv/bin` paths, but install Python 3.11 or newer and
Git with your normal package manager first.

### 2. Test the unified Items path locally

Without Airtable credentials, the new collection path reads
`data/sources.csv` and writes `output/items.csv`:

Open `data/sources.csv` in a text editor. Replace the example row with a real
public RSS or Atom feed. Keep the header unchanged, set `format` to `rss`, and
set `active` to `true`. For example:

```csv
organization,name,url,format,default_kind,active,notes
Example Organization,News feed,https://example.org/feed.xml,rss,article,true,
```

Use a real feed URL in place of `https://example.org/feed.xml`. The checked-in
example is inactive so a fresh checkout does not make an unexpected network
request. Run collection from the repository root:

```powershell
.\.venv\Scripts\abundroid.exe collect
```

The command should name the Source, report it as `ok`, and create
`output/items.csv` plus `output/source_runs.csv`. Run the same command a second
time. The second summary should report `0 new`; the CSV should not gain a
duplicate Item row.

This step tests local CSV mode only. The legacy calendar path remains available
as `.\.venv\Scripts\abundroid.exe run`; it reads `data/organizations.csv` and
writes `output/events.csv`.

### 3. Create the Airtable base

Open [Airtable](https://airtable.com/) in a browser and create or select the
base that Abundroid will use. A new deployment may name it `Abundroid`.

Create these five tables before adding linked-record fields:

1. **Organizations**
2. **Sources**
3. **Items**
4. **Topics**
5. **Source Runs**

Then create every field with the exact name and type in
[airtable-schema.md](airtable-schema.md). Airtable creates sample fields in a
new table; rename or delete those fields rather than leaving similarly named
duplicates. Pay particular attention to these contracts:

- The primary fields are **Name**, **Name**, **Item UID**, **Topic**, and
  **Run ID**, respectively.
- **Sources -> Organization** links to exactly one **Organizations** record.
- **Sources -> Organization Name** is a lookup of the linked Organization's
  **Name**; do not type it manually.
- **Source Runs -> Source** links to **Sources**.
- The only **Sources -> Format** option needed now is lowercase `rss`.
- Field names are case- and space-sensitive to the integration. Do not rename
  fields such as **Default Kind**, **Published At**, or **Items Found**.

Keep **Events** in an existing deployment because it supports the legacy
`abundroid run` path. Retain **Run Log** if the base already uses it for
history, but the current commands do not write it. A new deployment does not
need to create either legacy table.

Do not create the Interface yet. First validate table reads and writes in steps
6 and 7; live records make the Interface easier to configure correctly.

### 4. Create an Airtable token

On Airtable's website:

1. Open [airtable.com/create/tokens](https://airtable.com/create/tokens).
2. Create a token named `Abundroid`.
3. Add `data.records:read` and `data.records:write` scopes.
4. Restrict access to the Abundroid base.
5. Copy the token once and store it in a password manager until `.env` is
   configured. Do not paste it into Airtable records, chat, or Git.

### 5. Configure environment variables

On Windows, return to PowerShell on the collection computer and confirm that it
is still in the repository root. Copy the ignored template and open the copy in
Notepad:

```powershell
Copy-Item .\.env.example .\.env
notepad .\.env
```

On Ubuntu, run this from the repository root instead:

```bash
cp .env.example .env
nano .env
```

In nano, press `Ctrl+O`, then Enter to save; press `Ctrl+X` to close it.

Replace only the two blank credential values:

```dotenv
AIRTABLE_API_KEY=pat_your_token
AIRTABLE_BASE_ID=app_your_base_id
```

Do not add quotes around either value. The token begins with `pat`; the base ID
begins with `app` and appears in the Airtable base URL. Save and close the text
editor. Abundroid loads `.env` from the current directory each time it starts,
which is why commands must run from the repository root.

The default table names already match this guide. Only uncomment a table-name
override in `.env` when an existing base uses a different name. Never point
`AIRTABLE_EVENTS_TABLE` at **Items**.

Confirm that Git is ignoring the credential file:

```powershell
git status --short
```

The output must not include `.env`. Do not continue if it does.

For GitHub Actions or another scheduler, store the token and base ID as secret
environment variables rather than committing a `.env` file.

### 6. Add the first Organization and Source

In Airtable, create one **Organizations** record:

| Field | Test value |
|---|---|
| Name | Name of the publisher being tested |
| Website | Publisher's public homepage |
| Active | Checked |
| Stage | `Approved` |

Create one linked **Sources** record:

| Field | Test value |
|---|---|
| Name | A friendly name such as `News feed` |
| Organization | Link to the Organization above |
| URL | A real public RSS or Atom feed URL |
| Format | `rss` |
| Default Kind | Usually `article`, `post`, or `update` |
| Active | Checked |

Confirm that **Organization Name** fills itself from the link. Leave it alone if
it is blank; fix the lookup definition instead. **Topics** may remain empty for
the first test.

### 7. Validate the live collection path

First perform a read-only preview from PowerShell in the repository root:

```powershell
.\.venv\Scripts\abundroid.exe collect --dry-run
```

The Source should report `ok`, and parsed Items should print in the terminal.
Dry-run reads Airtable and fetches the feed but writes neither **Items** nor
**Source Runs**. If the command instead reads `data/sources.csv`, stop and check
that `.env` is in the repository root and both credential values are present.

Run the write path:

```powershell
.\.venv\Scripts\abundroid.exe collect
```

Confirm all of the following before continuing:

1. The command exits without an error and reports the Source as `ok`.
2. **Items** contains the feed entries with **Status = Needs Review**.
3. **Source Runs** contains one linked record with **Result = Working** or
   **No recent items**.
4. **Item UID**, **Source Hash**, **First Seen**, and **Last Seen** are filled.

Run the same command again. The Item count must not increase for unchanged feed
entries, the terminal should report `0 new`, and one additional Source Run
should appear.

Edit one Item's **Title**, **Summary**, **Topics**, and **Status** in Airtable,
then run collection a third time. Confirm that those reviewer-owned edits remain
unchanged.

Existing calendar deployments should separately run
`.\.venv\Scripts\abundroid.exe run` and confirm their **Events** queue still
works. New deployments should skip that compatibility check.

### 8. Validate failure and pause behavior

Add a second active Source linked to the same test Organization, but give it a
deliberately invalid URL. Run collection and confirm that:

- The command returns a failure status after attempting both Sources.
- Items from the working Source are still retained.
- The broken Source receives a **Source Runs** record with
  **Result = Needs attention** and a useful **Error**.

Then correct or deactivate the broken Source. Also create a Source with no
Organization link and verify that collection skips it. Unlinked, inactive, and
Organization-paused Sources are not fetched and do not receive a new Source Run.
Their `Paused` state is inferred from **Active** and the Organization link, not
written as a new attempt record.

### 9. Create and test the operator Interface

Create the saved views and **Abundroid Admin** Interface described in
[airtable-schema.md](airtable-schema.md). Use the live test records to verify
the Review Queue and Source Health pages. In Source Health, show the Source's
**Active** value and related Source Runs sorted by **Started At**, newest first.

Have someone who did not perform deployment use the Interface to add, edit,
pause, archive, restore, and review a test Organization. Record any step that
requires a raw table, terminal, or explanation from the deployer; those are
validation findings rather than operator training failures.

Automatic scheduling and source discovery are Phase 4 work. Until scheduling
is configured, a technical operator must start collection with the command
above; daily Airtable review work still requires no terminal.

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
  but their Items and historical Source Runs remain available.
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

### Check source health

The collector records every active collection attempt as a **Source Run**
record. For local CSV runs, history is appended to `output/source_runs.csv`
beside the Items file. For Airtable mode, run records are written to **Source
Runs**. Read the latest related run together with the Source's **Active** value:

| Status | Meaning | Operator action |
|---|---|---|
| `Working` | The last fetch succeeded and returned one or more valid items | None |
| `No recent items` | Fetch succeeded but returned no items | Usually none; inspect if unexpected |
| `Needs attention` | The source failed or its format changed | Open the latest Source Run and ask an advanced admin to fix the URL or format |
| `Paused` | The Source or its Organization is inactive or unlinked; no new attempt is recorded | None unless it should resume |

One broken Source does not stop other active Sources from being collected,
although the overall command returns a failure status so the problem is not
hidden.

## Legacy Events Compatibility

`abundroid run` is the existing calendar-oriented command. It continues to
read the legacy **Events URL** and **Source Type** fields on **Organizations**
and write the **Events** table. Do not rename those fields, remove the table,
or point `AIRTABLE_EVENTS_TABLE` at **Items**.

The unified `abundroid collect` command reads **Sources** and writes **Items**.
Running both during migration is supported.

### Migrating Legacy Events to Unified Items

The `migrate-events` subcommand copies legacy Event records into unified Items with `kind = event`:

```powershell
# CSV mode (local files)
.\.venv\Scripts\abundroid.exe migrate-events --events data/events.csv --items output/items.csv

# Write the migrated records to the target CSV store (apply)
.\.venv\Scripts\abundroid.exe migrate-events --events data/events.csv --items output/items.csv --apply
```

If `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` are set in your environment, the migration command operates on Airtable instead:

```powershell
# Airtable preview mode
.\.venv\Scripts\abundroid.exe migrate-events

# Airtable apply mode
.\.venv\Scripts\abundroid.exe migrate-events --apply
```

Without `--apply`, the tool runs in preview mode, performing no writes but displaying counts and warnings (e.g. invalid dates, missing required fields, unresolved duplicate links). With `--apply`, the converted Items are upserted into the target store. The migration is idempotent; running apply again does not overwrite reviewer edits or create duplicate Items.

## Troubleshooting

| Symptom | Action |
|---|---|
| `abundroid: command not found` | From the repository root, run `.\.venv\Scripts\abundroid.exe`; if it is missing, repeat the install command in step 1 |
| `python` or `git` is not recognized | Install the missing prerequisite, close PowerShell, open it again, and repeat the version check |
| Collection uses CSV after `.env` was created | Run from the repository root, confirm `.env` is there, and set both Airtable credential values without quotes |
| Airtable returns `401` or `403` | Check the token, scopes, and base access |
| Airtable reports an unknown field | Match field names and types to `airtable-schema.md` |
| A Source is not collected | Confirm its Organization is `Approved` and Active, and the Source is Active |
| A feed succeeds but produces no Items | An empty feed may be valid; inspect its latest Source Run and the feed directly |
| The same publication appears twice | Mark one `Duplicate`; retain both until identity rules are checked |
| An archived organization still runs | Confirm **Active** is off on the Organization and restart the next collection |

## Safety Rules

- The bot never approves or publishes an Item.
- Missing source facts remain blank; the bot does not invent them.
- Human editorial changes are not silently overwritten.
- Archiving configuration preserves history.
- Credentials belong in environment secrets, never Airtable fields or Git.
