# Build the Abundroid Airtable Base

> You can create everything in sections 1-8 automatically with
> `abundroid setup` (see [SETUP.md](SETUP.md)). Follow the manual steps below
> only if you prefer to build by hand or need to understand the schema.
> Sections 9-12 (views, Interface, token) are manual either way.

This is a click-by-click guide for someone who has not used Airtable before.
Use Airtable in a desktop browser. Create a free Airtable account if you do not
already have one, then sign in to an account that can create a base. You need
**Owner** or **Creator** permission to configure fields and the Interface.

Useful Airtable terms:

| Term | Meaning in this guide |
|---|---|
| Workspace | The folder-like area that owns the base |
| Base | The complete Abundroid database |
| Table | One tab of related records, similar to a spreadsheet sheet |
| Field | A column with a configured data type |
| Record | One row |
| Primary field | The first column; Airtable uses it to name each record |
| View | A saved filter/sort of one table |
| Interface | The simplified app that daily operators use |

Airtable's official documentation calls the first column the primary field and
does not allow it to be deleted or hidden. Create the five tables before adding
linked fields so every link target already exists. See Airtable's
[table guide](https://support.airtable.com/docs/tables-overview),
[field guide](https://support.airtable.com/docs/airtable-field-actions), and
[primary-field guide](https://support.airtable.com/docs/the-primary-field) if a
control has moved.

## 1. Create a Blank Base

1. Open [airtable.com](https://airtable.com/). Create a free account if needed,
   then sign in.
2. On the Home screen, select the workspace that should own Abundroid.
3. Click **+ Create** and choose the blank or start-from-scratch base option.
   Do not import a spreadsheet or choose a template.
4. Name the base `Abundroid`.
5. Open the base. Airtable creates one table with sample fields and rows.
6. Delete the sample rows.
7. Open the first table's menu using the down arrow beside its name, choose
   **Rename table**, and name it `Organizations`.

## 2. Create All Five Tables

Keep the existing **Organizations** table. Create four more:

1. Click **+ Add or import** beside the table tabs.
2. Choose the blank-table option.
3. Name the table and save it.
4. Repeat until the tabs are exactly:

```text
Organizations
Sources
Items
Topics
Source Runs
```

Delete any sample rows Airtable added. Names, capitalization, and spaces must
match exactly because the collector addresses tables and fields by name.

## 3. Learn the Two Field Actions

You will repeat these actions throughout the build:

**Edit the primary field:** click the first column header, choose **Edit field**,
set its name and type, then click **Save**.

**Add another field:** click the **+** at the far right of the column headers,
enter the field name, select its type, configure its settings, then click
**Create field**.

Delete unused sample columns. Do not create fields that are not listed below.

## 4. Configure Organizations

Open **Organizations**. Edit the first column, then add the remaining fields.
Do not manually add **Sources**; Airtable creates that reciprocal field when
you configure the link from the Sources table in the next section.

| Field | Airtable field type | Settings |
|---|---|---|
| Name | Single line text, primary | Required publisher name |
| Website | URL | Public homepage, not the feed URL |
| Category | Multiple select | Leave choices empty until needed |
| Priority | Single select | Add `High`, `Medium`, `Low` |
| Active | Checkbox | Checked means collection is allowed |
| Stage | Single select | Add `Approved`, `Watchlist`, `Suggested`, `Archived` |
| Notes | Long text | Internal operator notes |

Checkpoint: the first column is **Name**, and there are seven configured
fields. **Sources** will appear automatically later.

## 5. Configure Sources and Its Organization Link

Open **Sources** and create these fields in order:

| Field | Airtable field type | Settings |
|---|---|---|
| Name | Single line text, primary | Friendly label such as `News feed` |
| Organization | Link to another record | Link to **Organizations**; turn off linking to multiple records |
| Organization Name | Lookup | Source: **Organization**; field to look up: **Name** |
| URL | URL | Exact public RSS or Atom endpoint, or an iCalendar (.ics) URL |
| Format | Single select | Add `rss` and `ical`. Use `rss` for RSS and Atom; use `ical` for iCalendar (.ics) event calendars |
| Default Kind | Single select | Add `article`, `post`, `update`, `announcement`, `report`, `event`, `other` |
| Active | Checkbox | Checked means this Source may run |
| Notes | Long text | Setup or troubleshooting notes |

Use `rss` for both RSS and Atom feed URLs. Abundroid uses the same parser for
both feed standards, so there is intentionally no separate `atom` choice.

To create **Organization**:

1. Add a field and choose **Link to another record**.
2. Select **Organizations** as the linked table.
3. Disable the option that allows linking to multiple records.
4. Name the field `Organization` and create it.
5. Return briefly to **Organizations** and confirm Airtable automatically added
   a reciprocal field named **Sources**. Do not create a second one.

To create **Organization Name**, first finish the linked field above. Then add a
**Lookup** field, select **Organization** as the lookup source, and select
**Name** as the value to copy. Lookup fields require an existing linked-record
field; Airtable documents that sequence in its
[lookup guide](https://support.airtable.com/docs/lookup-field-overview).

## 6. Configure Items

Open **Items**. These records are created by Abundroid and reviewed by people.

| Field | Airtable field type | Settings |
|---|---|---|
| Item UID | Single line text, primary | Bot-owned stable identifier |
| Source Item ID | Single line text | Bot-owned source identifier |
| Canonical URL | URL | Preferred public publication link |
| Source URL | URL | Feed used to find the Item |
| Title | Single line text | Reviewer may edit |
| Publisher | Single line text | Organization name snapshot |
| Kind | Single select | `article`, `post`, `update`, `announcement`, `report`, `event`, `other` |
| Published At | Date | Turn on **Include time** |
| Author | Single line text | Reviewer may edit |
| Summary | Long text | Reviewer may edit |
| Topics | Multiple select | Choices may be added later |
| Status | Single select | `Needs Review`, `Approved`, `Rejected`, `Duplicate`, `Published`, `Archived` |
| Reviewer Notes | Long text | Human-only notes |
| Scheduled Start | Date | Turn on **Include time** |
| Scheduled End | Date | Turn on **Include time** |
| Location | Single line text | Optional scheduled-item location |
| Source Hash | Single line text | Bot-owned change fingerprint |
| First Seen | Date | Date only; leave **Include time** off |
| Last Seen | Date | Date only; leave **Include time** off |
| Changed | Checkbox | Bot checks this after source facts change |
| Possible Duplicate Of | Single line text | Suspected matching Item UID |

Use the same date format and timezone display for all date-and-time fields. Do
not make **Item UID** an autonumber; Abundroid supplies it.

## 7. Configure Topics

Open **Topics**:

| Field | Airtable field type | Settings |
|---|---|---|
| Topic | Single line text, primary | Topic label shown to reviewers |
| Keywords | Long text | Comma-separated matching terms |
| Aliases | Long text | Comma-separated alternate terms |
| Exclusions | Long text | Comma-separated terms that veto a match |
| Priority | Single select | Add `High`, `Medium`, `Low` |
| Active | Checkbox | Only checked Topics are suggested |
| Notes | Long text | Examples and guidance |

Topics are optional for the first collection test. When you add one later, use
the same spelling for its **Topic** value and the matching **Items -> Topics**
multiple-select choice.

## 8. Configure Source Runs and Its Source Link

Open **Source Runs**:

| Field | Airtable field type | Settings |
|---|---|---|
| Run ID | Single line text, primary | Bot-owned unique attempt ID |
| Source | Link to another record | Link to **Sources**; turn off linking to multiple records |
| Started At | Date | Turn on **Include time** |
| Finished At | Date | Turn on **Include time** |
| Result | Single select | Add `Working`, `No recent items`, `Needs attention` |
| Items Found | Number | Integer, precision `0` |
| HTTP Status | Number | Integer, precision `0` |
| Error | Long text | Empty on success; actionable text on failure |

Creating the **Source** link automatically adds a reciprocal **Source Runs**
field to **Sources**. Keep it; the Source Health Interface uses it.

## 9. Add the Minimum Saved Views

A view is a saved filter and sort over a table; it does not copy records. To
create one, open the table, open the views sidebar if necessary, click
**+ Create new**, choose **Grid**, name the view, and choose **Collaborative**.
Then use **Filter**, **Sort**, and **Hide fields**. Airtable documents these
controls in its [views guide](https://support.airtable.com/docs/en/getting-started-with-airtable-views).

Create only these views for the first deployment:

| Table | View | Filter | Sort |
|---|---|---|---|
| Organizations | Active Organizations | `Stage is Approved` AND `Active is checked` | Name A-Z |
| Organizations | Candidates | `Stage is Watchlist` OR `Stage is Suggested` | Priority, then Name |
| Organizations | Archived Organizations | `Stage is Archived` | Name A-Z |
| Sources | Active Sources | `Active is checked` | Organization Name, then Name |
| Sources | Sources Needing Setup | `URL is empty` OR `Format is empty` OR `Organization is empty` | Name A-Z |
| Sources | Paused Sources | `Active is unchecked` | Organization Name, then Name |
| Items | Review Queue | `Status is Needs Review` | Published At newest first |
| Items | Needs Re-review | `Changed is checked` OR `Possible Duplicate Of is not empty` | Last Seen newest first |
| Source Runs | Needs Attention | `Result is Needs attention` | Started At newest first |

Checkpoint: switch between views and confirm each one changes only filters and
sorting, not the underlying records.

## 10. Build the Abundroid Admin Interface

Interfaces give daily operators a smaller app instead of exposing raw tables.
Interface Designer and the **Update record** button are currently documented as
available on all Airtable plan types. Sharing an Interface separately from its
base requires a paid plan; on the Free plan, give each operator appropriate
access to the base as well. Airtable changes its UI over time, so if a named
control is missing, first check the selected layout and your **Owner** or
**Creator** permission, then compare the current
[Interface permissions guide](https://support.airtable.com/v1/docs/interface-designer-permissions)
and [Interface button guide](https://support.airtable.com/docs/using-buttons-in-interfaces).

1. Open the base and click **Interfaces** near the top.
2. For the first Interface, choose **Build it yourself**. If an Interface
   already exists, enter edit mode and click **+ New interface**.
3. Name it `Abundroid Admin`.
4. Create the three pages below. Start from a provided layout rather than a
   blank page; Airtable recommends layouts for first-time builders in its
   [layout guide](https://support.airtable.com/docs/adding-layouts-to-interfaces).

### Organizations Page

1. Add a **List** page using **Organizations** as the source table.
2. Filter it to `Stage is not Archived`.
3. Enable search and **Click into record details**.
4. Enable **Add records through a form**. Include Name, Website, Category,
   Priority, Active, Stage, and Notes in the form.
5. In the record detail, make those same fields editable and show the related
   **Sources** list. Keep configuration IDs out of the page.
6. Add three **Update record** buttons to the record detail:
   - `Pause`: set **Active** to unchecked.
   - `Archive`: set **Active** to unchecked and **Stage** to `Archived`.
   - `Restore`: set **Active** to checked and **Stage** to `Approved`.

Update-record buttons work on record detail/review layouts. In button settings,
choose **Update record**, click the field-action control, add each **Set field**
action, and optionally require confirmation for Archive. See Airtable's
[Interface button guide](https://support.airtable.com/docs/using-buttons-in-interfaces).

### Review Page

1. Add a **Record review** page using **Items** as the source table.
2. Filter it to `Status is Needs Review`.
3. Sort by **Published At**, newest first.
4. Treat the page as a publication report rather than a database record. Make
   **Title** the prominent heading. Place Publisher, Published At, Kind, Author,
   and Topics together as supporting information.
5. Show **Summary** as wrapped text, followed immediately by **Canonical URL**
   so the original publication is easy to open. Keep Status and Reviewer Notes
   near the review controls.
6. Show Changed and Possible Duplicate Of as attention indicators, not as the
   main content.
7. Make Title, Kind, Published At, Author, Summary, Topics, Status, and Reviewer
   Notes editable.
8. Hide Item UID, Source Item ID, Source URL, Source Hash, First Seen, and Last
   Seen from the normal review page. They may remain view-only in an
   administrator-only record detail.

### Source Health Page

1. Add a **List** page using **Sources** as the source table.
2. Show Name, Organization Name, URL, Active, Format, and Source Runs.
3. Enable **Click into record details**.
4. In record detail, show related **Source Runs** sorted by **Started At**,
   newest first. Show Result, Started At, Items Found, HTTP Status, and Error.
5. An unchecked Source or inactive Organization is paused even though no new
   Source Run is written for a skipped Source.

In each page's **User actions** settings, allow only the edits described above.
Airtable documents inline editing, record details, and add-record forms in its
[Interface permissions guide](https://support.airtable.com/v1/docs/interface-designer-permissions).

## 11. Publish and Test the Interface

Interface edits are saved while you build, but operators do not receive them
until you click **Publish**.

1. Click **Publish** and confirm.
2. Open the published Interface as the intended operator account.
3. Add a test Organization.
4. Open it, edit its Notes, click Pause, Restore, and Archive, and confirm the
   corresponding fields change.
5. Restore it before collection testing.
6. If a required control is missing, confirm the operator's permissions and the
   page's **User actions** settings before changing the schema.

## 12. Create the Airtable Personal Access Token

Abundroid reads and writes records; it does not create the schema through the
API.

1. Open Airtable's [Developer Hub token page](https://airtable.com/create/tokens).
2. Click **Create token**.
3. Name it `Abundroid collector`.
4. Click **+ Add a scope** and add `data.records:read`.
5. Add a second scope: `data.records:write`.
6. Under **Access**, click **+ Add a base** and select only the `Abundroid`
   base. Do not grant every workspace or base.
7. Create the token and copy the value beginning with `pat` into a password
   manager. Airtable shows it only once.
8. Never place the token in an Airtable field, chat message, screenshot, or Git
   commit.

Scopes and base access are separate settings; both are required. Airtable's
[token guide](https://support.airtable.com/v1/docs/creating-personal-access-tokens)
documents the current flow.

## 13. Find the Base ID

Open the base's data view and inspect the browser address. The segment beginning
with `app` is the base ID, for example:

```text
https://airtable.com/appAbCdEf12345678/...
                     ^^^^^^^^^^^^^^^^^
```

Copy only the `app...` segment. Airtable's
[ID guide](https://support.airtable.com/docs/finding-airtable-ids) shows the URL
formats. Keep the base ID with deployment configuration; it is not a substitute
for the secret token.

## Completion Checklist

- [ ] The base is named `Abundroid`.
- [ ] Exactly five tables exist with exact names.
- [ ] Every primary field and field type matches this guide.
- [ ] Sources links to one Organization and its lookup populates.
- [ ] Source Runs links to one Source.
- [ ] The nine minimum views exist with the documented filters.
- [ ] The three Interface pages exist and are published.
- [ ] Pause, Archive, and Restore update the expected fields.
- [ ] The token has only record read/write scopes and access to this base.
- [ ] The `pat...` token and `app...` base ID are ready for `.env` setup.
