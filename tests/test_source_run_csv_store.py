"""Tests for the SourceRun CSV store."""

from __future__ import annotations

import csv
from datetime import datetime, timezone

from abundroid.models import SourceRun
from abundroid.stores.source_run_csv_store import SourceRunCsvStore


def test_csv_store_saves_runs_and_preserves_history(tmp_path):
    csv_file = tmp_path / "source_runs.csv"
    store = SourceRunCsvStore(csv_file)

    now = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
    run1 = SourceRun(
        run_id="run-1",
        source_id="src-1",
        source_name="Name A",
        source_url="https://example.com/1",
        start_time=now,
        finish_time=now,
        result="success",
        items_found=5,
    )

    # Save first run
    store.save_runs([run1])
    assert csv_file.exists()

    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["items_found"] == "5"

    # Save second run, should append
    run2 = SourceRun(
        run_id="run-2",
        source_id="src-2",
        source_name="Name B",
        source_url="https://example.com/2",
        start_time=now,
        finish_time=now,
        result="failure",
        items_found=0,
        error="Timeout",
    )
    store.save_runs([run2])

    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["run_id"] == "run-1"
    assert rows[1]["run_id"] == "run-2"
    assert rows[1]["error"] == "Timeout"
