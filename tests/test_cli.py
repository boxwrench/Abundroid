"""Tests for the CLI — strict TDD."""

import tempfile
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from abundroid.cli import main
from abundroid import pipeline


class TestCliRunBasic:
    """Tests for the cli run subcommand."""

    def test_cli_run_creates_events_csv(self, tmp_path):
        """Running `cli run` should write events.csv with Needs Review rows."""
        # Create org CSV
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        # Mock fetch to return test RSS
        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 0
        assert output_csv.exists()

        # Verify CSV has Needs Review status
        content = output_csv.read_text()
        assert "Needs Review" in content
        assert "Event 1" in content

    def test_cli_run_dry_run_no_write(self, tmp_path, capsys):
        """--dry-run should not write to file."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv), "--dry-run"])

        assert result == 0
        assert not output_csv.exists()  # File should not be created in dry-run

        # Verify output shows the event
        captured = capsys.readouterr()
        assert "Event 1" in captured.out

    def test_cli_run_default_paths(self, tmp_path, monkeypatch):
        """Default paths should be data/organizations.csv and output/events.csv."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create directory structure
        (tmp_path / "data").mkdir()
        orgs_csv = tmp_path / "data" / "organizations.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        (tmp_path / "output").mkdir()
        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run"])

        assert result == 0
        assert output_csv.exists()

    def test_cli_prints_summary(self, tmp_path, capsys):
        """CLI should print summary lines for each org."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 0
        captured = capsys.readouterr()
        # Should print org name, ok status, events found, new, seen
        assert "Test Org" in captured.out
        assert "ok" in captured.out or "True" in captured.out
        assert "1" in captured.out  # events found

    def test_cli_handles_error_org(self, tmp_path, capsys):
        """CLI should handle errors gracefully and print error summary."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Good Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
            "Bad Org,https://test.com,https://test.com/bad.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            if "bad" in url:
                raise ValueError("Network error")
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        # Task 4: mixed success/failure should return 1
        assert result == 1
        captured = capsys.readouterr()
        assert "Good Org" in captured.out
        assert "Bad Org" in captured.out
        assert "Network error" in captured.out

    def test_cli_run_monkeypatch_fetch(self, tmp_path):
        """Monkeypatching abundroid.pipeline.default_fetch should work for cli."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Mocked Event</title><link>https://example.com/event</link></item></channel></rss>'

        # Patch the default_fetch at pipeline module level
        with patch.object(pipeline, "default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 0
        assert output_csv.exists()

    def test_cli_all_failure_returns_1(self, tmp_path, capsys):
        """Task 4: All-failure run should return 1."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Bad Org 1,https://test.com,https://test.com/bad1.xml,rss,yes,\n"
            "Bad Org 2,https://test.com,https://test.com/bad2.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            raise ValueError("Network error")

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 1
        captured = capsys.readouterr()
        assert "Bad Org 1" in captured.out
        assert "Bad Org 2" in captured.out
        assert "Totals:" in captured.out

    def test_cli_success_only_returns_0(self, tmp_path, capsys):
        """Task 4: Fully successful run should return 0."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Org 1,https://test.com,https://test.com/feed1.xml,rss,yes,\n"
            "Org 2,https://test.com,https://test.com/feed2.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event</title><link>https://example.com/e</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 0
        captured = capsys.readouterr()
        assert "Org 1" in captured.out
        assert "Org 2" in captured.out
        assert "Totals:" in captured.out

    def test_cli_partial_failure_prints_before_exit(self, tmp_path, capsys):
        """Task 4: Output must be printed before returning exit code."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Good Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
            "Bad Org,https://test.com,https://test.com/bad.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            if "bad" in url:
                raise ValueError("Network error")
            return '<?xml version="1.0"?><rss><channel><item><title>Event</title><link>https://example.com/e</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        # Should have output before returning
        captured = capsys.readouterr()
        assert "Good Org" in captured.out
        assert "Bad Org" in captured.out
        assert "error" in captured.out
        assert "Totals:" in captured.out
        # Now check exit code
        assert result == 1

    @pytest.mark.parametrize(
        ("key", "base"),
        [("test-key", ""), ("", "test-base")],
    )
    def test_legacy_run_rejects_partial_airtable_credentials(
        self, tmp_path, monkeypatch, capsys, key, base
    ):
        monkeypatch.setenv("AIRTABLE_API_KEY", key)
        monkeypatch.setenv("AIRTABLE_BASE_ID", base)
        output = tmp_path / "events.csv"

        assert main(["run", "--out", str(output)]) == 1
        assert "must both be set" in capsys.readouterr().err
        assert not output.exists()

    def test_cli_env_loader_skip_blank_and_comments(self, tmp_path, monkeypatch):
        """CLI should skip blank lines and comments in .env file."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create .env file with comments and blanks
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\n"
            "\n"
            "AIRTABLE_API_KEY=\n"  # Empty value
            "  \n"
        )

        # The env loader should handle this without errors
        # We can't test it directly without more complex setup,
        # but at least verify the CLI doesn't crash
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )

        output_csv = tmp_path / "output" / "events.csv"

        def mock_fetch(url):
            return '<?xml version="1.0"?><rss><channel><item><title>Event 1</title><link>https://example.com/event1</link></item></channel></rss>'

        with patch("abundroid.pipeline.default_fetch", mock_fetch):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        # Should complete without error (CSV mode, not Airtable)
        assert result == 0


class TestCliTopicsAndFlags:
    """Phase 2 CLI behavior: topic tagging and cancellation flags."""

    RSS = ('<?xml version="1.0"?><rss><channel><item>'
           '<title>Zoning Reform Meetup</title>'
           '<link>https://example.com/zoning</link>'
           '</item></channel></rss>')

    def _write_orgs(self, tmp_path):
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )
        return orgs_csv

    def test_cli_tags_events_from_topics_csv(self, tmp_path):
        """--topics file drives tagging; tagged names land in the output CSV."""
        orgs_csv = self._write_orgs(tmp_path)
        topics_csv = tmp_path / "topics.csv"
        topics_csv.write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Housing,zoning,,,yes\n"
        )
        output_csv = tmp_path / "output" / "events.csv"

        with patch("abundroid.pipeline.default_fetch", lambda url: self.RSS):
            result = main(["run", "--orgs", str(orgs_csv),
                           "--out", str(output_csv), "--topics", str(topics_csv)])

        assert result == 0
        assert "Housing" in output_csv.read_text()

    def test_cli_missing_topics_file_is_fine(self, tmp_path):
        """A nonexistent topics file means no tagging, not a crash."""
        orgs_csv = self._write_orgs(tmp_path)
        output_csv = tmp_path / "output" / "events.csv"

        with patch("abundroid.pipeline.default_fetch", lambda url: self.RSS):
            result = main(["run", "--orgs", str(orgs_csv),
                           "--out", str(output_csv),
                           "--topics", str(tmp_path / "nope.csv")])

        assert result == 0
        assert "Zoning Reform Meetup" in output_csv.read_text()

    def test_cli_default_topics_path(self, tmp_path, monkeypatch):
        """data/topics.csv is picked up automatically when present."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "organizations.csv").write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Test Org,https://test.com,https://test.com/feed.xml,rss,yes,\n"
        )
        (tmp_path / "data" / "topics.csv").write_text(
            "topic,keywords,aliases,exclusions,active\n"
            "Housing,zoning,,,yes\n"
        )

        with patch("abundroid.pipeline.default_fetch", lambda url: self.RSS):
            result = main(["run"])

        assert result == 0
        assert "Housing" in (tmp_path / "output" / "events.csv").read_text()

    def test_cli_reports_possibly_cancelled(self, tmp_path, capsys):
        """A future event that vanished from an iCal source is reported."""
        orgs_csv = tmp_path / "orgs.csv"
        orgs_csv.write_text(
            "name,website,events_url,source_type,active,notes\n"
            "Cal Org,https://test.com,https://test.com/cal.ics,ical,yes,\n"
        )
        output_csv = tmp_path / "output" / "events.csv"
        output_csv.parent.mkdir(parents=True)
        # Pre-seed a future event from Cal Org whose uid the feed won't contain
        output_csv.write_text(
            "uid,title,organizer,url,start,end,location,description,source_url,"
            "topics,possible_duplicate_of,status,changed,possibly_cancelled,"
            "source_hash,first_seen,last_seen\n"
            "url:https://gone.com/e,Vanished Event,Cal Org,https://gone.com/e,"
            "2030-01-01T18:00:00,,,,https://test.com/cal.ics,,,Needs Review,,,"
            "abc123,2026-07-01,2026-07-01\n"
        )
        fixture = Path(__file__).parent / "fixtures" / "sample.ics"
        ical_content = fixture.read_text()

        with patch("abundroid.pipeline.default_fetch", lambda url: ical_content):
            result = main(["run", "--orgs", str(orgs_csv), "--out", str(output_csv)])

        assert result == 0
        out_text = output_csv.read_text()
        assert "yes" in [row.split(",")[13] for row in out_text.splitlines()[1:]
                         if row.startswith("url:https://gone.com/e")][0]
        captured = capsys.readouterr()
        assert "1 possibly cancelled" in captured.out


def test_module_is_runnable_via_python_dash_m():
    """python -m abundroid.cli must invoke main, not silently no-op."""
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, "-m", "abundroid.cli"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0
    assert "usage" in proc.stdout.lower()
