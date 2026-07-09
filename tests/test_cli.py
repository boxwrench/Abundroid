"""Tests for the CLI — strict TDD."""

import tempfile
import os
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

        assert result == 0
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
