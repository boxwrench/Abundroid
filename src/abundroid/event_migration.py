"""Pure event migration logic to convert legacy Event records into unified Items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from abundroid.models import Item
from abundroid.item_uid import compute_item_uid, item_content_hash

CSV_TO_LEGACY_MAP = {
    "uid": "uid",
    "title": "title",
    "organizer": "organizer",
    "url": "url",
    "source_url": "source_url",
    "start": "start",
    "end": "end",
    "location": "location",
    "description": "description",
    "topics": "topics",
    "status": "status",
    "reviewer_notes": "reviewer_notes",
    "first_seen": "first_seen",
    "last_seen": "last_seen",
    "changed": "changed",
    "possible_duplicate_of": "possible_duplicate_of",
}

AIRTABLE_TO_LEGACY_MAP = {
    "UID": "uid",
    "uid": "uid",
    "Event UID": "uid",
    "Title": "title",
    "title": "title",
    "Organizer": "organizer",
    "organizer": "organizer",
    "Registration URL": "url",
    "url": "url",
    "Source URL": "source_url",
    "source_url": "source_url",
    "Start": "start",
    "start": "start",
    "End": "end",
    "end": "end",
    "Location": "location",
    "location": "location",
    "Description": "description",
    "description": "description",
    "Topics": "topics",
    "topics": "topics",
    "Status": "status",
    "status": "status",
    "Reviewer Notes": "reviewer_notes",
    "reviewer_notes": "reviewer_notes",
    "First Seen": "first_seen",
    "first_seen": "first_seen",
    "Last Seen": "last_seen",
    "last_seen": "last_seen",
    "Changed": "changed",
    "changed": "changed",
    "Possible Duplicate Of": "possible_duplicate_of",
    "possible_duplicate_of": "possible_duplicate_of",
}


@dataclass
class MigrationWarning:
    row_index: int
    warning_type: str  # "missing_field", "blank_date", "invalid_date", "unresolved_duplicate"
    message: str
    legacy_uid: str = ""
    title: str = ""
    organizer: str = ""


def normalize_row(row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Normalize a raw input row to standard legacy keys without mutating it."""
    normalized = {}
    for src_key, dest_key in mapping.items():
        if src_key in row:
            normalized[dest_key] = row[src_key]
    return normalized


def _parse_date_field(val: Any, field_name: str) -> tuple[datetime | None, str | None]:
    if val is None:
        return None, "blank"
    if isinstance(val, datetime):
        return val, None
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day), None

    s = str(val).strip()
    if not s:
        return None, "blank"

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt, None
    except Exception:
        return None, "invalid"


def parse_topics(val: Any) -> list[str]:
    """Parse topics list from Airtable lists or CSV semicolon-separated strings."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(t).strip() for t in val if str(t).strip()]
    if isinstance(val, str):
        return [t.strip() for t in val.split(";") if t.strip()]
    return []


def migrate_events(rows: list[dict[str, Any]]) -> tuple[list[Item], list[MigrationWarning]]:
    """Convert normalized legacy Event records into unified Items."""
    converted_items: list[Item] = []
    warnings: list[MigrationWarning] = []

    # Map legacy UID to new Item UID
    legacy_to_new_uid_map: dict[str, str] = {}

    # Keep track of first pass results for second pass duplicate resolution
    first_pass_results: list[tuple[Item, dict[str, Any], int]] = []

    for index, row in enumerate(rows):
        title = str(row.get("title") or "").strip()
        organizer = str(row.get("organizer") or "").strip()
        legacy_uid = str(row.get("uid") or "").strip()

        if not title or not organizer:
            missing_fields = []
            if not title:
                missing_fields.append("title")
            if not organizer:
                missing_fields.append("organizer")
            warnings.append(
                MigrationWarning(
                    row_index=index,
                    warning_type="missing_field",
                    message=f"Skipping row: missing required fields: {', '.join(missing_fields)}",
                    legacy_uid=legacy_uid,
                    title=title,
                    organizer=organizer,
                )
            )
            continue

        # Parse date fields
        start_dt, start_warn = _parse_date_field(row.get("start"), "start")
        end_dt, end_warn = _parse_date_field(row.get("end"), "end")
        first_seen_dt, first_seen_warn = _parse_date_field(row.get("first_seen"), "first_seen")
        last_seen_dt, last_seen_warn = _parse_date_field(row.get("last_seen"), "last_seen")

        for warn_type, field_name, original_value in [
            (start_warn, "start", row.get("start")),
            (end_warn, "end", row.get("end")),
            (first_seen_warn, "first_seen", row.get("first_seen")),
            (last_seen_warn, "last_seen", row.get("last_seen")),
        ]:
            if warn_type == "blank":
                warnings.append(
                    MigrationWarning(
                        row_index=index,
                        warning_type="blank_date",
                        message=f"Optional date field '{field_name}' is blank.",
                        legacy_uid=legacy_uid,
                        title=title,
                        organizer=organizer,
                    )
                )
            elif warn_type == "invalid":
                warnings.append(
                    MigrationWarning(
                        row_index=index,
                        warning_type="invalid_date",
                        message=f"Invalid timestamp format: '{original_value}' for field '{field_name}'.",
                        legacy_uid=legacy_uid,
                        title=title,
                        organizer=organizer,
                    )
                )

        # Topics
        topics = parse_topics(row.get("topics"))

        # Changed
        changed_val = row.get("changed")
        changed = False
        if changed_val is not None:
            if isinstance(changed_val, bool):
                changed = changed_val
            else:
                changed = str(changed_val).strip().lower() in {"yes", "true", "1"}

        # Build converted Item
        item = Item(
            title=title,
            publisher=organizer,
            kind="event",
            canonical_url=str(row.get("url") or "").strip(),
            source_url=str(row.get("source_url") or "").strip(),
            scheduled_start=start_dt,
            scheduled_end=end_dt,
            location=str(row.get("location") or "").strip(),
            summary=str(row.get("description") or "").strip(),
            topics=topics,
            status=str(row.get("status") or "").strip() or "Needs Review",
            reviewer_notes=str(row.get("reviewer_notes") or "").strip(),
            first_seen=first_seen_dt,
            last_seen=last_seen_dt,
            changed=changed,
        )

        # Compute UID and source_hash
        item.uid = compute_item_uid(item)
        item.source_hash = item_content_hash(item)

        if legacy_uid:
            legacy_to_new_uid_map[legacy_uid] = item.uid

        converted_items.append(item)
        first_pass_results.append((item, row, index))

    # Second pass: translate duplicate references
    for item, row, index in first_pass_results:
        legacy_dup = str(row.get("possible_duplicate_of") or "").strip()
        if legacy_dup:
            if legacy_dup in legacy_to_new_uid_map:
                item.possible_duplicate_of = legacy_to_new_uid_map[legacy_dup]
            else:
                item.possible_duplicate_of = ""
                warnings.append(
                    MigrationWarning(
                        row_index=index,
                        warning_type="unresolved_duplicate",
                        message=f"Unresolved duplicate reference: '{legacy_dup}' not found in migration set.",
                        legacy_uid=str(row.get("uid") or "").strip(),
                        title=item.title,
                        organizer=item.publisher,
                    )
                )

    return converted_items, warnings
