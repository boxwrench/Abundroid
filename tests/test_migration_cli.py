"""CLI tests for the events-to-items migration command."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from abundroid.cli import main
from tests.test_item_airtable_store import FakeTable


def _clear_airtable(monkeypatch):
    monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
    monkeypatch.delenv("AIRTABLE_BASE_ID", raising=False)
    monkeypatch.delenv("AIRTABLE_EVENTS_TABLE", raising=False)
    monkeypatch.delenv("AIRTABLE_ITEMS_TABLE", raising=False)


@pytest.fixture
def clean_env(monkeypatch):
    _clear_airtable(monkeypatch)
    yield


def test_cli_migrate_missing_args(tmp_path, clean_env, capsys):
    # CSV mode requires --events and --items
    result = main(["migrate-events"])
    assert result == 1
    captured = capsys.readouterr()
    assert "Error: --events path is required in CSV mode" in captured.err


def test_cli_migrate_missing_events_file(tmp_path, clean_env, capsys):
    events_file = tmp_path / "nonexistent.csv"
    items_file = tmp_path / "items.csv"
    result = main(["migrate-events", "--events", str(events_file), "--items", str(items_file)])
    assert result == 1
    captured = capsys.readouterr()
    assert "Error: legacy events file not found:" in captured.err


def test_cli_migrate_csv_preview_and_apply(tmp_path, clean_env, capsys):
    events_file = tmp_path / "events.csv"
    items_file = tmp_path / "items.csv"

    # Write a valid legacy events CSV
    # Headers must match legacy Event CSV fields
    events_file.write_text(
        "uid,title,organizer,url,start,end,location,description,source_url,topics,possible_duplicate_of,status,changed,first_seen,last_seen\n"
        "legacy-1,My Event,My Org,https://example.com/reg,2026-07-15T10:00:00Z,2026-07-15T12:00:00Z,Location A,Description A,https://example.com/source,Housing,legacy-2,Needs Review,no,2026-07-01T09:00:00Z,2026-07-01T09:00:00Z\n"
        "legacy-2,Duplicate Event,My Org,https://example.com/reg2,2026-07-15T10:00:00Z,2026-07-15T12:00:00Z,Location A,Description A,https://example.com/source,Housing,,Needs Review,no,2026-07-01T09:00:00Z,2026-07-01T09:00:00Z\n",
        encoding="utf-8"
    )

    # 1. Preview mode (no --apply)
    result_preview = main(["migrate-events", "--events", str(events_file), "--items", str(items_file)])
    assert result_preview == 0
    assert not items_file.exists()  # Preview must not write any file

    captured_preview = capsys.readouterr()
    assert "Converted: 2" in captured_preview.out
    assert "Skipped: 0" in captured_preview.out
    assert "Warnings: 0" in captured_preview.out

    # 2. Apply mode
    result_apply = main(["migrate-events", "--events", str(events_file), "--items", str(items_file), "--apply"])
    assert result_apply == 0
    assert items_file.exists()

    captured_apply = capsys.readouterr()
    assert "Converted: 2" in captured_apply.out
    assert "Skipped: 0" in captured_apply.out
    assert "New: 2" in captured_apply.out
    assert "Seen: 0" in captured_apply.out

    # Verify written items
    with open(items_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["title"] == "My Event"
    assert rows[0]["publisher"] == "My Org"
    assert rows[0]["kind"] == "event"
    # Duplicate resolved legacy-2 to new Item UID (url:...)
    assert rows[0]["possible_duplicate_of"].startswith("url:")


def test_cli_migrate_csv_idempotency_and_preserves_editorial(tmp_path, clean_env, capsys):
    events_file = tmp_path / "events.csv"
    items_file = tmp_path / "items.csv"

    events_file.write_text(
        "uid,title,organizer,url,start,end,location,description,source_url,topics,possible_duplicate_of,status,changed,first_seen,last_seen\n"
        "legacy-1,My Event,My Org,https://example.com/reg,2026-07-15T10:00:00Z,2026-07-15T12:00:00Z,Location A,Description A,https://example.com/source,Housing,,Needs Review,no,2026-07-01T09:00:00Z,2026-07-01T09:00:00Z\n",
        encoding="utf-8"
    )

    # First apply
    assert main(["migrate-events", "--events", str(events_file), "--items", str(items_file), "--apply"]) == 0

    # Simulate editorial changes by a reviewer in items.csv
    with open(items_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows[0]["title"] = "Reviewed Event Title"
    rows[0]["status"] = "Approved"
    rows[0]["reviewer_notes"] = "Reviewed note"

    from abundroid.stores.item_csv_store import ITEM_FIELDNAMES
    with open(items_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ITEM_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    # Run apply again (rerun)
    capsys.readouterr()  # Clear stdout
    assert main(["migrate-events", "--events", str(events_file), "--items", str(items_file), "--apply"]) == 0

    captured_rerun = capsys.readouterr()
    assert "New: 0" in captured_rerun.out
    assert "Seen: 1" in captured_rerun.out

    # Verify editorial changes are preserved
    with open(items_file, "r", encoding="utf-8") as f:
        rows_after = list(csv.DictReader(f))
    assert len(rows_after) == 1
    assert rows_after[0]["title"] == "Reviewed Event Title"
    assert rows_after[0]["status"] == "Approved"
    assert rows_after[0]["reviewer_notes"] == "Reviewed note"


class FakeAirtableApi:
    def __init__(self, key):
        self.key = key
        self.tables = {}

    def table(self, base_id, table_name):
        if table_name not in self.tables:
            self.tables[table_name] = FakeTable()
        return self.tables[table_name]


def test_cli_migrate_airtable_preview_and_apply(monkeypatch, capsys):
    # Set Airtable credentials
    monkeypatch.setenv("AIRTABLE_API_KEY", "test-key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test-base")
    monkeypatch.setenv("AIRTABLE_EVENTS_TABLE", "EventsTable")
    monkeypatch.setenv("AIRTABLE_ITEMS_TABLE", "ItemsTable")

    # Seed the mock events table
    fake_api = FakeAirtableApi("test-key")
    events_table = fake_api.table("test-base", "EventsTable")
    events_table.create({
        "Event UID": "legacy-1",
        "Title": "Airtable Event",
        "Organizer": "Airtable Org",
        "Registration URL": "https://example.com/air",
        "Start": "2026-07-15T10:00:00Z",
        "End": "2026-07-15T12:00:00Z",
        "Status": "Needs Review",
    })

    with patch("pyairtable.Api", return_value=fake_api):
        # 1. Preview mode (no --apply)
        result_preview = main(["migrate-events"])
        assert result_preview == 0

        # Verify no create/update was called on items table
        items_table = fake_api.table("test-base", "ItemsTable")
        assert len(items_table.records) == 0

        captured_preview = capsys.readouterr()
        assert "Converted: 1" in captured_preview.out
        assert "Skipped: 0" in captured_preview.out

        # 2. Apply mode
        result_apply = main(["migrate-events", "--apply"])
        assert result_apply == 0

        # Verify created record in items table
        assert len(items_table.records) == 1
        record = items_table.records[0]["fields"]
        assert record["Title"] == "Airtable Event"
        assert record["Publisher"] == "Airtable Org"
        assert record["Kind"] == "event"

        captured_apply = capsys.readouterr()
        assert "Converted: 1" in captured_apply.out
        assert "New: 1" in captured_apply.out
        assert "Seen: 0" in captured_apply.out


def test_cli_migrate_airtable_failures(monkeypatch, capsys):
    monkeypatch.setenv("AIRTABLE_API_KEY", "test-key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test-base")

    # Make pyairtable.Api raise an exception to simulate connection failure
    with patch("pyairtable.Api", side_effect=Exception("API connection failed")):
        result = main(["migrate-events"])
        assert result == 1

        captured = capsys.readouterr()
        assert "Error connecting to Airtable: API connection failed" in captured.err
        # Make sure it didn't fall back to CSV mode (which would complain about --events)
        assert "--events path is required" not in captured.err


@pytest.mark.parametrize(
    ("key", "base"),
    [("test-key", ""), ("", "test-base")],
)
def test_cli_migrate_rejects_partial_airtable_credentials(monkeypatch, capsys, key, base):
    monkeypatch.setenv("AIRTABLE_API_KEY", key)
    monkeypatch.setenv("AIRTABLE_BASE_ID", base)

    assert main(["migrate-events"]) == 1
    assert "must both be set" in capsys.readouterr().err
