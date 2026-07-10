"""Airtable persistence for unified Sources and Items."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime
from typing import Any

from abundroid.models import Item, Source


AIRTABLE_ITEM_FIELDS = {
    "uid": "Item UID",
    "source_item_id": "Source Item ID",
    "canonical_url": "Canonical URL",
    "source_url": "Source URL",
    "title": "Title",
    "publisher": "Publisher",
    "kind": "Kind",
    "published_at": "Published At",
    "author": "Author",
    "summary": "Summary",
    "topics": "Topics",
    "status": "Status",
    "reviewer_notes": "Reviewer Notes",
    "scheduled_start": "Scheduled Start",
    "scheduled_end": "Scheduled End",
    "location": "Location",
    "source_hash": "Source Hash",
    "first_seen": "First Seen",
    "last_seen": "Last Seen",
    "changed": "Changed",
    "possible_duplicate_of": "Possible Duplicate Of",
}

_AIRTABLE_DATE_FIELDS = {
    "published_at",
    "scheduled_start",
    "scheduled_end",
    "first_seen",
    "last_seen",
}


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else ""
    return value


def _iso(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if value is not None else ""


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_sources(source_table, organization_table=None) -> list[Source]:
    """Load Sources and resolve their linked Organization names when possible."""
    organizations: dict[str, tuple[str, bool]] = {}
    if organization_table is not None:
        for record in organization_table.all():
            org_fields = record.get("fields", {})
            stage = org_fields.get("Stage", "Approved")
            usable = bool(org_fields.get("Active", False)) and stage == "Approved"
            organizations[record.get("id", "")] = (org_fields.get("Name", ""), usable)

    sources: list[Source] = []
    for record in source_table.all():
        source_fields = record.get("fields", {})
        organization_ids = source_fields.get("Organization", [])
        organization_id = _first(organization_ids)
        lookup_name = _first(source_fields.get("Organization Name", ""))
        organization_name = lookup_name or organization_id or ""
        organization_usable = bool(organization_id or lookup_name)
        if organization_table is not None and organization_id not in organizations:
            organization_usable = False
        elif organization_id in organizations:
            organization_name, organization_usable = organizations[organization_id]

        sources.append(
            Source(
                organization=organization_name,
                name=source_fields.get("Name", ""),
                url=source_fields.get("URL", ""),
                format=source_fields.get("Format", ""),
                default_kind=source_fields.get("Default Kind", "other"),
                active=bool(source_fields.get("Active", False)) and organization_usable,
                notes=source_fields.get("Notes", ""),
            )
        )
    return sources


def _item_to_airtable_fields(item: Item, today: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for attribute, field_name in AIRTABLE_ITEM_FIELDS.items():
        value = getattr(item, attribute, None)
        if attribute == "status":
            value = value or "Needs Review"
        elif attribute in {"first_seen", "last_seen"}:
            value = _iso(value) or today
        elif attribute in _AIRTABLE_DATE_FIELDS:
            value = _iso(value)
        if value not in (None, "", [], False):
            values[field_name] = value
    return values


def _record_to_item(record: dict[str, Any]) -> Item:
    airtable_fields = record.get("fields", {})
    model_fields = {field.name for field in fields(Item)}
    values: dict[str, Any] = {}
    for attribute, field_name in AIRTABLE_ITEM_FIELDS.items():
        if attribute not in model_fields:
            continue
        value = airtable_fields.get(field_name, [] if attribute == "topics" else "")
        if attribute == "changed":
            value = bool(value)
        elif attribute in _AIRTABLE_DATE_FIELDS:
            value = _parse_datetime(value)
        values[attribute] = value
    return Item(**values)


class AirtableItemStore:
    """Batch-upsert Items without overwriting fields owned by reviewers."""

    def __init__(self, table):
        self.table = table

    def upsert(self, items: list[Item]) -> dict[str, int]:
        """Load existing records once, then create or update the whole batch."""
        existing = {}
        for record in self.table.all():
            uid = record.get("fields", {}).get("Item UID", "")
            if uid:
                existing[uid] = record

        today = date.today().isoformat()
        seen_in_batch: set[str] = set()
        new_count = 0
        seen_count = 0

        for item in items:
            uid = item.uid
            if uid in seen_in_batch:
                seen_count += 1
                continue

            record = existing.get(uid)
            if record is None:
                created = self.table.create(_item_to_airtable_fields(item, today), typecast=True)
                # Some pyairtable-compatible fakes return only an ID; no later lookup is
                # needed because duplicate UIDs are handled by seen_in_batch.
                existing[uid] = created
                new_count += 1
            else:
                current_fields = record.get("fields", {})
                stored_hash = current_fields.get("Source Hash", "")
                incoming_hash = item.source_hash or ""
                updates: dict[str, Any] = {"Last Seen": today}
                if incoming_hash and stored_hash and incoming_hash != stored_hash:
                    updates.update({"Source Hash": incoming_hash, "Changed": True})
                elif incoming_hash and not stored_hash:
                    updates["Source Hash"] = incoming_hash
                if item.possible_duplicate_of:
                    updates["Possible Duplicate Of"] = item.possible_duplicate_of
                self.table.update(record["id"], updates)
                seen_count += 1

            seen_in_batch.add(uid)

        return {"new": new_count, "seen": seen_count}

    def recent_items(self, since: datetime | date | None = None) -> list[Item]:
        """Return persisted Items seen at or after ``since``, newest first."""
        cutoff = since.isoformat() if since is not None else ""
        records = [
            record
            for record in self.table.all()
            if not cutoff
            or (
                record.get("fields", {}).get("Last Seen", "")
                or record.get("fields", {}).get("First Seen", "")
            )
            >= cutoff
        ]
        records.sort(
            key=lambda record: record.get("fields", {}).get("Last Seen", "")
            or record.get("fields", {}).get("First Seen", ""),
            reverse=True,
        )
        return [_record_to_item(record) for record in records]

    def set_possible_duplicates(self, mapping: dict[str, str]) -> int:
        """Set only duplicate bookkeeping for UIDs already present in Airtable."""
        existing = {}
        for record in self.table.all():
            uid = record.get("fields", {}).get("Item UID", "")
            if uid:
                existing[uid] = record

        updated = 0
        for uid, duplicate_uid in mapping.items():
            record = existing.get(uid)
            if record is None:
                continue
            current = record.get("fields", {}).get("Possible Duplicate Of", "")
            if current != duplicate_uid:
                self.table.update(record["id"], {"Possible Duplicate Of": duplicate_uid})
                updated += 1
        return updated
