"""Core data objects shared by adapters, stores, and the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Organization:
    """A monitored source, mirroring one row of the Organizations table."""

    name: str
    events_url: str
    source_type: str  # "ical" | "rss" (more types in later phases)
    website: str = ""
    active: bool = True
    notes: str = ""


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
