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
