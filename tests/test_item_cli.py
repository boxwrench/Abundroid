'''CLI tests for the unified Items collection path.'''

from unittest.mock import patch

from abundroid.cli import main


RSS = '''<?xml version='1.0'?>
<rss version='2.0'><channel><title>News</title><item>
<title>Housing reform update</title>
<guid>post-1</guid>
<link>https://example.com/posts/1</link>
<pubDate>Thu, 09 Jul 2026 17:00:00 GMT</pubDate>
<description>New zoning legislation.</description>
</item></channel></rss>'''


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
    assert '[update] Housing reform update' in capsys.readouterr().out
