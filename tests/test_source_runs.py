"""Tests for SourceRun validation and operator-facing results."""

from datetime import datetime, timedelta, timezone

import pytest

from abundroid.models import SourceRun


def run(**changes):
    now = datetime.now(timezone.utc)
    values = {
        "run_id": "run-1",
        "source_id": "src-1",
        "source_name": "News",
        "source_url": "https://example.com/feed",
        "start_time": now,
        "finish_time": now,
        "result": "success",
        "items_found": 1,
    }
    values.update(changes)
    return SourceRun(**values)


def test_source_run_accepts_a_valid_attempt():
    attempt = run()

    assert attempt.run_id == "run-1"
    assert attempt.derive_health() == "Working"


def test_source_run_requires_aware_ordered_timestamps():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        run(start_time=datetime.now())
    with pytest.raises(ValueError, match="timezone-aware"):
        run(finish_time=datetime.now())
    with pytest.raises(ValueError, match="earlier"):
        run(start_time=now, finish_time=now - timedelta(seconds=1))


def test_source_run_validates_result_counts_and_success_error():
    with pytest.raises(ValueError, match="Result must be"):
        run(result="unknown")
    with pytest.raises(ValueError, match="negative"):
        run(items_found=-1)
    with pytest.raises(ValueError, match="cannot contain an error"):
        run(error="stale")


@pytest.mark.parametrize(
    ("result", "items_found", "error", "health"),
    [
        ("failure", 0, "Connection timeout", "Needs attention"),
        ("success", 0, "", "No recent items"),
        ("success", 2, "", "Working"),
    ],
)
def test_source_run_health(result, items_found, error, health):
    assert run(result=result, items_found=items_found, error=error).derive_health() == health
