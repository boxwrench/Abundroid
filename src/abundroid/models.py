"""Core data objects shared by adapters, stores, and the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Source:
    '''One monitored endpoint belonging to an organization.'''

    organization: str
    name: str
    url: str
    format: str  # rss
    default_kind: str = 'other'
    active: bool = True
    notes: str = ''
    record_id: str = ''


@dataclass
class Item:
    '''One publication or event collected from a monitored source.'''

    title: str
    publisher: str
    kind: str = 'other'
    uid: str = ''
    source_item_id: str = ''
    canonical_url: str = ''
    source_url: str = ''
    published_at: datetime | None = None
    author: str = ''
    summary: str = ''
    topics: list[str] = field(default_factory=list)
    status: str = 'Needs Review'
    reviewer_notes: str = ''
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    location: str = ''
    source_hash: str = ''
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    changed: bool = False
    possible_duplicate_of: str = ''

@dataclass
class Topic:
    """One row of the Topics table: a tagging rule, not just a label."""

    name: str
    keywords: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    active: bool = True


@dataclass
class SourceRun:
    """One check or collection attempt for a Source."""

    run_id: str
    source_id: str
    source_name: str
    source_url: str
    start_time: datetime
    finish_time: datetime
    result: str  # "success" | "failure"
    items_found: int
    items_new: int = 0
    items_seen: int = 0
    http_status: int | None = None
    error: str = ""

    def __post_init__(self):
        if self.start_time.utcoffset() is None or self.finish_time.utcoffset() is None:
            raise ValueError("Timestamps must be timezone-aware.")
        if self.finish_time < self.start_time:
            raise ValueError("Finish time cannot be earlier than start time.")
        if self.result not in {"success", "failure"}:
            raise ValueError("Result must be success or failure.")
        if min(self.items_found, self.items_new, self.items_seen) < 0:
            raise ValueError("Item counts cannot be negative.")
        if self.result == "success" and self.error:
            raise ValueError("Successful runs cannot contain an error.")

    def derive_health(self) -> str:
        """Translate an attempted run into its operator-facing result."""
        if self.result == "failure":
            return "Needs attention"
        if self.items_found == 0:
            return "No recent items"
        return "Working"
