'''Ingestion pipeline for published items.'''

from __future__ import annotations

from datetime import date, timedelta

from abundroid.adapters import rss
from abundroid.classifier import tag_items
from abundroid.item_dedupe import flag_possible_item_duplicates
from abundroid.item_uid import compute_item_uid, item_content_hash
from abundroid.fetch import default_fetch


ITEM_ADAPTERS = {'rss': rss.parse_items}


def run_item_pipeline(
    sources,
    item_store,
    *,
    fetch=None,
    adapters=None,
    topics=None,
    duplicate_lookback_days=90,
    clock=None,
    id_gen=None,
):
    '''Fetch active sources, enrich their items, and persist one batch.'''
    import uuid
    from datetime import datetime, timezone
    from abundroid.models import SourceRun

    fetch = fetch or default_fetch
    adapters = adapters or ITEM_ADAPTERS
    clock = clock or (lambda: datetime.now(timezone.utc))
    id_gen = id_gen or (lambda: str(uuid.uuid4()))

    summaries = []
    collected = []
    source_runs = []
    active_attempts = []

    for source in sources:
        if not source.active:
            continue

        run_id = id_gen()
        start_time = clock()

        summary = {
            'source': source.name or source.url,
            'organization': source.organization,
            'ok': False,
            'error': '',
            'items_found': 0,
        }
        summaries.append(summary)

        attempt = {
            'run_id': run_id,
            'source': source,
            'start_time': start_time,
            'finish_time': None,
            'result': 'failure',
            'items_found': 0,
            'http_status': None,
            'error': '',
        }
        active_attempts.append(attempt)

        adapter = adapters.get(source.format)
        if adapter is None:
            err_msg = f'unknown source format: {source.format}'
            summary['error'] = err_msg
            attempt['error'] = err_msg
            attempt['finish_time'] = clock()
            continue

        try:
            content = fetch(source.url)
            items = adapter(content, source)
            for item in items:
                item.uid = compute_item_uid(item)
                item.source_hash = item_content_hash(item)
            collected.extend(items)
            summary['items_found'] = len(items)
            summary['ok'] = True

            attempt['result'] = 'success'
            attempt['items_found'] = len(items)
            attempt['finish_time'] = clock()
        except Exception as exc:
            err_msg = str(exc)
            summary['error'] = err_msg
            attempt['error'] = err_msg
            attempt['finish_time'] = clock()
            response = getattr(exc, 'response', None)
            if response is not None and hasattr(response, 'status_code'):
                attempt['http_status'] = response.status_code
            elif hasattr(exc, 'status_code'):
                attempt['http_status'] = getattr(exc, 'status_code')
            elif hasattr(exc, 'code'):
                attempt['http_status'] = getattr(exc, 'code')

    if topics:
        tag_items(collected, topics)

    recent_since = date.today() - timedelta(days=duplicate_lookback_days)
    recent_items = getattr(item_store, 'recent_items', lambda since: [])(recent_since)
    duplicate_links = flag_possible_item_duplicates(collected, recent_items)
    result = item_store.upsert(collected)

    set_duplicates = getattr(item_store, 'set_possible_duplicates', None)
    if set_duplicates and duplicate_links:
        set_duplicates(duplicate_links)

    for attempt in active_attempts:
        source_run = SourceRun(
            run_id=attempt['run_id'],
            source_id=attempt['source'].record_id,
            source_name=attempt['source'].name,
            source_url=attempt['source'].url,
            start_time=attempt['start_time'],
            finish_time=attempt['finish_time'] or clock(),
            result=attempt['result'],
            items_found=attempt['items_found'],
            http_status=attempt['http_status'],
            error=attempt['error'],
        )
        source_runs.append(source_run)

    return {
        'sources': summaries,
        'items_found': len(collected),
        'new': result['new'],
        'seen': result['seen'],
        'source_runs': source_runs,
    }
