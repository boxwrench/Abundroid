from dataclasses import replace
from datetime import datetime, timezone

from abundroid.item_uid import compute_item_uid, item_content_hash
from abundroid.models import Item


def test_source_native_id_has_priority_over_other_identity_fields():
    item = Item(
        title='Original title',
        publisher='Publisher',
        source_item_id='post-42',
        canonical_url='https://example.com/original',
        source_url='https://example.com/feed?utm_source=email',
    )
    changed = replace(
        item,
        title='Changed title',
        canonical_url='https://example.com/moved',
        source_url='https://example.com/feed',
    )

    assert compute_item_uid(item).startswith('source:')
    assert compute_item_uid(item) == compute_item_uid(changed)


def test_source_native_ids_are_namespaced_by_source():
    first = Item(
        title='Post',
        publisher='Publisher',
        source_item_id='42',
        source_url='https://example.com/feed-a',
    )
    second = replace(first, source_url='https://example.com/feed-b')

    assert compute_item_uid(first) != compute_item_uid(second)


def test_canonical_url_is_normalized_when_source_id_is_missing():
    first = Item(
        title='Post',
        publisher='Publisher',
        canonical_url='HTTPS://EXAMPLE.COM/post/?utm_source=email#more',
    )
    second = replace(first, canonical_url='https://example.com/post')

    assert compute_item_uid(first) == compute_item_uid(second)
    assert compute_item_uid(first) == 'url:https://example.com/post'


def test_metadata_fallback_uses_publisher_title_date_and_source():
    published = datetime(2026, 7, 9, 10, 30, tzinfo=timezone.utc)
    first = Item(
        title='  A   New Post ',
        publisher='TEST PUBLISHER',
        published_at=published,
        source_url='https://example.com/feed',
    )
    second = replace(
        first,
        title='a new post',
        publisher=' test publisher ',
        published_at=datetime(2026, 7, 9, 23, 59, tzinfo=timezone.utc),
    )

    assert compute_item_uid(first).startswith('hash:')
    assert compute_item_uid(first) == compute_item_uid(second)
    assert compute_item_uid(first) != compute_item_uid(
        replace(second, source_url='https://other.example/feed')
    )


def test_event_fallback_uses_scheduled_date_when_publication_date_is_missing():
    first = Item(
        title='Weekly Meeting',
        publisher='Publisher',
        kind='event',
        scheduled_start=datetime(2026, 8, 1, 10, 0),
        source_url='https://example.com/calendar',
    )

    assert compute_item_uid(first) != compute_item_uid(
        replace(first, scheduled_start=datetime(2026, 8, 8, 10, 0))
    )


def test_content_hash_ignores_editorial_and_bookkeeping_fields():
    item = Item(
        title='Post',
        publisher='Publisher',
        summary='Source summary',
        topics=['Housing'],
        status='Needs Review',
    )
    edited = replace(
        item,
        topics=['Transit'],
        status='Approved',
        reviewer_notes='Checked by an editor',
        changed=True,
        possible_duplicate_of='other-item',
    )

    assert item_content_hash(item) == item_content_hash(edited)
    assert item_content_hash(item) != item_content_hash(
        replace(item, summary='Updated at the source')
    )
