"""Airtable store for tracking Source collection run histories."""

from __future__ import annotations

from typing import Any

from abundroid.models import SourceRun


class AirtableSourceRunStore:
    """Store SourceRun records in Airtable."""

    def __init__(self, table: Any):
        self.table = table

    def save_runs(self, runs: list[SourceRun]) -> None:
        """Create records in Airtable for the completed batch of runs."""
        records = []
        for run in runs:
            fields = {
                "Run ID": run.run_id,
                "Started At": run.start_time.isoformat(),
                "Finished At": run.finish_time.isoformat(),
                "Result": run.derive_health(),
                "Items Found": run.items_found,
                "Items New": run.items_new,
                "Items Seen": run.items_seen,
                "Error": run.error or "",
            }
            if run.source_id:
                fields["Source"] = [run.source_id]
            if run.http_status is not None:
                fields["HTTP Status"] = run.http_status

            records.append({"fields": fields})

        if records:
            self.table.batch_create(records, typecast=True)
