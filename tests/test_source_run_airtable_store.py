"""Tests for the SourceRun Airtable store."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from abundroid.models import SourceRun
from abundroid.stores.source_run_airtable_store import AirtableSourceRunStore
from tests.test_item_airtable_store import FakeTable


def test_airtable_store_saves_runs_correctly():
    class BatchTable(FakeTable):
        def batch_create(self, records, typecast=False):
            assert typecast is True
            for record in records:
                self.create(record["fields"], typecast=typecast)

    table = BatchTable()
    store = AirtableSourceRunStore(table)

    now = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
    run = SourceRun(
        run_id="run-123",
        source_id="recSrc1",
        source_name="Name A",
        source_url="https://example.com/feed",
        start_time=now,
        finish_time=now,
        result="success",
        items_found=5,
        items_new=2,
        items_seen=3,
        http_status=200,
    )

    store.save_runs([run])

    assert len(table.records) == 1
    fields = table.records[0]["fields"]
    assert fields["Run ID"] == "run-123"
    assert fields["Source"] == ["recSrc1"]
    assert fields["Started At"] == now.isoformat()
    assert fields["Finished At"] == now.isoformat()
    assert fields["Result"] == "Working"
    assert fields["Items Found"] == 5
    assert fields["Items New"] == 2
    assert fields["Items Seen"] == 3
    assert fields["HTTP Status"] == 200
    assert fields["Error"] == ""


def test_airtable_store_bubbles_up_exceptions():
    class FailingTable:
        def batch_create(self, records, typecast=False):
            raise RuntimeError("Airtable API down")

    store = AirtableSourceRunStore(FailingTable())
    now = datetime.now(timezone.utc)
    run = SourceRun(
        run_id="run-1", source_id="src-1", source_name="Name", source_url="url",
        start_time=now, finish_time=now, result="success", items_found=0
    )

    with pytest.raises(RuntimeError, match="Airtable API down"):
        store.save_runs([run])
