"""CSV-based storage for organizations and events."""

import csv
from pathlib import Path
from datetime import date, datetime

from abundroid.models import Event, Organization
from abundroid.uid import content_hash


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
        - If uid not present: append row with status "Needs Review", first_seen and last_seen = today,
          plus Phase 2 fields: source_hash, topics, possible_duplicate_of, changed="", possibly_cancelled=""
        - If present: update last_seen, clear possibly_cancelled, check for content changes, preserve human edits

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
                # Already exists: Rule B - update last_seen, clear possibly_cancelled, check for changes
                row = existing_rows[uid]
                row["last_seen"] = today
                row["possibly_cancelled"] = ""

                # Check for content changes
                new_hash = content_hash(event)
                stored_hash = row.get("source_hash", "")
                if stored_hash and stored_hash != new_hash:
                    # Content changed and we had a stored hash
                    row["changed"] = "yes"
                    row["source_hash"] = new_hash
                elif not stored_hash:
                    # Backfill source_hash for legacy rows (don't set changed)
                    row["source_hash"] = new_hash

                seen_count += 1
            else:
                # New event: Rule A - set all Phase 2 fields
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
                    "topics": "; ".join(event.topics),
                    "possible_duplicate_of": event.possible_duplicate_of,
                    "source_hash": content_hash(event),
                    "changed": "",
                    "possibly_cancelled": "",
                    "status": "Needs Review",
                    "first_seen": today,
                    "last_seen": today,
                }
                existing_rows[uid] = new_row
                new_count += 1

            seen_in_batch.add(uid)

        # Write all rows back - Rule C: use restval for missing columns
        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
            writer.writeheader()
            for row in existing_rows.values():
                writer.writerow(row)

        return {"new": new_count, "seen": seen_count}

    def flag_missing(self, organizer: str, source_url: str, present_uids: set[str]) -> int:
        """
        Flag likely-cancelled events.

        For each existing row where:
        - row organizer == organizer
        - row source_url == source_url
        - row uid not in present_uids
        - row status is "Needs Review" or "Approved"
        - row start is non-empty AND datetime.fromisoformat(start).date() > date.today()

        Sets possibly_cancelled = "yes" and persists the file.
        Returns the count flagged.
        Rows with blank start are never flagged.
        """
        if not self.path.exists():
            return 0

        count = 0
        rows_to_write = []

        with open(self.path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows_to_write = list(reader)

        today = date.today()

        for row in rows_to_write:
            if (row.get("organizer", "") == organizer and
                row.get("source_url", "") == source_url and
                row.get("uid", "") not in present_uids and
                row.get("status", "") in ("Needs Review", "Approved")):

                start_str = row.get("start", "").strip()
                if start_str:
                    try:
                        start_dt = datetime.fromisoformat(start_str)
                        if start_dt.date() > today:
                            row["possibly_cancelled"] = "yes"
                            count += 1
                    except (ValueError, TypeError):
                        # Unparseable start: skip
                        pass

        # Write all rows back
        fieldnames = [
            "uid", "title", "organizer", "url", "start", "end",
            "location", "description", "source_url", "topics",
            "possible_duplicate_of", "status", "changed",
            "possibly_cancelled", "source_hash", "first_seen", "last_seen"
        ]
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
            writer.writeheader()
            for row in rows_to_write:
                writer.writerow(row)

        return count
