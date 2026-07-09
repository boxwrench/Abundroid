"""Airtable-based storage for organizations and events."""

from datetime import date

from abundroid.models import Event, Organization


def load_organizations(table) -> list[Organization]:
    """
    Load organizations from an Airtable table.

    Args:
        table: pyairtable-compatible object with .all() returning
               [{"id": ..., "fields": {...}}, ...]

    Returns:
        List of Organization objects.
    """
    orgs = []
    for record in table.all():
        fields = record.get("fields", {})
        # Stage "Watchlist"/"Suggested" parks an org: humans are still deciding,
        # so the bot must not monitor it even if Active is checked.
        stage = fields.get("Stage", "Approved")
        org = Organization(
            name=fields.get("Name", ""),
            website=fields.get("Website", ""),
            events_url=fields.get("Events URL", ""),
            source_type=fields.get("Source Type", ""),
            active=fields.get("Active", False) and stage == "Approved",
            notes=fields.get("Notes", ""),
        )
        orgs.append(org)

    return orgs


class AirtableEventStore:
    """Store events in Airtable."""

    def __init__(self, table):
        """
        Initialize with a pyairtable table.

        Args:
            table: Any object with .all(), .create(fields: dict), .update(record_id, fields: dict)
        """
        self.table = table

    def upsert(self, events: list[Event]) -> dict:
        """
        Upsert events into Airtable.

        For each event:
        - If uid not present: create with Status "Needs Review", First Seen/Last Seen = today ISO
        - If present: update only {"Last Seen": today}

        Returns {"new": int, "seen": int}
        """
        # Load all existing records, map "Event UID" -> record id
        existing = {}
        for record in self.table.all():
            uid = record.get("fields", {}).get("Event UID", "")
            if uid:
                existing[uid] = record["id"]

        # Track uids seen in this batch
        seen_in_batch = set()
        new_count = 0
        seen_count = 0
        today = date.today().isoformat()

        for event in events:
            uid = event.uid
            if uid in seen_in_batch:
                # Duplicate in batch: seen
                seen_count += 1
            elif uid in existing:
                # Already exists: update Last Seen only
                record_id = existing[uid]
                self.table.update(record_id, {"Last Seen": today})
                seen_count += 1
            else:
                # New event: create
                fields = {
                    "Event UID": uid,
                    "Title": event.title,
                    "Organizer": event.organizer,
                    "Registration URL": event.url or "",
                    "Source URL": event.source_url or "",
                    "Location": event.location or "",
                    "Description": event.description or "",
                    "Status": "Needs Review",
                    "First Seen": today,
                    "Last Seen": today,
                }
                # Include Start/End only if not None
                if event.start:
                    fields["Start"] = event.start.isoformat()
                if event.end:
                    fields["End"] = event.end.isoformat()

                self.table.create(fields)
                new_count += 1

            seen_in_batch.add(uid)

        return {"new": new_count, "seen": seen_count}
