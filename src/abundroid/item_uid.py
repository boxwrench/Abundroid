'''Stable identity and source-content fingerprints for unified items.'''

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse

from abundroid.models import Item


def normalize_url(url: str) -> str:
    """Normalize a URL for stable identity while dropping tracking parameters."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.hostname.lower() if parsed.hostname else ""
    if parsed.port and not (
        (scheme == "http" and parsed.port == 80)
        or (scheme == "https" and parsed.port == 443)
    ):
        netloc += f":{parsed.port}"

    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else ""
    query = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {
        key: values[0] if values else ""
        for key, values in query.items()
        if not key.startswith("utm_") and key not in {"fbclid", "gclid"}
    }
    normalized = f"{scheme}://{netloc}{path}"
    sorted_query = urlencode(sorted(filtered.items()))
    return f"{normalized}?{sorted_query}" if sorted_query else normalized


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

    identity_date = item.published_at or item.scheduled_start
    date_value = identity_date.date().isoformat() if identity_date else ''
    identity = '|'.join(
        [
            _normalize_text(item.publisher),
            _normalize_text(item.title),
            date_value,
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
