"""CSV-based storage for organizations and events."""

import csv
from pathlib import Path
from datetime import date

from abundroid.models import Event, Organization


def load_organizations(path: str | Path) -> list[Organization]:
    """
    Load organizations from a CSV file.

    Columns: name, website, events_url, source_type, active, notes
    - active parses "yes"/"true"/"1" (case-insensitive, stripped) as True
    - Skip rows where name or events_url is empty
    """
    orgs = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            events_url = (row.get("events_url") or "").strip()

            # Skip if name or events_url is empty
            if not name or not events_url:
                continue

            # Parse active flag
            active_str = (row.get("active") or "").strip().lower()
            active = active_str in ("yes", "true", "1")

            org = Organization(
                name=name,
                website=(row.get("website") or "").strip(),
                events_url=events_url,
                source_type=(row.get("source_type") or "").strip(),
                active=active,
                notes=(row.get("notes") or "").strip(),
            )
            orgs.append(org)

    return orgs


class CsvEventStore:
    """Store events in a CSV file."""

    def __init__(self, path: str | Path):
        """Initialize with path to events CSV."""
        self.path = Path(path)

    def upsert(self, events: list[Event]) -> dict:
        """
        Upsert events into the CSV.

        For each event:
        - If uid not present: append row with status "Needs Review", first_seen and last_seen = today
        - If present: update only last_seen, preserving other columns

        Returns {"new": int, "seen": int}
        """
        # Create parent directory if missing
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing events keyed by uid
        existing = {}
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row.get("uid", "")
                    if uid:
                        existing[uid] = row

        # Track uids we've seen in this batch (for dedup)
        seen_in_batch = set()
        new_count = 0
        seen_count = 0

        # Process each event
        rows_to_write = []
        if self.path.exists():
            # Read existing rows first
            with open(self.path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows_to_write = list(reader)

        today = date.today().isoformat()

        # Build a map of existing rows by uid for easier updating
        existing_rows = {row.get("uid", ""): row for row in rows_to_write if row.get("uid", "")}

        # Process incoming events
        for event in events:
            uid = event.uid
            if uid in seen_in_batch:
                # Duplicate in batch: seen
                seen_count += 1
            elif uid in existing_rows:
                # Already exists: update last_seen only
                existing_rows[uid]["last_seen"] = today
                seen_count += 1
            else:
                # New event: append new row
                new_row = {
                    "uid": uid,
                    "title": event.title,
                    "organizer": event.organizer,
                    "url": event.url or "",
                    "start": event.start.isoformat() if event.start else "",
                    "end": event.end.isoformat() if event.end else "",
                    "location": event.location or "",
                    "description": event.description or "",
                    "source_url": event.source_url or "",
                    "status": "Needs Review",
                    "first_seen": today,
                    "last_seen": today,
                }
                existing_rows[uid] = new_row
                new_count += 1

            seen_in_batch.add(uid)

        # Write all rows back
        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "status",
            "first_seen", "last_seen"
        ]
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in existing_rows.values():
                writer.writerow(row)

        return {"new": new_count, "seen": seen_count}
