from abundroid.models import Item, Source


def test_source_defaults_support_a_simple_operator_configuration():
    source = Source(
        organization='Test Publisher',
        name='Newsroom',
        url='https://example.com/feed.xml',
        format='rss',
    )

    assert source.default_kind == 'other'
    assert source.active is True
    assert source.notes == ''


def test_item_defaults_start_in_review_without_shared_topic_lists():
    first = Item(title='First', publisher='Publisher')
    second = Item(title='Second', publisher='Publisher')

    first.topics.append('Housing')

    assert first.status == 'Needs Review'
    assert first.kind == 'other'
    assert first.changed is False
    assert second.topics == []
