'''Safety tests for Airtable Source administration.'''

from abundroid.stores.item_airtable_store import load_sources


class Table:
    def __init__(self, records):
        self.records = records

    def all(self):
        return list(self.records)


def source_record(organization=None):
    fields = {
        'Name': 'News',
        'URL': 'https://example.com/feed',
        'Format': 'rss',
        'Default Kind': 'article',
        'Active': True,
    }
    if organization is not None:
        fields['Organization'] = [organization]
    return {'id': 'src1', 'fields': fields}


def test_unlinked_source_is_inactive():
    loaded = load_sources(Table([source_record()]), Table([]))

    assert len(loaded) == 1
    assert loaded[0].active is False


def test_source_linked_to_deleted_organization_is_inactive():
    loaded = load_sources(Table([source_record('rec-deleted')]), Table([]))

    assert len(loaded) == 1
    assert loaded[0].active is False
