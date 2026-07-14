'''Tests for the unified published-items pipeline.'''

from abundroid.item_pipeline import run_item_pipeline
from abundroid.models import Item, Source, Topic


class RecordingStore:
    def __init__(self, existing=()):
        self.existing = list(existing)
        self.upserts = []
        self.duplicate_mapping = {}

    def recent_items(self, since=None):
        return list(self.existing)

    def upsert(self, items):
        self.upserts.append(list(items))
        return {'new': len(items), 'seen': 0}

    def set_possible_duplicates(self, mapping):
        self.duplicate_mapping = dict(mapping)
        return len(mapping)


def source(name='News'):
    return Source(
        organization='Example Org',
        name=name,
        url='https://example.com/feed',
        format='rss',
        default_kind='article',
    )


def test_pipeline_batches_sources_and_tags_items():
    store = RecordingStore()
    sources = [source('News'), source('Updates')]

    def parse(text, configured_source):
        return [
            Item(
                title='Housing reform update',
                publisher=configured_source.organization,
                source_url=configured_source.url,
            )
        ]

    result = run_item_pipeline(
        sources,
        store,
        fetch=lambda url: 'feed',
        adapters={'rss': parse},
        topics=[Topic(name='Housing', keywords=['housing'])],
    )

    assert len(store.upserts) == 1
    assert len(store.upserts[0]) == 2
    assert store.upserts[0][0].topics == ['Housing']
    assert store.upserts[0][0].uid
    assert store.upserts[0][0].source_hash
    assert result['new'] == 2


def test_pipeline_isolates_broken_source():
    store = RecordingStore()

    def fetch(url):
        if 'broken' in url:
            raise ValueError('network failed')
        return 'feed'

    sources = [
        source(),
        Source('Other Org', 'Broken', 'https://broken.test/feed', 'rss'),
    ]
    result = run_item_pipeline(
        sources,
        store,
        fetch=fetch,
        adapters={'rss': lambda text, src: [Item('A post', src.organization)]},
    )

    assert result['items_found'] == 1
    assert result['sources'][0]['ok'] is True
    assert result['sources'][1]['ok'] is False
    assert result['sources'][1]['error'] == 'network failed'


def test_pipeline_flags_duplicate_from_earlier_run_on_both_records():
    existing = Item('Shared announcement', 'Another Org', uid='existing')
    store = RecordingStore([existing])

    result = run_item_pipeline(
        [source()],
        store,
        fetch=lambda url: 'feed',
        adapters={
            'rss': lambda text, src: [
                Item('Shared announcement', src.organization, source_url=src.url)
            ]
        },
    )

    new_uid = store.upserts[0][0].uid
    assert result['new'] == 1
    assert store.duplicate_mapping == {
        new_uid: 'existing',
        'existing': new_uid,
    }


def test_pipeline_produces_source_runs_with_injections():
    from datetime import datetime, timezone
    store = RecordingStore()
    sources = [
        Source("Org A", "Active RSS", "https://example.com/rss", "rss", active=True, record_id="recSrcActive"),
        Source("Org B", "Inactive RSS", "https://example.com/rss2", "rss", active=False, record_id="recSrcInactive"),
        Source("Org C", "Broken format", "https://example.com/unknown", "unknown", active=True, record_id="recSrcBroken"),
    ]

    mock_time = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    clock = lambda: mock_time
    id_gen = lambda: "deterministic-run-id"

    result = run_item_pipeline(
        sources,
        store,
        fetch=lambda url: "feed",
        adapters={"rss": lambda text, src: [Item("Post", src.organization)]},
        clock=clock,
        id_gen=id_gen,
    )

    # We expect 2 SourceRun objects: active RSS (success) and broken format (failure)
    # Inactive RSS must not have a run.
    runs = result["source_runs"]
    assert len(runs) == 2

    # Active RSS run check
    run_success = [r for r in runs if r.source_id == "recSrcActive"][0]
    assert run_success.run_id == "deterministic-run-id"
    assert run_success.result == "success"
    assert run_success.items_found == 1
    assert run_success.start_time == mock_time
    assert run_success.finish_time == mock_time
    # Broken format run check
    run_broken = [r for r in runs if r.source_id == "recSrcBroken"][0]
    assert run_broken.result == "failure"
    assert "unknown source format: unknown" in run_broken.error
