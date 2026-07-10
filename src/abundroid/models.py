"""Core data objects shared by adapters, stores, and the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Organization:
    """A monitored source, mirroring one row of the Organizations table."""

    name: str
    events_url: str
    source_type: str  # "ical" | "rss" | "jsonld" (more types in later phases)
    website: str = ""
    active: bool = True
    notes: str = ""


@dataclass
class Source:
    '''One monitored endpoint belonging to an organization.'''

    organization: str
    name: str
    url: str
    format: str  # rss | jsonld | html | ical
    default_kind: str = 'other'
    active: bool = True
    notes: str = ''


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
class Event:
    """One normalized event, before or after review."""

    title: str
    organizer: str
    url: str = ""  # registration / event page URL
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    description: str = ""
    source_url: str = ""  # the feed or page this was pulled from
    uid: str = ""  # deterministic identity, computed by abundroid.uid
    topics: list[str] = field(default_factory=list)  # bot-suggested topic names
    possible_duplicate_of: str = ""  # uid of a suspected cross-org twin


@dataclass
class Topic:
    """One row of the Topics table — a tagging rule, not just a label."""

    name: str
    keywords: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    active: bool = True
