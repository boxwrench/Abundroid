'''CLI tests for the unified Items collection path.'''

import csv
from unittest.mock import patch

from abundroid.cli import main
from tests.test_item_airtable_store import FakeTable


RSS = '''<?xml version='1.0'?>
<rss version='2.0'><channel><title>News</title><item>
<title>Housing reform update</title>
<guid>post-1</guid>
<link>https://example.com/posts/1</link>
<pubDate>Thu, 09 Jul 2026 17:00:00 GMT</pubDate>
<author>Policy Desk</author>
<description>New zoning legislation.</description>
</item></channel></rss>'''


class FakeAirtableApi:
    def __init__(self, key):
        self.key = key
        self.tables = {}

    def table(self, base_id, table_name):
        if table_name not in self.tables:
            self.tables[table_name] = FakeTable()
        return self.tables[table_name]


def _sources_file(tmp_path):
    path = tmp_path / 'sources.csv'
    path.write_text(
        'organization,name,url,format,default_kind,active,notes\n'
        'Example Org,News,https://example.com/feed,rss,update,true,\n',
        encoding='utf-8',
    )
    return path


def _clear_airtable(monkeypatch):
    monkeypatch.delenv('AIRTABLE_API_KEY', raising=False)
    monkeypatch.delenv('AIRTABLE_BASE_ID', raising=False)
    # A real .env in the repo root (present after `abundroid setup` writes
    # AIRTABLE_BASE_ID) would otherwise be reloaded by main() and repopulate
    # credentials, breaking CSV-mode collection tests. Keep the env clean.
    monkeypatch.setattr('abundroid.cli.load_env', lambda *args, **kwargs: None)


def test_collect_writes_items_and_is_idempotent(tmp_path, monkeypatch, capsys):
    _clear_airtable(monkeypatch)
    sources = _sources_file(tmp_path)
    output = tmp_path / 'items.csv'
    arguments = [
        'collect', '--sources', str(sources), '--out', str(output),
        '--topics', str(tmp_path / 'missing-topics.csv'),
    ]

    with patch('abundroid.item_pipeline.default_fetch', lambda url: RSS):
        assert main(arguments) == 0
        assert main(arguments) == 0

    rows = output.read_text(encoding='utf-8').splitlines()
    assert len(rows) == 2
    assert 'Housing reform update' in rows[1]
    assert '[update]' not in rows[1]
    assert 'Totals: 1 found, 0 new, 1 seen' in capsys.readouterr().out


def test_collect_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    _clear_airtable(monkeypatch)
    sources = _sources_file(tmp_path)
    output = tmp_path / 'items.csv'

    with patch('abundroid.item_pipeline.default_fetch', lambda url: RSS):
        result = main([
            'collect', '--sources', str(sources), '--out', str(output),
            '--topics', str(tmp_path / 'missing.csv'), '--dry-run',
        ])

    assert result == 0
    assert not output.exists()
    report = capsys.readouterr().out
    assert '[UPDATE] Housing reform update' in report
    assert 'Example Org | Jul 9, 2026' in report
    assert 'By Policy Desk' in report
    assert 'New zoning legislation.' in report
    assert 'Link: https://example.com/posts/1' in report
    assert '[source:' not in report


def test_collect_partial_airtable_credentials_fails(tmp_path, monkeypatch, capsys):
    _clear_airtable(monkeypatch)
    sources = _sources_file(tmp_path)
    output = tmp_path / 'items.csv'

    # Only API key is set
    monkeypatch.setenv('AIRTABLE_API_KEY', 'some_key')
    monkeypatch.delenv('AIRTABLE_BASE_ID', raising=False)
    result = main(['collect', '--sources', str(sources), '--out', str(output)])
    assert result == 1
    assert "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must both be set" in capsys.readouterr().err
    assert not output.exists()

    # Only Base ID is set
    monkeypatch.delenv('AIRTABLE_API_KEY', raising=False)
    monkeypatch.setenv('AIRTABLE_BASE_ID', 'some_base')
    result = main(['collect', '--sources', str(sources), '--out', str(output)])
    assert result == 1
    assert "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must both be set" in capsys.readouterr().err
    assert not output.exists()


def test_collect_exit_policy_success_and_failure(tmp_path, monkeypatch, capsys):
    _clear_airtable(monkeypatch)
    output = tmp_path / 'items.csv'

    # Create a sources file with one working and one failing/unknown format source
    sources = tmp_path / 'sources.csv'
    sources.write_text(
        'organization,name,url,format,default_kind,active,notes\n'
        'Org A,News A,https://example.com/feed1,rss,update,true,\n'
        'Org B,News B,https://example.com/feed2,unknown,update,true,\n',
        encoding='utf-8',
    )

    with patch('abundroid.item_pipeline.default_fetch', lambda url: RSS):
        result = main([
            'collect', '--sources', str(sources), '--out', str(output),
            '--topics', str(tmp_path / 'missing.csv'),
        ])
    assert result == 1  # exits 1 because one source fails
    assert output.exists()  # successful sources are still persisted

    # Totals summary is still printed
    captured = capsys.readouterr()
    assert 'News B: error' in captured.out
    assert 'News A: ok' in captured.out
    assert 'Totals:' in captured.out


def test_collect_saves_source_runs_to_csv(tmp_path, monkeypatch):
    _clear_airtable(monkeypatch)
    sources = _sources_file(tmp_path)
    output = tmp_path / 'items.csv'
    runs_file = tmp_path / 'source_runs.csv'

    with patch('abundroid.item_pipeline.default_fetch', lambda url: RSS):
        result = main([
            'collect', '--sources', str(sources), '--out', str(output),
            '--topics', str(tmp_path / 'missing.csv'),
        ])

    assert result == 0
    assert runs_file.exists()
    with open(runs_file, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]['source_name'] == 'News'
    assert rows[0]['result'] == 'success'


def test_collect_saves_source_runs_to_airtable(monkeypatch):
    monkeypatch.setenv('AIRTABLE_API_KEY', 'key')
    monkeypatch.setenv('AIRTABLE_BASE_ID', 'base')
    monkeypatch.setenv('AIRTABLE_ORGS_TABLE', 'Orgs')
    monkeypatch.setenv('AIRTABLE_SOURCES_TABLE', 'Sources')
    monkeypatch.setenv('AIRTABLE_ITEMS_TABLE', 'Items')
    monkeypatch.setenv('AIRTABLE_SOURCE_RUNS_TABLE', 'Runs')

    fake_api = FakeAirtableApi('key')

    # Setup mock active source in fake api
    orgs_table = fake_api.table('base', 'Orgs')
    orgs_table.records.append({
        "id": "org1",
        "fields": {
            "Name": "My Org",
            "Active": True,
            "Stage": "Approved",
        }
    })

    sources_table = fake_api.table('base', 'Sources')
    sources_table.create({
        "Name": "Airtable RSS",
        "URL": "https://example.com/rss",
        "Format": "rss",
        "Active": True,
        "Organization": ["org1"],
        "Organization Name": ["My Org"],
    })

    # Mock topics loading to be empty
    with patch('pyairtable.Api', return_value=fake_api), \
         patch('abundroid.item_pipeline.default_fetch', lambda url: RSS), \
         patch('abundroid.cli._load_airtable_topics', return_value=[]), \
         patch(
             'abundroid.stores.source_run_airtable_store.AirtableSourceRunStore.save_runs'
         ) as save_runs:
        result = main(['collect'])

    assert result == 0
    [runs] = save_runs.call_args.args
    assert len(runs) == 1
    assert runs[0].derive_health() == 'Working'
    assert runs[0].items_found == 1


def test_collect_reports_airtable_setup_errors_without_a_traceback(monkeypatch, capsys):
    monkeypatch.setenv('AIRTABLE_API_KEY', 'key')
    monkeypatch.setenv('AIRTABLE_BASE_ID', 'base')
    fake_api = FakeAirtableApi('key')

    with patch('pyairtable.Api', return_value=fake_api), \
         patch.object(fake_api.table('base', 'Organizations'), 'all',
                      side_effect=RuntimeError('table not found')):
        result = main(['collect'])

    assert result == 1
    assert 'Error loading collection configuration: table not found' in capsys.readouterr().err


def test_collect_fails_when_saving_runs_fails(tmp_path, monkeypatch, capsys):
    _clear_airtable(monkeypatch)
    sources = _sources_file(tmp_path)
    output = tmp_path / 'items.csv'

    # Mock save_runs to raise an exception
    from abundroid.stores.source_run_csv_store import SourceRunCsvStore
    with patch('abundroid.item_pipeline.default_fetch', lambda url: RSS), \
         patch.object(SourceRunCsvStore, 'save_runs', side_effect=Exception('Disk Full')):
        result = main([
            'collect', '--sources', str(sources), '--out', str(output),
            '--topics', str(tmp_path / 'missing.csv'),
        ])

    assert result == 1
    assert "Error saving source runs: Disk Full" in capsys.readouterr().err


def test_help_exposes_the_collect_command(capsys):
    assert main([]) == 0

    output = capsys.readouterr().out
    assert "{collect,setup}" in output
    assert "collect" in output


def test_module_is_runnable_via_python_dash_m():
    import subprocess
    import sys

    process = subprocess.run(
        [sys.executable, "-m", "abundroid.cli"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert process.returncode == 0
    assert "usage" in process.stdout.lower()
