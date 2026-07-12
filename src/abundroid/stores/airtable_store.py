"""Airtable-based storage for organizations and events."""

from datetime import date, datetime

from abundroid.models import Event, Organization
from abundroid.uid import content_hash


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
        - If uid not present: create with Status "Needs Review", First Seen/Last Seen = today ISO,
          plus Phase 2 fields: Source Hash, Topics (if non-empty), Possible Duplicate Of (if non-empty)
        - If present: update Last Seen, clear Possibly Cancelled if truthy, check for content changes

        Returns {"new": int, "seen": int}
        """
        # Load all existing records, map "Event UID" -> record id and fields
        existing = {}
        for record in self.table.all():
            uid = record.get("fields", {}).get("Event UID", "")
            if uid:
                existing[uid] = (record["id"], record.get("fields", {}))

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
                # Already exists: Rule B - update Last Seen, clear Possibly Cancelled, check for changes
                record_id, existing_fields = existing[uid]
                update_dict = {"Last Seen": today}

                # Clear Possibly Cancelled if it was truthy
                if existing_fields.get("Possibly Cancelled"):
                    update_dict["Possibly Cancelled"] = False

                # Check for content changes
                new_hash = content_hash(event)
                stored_hash = existing_fields.get("Source Hash", "")
                if stored_hash and stored_hash != new_hash:
                    # Content changed and we had a stored hash
                    update_dict["Changed"] = True
                    update_dict["Source Hash"] = new_hash
                elif not stored_hash:
                    # Backfill source_hash for legacy records (don't set changed)
                    update_dict["Source Hash"] = new_hash

                self.table.update(record_id, update_dict)
                seen_count += 1
            else:
                # New event: create with Phase 2 fields
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
                    "Source Hash": content_hash(event),
                }
                # Include Start/End only if not None
                if event.start:
                    fields["Start"] = event.start.isoformat()
                if event.end:
                    fields["End"] = event.end.isoformat()
                # Include Topics only if non-empty
                if event.topics:
                    fields["Topics"] = event.topics
                # Include Possible Duplicate Of only if non-empty
                if event.possible_duplicate_of:
                    fields["Possible Duplicate Of"] = event.possible_duplicate_of

                self.table.create(fields, typecast=True)
                new_count += 1

            seen_in_batch.add(uid)

        return {"new": new_count, "seen": seen_count}

    def flag_missing(self, organizer: str, source_url: str, present_uids: set[str]) -> int:
        """
        Flag likely-cancelled events.

        For each existing record where:
        - record organizer == organizer
        - record Source URL == source_url
        - record uid not in present_uids
        - record status is "Needs Review" or "Approved"
        - record Start is non-empty AND datetime.fromisoformat(start).date() > date.today()

        Sets Possibly Cancelled = True and returns the count flagged.
        Records with missing or unparseable Start are skipped.
        """
        count = 0
        today = date.today()

        for record in self.table.all():
            fields = record.get("fields", {})
            if (fields.get("Organizer", "") == organizer and
                fields.get("Source URL", "") == source_url and
                fields.get("Event UID", "") not in present_uids and
                fields.get("Status", "") in ("Needs Review", "Approved")):

                start_str = fields.get("Start", "").strip() if fields.get("Start") else ""
                if start_str:
                    try:
                        # Handle ISO format with Z suffix
                        if start_str.endswith("Z"):
                            start_str = start_str[:-1] + "+00:00"
                        start_dt = datetime.fromisoformat(start_str)
                        if start_dt.date() > today:
                            record_id = record["id"]
                            self.table.update(record_id, {"Possibly Cancelled": True})
                            count += 1
                    except (ValueError, TypeError):
                        # Unparseable start: skip
                        pass

        return count
