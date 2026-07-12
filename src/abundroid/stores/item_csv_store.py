"""CSV persistence for unified publication Items."""

from __future__ import annotations

import csv
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path

from abundroid.models import Item, Source


ITEM_FIELDNAMES = [
    "uid",
    "source_item_id",
    "canonical_url",
    "source_url",
    "title",
    "publisher",
    "kind",
    "published_at",
    "author",
    "summary",
    "topics",
    "status",
    "reviewer_notes",
    "scheduled_start",
    "scheduled_end",
    "location",
    "source_hash",
    "first_seen",
    "last_seen",
    "changed",
    "possible_duplicate_of",
]

_DATE_FIELDS = {
    "published_at",
    "scheduled_start",
    "scheduled_end",
    "first_seen",
    "last_seen",
}


def load_sources(path: str | Path) -> list[Source]:
    """Load configured Sources from CSV, skipping rows without an owner or URL."""
    sources = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            organization = (row.get("organization") or "").strip()
            url = (row.get("url") or "").strip()
            if not organization or not url:
                continue
            active = (row.get("active") or "").strip().lower() in {"yes", "true", "1"}
            sources.append(
                Source(
                    organization=organization,
                    name=(row.get("name") or "").strip(),
                    url=url,
                    format=(row.get("format") or "").strip(),
                    default_kind=(row.get("default_kind") or "other").strip() or "other",
                    active=active,
                    notes=(row.get("notes") or "").strip(),
                )
            )
    return sources


def _iso(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value) if value is not None else ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _item_to_row(item: Item, today: str) -> dict[str, str]:
    row = {name: _iso(getattr(item, name, "")) for name in ITEM_FIELDNAMES}
    row["topics"] = "; ".join(getattr(item, "topics", []) or [])
    row["status"] = getattr(item, "status", "") or "Needs Review"
    row["first_seen"] = _iso(getattr(item, "first_seen", "")) or today
    row["last_seen"] = _iso(getattr(item, "last_seen", "")) or today
    row["changed"] = "yes" if getattr(item, "changed", False) else ""
    return row


def _row_to_item(row: dict[str, str]) -> Item:
    """Convert a persisted row while tolerating future model additions."""
    model_fields = {field.name for field in fields(Item)}
    values: dict[str, object] = {}
    for name in model_fields:
        value: object = row.get(name, "")
        if name == "topics":
            value = [part.strip() for part in str(value).split(";") if part.strip()]
        elif name == "changed":
            value = str(value).strip().lower() in {"yes", "true", "1"}
        elif name in _DATE_FIELDS:
            value = _parse_datetime(str(value))
        values[name] = value
    return Item(**values)


class CsvItemStore:
    """Batch-upsert Items while preserving reviewer-owned CSV columns."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ITEM_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def upsert(self, items: list[Item]) -> dict[str, int]:
        """Create unseen Items and update bookkeeping for Items already stored."""
        rows = self._read_rows()
        by_uid = {row.get("uid", ""): row for row in rows if row.get("uid")}
        seen_in_batch: set[str] = set()
        new_count = 0
        seen_count = 0
        today = date.today().isoformat()

        for item in items:
            uid = item.uid
            if uid in seen_in_batch:
                seen_count += 1
                continue

            if uid in by_uid:
                row = by_uid[uid]
                incoming_hash = item.source_hash or ""
                stored_hash = row.get("source_hash", "")
                row["last_seen"] = today
                if incoming_hash and stored_hash and incoming_hash != stored_hash:
                    row["source_hash"] = incoming_hash
                    row["changed"] = "yes"
                elif incoming_hash and not stored_hash:
                    row["source_hash"] = incoming_hash
                if item.possible_duplicate_of and not row.get("possible_duplicate_of"):
                    row["possible_duplicate_of"] = item.possible_duplicate_of
                seen_count += 1
            else:
                row = _item_to_row(item, today)
                rows.append(row)
                by_uid[uid] = row
                new_count += 1

            seen_in_batch.add(uid)

        self._write_rows(rows)
        return {"new": new_count, "seen": seen_count}

    def recent_items(self, since: datetime | date | None = None) -> list[Item]:
        """Return persisted Items seen at or after ``since``, newest first."""
        cutoff = since.isoformat() if since is not None else ""
        rows = [
            row
            for row in self._read_rows()
            if not cutoff or (row.get("last_seen", "") or row.get("first_seen", "")) >= cutoff
        ]
        rows.sort(
            key=lambda row: row.get("last_seen", "") or row.get("first_seen", ""),
            reverse=True,
        )
        return [_row_to_item(row) for row in rows]

    def set_possible_duplicates(self, mapping: dict[str, str]) -> int:
        """Set duplicate bookkeeping for existing UIDs without marking them seen."""
        rows = self._read_rows()
        updated = 0
        for row in rows:
            uid = row.get("uid", "")
            if uid in mapping and row.get("possible_duplicate_of", "") != mapping[uid]:
                row["possible_duplicate_of"] = mapping[uid]
                updated += 1
        if updated:
            self._write_rows(rows)
        return updated
