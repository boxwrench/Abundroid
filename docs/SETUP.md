# Setting Up and Operating Abundroid

This guide has two audiences:

- **Technical deployer:** installs Abundroid, builds the Airtable base and
  Interface, stores credentials, and starts collection.
- **Daily operator:** manages Organizations and Sources, reviews Items, and
  checks Source health in the Airtable Interface without using a terminal.

## What Abundroid Does

Abundroid checks approved RSS or Atom feeds and adds new publications to an
Airtable review queue. Airtable uses these terms:

| Word | Meaning |
|---|---|
| Organization | A publisher being tracked |
| Source | One RSS or Atom feed belonging to that publisher |
| Item | One article, post, update, announcement, report, or scheduled item |
| Source Run | The result of checking one Source |
| Active | Include this Organization or Source in collection |
| Stage | Approved, candidate, or archived Organization state |

Daily operators edit friendly fields. They do not edit IDs, hashes, or
first/last-seen dates; those fields let the collector recognize an Item later.

## One-Time Technical Deployment

Complete terminal steps on the computer that will run collection. Browser-based
Airtable setup may happen on another computer. Run every terminal command from
the repository root: the `Abundroid` folder containing `pyproject.toml`, `src`,
and `docs`.

### 1. Install Abundroid

Follow only the subsection for your operating system. Windows uses `python` and
`.venv\Scripts`; Ubuntu uses `python3` and `.venv/bin`.

#### Windows 11

Install [Git](https://git-scm.com/downloads) and Python 3.11 or newer. Open
**Windows PowerShell** and verify them:

```powershell
git --version
python --version
```

Choose a parent folder. This example uses `C:\GitHub`:

```powershell
New-Item -ItemType Directory -Force C:\GitHub
Set-Location C:\GitHub
git clone https://github.com/boxwrench/Abundroid.git
Set-Location .\Abundroid
Test-Path .\pyproject.toml
```

The last command must print `True`. If the repository is already cloned, skip
`git clone` and use `Set-Location` to enter the existing folder.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

#### Ubuntu 24.04

Open **Terminal** and install the prerequisites:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ca-certificates nano
git --version
python3 --version
```

`python3 --version` must report 3.11 or newer. Ubuntu may not provide a command
named `python`; that is normal. Use `python3` and do not install an alias.

Choose a parent folder. This example uses `~/projects`:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/boxwrench/Abundroid.git
cd Abundroid
test -f pyproject.toml && echo "Repository root confirmed"
```

If the repository is already cloned, skip `git clone` and `cd` into the
existing folder.

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
./.venv/bin/python -m pytest
```

All tests should pass. On macOS, use the Ubuntu `.venv/bin` paths after
installing Python 3.11 or newer and Git with your package manager.

### 2. Test Collection Locally

Without Airtable credentials, Abundroid reads `data/sources.csv` and writes
`output/items.csv`.

A **feed** is a machine-readable list of a publisher's latest items, offered at a
fixed web address in RSS or Atom format. It is not the publisher's normal
homepage. To find one:

1. Look for a **Feed**, **RSS**, or **Subscribe** link on the publisher's site,
   often in the footer or on a subscribe page.
2. If none is visible, add `/feed/` to the site address and open it in a
   browser. Many sites, including WordPress and Substack publications, answer
   there.
3. A working feed opens as plain XML text beginning with `<?xml` or `<rss`, not
   as a styled web page.

For example, the Niskanen Center journal **Hypertext** has the homepage
`https://hypertext.niskanencenter.org`, and its feed is
`https://hypertext.niskanencenter.org/feed/`.

Open `data/sources.csv` in a text editor. Keep the header, replace the example
row with a real feed, and set `active` to `true`. Put the feed address in the
`url` column, not the homepage:

```csv
organization,name,url,format,default_kind,active,notes
Hypertext,Hypertext journal feed,https://hypertext.niskanencenter.org/feed/,rss,article,true,
```

Windows:

```powershell
.\.venv\Scripts\abundroid.exe collect
```

Ubuntu or macOS:

```bash
./.venv/bin/abundroid collect
```

The Source should report `ok`. Confirm that `output/items.csv` and
`output/source_runs.csv` exist. Run the command again; the second summary must
report `0 new`, and `items.csv` must not gain duplicate rows.

### 3. Build the Airtable Base and Interface

#### Automated: `abundroid setup` (recommended)

`abundroid setup` calls the Airtable metadata API to create the base, all five
tables, every field, every select option, and the Hypertext example
Organization and Source, then writes the resulting base ID into `.env`. It
does **not** create views, the Interface, or the runtime access token; those
three steps stay manual (sections 9 through 12 of the
[Airtable build guide](airtable-schema.md)).

1. Open Airtable's [Developer Hub token page](https://airtable.com/create/tokens)
   and create a one-time token scoped to `schema.bases:write`, with access to
   the workspace that should own Abundroid. The base does not exist yet, so
   you cannot scope the token to a base. Copy the value beginning with `pat`.
2. Find your workspace ID: open Airtable, select the workspace, and read the
   `wsp...` segment from the browser address bar.
3. Export both values and run `setup`. Do not put `AIRTABLE_SETUP_TOKEN` in
   `.env`; it is a one-time credential, not the runtime one.

```powershell
# Windows
$env:AIRTABLE_SETUP_TOKEN = "pat_one_time_schema_token"
$env:AIRTABLE_WORKSPACE_ID = "wsp_your_workspace"
.\.venv\Scripts\abundroid.exe setup
```

```bash
# Ubuntu or macOS
export AIRTABLE_SETUP_TOKEN=pat_one_time_schema_token
export AIRTABLE_WORKSPACE_ID=wsp_your_workspace
./.venv/bin/abundroid setup
```

`setup` prints the created base ID and confirms it wrote `AIRTABLE_BASE_ID` to
`.env`. Pass `--no-seed` to skip the Hypertext example Organization and
Source. Continue with sections 9 through 12 of the
[Airtable build guide](airtable-schema.md#9-add-the-minimum-saved-views) to
build the nine saved views, publish the three-page **Abundroid Admin**
Interface, and create the runtime access token. Revoke
`AIRTABLE_SETUP_TOKEN` once setup succeeds; it is no longer needed.

#### Manual fallback

Prefer to build the base by hand, or want to understand the schema before
automating it? Open
[Build the Abundroid Airtable Base](airtable-schema.md) in a second browser
tab and follow sections 1 through 11 in order. That guide explains Airtable
terminology and every click required to:

1. Create a blank base named `Abundroid`.
2. Create exactly five tables: **Organizations**, **Sources**, **Items**,
   **Topics**, and **Source Runs**.
3. Configure every primary field, normal field, select option, date setting,
   linked-record field, and lookup field.
4. Create the nine minimum saved views.
5. Build, publish, and test the three-page **Abundroid Admin** Interface.

Do not continue until the guide's field and Interface checkpoints pass. Field
names, capitalization, and spaces must match exactly.

### 4. Create the Airtable Token and Find the Base ID

If you ran `abundroid setup`, the base ID is already written to `.env`; follow
only section 12 of the
[Airtable build guide](airtable-schema.md#12-create-the-airtable-personal-access-token)
to create the runtime token. If you built the base manually, follow sections
12 and 13. Either way you will finish with:

- A secret personal access token beginning with `pat`.
- A base ID beginning with `app`.

The token must have only `data.records:read` and `data.records:write`, with
access restricted to the Abundroid base. Store the token in a password manager.
Do not put it in Airtable records, chat, screenshots, or Git.

### 5. Configure `.env`

If `abundroid setup` already created `.env` for you, skip the copy step below
and open the existing file directly; `AIRTABLE_BASE_ID` is already set and you
only need to add `AIRTABLE_API_KEY`.

On Windows, from the repository root:

```powershell
Copy-Item .\.env.example .\.env
notepad .\.env
```

On Ubuntu:

```bash
cp .env.example .env
nano .env
```

In nano, press `Ctrl+O`, Enter to save, then `Ctrl+X` to close. Set the two
values without quotes:

```dotenv
AIRTABLE_API_KEY=pat_your_token
AIRTABLE_BASE_ID=app_your_base_id
```

Leave the table-name overrides commented because the guide uses the default
names. Abundroid loads `.env` from the current directory, so run it from the
repository root.

Confirm Git ignores the credential file:

```bash
git status --short
```

The output must not include `.env`. Stop if it does.

### 6. Add the First Organization and Source

In the Airtable **Organizations** table, create one row:

| Field | Value |
|---|---|
| Name | Publisher name |
| Website | Publisher homepage |
| Active | Checked |
| Stage | `Approved` |

In **Sources**, create one row:

| Field | Value |
|---|---|
| Name | Friendly label such as `News feed` |
| Organization | Select the Organization above |
| URL | Real public RSS or Atom URL |
| Format | `rss` |
| Default Kind | Usually `article`, `post`, or `update` |
| Active | Checked |

Use `rss` in **Format** for an Atom feed too. Abundroid handles RSS and Atom
with the same parser, so Airtable does not need an `atom` option.

**Organization Name** must fill itself after you select the Organization. If it
stays blank, repair the Lookup field before continuing. Topics may remain empty.

### 7. Preview and Run Live Collection

Preview reads Airtable and fetches the feed but writes no Items or Source Runs.

Windows:

```powershell
.\.venv\Scripts\abundroid.exe collect --dry-run
```

Ubuntu or macOS:

```bash
./.venv/bin/abundroid collect --dry-run
```

The Airtable Source name should report `ok`, and parsed Items should print in
the terminal. If the local CSV Source name appears instead, confirm `.env` is in
the repository root and both values are present.

The exact content varies by feed, but a successful preview has this shape:

```text
[UPDATE] Housing reform update
  Example Organization | Jul 14, 2026
  A short description supplied by the feed.
  Link: https://example.org/posts/1

Example News: ok, 1 found
Totals: 1 found, 1 new, 0 seen
```

Run the write path:

```powershell
# Windows
.\.venv\Scripts\abundroid.exe collect
```

```bash
# Ubuntu or macOS
./.venv/bin/abundroid collect
```

Confirm:

1. The command reports the Source as `ok`.
2. **Items** contains records with **Status = Needs Review**.
3. **Source Runs** contains one record linked to the Source.
4. The Source Run Result is `Working` or `No recent items`.
5. Item UID, Source Hash, First Seen, and Last Seen are filled.

Run collection again. The Item count must not increase for unchanged feed
entries, the terminal must report `0 new`, and one new Source Run must appear.

Edit one Item's Title, Summary, Topics, and Status in Airtable. Run collection a
third time and confirm those human edits remain unchanged.

### 8. Test Failure and Pause Behavior

Add a second active Source linked to the same Organization with an invalid URL.
Run collection and confirm:

- The command reports the broken Source and returns a failure status.
- The working Source is still collected and retained.
- The broken Source gets a **Needs attention** Source Run with an Error.

Correct or deactivate that Source. Create another Source without an Organization
link and confirm it is skipped. Unlinked, inactive, and Organization-paused
Sources are not fetched and do not get a new Source Run.

### 9. Test the Operator Interface

Open the published **Abundroid Admin** Interface rather than the raw tables.
Have someone who did not build it:

1. Add and edit an Organization.
2. Pause, restore, and archive it.
3. Open Review and confirm the title, publisher, date, description, and original
   link can be scanned without opening a raw table; then edit the Item.
4. Open Source Health and identify the broken Source and its error.

Record every task that requires a raw table, terminal, or deployer explanation.
Those are product validation findings to fix before automation.

## Daily Operation

### Add an Organization

1. Open the **Organizations** Interface page.
2. Click **Add record**.
3. Enter Name and Website.
4. Check Active and set Stage to `Approved` when monitoring should begin.
5. Add a related Source with its feed URL, `rss` format, Default Kind, and
   Active checked.

An approved Organization without an active Source is safely stored but produces
no Items.

### Pause, Archive, and Restore

- **Pause** clears Organization Active and temporarily stops all its Sources.
- Clearing Active on one Source pauses only that endpoint.
- **Archive** clears Active and sets Stage to `Archived`; collected Items and
  Source Run history remain.
- **Restore** sets Stage to `Approved` and checks Active. A Source that was
  individually paused remains paused.

Use Archive instead of deleting records. Permanent deletion is an administrator
task outside the normal operator Interface.

### Review Items

1. Open **Review**.
2. Scan the title, publisher, date, kind, topics, and Summary.
3. Open Canonical URL and compare the original publication with the Item. A
   missing original link is a Source-quality issue to report to the deployer;
   Source URL points to the feed itself and is intentionally hidden.
4. Correct Title, Kind, Published At, Author, Summary, or Topics if necessary.
5. Set Status to `Approved`, `Rejected`, or `Duplicate`.
6. Add Reviewer Notes when another reviewer needs context.

Do not edit Item UID, Source Item ID, Source Hash, First Seen, or Last Seen.

### Check Source Health

Read the newest Source Run together with the Source's Active value:

| State | Meaning | Action |
|---|---|---|
| Working | The fetch succeeded and returned Items | None |
| No recent items | The fetch succeeded but returned no Items | Usually none |
| Needs attention | Fetching or parsing failed | Open the newest run and inspect Error |
| Paused | Source or Organization Active is unchecked, or Source is unlinked | Resume only if monitoring should continue |

One broken Source does not stop working Sources, but the overall command returns
a failure status so the problem is visible.

## Troubleshooting

| Symptom | Action |
|---|---|
| Ubuntu reports `python: command not found` | Use `python3`; after creating the environment use `./.venv/bin/python` |
| `abundroid: command not found` | Use `.\.venv\Scripts\abundroid.exe` on Windows or `./.venv/bin/abundroid` on Ubuntu from the repository root |
| Collection uses CSV after `.env` exists | Confirm the current folder contains `.env` and both credential values are set without quotes |
| Airtable returns `401` or `403` | Check token scopes, base access, and your permission in the base |
| Airtable reports an unknown field | Compare capitalization, spacing, field types, and select choices with `airtable-schema.md` |
| A Source is skipped | Confirm its Organization is Approved and Active, the Source is Active, and the Organization link exists |
| Feed succeeds but produces no Items | Inspect the feed directly and the newest Source Run; an empty feed can be valid |
| Duplicate publication appears | Mark one Duplicate and inspect the Source IDs and URLs before changing identity rules |

## Safety Rules

- The collector never approves or publishes an Item.
- Missing source facts remain blank; the collector does not invent them.
- Human editorial changes are not silently overwritten.
- Archiving preserves collected history.
- Credentials belong in `.env` or a deployment secret store, never Airtable or
  Git.
