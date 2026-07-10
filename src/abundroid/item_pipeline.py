'''Ingestion pipeline for published items.'''

from __future__ import annotations

from datetime import date, timedelta

from abundroid.adapters import rss
from abundroid.classifier import tag_items
from abundroid.item_dedupe import flag_possible_item_duplicates
from abundroid.item_uid import compute_item_uid, item_content_hash
from abundroid.pipeline import default_fetch


ITEM_ADAPTERS = {'rss': rss.parse_items}


def run_item_pipeline(
    sources,
    item_store,
    *,
    fetch=None,
    adapters=None,
    topics=None,
    duplicate_lookback_days=90,
):
    '''Fetch active sources, enrich their items, and persist one batch.'''
    fetch = fetch or default_fetch
    adapters = adapters or ITEM_ADAPTERS
    summaries = []
    collected = []

    for source in sources:
        if not source.active:
            continue

        summary = {
            'source': source.name or source.url,
            'organization': source.organization,
            'ok': False,
            'error': '',
            'items_found': 0,
        }
        summaries.append(summary)

        adapter = adapters.get(source.format)
        if adapter is None:
            summary['error'] = f'unknown source format: {source.format}'
            continue

        try:
            items = adapter(fetch(source.url), source)
            for item in items:
                item.uid = compute_item_uid(item)
                item.source_hash = item_content_hash(item)
            collected.extend(items)
            summary['items_found'] = len(items)
            summary['ok'] = True
        except Exception as exc:
            summary['error'] = str(exc)

    if topics:
        tag_items(collected, topics)

    recent_since = date.today() - timedelta(days=duplicate_lookback_days)
    recent_items = getattr(item_store, 'recent_items', lambda since: [])(recent_since)
    duplicate_links = flag_possible_item_duplicates(collected, recent_items)
    result = item_store.upsert(collected)

    set_duplicates = getattr(item_store, 'set_possible_duplicates', None)
    if set_duplicates and duplicate_links:
        set_duplicates(duplicate_links)

    return {
        'sources': summaries,
        'items_found': len(collected),
        'new': result['new'],
        'seen': result['seen'],
    }
