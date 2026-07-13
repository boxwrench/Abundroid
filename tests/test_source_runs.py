"""Tests for the SourceRun value object and health derivation."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from abundroid.models import Source, SourceRun, derive_source_health


def test_source_run_validation():
    # Timezone-aware timestamps work fine
    now = datetime.now(timezone.utc)
    run = SourceRun(
        run_id="run-1",
        source_id="src-1",
        source_name="Name A",
        source_url="https://example.com/feed",
        start_time=now,
        finish_time=now,
        result="success",
        items_found=0,
    )
    assert run.run_id == "run-1"

    # Naive start time raises ValueError
    naive = datetime.now()
    with pytest.raises(ValueError, match="Timestamps must be timezone-aware"):
        SourceRun(
            run_id="run-1",
            source_id="src-1",
            source_name="Name A",
            source_url="https://example.com/feed",
            start_time=naive,
            finish_time=now,
            result="success",
            items_found=0,
        )

    # Naive finish time raises ValueError
    with pytest.raises(ValueError, match="Timestamps must be timezone-aware"):
        SourceRun(
            run_id="run-1",
            source_id="src-1",
            source_name="Name A",
            source_url="https://example.com/feed",
            start_time=now,
            finish_time=naive,
            result="success",
            items_found=0,
        )

    # Finish time earlier than start time raises ValueError
    earlier = datetime.fromtimestamp(now.timestamp() - 10, timezone.utc)
    with pytest.raises(ValueError, match="Finish time cannot be earlier than start time"):
        SourceRun(
            run_id="run-1",
            source_id="src-1",
            source_name="Name A",
            source_url="https://example.com/feed",
            start_time=now,
            finish_time=earlier,
            result="success",
            items_found=0,
        )

    with pytest.raises(ValueError, match="Result must be"):
        SourceRun(
            run_id="run-1", source_id="src-1", source_name="Name A",
            source_url="https://example.com/feed", start_time=now,
            finish_time=now, result="unknown", items_found=0,
        )

    with pytest.raises(ValueError, match="cannot be negative"):
        SourceRun(
            run_id="run-1", source_id="src-1", source_name="Name A",
            source_url="https://example.com/feed", start_time=now,
            finish_time=now, result="success", items_found=-1,
        )

    with pytest.raises(ValueError, match="cannot contain an error"):
        SourceRun(
            run_id="run-1", source_id="src-1", source_name="Name A",
            source_url="https://example.com/feed", start_time=now,
            finish_time=now, result="success", items_found=0, error="stale",
        )


def test_health_derivation():
    now = datetime.now(timezone.utc)
    source_active = Source(
        organization="Org A",
        name="Name A",
        url="https://example.com/feed",
        format="rss",
        active=True,
    )
    source_inactive = Source(
        organization="Org A",
        name="Name A",
        url="https://example.com/feed",
        format="rss",
        active=False,
    )

    # 1. Inactive source -> Paused (regardless of latest run)
    assert derive_source_health(source_inactive, None) == "Paused"
    run_success = SourceRun(
        run_id="run-1", source_id="src-1", source_name="Name A", source_url="https://example.com/feed",
        start_time=now, finish_time=now, result="success", items_found=5
    )
    assert derive_source_health(source_inactive, run_success) == "Paused"

    # 2. No run yet for active source -> Paused
    assert derive_source_health(source_active, None) == "Paused"

    # 3. Failed attempt -> Needs attention
    run_failed = SourceRun(
        run_id="run-1", source_id="src-1", source_name="Name A", source_url="https://example.com/feed",
        start_time=now, finish_time=now, result="failure", items_found=0, error="Connection timeout"
    )
    assert derive_source_health(source_active, run_failed) == "Needs attention"
    assert run_failed.error == "Connection timeout"

    # 4. Successful attempt with zero items -> No recent items
    run_empty = SourceRun(
        run_id="run-1", source_id="src-1", source_name="Name A", source_url="https://example.com/feed",
        start_time=now, finish_time=now, result="success", items_found=0
    )
    assert derive_source_health(source_active, run_empty) == "No recent items"
    assert run_empty.error == ""  # blank on success

    # 5. Successful attempt with 1+ items -> Working
    assert derive_source_health(source_active, run_success) == "Working"
    assert run_success.error == ""  # blank on success
