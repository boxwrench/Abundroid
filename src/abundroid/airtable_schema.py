"""Declarative Airtable schema for the Abundroid base (single source of truth)."""

from __future__ import annotations

BASE_NAME = "Abundroid"

_CHECKBOX = {"icon": "check", "color": "greenBright"}
_DATE_ONLY = {"dateFormat": {"name": "iso"}}
_DATE_TIME = {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "utc"}
_KIND_CHOICES = [
    {"name": "article"}, {"name": "post"}, {"name": "update"},
    {"name": "announcement"}, {"name": "report"}, {"name": "event"}, {"name": "other"},
]
_PRIORITY_CHOICES = [{"name": "High"}, {"name": "Medium"}, {"name": "Low"}]


def _select(choices):
    return {"choices": choices}


SIMPLE_TABLES = [
    {
        "name": "Organizations",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "Website", "type": "url"},
            {"name": "Category", "type": "multipleSelects", "options": _select([])},
            {"name": "Priority", "type": "singleSelect", "options": _select(_PRIORITY_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Stage", "type": "singleSelect", "options": _select([
                {"name": "Approved"}, {"name": "Watchlist"},
                {"name": "Suggested"}, {"name": "Archived"},
            ])},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Sources",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "URL", "type": "url"},
            {"name": "Format", "type": "singleSelect", "options": _select([{"name": "rss"}])},
            {"name": "Default Kind", "type": "singleSelect", "options": _select(_KIND_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Items",
        "fields": [
            {"name": "Item UID", "type": "singleLineText"},
            {"name": "Source Item ID", "type": "singleLineText"},
            {"name": "Canonical URL", "type": "url"},
            {"name": "Source URL", "type": "url"},
            {"name": "Title", "type": "singleLineText"},
            {"name": "Publisher", "type": "singleLineText"},
            {"name": "Kind", "type": "singleSelect", "options": _select(_KIND_CHOICES)},
            {"name": "Published At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Author", "type": "singleLineText"},
            {"name": "Summary", "type": "multilineText"},
            {"name": "Topics", "type": "multipleSelects", "options": _select([])},
            {"name": "Status", "type": "singleSelect", "options": _select([
                {"name": "Needs Review"}, {"name": "Approved"}, {"name": "Rejected"},
                {"name": "Duplicate"}, {"name": "Published"}, {"name": "Archived"},
            ])},
            {"name": "Reviewer Notes", "type": "multilineText"},
            {"name": "Scheduled Start", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Scheduled End", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Location", "type": "singleLineText"},
            {"name": "Source Hash", "type": "singleLineText"},
            {"name": "First Seen", "type": "date", "options": _DATE_ONLY},
            {"name": "Last Seen", "type": "date", "options": _DATE_ONLY},
            {"name": "Changed", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Possible Duplicate Of", "type": "singleLineText"},
        ],
    },
    {
        "name": "Topics",
        "fields": [
            {"name": "Topic", "type": "singleLineText"},
            {"name": "Keywords", "type": "multilineText"},
            {"name": "Aliases", "type": "multilineText"},
            {"name": "Exclusions", "type": "multilineText"},
            {"name": "Priority", "type": "singleSelect", "options": _select(_PRIORITY_CHOICES)},
            {"name": "Active", "type": "checkbox", "options": _CHECKBOX},
            {"name": "Notes", "type": "multilineText"},
        ],
    },
    {
        "name": "Source Runs",
        "fields": [
            {"name": "Run ID", "type": "singleLineText"},
            {"name": "Started At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Finished At", "type": "dateTime", "options": _DATE_TIME},
            {"name": "Result", "type": "singleSelect", "options": _select([
                {"name": "Working"}, {"name": "No recent items"}, {"name": "Needs attention"},
            ])},
            {"name": "Items Found", "type": "number", "options": {"precision": 0}},
            {"name": "HTTP Status", "type": "number", "options": {"precision": 0}},
            {"name": "Error", "type": "multilineText"},
        ],
    },
]

LINK_FIELDS = [
    {"table": "Sources", "name": "Organization", "linked_table": "Organizations", "single": True},
    {"table": "Source Runs", "name": "Source", "linked_table": "Sources", "single": True},
]

LOOKUP_FIELDS = [
    {
        "table": "Sources",
        "name": "Organization Name",
        "via_link_field": "Organization",
        "linked_table": "Organizations",
        "linked_field": "Name",
    },
]

SEED_ORGANIZATION = {
    "Name": "Hypertext",
    "Website": "https://hypertext.niskanencenter.org",
    "Active": True,
    "Stage": "Approved",
}

SEED_SOURCE = {
    "Name": "Hypertext journal feed",
    "URL": "https://hypertext.niskanencenter.org/feed/",
    "Format": "rss",
    "Default Kind": "article",
    "Active": True,
}
