'''Stable identity and source-content fingerprints for unified items.'''

from __future__ import annotations

import hashlib
import re

from abundroid.models import Item
from abundroid.uid import normalize_url


def _normalize_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip().lower())


def _normalize_url_safely(value: str) -> str:
    value = value.strip()
    if not value:
        return ''
    try:
        return normalize_url(value)
    except ValueError:
        # A malformed port should not prevent ingestion. The raw value still
        # gives the item a deterministic identity for later review.
        return value


def compute_item_uid(item: Item) -> str:
    '''Compute item identity using source ID, canonical URL, then metadata.'''
    if item.source_item_id.strip():
        identity = f'{_normalize_url_safely(item.source_url)}|{item.source_item_id.strip()}'
        digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
        return f'source:{digest}'

    if item.canonical_url.strip():
        return f'url:{_normalize_url_safely(item.canonical_url)}'

    published_date = item.published_at.date().isoformat() if item.published_at else ''
    identity = '|'.join(
        [
            _normalize_text(item.publisher),
            _normalize_text(item.title),
            published_date,
            _normalize_url_safely(item.source_url),
        ]
    )
    digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return f'hash:{digest}'


def item_content_hash(item: Item) -> str:
    '''Fingerprint source-provided fields without hashing editorial state.'''
    parts = [
        item.title,
        item.publisher,
        item.kind,
        item.source_item_id,
        item.canonical_url,
        item.source_url,
        item.published_at.isoformat() if item.published_at else '',
        item.author,
        item.summary,
        item.scheduled_start.isoformat() if item.scheduled_start else '',
        item.scheduled_end.isoformat() if item.scheduled_end else '',
        item.location,
    ]
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]
