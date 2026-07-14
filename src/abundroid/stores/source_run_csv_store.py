"""CSV store for tracking Source collection run histories."""

from __future__ import annotations

import csv
from pathlib import Path

from abundroid.models import SourceRun

SOURCERUN_FIELDNAMES = [
    "run_id",
    "source_id",
    "source_name",
    "source_url",
    "start_time",
    "finish_time",
    "result",
    "items_found",
    "http_status",
    "error",
]


class SourceRunCsvStore:
    """Store SourceRun records in a local CSV file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save_runs(self, runs: list[SourceRun]) -> None:
        """Append SourceRun records to the CSV, preserving prior history."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.path.exists()

        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SOURCERUN_FIELDNAMES, extrasaction="ignore")
            if not exists:
                writer.writeheader()
            for run in runs:
                row = {
                    "run_id": run.run_id,
                    "source_id": run.source_id,
                    "source_name": run.source_name,
                    "source_url": run.source_url,
                    "start_time": run.start_time.isoformat(),
                    "finish_time": run.finish_time.isoformat(),
                    "result": run.result,
                    "items_found": run.items_found,
                    "http_status": run.http_status if run.http_status is not None else "",
                    "error": run.error,
                }
                writer.writerow(row)
